"""API router for OCR Prescription Extraction and Confirmation."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.api.deps import require_patient
from app.core.database import get_db
from app.core.logging import logger
from app.models.user import User
from app.models.medicine_reference import MedicineReference
from app.schemas.ocr import (
    OCRExtractionResponse,
    OCRConfirmationRequest,
    OCRConfirmationResponse,
    OCRJobCreatedResponse,
    OCRJobStatusResponse,
    OCRJobErrorSchema,
)
from app.schemas.prescription import PrescriptionCreate
from app.schemas.medicine import MedicineCreate
from app.schemas.schedule import ScheduleCreate
from app.services.ocr.service import OCRPrescriptionService, FileValidationError
from app.services.ocr.job_service import OCRJobService
from app.services.ocr.engine import OCREngineError, PDFProcessingError
from app.services.prescription_service import PrescriptionService
from app.services.medicine_service import MedicineService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/ocr", tags=["OCR Prescriptions"])


@router.post(
    "/prescription",
    response_model=OCRJobCreatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and queue a prescription image or PDF for asynchronous OCR scanning",
)
async def scan_prescription(
    file: UploadFile = File(...),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """
    Secure patient endpoint to upload and queue a prescription for asynchronous OCR processing.
    - Validates file size (max 10 MB), extension, and magic byte signature.
    - Immediately returns a unique job_id and 'queued' status.
    - Progress and final results are polled via GET /api/v1/ocr/prescription/{job_id}.
    """
    logger.info(
        "User %s [role=%s] submitted prescription upload: %s (content_type=%s)",
        current_user.id,
        current_user.role,
        file.filename,
        file.content_type,
    )

    try:
        file_bytes = await file.read()
        filename = file.filename or "uploaded_document"
        content_type = file.content_type or "application/octet-stream"

        job_service = OCRJobService(db)
        job = job_service.create_job(
            user_id=current_user.id,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

        return OCRJobCreatedResponse(
            job_id=job.id,
            status=job.status,
            message="Prescription upload received and queued for processing.",
        )

    except FileValidationError as fve:
        logger.warning("File validation rejected upload for user %s: %s", current_user.id, fve.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": fve.code, "message": fve.message},
        )
    except Exception as e:
        logger.error("Unexpected error queueing OCR job: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "OCR_ENGINE_FAILURE", "message": "Failed to queue prescription for OCR scanning."},
        )
    finally:
        await file.close()


@router.get(
    "/prescription/{job_id}",
    response_model=OCRJobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll status and results of an asynchronous prescription OCR job",
)
def get_prescription_job_status(
    job_id: str,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """
    Poll the status of an active OCR job.
    Statuses: 'queued' -> 'processing' -> 'completed' / 'failed'.
    Strictly authorized to the user who uploaded the prescription.
    """
    job_service = OCRJobService(db)
    job = job_service.get_job(job_id=job_id, user_id=current_user.id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"OCR Job '{job_id}' was not found."},
        )

    result_data = None
    if job.status == "completed" and job.result_json:
        try:
            import json
            result_data = json.loads(job.result_json)
        except Exception:
            result_data = None

    error_data = None
    if job.status == "failed":
        error_data = OCRJobErrorSchema(
            code=job.error_code or "OCR_ENGINE_FAILURE",
            message=job.error_message or "Prescription processing failed.",
        )

    return OCRJobStatusResponse(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        progress_message=job.progress_message,
        result=result_data,
        error=error_data,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )




@router.post(
    "/confirm",
    response_model=OCRConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm and save reviewed OCR prescription into patient medication records",
)
def confirm_ocr_prescription(
    payload: OCRConfirmationRequest,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """
    Save user-reviewed prescription, medicine, and schedule.
    - Reuses existing Phase 2 Prescription, Medicine, and Schedule services.
    - Records strictly belong to current_user.id.
    """
    logger.info("Confirming OCR prescription for user: %s", current_user.id)

    created_prescription_id: Optional[int] = None
    created_medicine_id: Optional[int] = None
    created_schedule_id: Optional[int] = None

    try:
        # 1. Optionally create Prescription record
        if payload.create_prescription or payload.prescription_number or payload.doctor_name:
            prescription_service = PrescriptionService(db)
            prescription_data = PrescriptionCreate(
                prescription_number=payload.prescription_number,
                doctor_name=payload.doctor_name,
                issue_date=payload.issue_date,
                expiry_date=payload.expiry_date,
                notes=payload.notes,
            )
            prescription = prescription_service.create_prescription(
                current_user=current_user,
                data=prescription_data,
            )
            created_prescription_id = prescription.id

        # 2. Create Medicine record (belongs to current_user.id)
        medicine_service = MedicineService(db)
        medicine_data = MedicineCreate(
            name=payload.name,
            dosage_amount=payload.dosage_amount,
            dosage_unit=payload.dosage_unit,
            quantity=payload.quantity,
            medicine_form=payload.medicine_form,
            instructions=payload.instructions,
            start_date=payload.start_date,
            end_date=payload.end_date,
            prescription_id=created_prescription_id,
            condition_id=payload.condition_id,
        )
        medicine = medicine_service.create_medicine(
            current_user=current_user,
            data=medicine_data,
        )
        created_medicine_id = medicine.id

        # 3. Optionally create MedicationSchedule record
        if payload.create_schedule and payload.scheduled_times:
            schedule_service = ScheduleService(db)
            schedule_data = ScheduleCreate(
                medicine_id=medicine.id,
                frequency_type=payload.frequency_type,
                times_per_day=len(payload.scheduled_times),
                scheduled_times=payload.scheduled_times,
                dose_quantity=payload.dose_quantity,
                start_date=payload.start_date,
                end_date=payload.end_date,
            )
            schedule = schedule_service.create_schedule(
                current_user=current_user,
                medicine_id=medicine.id,
                data=schedule_data,
            )
            created_schedule_id = schedule.id

        return OCRConfirmationResponse(
            success=True,
            prescription_id=created_prescription_id,
            medicine_id=created_medicine_id,
            schedule_id=created_schedule_id,
            message="Medication, prescription, and schedule successfully saved.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error confirming OCR prescription: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save medication: {str(e)}",
        )


@router.get(
    "/reference-medicines",
    status_code=status.HTTP_200_OK,
    summary="Search global medicine reference database for autocomplete",
)
def search_reference_medicines(
    query: str = Query(..., min_length=2, max_length=100),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    """Search unique medicine reference names and their forms/strengths."""
    search_term = f"%{query.strip().lower()}%"
    results = (
        db.query(MedicineReference)
        .filter(MedicineReference.normalized_name.like(search_term) | MedicineReference.name.ilike(search_term))
        .limit(20)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "dosage_form": r.dosage_form,
            "strength": r.strength,
            "manufacturer": r.manufacturer,
            "frequency": r.frequency,
        }
        for r in results
    ]
