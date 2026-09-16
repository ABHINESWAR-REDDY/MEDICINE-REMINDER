"""OCR Engine Abstraction Module with Provider Architecture.

Primary canonical engine: Tesseract OCR + PyMuPDF (Docker / Linux).
Handwriting engine: TrOCR / HTR Provider.
Region detector engine: Faster R-CNN MobileNetV3.
Development fallback: Windows Native OCR (winocr) on Windows platforms.
"""

import io
import os
import shutil
import sys
from typing import List, Optional, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError

from app.core.logging import logger
from app.services.ocr.provider import (
    OCREngineError,
    PDFProcessingError,
    BaseOCRProvider,
    TesseractProvider,
    HandwritingOCRProvider,
    PrescriptionDetectorProvider,
    CompositeOCRProvider,
)


class OCREngine:
    """Production-oriented OCR Engine supporting PNG, JPEG, and PDF documents with modular providers."""

    def __init__(self, mode: str = "auto"):
        self.mode = mode
        self.tesseract_provider = TesseractProvider()
        self.handwriting_provider = HandwritingOCRProvider()
        self.detector_provider = PrescriptionDetectorProvider()
        self.composite_provider = CompositeOCRProvider(
            tesseract_provider=self.tesseract_provider,
            handwriting_provider=self.handwriting_provider,
            detector_provider=self.detector_provider,
        )

    @property
    def _tesseract_available(self) -> bool:
        return self.tesseract_provider.is_available()

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Apply contrast and sharpening enhancements to improve OCR accuracy."""
        logger.info("OCR image preprocessing started (mode=%s, size=%dx%d)", image.mode, image.width, image.height)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        gray = image.convert("L")
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        return sharpened

    def extract_text_from_image_bytes(self, image_bytes: bytes, mode: Optional[str] = None) -> str:
        """Process image file bytes and perform OCR."""
        target_mode = mode or self.mode
        return self.composite_provider.extract_text(image_bytes, "image/png", mode=target_mode)

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Process PDF file bytes via PyMuPDF by rendering pages and running OCR."""
        return self.tesseract_provider.extract_text(pdf_bytes, "application/pdf")

    def extract_text(self, file_bytes: bytes, content_type: str, mode: Optional[str] = None) -> str:
        """Route to appropriate extraction method based on content type."""
        target_mode = mode or self.mode
        return self.composite_provider.extract_text(file_bytes, content_type, mode=target_mode)

    def process_prescription_document(self, file_bytes: bytes, content_type: str) -> Dict[str, Any]:
        """Execute multi-stage document pipeline."""
        return self.composite_provider.process_prescription_document(file_bytes, content_type)
