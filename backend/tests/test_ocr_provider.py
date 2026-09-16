"""Unit tests for OCR Provider Architecture and Fallback Mechanisms."""

import io
import pytest
from PIL import Image

from app.services.ocr.provider import (
    BaseOCRProvider,
    TesseractProvider,
    HandwritingOCRProvider,
    CompositeOCRProvider,
)
from app.services.ocr.engine import OCREngine
from app.services.ocr.matcher import MedicineMatcher


class MockOCRProvider(BaseOCRProvider):
    def __init__(self, name: str, return_text: str = "", available: bool = True):
        self._name = name
        self._text = return_text
        self._available = available

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    def extract_text(self, file_bytes: bytes, content_type: str) -> str:
        return self._text


def test_composite_provider_routing_and_fallback():
    """Verify CompositeOCRProvider delegates to primary engine and falls back as required."""
    mock_tesseract = MockOCRProvider("tesseract", return_text="Rx Amoxicillin 500mg")
    mock_handwriting = MockOCRProvider("handwriting_trocr", return_text="Amoxicillin")

    composite = CompositeOCRProvider(
        tesseract_provider=mock_tesseract,
        handwriting_provider=mock_handwriting,
    )

    dummy_bytes = b"dummy_image_bytes"

    # 1. Auto mode returns Tesseract if it has text
    assert composite.extract_text(dummy_bytes, "image/png", mode="auto") == "Rx Amoxicillin 500mg"

    # 2. Handwriting mode returns handwriting text
    assert composite.extract_text(dummy_bytes, "image/png", mode="handwriting") == "Amoxicillin"

    # 3. Fallback when Tesseract is empty in auto mode
    empty_tesseract = MockOCRProvider("tesseract", return_text="")
    composite_fallback = CompositeOCRProvider(
        tesseract_provider=empty_tesseract,
        handwriting_provider=mock_handwriting,
    )
    assert composite_fallback.extract_text(dummy_bytes, "image/png", mode="auto") == "Amoxicillin"


def test_handwriting_to_medicine_reference_matching(db_session):
    """Verify handwriting transcription text seamlessly normalizes against medicine_reference table."""
    from app.models.medicine_reference import MedicineReference

    ref = MedicineReference(
        name="Amoxicillin",
        normalized_name="amoxicillin",
        category="Antibiotic",
        dosage_form="Tablet",
        strength="500 mg",
        frequency="Twice Daily",
    )
    db_session.add(ref)
    db_session.commit()

    matcher = MedicineMatcher(db_session)

    # Simulated handwriting OCR output with common transcription typo: 'Amoxicilin'
    htr_output = "Amoxicilin"
    match_res = matcher.find_best_match(htr_output)

    assert match_res is not None
    # Matches reference database entry 'Amoxicillin' with high fuzzy score
    assert "amoxicillin" in match_res["matched_name"].lower()
    assert match_res["confidence"] >= 0.85
