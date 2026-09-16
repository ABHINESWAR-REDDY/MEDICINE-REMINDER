"""Phase 3 OCR prescription extraction and medication import test suite."""

import io
from datetime import date
from unittest.mock import patch
import pytest
from fastapi import status
from PIL import Image

from app.core.security import create_access_token
from app.models.user import UserRole
from app.models.medicine_reference import MedicineReference
from app.models.prescription import Prescription
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.services.ocr.preprocessor import OCRTextPreprocessor
from app.services.ocr.matcher import MedicineMatcher
from app.services.ocr.extractor import PrescriptionFieldExtractor


@pytest.fixture
def populate_medicine_references(db_session):
    """Seed test database with sample reference medicines."""
    sample_data = [
        ("Amoxicillin", "amoxicillin", "Antibiotic", "Tablet", "500 mg", "Twice Daily"),
        ("Acetocillin", "acetocillin", "Antibiotic", "Capsule", "250 mg", "Once Daily"),
        ("Ibuproprofen", "ibuproprofen", "Analgesic", "Tablet", "400 mg", "Three Times Daily"),
        ("Dextrocillin", "dextrocillin", "Antibiotic", "Syrup", "125 mg/5ml", "Twice Daily"),
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


# =========================================================================
# 1. OCR Text Preprocessor Tests
# =========================================================================

def test_ocr_preprocessor_digit_repair_and_clean():
    """Test OCR text normalization repairs context-aware digit confusion."""
    raw = "Dr. Jane Smith\nRx: Amoxicillin 50O mg tab\nTake 1O ml b.i.d. after food\n"
    cleaned = OCRTextPreprocessor.clean_text(raw)
    assert "500 mg" in cleaned
    assert "10 ml" in cleaned
    assert "Amoxicillin" in cleaned

    expanded = OCRTextPreprocessor.expand_abbreviations(cleaned)
    assert "Twice Daily" in expanded


# =========================================================================
# 2. Medicine Matching & Confidence Scoring Tests
# =========================================================================

def test_medicine_matcher_exact_match(db_session, populate_medicine_references):
    """Test exact medicine name match yields 1.0 confidence and HIGH level."""
    matcher = MedicineMatcher(db_session)
    result = matcher.match_medicine_name("Amoxicillin")
    assert result["matched_name"] == "Amoxicillin"
    assert result["confidence"] == 1.0
    assert result["confidence_level"] == "HIGH"
    assert result["match_type"] == "EXACT"


def test_medicine_matcher_fuzzy_match_spelling_variation(db_session, populate_medicine_references):
    """Test spelling variation (e.g. 'Amoxicilin') correctly matches 'Amoxicillin' with high confidence."""
    matcher = MedicineMatcher(db_session)
    result = matcher.match_medicine_name("Amoxicilin")
    assert result["matched_name"] == "Amoxicillin"
    assert result["confidence"] >= 0.90
    assert result["confidence_level"] == "HIGH"
    assert result["match_type"] == "FUZZY"


def test_medicine_matcher_low_confidence_or_no_match(db_session, populate_medicine_references):
    """Test unknown medicine returns low confidence / no auto-selection."""
    matcher = MedicineMatcher(db_session)
    result = matcher.match_medicine_name("ZzzNonExistentMedXYZ")
    assert result["confidence"] < 0.70
    assert result["confidence_level"] == "LOW"


# =========================================================================
# 3. Structured Field Extraction Tests
# =========================================================================

def test_structured_field_extraction_full(db_session, populate_medicine_references):
    """Test full structured field extraction from realistic prescription text."""
    sample_prescription_text = """
    Dr. Robert Wilson, MD
    General Hospital Clinic
    Date: 2026-08-18
    Rx #RX-982341
    Patient: John Doe

    Rx: Amoxicilin 500 mg tablets
    Sig: Take 1 tablet twice daily at 08:00 and 20:00 after food
    Duration: for 7 days
    """
    extractor = PrescriptionFieldExtractor(db_session)
    result = extractor.extract_fields(sample_prescription_text)

    fields = result["fields"]
    assert "Robert Wilson" in (fields["doctor_name"] or "")
    assert fields["prescription_number"] == "RX-982341"
    assert fields["medicine_name"] == "Amoxicilin"
    assert result["match"]["matched_name"] == "Amoxicillin"
    assert fields["dosage_amount"] == 500.0
    assert fields["dosage_unit"] == DosageUnit.MG.value
    assert fields["dosage_form"] == MedicineForm.TABLET.value
    assert fields["frequency"] == ScheduleFrequency.TWICE_DAILY.value
    assert fields["dose_quantity"] == 1.0
    assert fields["scheduled_times"] == ["08:00", "20:00"]
    assert "After food" in (fields["instructions"] or "")
    assert fields["duration_days"] == 7
    assert result["confidence_level"] == "HIGH"


def test_missing_fields_remain_none(db_session, populate_medicine_references):
    """Test that missing prescription fields remain None and are NOT fabricated from dataset."""
    sparse_text = "Amoxicillin 500 mg"
    extractor = PrescriptionFieldExtractor(db_session)
    result = extractor.extract_fields(sparse_text)

    fields = result["fields"]
    assert fields["doctor_name"] is None
    assert fields["prescription_number"] is None
    assert fields["scheduled_times"] is None
    assert fields["instructions"] is None
    assert fields["duration_days"] is None
    assert fields["quantity"] is None


# =========================================================================
# 4. API Endpoints & RBAC Security Tests
# =========================================================================

def _create_dummy_image_bytes() -> bytes:
    """Create a minimal PNG image in memory."""
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_ocr_unauthenticated_rejected(client):
    """Unauthenticated request to OCR upload endpoint returns 401."""
    img_bytes = _create_dummy_image_bytes()
    response = client.post(
        "/api/v1/ocr/prescription",
        files={"file": ("prescription.png", img_bytes, "image/png")},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_ocr_caregiver_and_admin_forbidden(client, create_user):
    """Caregiver and Admin roles are forbidden (403) from accessing OCR prescription upload."""
    caregiver = create_user(email="caregiver@example.com", role=UserRole.CAREGIVER)
    admin = create_user(email="admin@example.com", role=UserRole.ADMIN)

    img_bytes = _create_dummy_image_bytes()

    for user in [caregiver, admin]:
        token = create_access_token(subject=user.id)
        response = client.post(
            "/api/v1/ocr/prescription",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("prescription.png", img_bytes, "image/png")},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_ocr_patient_upload_flow(client, create_user, populate_medicine_references):
    """Authenticated patient uploads prescription, receives job_id, and polls result."""
    patient = create_user(email="patient@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    img_bytes = _create_dummy_image_bytes()
    mock_ocr_text = "Dr. Alice Adams\nRx #RX-5544\nAmoxicillin 500 mg Tablet\nTake 1 tablet once daily"

    with patch("app.services.ocr.engine.OCREngine.extract_text", return_value=mock_ocr_text):
        response = client.post(
            "/api/v1/ocr/prescription",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("rx.png", img_bytes, "image/png")},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

    job_id = data["job_id"]
    
    # Poll job status
    import time
    for _ in range(50):
        poll_res = client.get(
            f"/api/v1/ocr/prescription/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert poll_res.status_code == status.HTTP_200_OK
        job_data = poll_res.json()
        if job_data["status"] == "completed":
            break
        time.sleep(0.1)

    assert job_data["status"] == "completed"
    res_data = job_data["result"]
    assert res_data["fields"]["medicine_name"] == "Amoxicillin"
    assert res_data["fields"]["dosage_amount"] == 500.0
    assert res_data["confidence_level"] == "HIGH"

    # Ensure no patient records were created before confirmation
    assert len(patient.medicines) == 0
    assert len(patient.prescriptions) == 0


def test_ocr_invalid_file_format_rejected(client, create_user):
    """Uploading unsupported MIME type or extension is safely rejected with 400."""
    patient = create_user(email="patient2@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    response = client.post(
        "/api/v1/ocr/prescription",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("malicious.exe", b"executable_bytes", "application/octet-stream")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"]["code"] == "FILE_INVALID"


def test_ocr_corrupted_image_magic_bytes_rejected(client, create_user):
    """Uploading a file disguised as PNG but with invalid bytes is rejected with 400 and FILE_INVALID."""
    patient = create_user(email="patient_corrupt@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    response = client.post(
        "/api/v1/ocr/prescription",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("corrupted.png", b"fake_png_header_content_xyz", "image/png")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"]["code"] == "FILE_INVALID"


def test_ocr_oversized_file_rejected(client, create_user):
    """Uploading file > 10MB is rejected with 400."""
    patient = create_user(email="patient3@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    oversized_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024 + 100)
    response = client.post(
        "/api/v1/ocr/prescription",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("large.png", oversized_bytes, "image/png")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"]["code"] == "FILE_INVALID"


def test_ocr_no_text_detected_response(client, create_user):
    """When OCR engine detects no text, response returns clear guidance without server crash."""
    patient = create_user(email="patient_notext@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    img_bytes = _create_dummy_image_bytes()

    with patch("app.services.ocr.engine.OCREngine.extract_text", return_value=""):
        response = client.post(
            "/api/v1/ocr/prescription",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("blank.png", img_bytes, "image/png")},
        )

    assert response.status_code == status.HTTP_200_OK
    job_id = response.json()["job_id"]

    import time
    for _ in range(50):
        poll_res = client.get(
            f"/api/v1/ocr/prescription/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        job_data = poll_res.json()
        if job_data["status"] == "completed":
            break
        time.sleep(0.1)

    assert job_data["status"] == "completed"
    res = job_data["result"]
    assert "No readable text" in res.get("message", "")
    assert res["fields"]["medicine_name"] is None


def test_ocr_pdf_direct_and_rendered_processing(client, create_user, populate_medicine_references):
    """Uploading a valid PDF document processes correctly via PyMuPDF."""
    patient = create_user(email="patient_pdf@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    import pymupdf
    pdf_doc = pymupdf.open()
    page = pdf_doc.new_page()
    page.insert_text((50, 72), "Dr. Emily Vance\nRx #PDF-992\nMetformin 850 mg Tablet\nTake 1 tablet twice daily")
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    response = client.post(
        "/api/v1/ocr/prescription",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("prescription.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == status.HTTP_200_OK
    job_id = response.json()["job_id"]

    import time
    for _ in range(50):
        poll_res = client.get(
            f"/api/v1/ocr/prescription/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        job_data = poll_res.json()
        if job_data["status"] == "completed":
            break
        time.sleep(0.1)

    assert job_data["status"] == "completed"
    res = job_data["result"]
    assert res["fields"]["medicine_name"] == "Metformin"
    assert res["fields"]["dosage_amount"] == 850.0
    assert res["fields"]["dosage_unit"] == "mg"


# =========================================================================
# 5. Confirmation Workflow & PostgreSQL Persistence Tests

# =========================================================================

def test_ocr_confirmation_creates_medication_workflow(client, create_user, db_session):
    """Confirming OCR draft creates Prescription, Medicine, and MedicationSchedule in PostgreSQL for current_user.id."""
    patient = create_user(email="patient_confirm@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    confirm_payload = {
        "create_prescription": True,
        "prescription_number": "RX-CONFIRM-123",
        "doctor_name": "Dr. Sarah Connor",
        "name": "Amoxicillin",
        "dosage_amount": 500.0,
        "dosage_unit": DosageUnit.MG.value,
        "medicine_form": MedicineForm.TABLET.value,
        "quantity": 30,
        "instructions": "Take after breakfast and dinner",
        "start_date": str(date.today()),
        "create_schedule": True,
        "frequency_type": ScheduleFrequency.TWICE_DAILY.value,
        "dose_quantity": 1.0,
        "scheduled_times": ["08:00", "20:00"],
    }

    response = client.post(
        "/api/v1/ocr/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json=confirm_payload,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["prescription_id"] is not None
    assert data["medicine_id"] is not None
    assert data["schedule_id"] is not None

    # Verify database persistence & ownership
    medicine = db_session.query(Medicine).filter_by(id=data["medicine_id"]).first()
    assert medicine is not None
    assert medicine.user_id == patient.id
    assert medicine.name == "Amoxicillin"
    assert medicine.prescription_id == data["prescription_id"]

    schedule = db_session.query(MedicationSchedule).filter_by(id=data["schedule_id"]).first()
    assert schedule is not None
    assert schedule.medicine_id == medicine.id
    assert schedule.scheduled_times == ["08:00", "20:00"]


def test_search_reference_medicines_autocomplete(client, create_user, populate_medicine_references):
    """Patient can search reference medicines for autocomplete."""
    patient = create_user(email="patient_search@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)

    response = client.get(
        "/api/v1/ocr/reference-medicines?query=amox",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Amoxicillin"
