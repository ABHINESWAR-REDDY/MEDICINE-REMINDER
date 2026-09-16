"""Comprehensive unit and integration tests for Patient Portal Medication History and Refill Predictions."""

import pytest
from datetime import datetime, date, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole, ApprovalStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.dose import MedicationDose, DoseStatus
from app.models.prescription import Prescription, PrescriptionStatus


@pytest.fixture
def auth_headers_factory(db_session: Session):
    """Factory creating authenticated test users and JWT authorization headers."""
    def _create_user_and_headers(
        email: str,
        role: UserRole = UserRole.PATIENT,
        name: str = "Test User",
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        is_active: bool = True
    ):
        user = db_session.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name=name,
                email=email,
                password_hash=get_password_hash("Password123!"),
                role=role,
                approval_status=approval_status,
                is_active=is_active
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

        token = create_access_token(subject=user.id)
        return user, {"Authorization": f"Bearer {token}"}

    return _create_user_and_headers


# =====================================================================
# 1. AUTHENTICATION & RBAC SECURITY TESTS
# =====================================================================

def test_unauthenticated_access_rejected_401(client: TestClient):
    """Unauthenticated requests to history and refill endpoints return HTTP 401."""
    res1 = client.get("/api/v1/patient/medication-history")
    assert res1.status_code == 401

    res2 = client.get("/api/v1/patient/refill-predictions")
    assert res2.status_code == 401


def test_caregiver_and_admin_cannot_access_patient_endpoints_403(client: TestClient, auth_headers_factory):
    """Caregiver and Admin roles receive HTTP 403 on patient portal endpoints."""
    _, cg_headers = auth_headers_factory("cg_portal@pillsync.com", UserRole.CAREGIVER, name="Caregiver User")
    _, adm_headers = auth_headers_factory("admin_portal@pillsync.com", UserRole.ADMIN, name="Admin User")

    for h in [cg_headers, adm_headers]:
        res1 = client.get("/api/v1/patient/medication-history", headers=h)
        assert res1.status_code == 403

        res2 = client.get("/api/v1/patient/refill-predictions", headers=h)
        assert res2.status_code == 403


# =====================================================================
# 2. MEDICATION HISTORY TESTS
# =====================================================================

