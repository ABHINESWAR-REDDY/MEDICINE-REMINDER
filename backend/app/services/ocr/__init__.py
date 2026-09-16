"""OCR Service Package Initialization."""

from app.services.ocr.service import OCRPrescriptionService
from app.services.ocr.engine import OCREngine
from app.services.ocr.provider import (
    BaseOCRProvider,
    TesseractProvider,
    HandwritingOCRProvider,
    CompositeOCRProvider,
)
from app.services.ocr.preprocessor import OCRTextPreprocessor
from app.services.ocr.matcher import MedicineMatcher
from app.services.ocr.extractor import PrescriptionFieldExtractor

__all__ = [
    "OCRPrescriptionService",
    "OCREngine",
    "BaseOCRProvider",
    "TesseractProvider",
    "HandwritingOCRProvider",
    "CompositeOCRProvider",
    "OCRTextPreprocessor",
    "MedicineMatcher",
    "PrescriptionFieldExtractor",
]
