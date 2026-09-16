"""OCR Model Manager and Lifecycle Controller for PillSync Backend.

Maintains singleton in-memory instances of:
- Faster R-CNN Prescription Medicine Detector
- Fine-Tuned RxHandBD TrOCR Handwriting Recognition Engine
- Comprehensive Timing & Technical Telemetry Instrumentation
"""

import os
import sys
import json
import time
import torch
from typing import Dict, Any, Optional, Tuple
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.logging import logger


class OCRModelManager:
    """Singleton model lifecycle manager holding detector and TrOCR in memory."""

    _instance: Optional["OCRModelManager"] = None

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.device_str = "CUDA" if torch.cuda.is_available() else "CPU"
        
        self.detector = None
        self.detector_ready = False
        self.detector_device = self.device_str
        
        self.trocr_processor = None
        self.trocr_model = None
        self.trocr_ready = False
        self.trocr_device = self.device_str
        self.trocr_checkpoint_info = {}

        self._initialize_models()

    @classmethod
    def get_instance(cls) -> "OCRModelManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_models(self):
        """Load detector and fine-tuned TrOCR once into application memory."""
        logger.info("==================================================")
        logger.info("Initializing PillSync OCR Model Manager")
        logger.info("System Device:            %s", self.device_str)
        
        # 1. Initialize Detector
        detector_path = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "artifacts", "detector", "best_model.pth")
        if os.path.exists(detector_path):
            try:
                from ml.prescription_ocr.src.detector.inference import PrescriptionRegionDetector
                t0 = time.time()
                self.detector = PrescriptionRegionDetector(
                    checkpoint_path=detector_path,
                    default_confidence=0.40,
                    nms_iou_threshold=0.35,
                    device_str=str(self.device),
                )
                self.detector_ready = True
                dt = round((time.time() - t0) * 1000, 2)
                logger.info("Detector Device:          %s (Loaded in %.1f ms)", self.detector_device, dt)
            except Exception as e:
                logger.warning("Detector initialization failed: %s", str(e))
                self.detector_ready = False
        else:
            logger.warning("Detector checkpoint not found at %s", detector_path)

        # 2. Initialize Fine-Tuned TrOCR (Prioritize production/ directory)
        prod_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "models", "production")
        default_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "models")
        model_dir = prod_dir if os.path.exists(os.path.join(prod_dir, "config.json")) else default_dir

        summary_path = os.path.join(model_dir, "training_summary.json")
        config_path = os.path.join(model_dir, "config.json")
        weights_path = os.path.join(model_dir, "model.safetensors")

        is_valid_checkpoint = os.path.exists(config_path) and os.path.exists(weights_path)

        if is_valid_checkpoint:
            try:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                t0 = time.time()
                self.trocr_processor = TrOCRProcessor.from_pretrained(model_dir)
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(self.device)
                self.trocr_model.eval()
                self.trocr_ready = True
                dt = round((time.time() - t0) * 1000, 2)

                if os.path.exists(summary_path):
                    with open(summary_path, "r", encoding="utf-8") as f:
                        self.trocr_checkpoint_info = json.load(f)

                logger.info("Provider:                 TrOCR")
                logger.info("Model:                    trocr-small-handwritten")
                logger.info("Checkpoint:               %s", model_dir)
                logger.info("Device:                   %s", self.trocr_device)
                logger.info("CUDA available:           %s", str(torch.cuda.is_available()).lower())
                logger.info("Model loaded:             true")
            except Exception as e:
                logger.warning("TrOCR fine-tuned model loading exception: %s", str(e))
                self.trocr_ready = False
        else:
            logger.info("Provider:                 TrOCR")
            logger.info("Model:                    trocr-small-handwritten")
            logger.info("Checkpoint:               %s", model_dir)
            logger.info("Device:                   %s", self.trocr_device)
            logger.info("CUDA available:           %s", str(torch.cuda.is_available()).lower())
            logger.info("Model loaded:             false (using baseline engine)")
            self.trocr_ready = False

        logger.info("==================================================")


    def reload_trocr_if_updated(self):
        """Check and reload TrOCR if newly trained weights became available."""
        model_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "models")
        summary_path = os.path.join(model_dir, "training_summary.json")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
                # Check if it is a completed full run
                if summary.get("status") == "COMPLETED" and not summary.get("smoke_test", False):
                    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                    self.trocr_processor = TrOCRProcessor.from_pretrained(model_dir)
                    self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(self.device)
                    self.trocr_model.eval()
                    self.trocr_ready = True
                    self.trocr_checkpoint_info = summary
                    logger.info("Successfully reloaded fine-tuned TrOCR model: %s", summary.get("model_id"))
            except Exception as e:
                logger.warning("Could not reload updated TrOCR: %s", str(e))