def test_patient_empty_medication_history(client: TestClient, auth_headers_factory):
    """Patient with no medications receives an empty history list with zero mock data."""
    patient, headers = auth_headers_factory("empty_patient@pillsync.com", UserRole.PATIENT)

    res = client.get("/api/v1/patient/medication-history", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == patient.id
    assert data["total_records"] == 0
    assert data["history"] == []


def test_patient_retrieves_own_medication_history_timeline(client: TestClient, db_session: Session, auth_headers_factory):
    """Patient retrieves complete medication and dose timeline with status and timestamps."""
    patient, headers = auth_headers_factory("history_patient@pillsync.com", UserRole.PATIENT)

    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    # Create real medicine
    med = Medicine(
        user_id=patient.id,
        name="Amoxicillin",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.CAPSULE,
        instructions="Take with water after meals",
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=10),
        is_active=True,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.TWICE_DAILY,
        times_per_day=2,
        scheduled_times=["08:00", "20:00"],
        dose_quantity=1.0,
        start_date=med.start_date,
        end_date=med.end_date,
        is_active=True,
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # Add dose records: 1 TAKEN, 1 MISSED, 1 SCHEDULED
    dose1 = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=now_utc - timedelta(hours=14),
        actual_time=now_utc - timedelta(hours=13, minutes=50),
        status=DoseStatus.TAKEN,
    )
    dose2 = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=now_utc - timedelta(hours=2),
        actual_time=None,
        status=DoseStatus.MISSED,
    )
    dose3 = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=now_utc + timedelta(hours=6),
        actual_time=None,
        status=DoseStatus.SCHEDULED,
    )
    db_session.add_all([dose1, dose2, dose3])
    db_session.commit()

    res = client.get("/api/v1/patient/medication-history", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == patient.id
    assert data["total_records"] == 3

    statuses = [item["status"] for item in data["history"]]
    assert "TAKEN" in statuses
    assert "MISSED" in statuses
    assert "SCHEDULED" in statuses

    taken_item = next(item for item in data["history"] if item["status"] == "TAKEN")
    assert taken_item["medicine_name"] == "Amoxicillin"
    assert taken_item["strength"] == 500.0
    assert taken_item["unit"] == "mg"
    assert taken_item["dosage_form"] == "CAPSULE"
    assert taken_item["actual_time"] is not None


def test_cross_patient_data_isolation(client: TestClient, db_session: Session, auth_headers_factory):
    """Patient A never sees records belonging to Patient B."""
    patient_a, headers_a = auth_headers_factory("patient_a@pillsync.com", UserRole.PATIENT, name="Patient A")
    patient_b, headers_b = auth_headers_factory("patient_b@pillsync.com", UserRole.PATIENT, name="Patient B")

    today = datetime.now(timezone.utc).date()

    # Create med for Patient B
    med_b = Medicine(
        user_id=patient_b.id,
        name="Lisinopril Private",
        dosage_amount=10.0,
        dosage_unit=DosageUnit.MG,
        quantity=60,
        medicine_form=MedicineForm.TABLET,
        start_date=today,
        is_active=True,
    )
    db_session.add(med_b)
    db_session.commit()

    # Patient A requests history
    res_a = client.get("/api/v1/patient/medication-history", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["total_records"] == 0
    assert "Lisinopril Private" not in [item["medicine_name"] for item in data_a["history"]]

    # Patient B requests history
    res_b = client.get("/api/v1/patient/medication-history", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["total_records"] == 1
    assert data_b["history"][0]["medicine_name"] == "Lisinopril Private"


# =====================================================================
# 3. REFILL PREDICTION CALCULATION TESTS
# =====================================================================

def test_dynamic_refill_prediction_math(client: TestClient, db_session: Session, auth_headers_factory):
    """Verify mathematically accurate refill predictions with stock deduction."""
    patient, headers = auth_headers_factory("math_patient@pillsync.com", UserRole.PATIENT)

    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    # Initial stock: 60 tablets
    med = Medicine(
        user_id=patient.id,
        name="Metformin HCl",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=60,
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=10),
        is_active=True,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    # Twice daily, 1 tablet per intake = 2.0 daily consumption
    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.TWICE_DAILY,
        times_per_day=2,
        scheduled_times=["08:00", "20:00"],
        dose_quantity=1.0,
        start_date=med.start_date,
        is_active=True,
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # Record 10 doses TAKEN (10 * 1.0 = 10 units consumed)
    # Remaining: 60 - 10 = 50 tablets
    # Daily usage: 2 tablets/day
    # Remaining days: 50 / 2 = 25 days
    for i in range(10):
        d = MedicationDose(
            schedule_id=sched.id,
            medicine_id=med.id,
            patient_id=patient.id,
            scheduled_time=now_utc - timedelta(days=i + 1),
            actual_time=now_utc - timedelta(days=i + 1),
            status=DoseStatus.TAKEN,
        )
        db_session.add(d)
    db_session.commit()

    res = client.get("/api/v1/patient/refill-predictions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == patient.id
    assert data["valid_predictions_count"] == 1
    assert data["insufficient_data_count"] == 0

    pred = data["predictions"][0]
    assert pred["medicine_name"] == "Metformin HCl"
    assert pred["status"] == "VALID"
    assert pred["current_stock"] == 60
    assert pred["doses_taken_count"] == 10
    assert pred["daily_consumption"] == 2.0
    assert pred["estimated_remaining_quantity"] == 50.0
    assert pred["estimated_remaining_days"] == 25

    expected_refill_date = (today + timedelta(days=25)).isoformat()
    assert pred["predicted_refill_date"] == expected_refill_date
    assert pred["urgency_level"] == "GOOD"


def test_refill_insufficient_data_handling(client: TestClient, db_session: Session, auth_headers_factory):
    """Missing stock or schedule produces INSUFFICIENT_DATA state without fake values."""
    patient, headers = auth_headers_factory("insufficient_patient@pillsync.com", UserRole.PATIENT)

    today = datetime.now(timezone.utc).date()

    # Medicine with no schedule attached
    med_no_sched = Medicine(
        user_id=patient.id,
        name="Atorvastatin",
        dosage_amount=20.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.TABLET,
        start_date=today,
        is_active=True,
    )
    db_session.add(med_no_sched)
    db_session.commit()

    res = client.get("/api/v1/patient/refill-predictions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["insufficient_data_count"] == 1
    assert data["valid_predictions_count"] == 0

    pred = data["predictions"][0]
    assert pred["medicine_name"] == "Atorvastatin"
    assert pred["status"] == "INSUFFICIENT_DATA"
    assert "insufficient medication data" in pred["status_message"].lower()
    assert pred["estimated_remaining_days"] is None
    assert pred["predicted_refill_date"] is None


def test_refill_ended_medication_handling(client: TestClient, db_session: Session, auth_headers_factory):
    """Discontinued or ended medication regimen returns ENDED status."""
    patient, headers = auth_headers_factory("ended_patient@pillsync.com", UserRole.PATIENT)

    today = datetime.now(timezone.utc).date()

    med_ended = Medicine(
        user_id=patient.id,
        name="Prednisone Taper",
        dosage_amount=10.0,
        dosage_unit=DosageUnit.MG,
        quantity=14,
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=20),
        end_date=today - timedelta(days=5),
        is_active=True,
    )
    db_session.add(med_ended)
    db_session.commit()

    res = client.get("/api/v1/patient/refill-predictions", headers=headers)
    assert res.status_code == 200
    data = res.json()

    pred = data["predictions"][0]
    assert pred["medicine_name"] == "Prednisone Taper"
    assert pred["status"] == "ENDED"
    assert "ended" in pred["status_message"].lower()
