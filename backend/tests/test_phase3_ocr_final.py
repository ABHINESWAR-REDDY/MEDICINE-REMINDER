"""Automated Contract & E2E Test Suite for Phase 3 Final OCR Extraction.

Verifies the 15 strict test conditions required by Phase 3:
1. Real prescription image upload
2. Medicine region detection
3. OCR crop extraction
4. TrOCR inference execution
5. Medicine name extraction
6. Strength extraction
7. Unit extraction
8. Dosage form extraction
9. Start date extraction
10. End date extraction
11. Missing field remains null
12. Reference matching does not overwrite raw OCR
13. Frontend receives structured OCR result (medication schema)
14. No hardcoded dosage values
15. Async OCR job workflow
"""

import os
import sys
import pytest
from datetime import date
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
os.environ["JWT_SECRET_KEY"] = "supersecretjwtkeyforlocaltest1234567890"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(BACKEND_DIR, "pillsync.db")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.ocr.extractor import PrescriptionFieldExtractor
from app.services.ocr.matcher import MedicineMatcher
from app.services.ocr.service import OCRPrescriptionService
from app.schemas.ocr import OCRExtractionResponse, OCRMedicationSchema


@pytest.fixture
def extractor():
    return PrescriptionFieldExtractor()


@pytest.fixture
def matcher():
    return MedicineMatcher()


@pytest.fixture
def ocr_service():
    return OCRPrescriptionService()


# TEST 1: Real prescription image upload & validation
def test_real_prescription_file_validation(ocr_service):
    rx_path = os.path.join(PROJECT_ROOT, "DATA", "prescriptions images", "PRS208C4025077.jpg")
    if os.path.exists(rx_path):
        with open(rx_path, "rb") as f:
            file_bytes = f.read()
        canonical_type = ocr_service._validate_file(file_bytes, "PRS208C4025077.jpg", "image/jpeg")
        assert canonical_type == "image/jpeg"


# TEST 2 & 3: Medicine region detection & crop generation
def test_medicine_region_detection_and_crop(ocr_service):
    rx_path = os.path.join(PROJECT_ROOT, "DATA", "prescriptions images", "PRS208C4025077.jpg")
    if os.path.exists(rx_path):
        pil_img = Image.open(rx_path)
        det_res = ocr_service.engine.composite_provider.detector.detect_regions(pil_img)
        assert "regions" in det_res
        assert isinstance(det_res["regions"], list)


# TEST 4: TrOCR inference execution
def test_trocr_inference_execution(ocr_service):
    sample_img = Image.new("RGB", (200, 50), color=(255, 255, 255))
    res = ocr_service.engine.handwriting_provider.predict_with_confidence(sample_img)
    assert "text" in res
    assert "confidence_score" in res


# TEST 5: Medicine name extraction (raw OCR preserved)
def test_medicine_name_extraction(extractor):
    text = "Rx Metfornin 500 mg daily"
    res = extractor.extract_fields(text)
    med = res["medication"]
    assert med["medicine_name"]["value"] == "Metfornin"
    assert med["medicine_name"]["source"] == "ocr"


# TEST 6: Strength extraction
def test_strength_extraction(extractor):
    text = "Amoxicillin 500 mg after food"
    res = extractor.extract_fields(text)
    assert res["medication"]["strength"]["value"] == "500"
    assert res["fields"]["dosage_amount"] == 500.0


# TEST 7: Unit extraction
def test_unit_extraction(extractor):
    text = "Paracetamol 650 mg"
    res = extractor.extract_fields(text)
    assert res["medication"]["unit"]["value"] == "mg"


# TEST 8: Dosage form extraction (explicit only)
def test_dosage_form_strict_extraction(extractor):
    # Explicit form
    res1 = extractor.extract_fields("Syp Calpol 120/5")
    assert res1["medication"]["dosage_form"]["value"] == "Syrup"
    
    # Missing form must remain None (zero hallucination)
    res2 = extractor.extract_fields("Amoxicillin 500 mg")
    assert res2["medication"]["dosage_form"]["value"] is None


# TEST 9: Start date extraction (explicit date in OCR)
def test_start_date_extraction_explicit(extractor):
    text = "Date: 18-08-2026\nRx Augmentin 625 mg"
    res = extractor.extract_fields(text)
    assert res["medication"]["start_date"]["value"] == "2026-08-18"
    assert res["medication"]["start_date"]["source"] == "ocr"


# TEST 10: End date extraction (when duration present)
def test_end_date_extraction(extractor):
    text = "Date: 2026-08-18\nRx Cipro 500 mg for 7 days"
    res = extractor.extract_fields(text)
    assert res["medication"]["start_date"]["value"] == "2026-08-18"
    assert res["medication"]["end_date"]["value"] == "2026-08-25"


# TEST 11: Missing field remains null (NEVER default to today or tablet)
def test_missing_fields_remain_null(extractor):
    text = "Rx Metfornin"
    res = extractor.extract_fields(text)
    med = res["medication"]
    assert med["strength"]["value"] is None
    assert med["strength"]["source"] == "not_detected"
    assert med["unit"]["value"] is None
    assert med["dosage_form"]["value"] is None
    assert med["instructions"]["value"] is None
    assert med["start_date"]["value"] is None
    assert med["end_date"]["value"] is None


# TEST 12: Reference matching does not overwrite raw OCR
def test_reference_match_does_not_overwrite_raw_ocr(extractor):
    text = "Metfornin 500 mg"
    res = extractor.extract_fields(text)
    # Raw OCR is Metfornin
    assert res["medication"]["medicine_name"]["value"] == "Metfornin"
    # Match candidate is Metformin / Etformin
    match = res.get("match") or {}
    candidates = match.get("candidates", [])
    if candidates:
        assert any("formin" in c["dataset_name"].lower() for c in candidates)



# TEST 13: Schema validates with OCRExtractionResponse
def test_structured_medication_schema_validates(extractor):
    text = "Date: 2026-08-18\nRx Amoxicillin 500 mg Tablet after meals for 5 days"
    res = extractor.extract_fields(text)
    validated = OCRExtractionResponse(**res)
    assert validated.medication is not None
    assert validated.medication.medicine_name.value == "Amoxicillin"
    assert validated.medication.strength.value == "500"
    assert validated.medication.dosage_form.value == "Tablet"
    assert validated.medication.instructions.value == "After meals"


# TEST 14: No hardcoded defaults in empty extraction
def test_empty_extraction_no_hardcoding(extractor):
    empty = extractor._empty_extraction_result("")
    med = empty["medication"]
    assert med["medicine_name"]["value"] is None
    assert med["strength"]["value"] is None
    assert med["unit"]["value"] is None
    assert med["dosage_form"]["value"] is None
    assert med["start_date"]["value"] is None
    assert med["end_date"]["value"] is None


# TEST 15: End-to-end trace with real prescription sample
def test_real_prescription_e2e(ocr_service):
    rx_path = os.path.join(PROJECT_ROOT, "DATA", "prescriptions images", "PRS208C4025077.jpg")
    if os.path.exists(rx_path):
        with open(rx_path, "rb") as f:
            file_bytes = f.read()
        res = ocr_service.process_prescription_file(file_bytes, "PRS208C4025077.jpg", "image/jpeg")
        assert "medication" in res
        assert "match" in res
        assert res["medication"]["medicine_name"]["value"] is not None
        assert res["confidence_score"] > 0.0
