"""Unit and integration tests for Phase 3 Stage 3 Conditional TrOCR & Multi-Stage OCR pipeline."""

import os
import sys
import io
import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.ocr.service import OCRPrescriptionService
from app.services.ocr.provider import (
    PrescriptionDetectorProvider,
    HandwritingOCRProvider,
    CompositeOCRProvider,
)
from app.services.ocr.extractor import PrescriptionFieldExtractor
from app.services.ocr.matcher import MedicineMatcher
from app.schemas.ocr import OCRExtractionResponse
from app.models.medicine_reference import MedicineReference
from ml.prescription_ocr.src.detector.utils import expand_box_with_margin, sort_boxes_reading_order


@pytest.fixture
def seed_references(db_session):
    """Seed test database with reference medicines."""
    sample_data = [
        ("Amoxicillin", "amoxicillin", "Antibiotic", "Tablet", "500 mg", "Twice Daily"),
        ("Paracetamol", "paracetamol", "Analgesic", "Tablet", "500 mg", "As Needed"),
        ("Napa", "napa", "Analgesic", "Tablet", "500 mg", "Three Times Daily"),
    ]
    for name, norm_name, cat, form, strength, freq in sample_data:
        ref = MedicineReference(
            name=name,
            normalized_name=norm_name,
            category=cat,
            dosage_form=form,
            strength=strength,
            frequency=freq,
        )
        db_session.add(ref)
    db_session.commit()


@pytest.fixture
def dummy_prescription_image():
    """Create a dummy 800x1000 prescription image with synthetic text."""
    img = Image.new("RGB", (800, 1000), color="white")
    draw = ImageDraw.Draw(img)
    # Header
    draw.text((50, 40), "Dr. Sarah Johnson, MD", fill="black")
    draw.text((50, 70), "Date: 12/05/2026", fill="black")
    draw.text((50, 100), "Prescription No: RX-2026-9812", fill="black")
    # Medicine line 1
    draw.text((100, 250), "Rx: Amoxicillin 500mg", fill="black")
    draw.text((100, 280), "Take 1 tablet daily for 7 days", fill="black")
    # Medicine line 2
    draw.text((100, 450), "Rx: Paracetamol 500mg", fill="black")

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_crop_margin_and_coordinate_clamping():
    """Verify adaptive 8% crop margin computation on image boundaries."""
    box = (100, 200, 300, 400)
    cx1, cy1, cx2, cy2 = expand_box_with_margin(box, img_w=800, img_h=1000, margin_ratio=0.08)
    assert cx1 == 84
    assert cy1 == 184
    assert cx2 == 316
    assert cy2 == 416

    edge_box = (5, 5, 100, 100)
    cx1, cy1, cx2, cy2 = expand_box_with_margin(edge_box, img_w=800, img_h=1000, margin_ratio=0.08)
    assert cx1 == 0
    assert cy1 == 0
    assert cx2 <= 800
    assert cy2 <= 1000


def test_reading_order_sorting():
    """Verify top-to-bottom and left-to-right reading order sorting."""
    boxes = [
        (100, 500, 300, 550),
        (100, 200, 300, 250),
        (350, 205, 550, 255),
    ]
    scores = [0.8, 0.9, 0.85]

    sorted_boxes, sorted_scores = sort_boxes_reading_order(boxes, scores, y_threshold=20.0)

    assert sorted_boxes[0] == (100, 200, 300, 250)
    assert sorted_boxes[1] == (350, 205, 550, 255)
    assert sorted_boxes[2] == (100, 500, 300, 550)


def test_raw_ocr_preservation_and_candidate_separation(db_session, seed_references):
    """Ensure raw OCR text is stored verbatim and not overwritten by candidate normalization."""
    extractor = PrescriptionFieldExtractor(db_session)
    raw_ocr = "Rx: Amoxicillin 500mg"
    result = extractor.extract_fields(raw_ocr)

    # Raw text must remain intact
    assert result["raw_text"] == raw_ocr
    assert result["fields"]["medicine_name"] == "Amoxicillin"
    assert result["match"]["matched_name"] == "Amoxicillin"
    assert result["match"]["confidence"] >= 0.85


def test_field_provenance_and_no_missing_field_autofill(db_session, seed_references):
    """Verify that clinical fields not present in OCR are strictly None with provenance source 'not_detected'."""
    extractor = PrescriptionFieldExtractor(db_session)
    raw_text = "Rx: Napa"  # Only medicine name, no strength, quantity, frequency
    result = extractor.extract_fields(raw_text)

    fields = result["fields"]
    evidence = result["evidence"]

    assert fields["medicine_name"] == "Napa"
    assert fields["strength"] is None
    assert fields["dosage_amount"] is None
    assert fields["frequency"] is None
    assert fields["quantity"] is None

    # Provenance tracking verification
    assert evidence["strength"]["source"] == "not_detected"
    assert evidence["strength"]["confidence"] == 0.0
    assert evidence["frequency"]["source"] == "not_detected"
    assert evidence["quantity"]["source"] == "not_detected"


def test_zero_region_fallback_behavior(dummy_prescription_image):
    """When detector finds 0 regions, ensure fallback_used is True and full-page text is preserved."""
    service = OCRPrescriptionService()

    class MockZeroDetector:
        def is_available(self):
            return True
        def detect_regions(self, img):
            return {"total_detected": 0, "regions": [], "status": "SUCCESS"}

    service.engine.composite_provider.detector = MockZeroDetector()

    result = service.process_prescription_file(dummy_prescription_image, "prescription.jpg", "image/jpeg")

    assert result["fallback_used"] is True
    assert result["detector_status"] == "fallback"
    assert result["detector_coverage_warning"] is True
    assert len(result["regions"]) == 0
    assert len(result["raw_text"]) > 0


def test_partial_detection_status_and_coverage_warning():
    """When detector finds <= 2 regions, partial_detection status and coverage warning must be set."""
    service = OCRPrescriptionService()

    class MockPartialDetector:
        def is_available(self):
            return True
        def detect_regions(self, img):
            return {
                "total_detected": 1,
                "regions": [{
                    "reading_order": 1,
                    "box": [100, 250, 400, 300],
                    "crop_box": [90, 240, 410, 310],
                    "confidence": 0.48,
                    "class_name": "medicine",
                }],
                "status": "SUCCESS",
            }

    service.engine.composite_provider.detector = MockPartialDetector()

    img = Image.new("RGB", (500, 500), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    result = service.process_prescription_file(buf.getvalue(), "rx.jpg", "image/jpeg")

    assert result["detector_status"] == "partial_detection"
    assert result["detector_coverage_warning"] is True
    assert result["fallback_used"] is False
    assert len(result["regions"]) == 1


def test_api_response_schema_validation(dummy_prescription_image):
    """Verify that multi-stage OCR output conforms to OCRExtractionResponse Pydantic schema."""
    service = OCRPrescriptionService()
    result = service.process_prescription_file(dummy_prescription_image, "rx.jpg", "image/jpeg")

    validated = OCRExtractionResponse(**result)
    assert validated.fields is not None
    assert isinstance(validated.regions, list)
    assert validated.detector_status in ["full_detection", "partial_detection", "fallback"]
    assert isinstance(validated.detector_coverage_warning, bool)
    assert isinstance(validated.fallback_used, bool)
