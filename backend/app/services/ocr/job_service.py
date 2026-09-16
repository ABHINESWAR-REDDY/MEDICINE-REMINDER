"""Asynchronous OCR Job Service and Background Worker for Prescription Scanning."""

import json
import os
import time
import uuid
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging import logger
from app.models.ocr_job import OCRJob
from app.services.ocr.service import OCRPrescriptionService, FileValidationError
from app.services.ocr.engine import OCREngineError, PDFProcessingError
from app.services.ocr.model_manager import OCRModelManager

# Global concurrency limiter for local CPU processing (maximum 1 active job at a time)
_JOB_SEMAPHORE = threading.Semaphore(1)


class OCRJobService:
    """Manages creation, execution, and polling of asynchronous OCR prescription jobs."""

    def __init__(self, db: Session):
        self.db = db
        self.ocr_service = OCRPrescriptionService(db)

    def create_job(
        self,
        user_id: int,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> OCRJob:
        """
        Validate file, create database job record in queued state, and trigger background worker.
        """
        t_start = time.time()
        
        # 1. Immediate File Validation
        canonical_type = self.ocr_service._validate_file(file_bytes, filename, content_type)
        t_val = round((time.time() - t_start) * 1000, 2)
        logger.info("OCR_STAGE file_validation duration_ms=%.1f", t_val)

        # 2. Create Persistent OCRJob Record
        job_id = str(uuid.uuid4())
        job = OCRJob(
            id=job_id,
            user_id=user_id,
            status="queued",
            stage="uploading",
            progress_message="Uploading prescription...",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info("OCR job created (job_id=%s, user_id=%s, canonical_type=%s)", job_id, user_id, canonical_type)

        # 4. Dispatch Asynchronous Background Worker Thread
        db_bind = self.db.get_bind() if self.db else None
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self._execute_job_worker(job_id, file_bytes, filename, canonical_type, db_bind)
        else:
            thread = threading.Thread(
                target=self._execute_job_worker,
                args=(job_id, file_bytes, filename, canonical_type, db_bind),
                daemon=True,
            )
            thread.start()

        return job

    def get_job(self, job_id: str, user_id: int) -> Optional[OCRJob]:
        """Fetch OCRJob ensuring strict user-level authorization and fresh state."""
        self.db.expire_all()
        return (
            self.db.query(OCRJob)
            .filter(OCRJob.id == job_id, OCRJob.user_id == user_id)
            .first()
        )

    @classmethod
    def _execute_job_worker(
        cls,
        job_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        bind: Any = None,
    ):
        """Worker thread executing the multi-stage OCR pipeline under a controlled semaphore."""
        with _JOB_SEMAPHORE:
            db = Session(bind=bind) if bind is not None else SessionLocal()
            t_total_start = time.time()
            try:
                job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
                if not job:
                    logger.error("Job %s not found in worker thread", job_id)
                    return

                job.status = "processing"
                job.stage = "analyzing"
                job.progress_message = "Analyzing prescription..."
                job.started_at = datetime.now(timezone.utc)
                db.commit()

                logger.info("OCR_STAGE processing started (job_id=%s)", job_id)

                service = OCRPrescriptionService(db)
                
                # Check for TrOCR readiness
                mm = OCRModelManager.get_instance()
                mm.reload_trocr_if_updated()
                
                # Step update: Detecting medicine regions
                job.stage = "detecting_regions"
                job.progress_message = "Detecting medicine regions..."
                db.commit()

                t_pipe_start = time.time()
                result = service.process_prescription_file(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=content_type,
                )
                t_pipe_duration = round((time.time() - t_pipe_start) * 1000, 2)
                t_total_duration = round((time.time() - t_total_start) * 1000, 2)

                logger.info("OCR_STAGE pipeline duration_ms=%.1f", t_pipe_duration)
                logger.info("OCR_STAGE total duration_ms=%.1f", t_total_duration)

                # Persist completed result
                job.status = "completed"
                job.stage = "completed"
                job.progress_message = "Extraction complete"
                job.completed_at = datetime.now(timezone.utc)
                job.result_json = json.dumps(result)
                db.commit()

                logger.info("OCR job completed successfully (job_id=%s, total_ms=%.1f)", job_id, t_total_duration)

            except FileValidationError as fve:
                logger.warning("Job %s failed with file validation error: %s", job_id, fve.message)
                cls._mark_job_failed(db, job_id, fve.code, fve.message)
            except PDFProcessingError as ppe:
                logger.warning("Job %s failed with PDF processing error: %s", job_id, ppe.message)
                cls._mark_job_failed(db, job_id, ppe.code, ppe.message)
            except OCREngineError as oee:
                logger.error("Job %s failed with OCR engine error: %s", job_id, oee.message)
                cls._mark_job_failed(db, job_id, oee.code, oee.message)
            except Exception as e:
                logger.error("Job %s unexpected exception: %s", job_id, str(e), exc_info=True)
                cls._mark_job_failed(db, job_id, "OCR_ENGINE_FAILURE", "The OCR engine could not process this prescription.")
            finally:
                db.close()

    @staticmethod
    def _mark_job_failed(db: Session, job_id: str, code: str, message: str):
        try:
            job = db.query(OCRJob).filter(OCRJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.stage = "failed"
                job.progress_message = message
                job.error_code = code
                job.error_message = message
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as e:
            logger.error("Could not record job failure in db: %s", str(e))
