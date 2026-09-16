"""Comprehensive unit and integration tests for Caregiver Refill Notifications and Adherence Reports."""

import pytest
from datetime import datetime, date, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole, ApprovalStatus
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.dose import MedicationDose, DoseStatus
from app.models.notification import Notification


@pytest.fixture
def auth_headers_factory(db_session: Session):
    """Factory creating authenticated test users and JWT authorization headers."""
    def _create_user_and_headers(
        email: str,
        role: UserRole = UserRole.CAREGIVER,
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

def test_unauthenticated_caregiver_endpoints_401(client: TestClient):
    """Unauthenticated access to adherence reports and refill notifications returns HTTP 401."""
    res1 = client.get("/api/v1/caregiver/adherence-reports")
    assert res1.status_code == 401

    res2 = client.get("/api/v1/caregiver/patients/1/adherence")
    assert res2.status_code == 401

    res3 = client.get("/api/v1/caregiver/refill-notifications")
    assert res3.status_code == 401


def test_patient_and_admin_cannot_access_caregiver_endpoints_403(client: TestClient, auth_headers_factory):
    """Patient and Admin roles receive HTTP 403 on Caregiver-only endpoints."""
    _, patient_headers = auth_headers_factory("patient_access@pillsync.com", UserRole.PATIENT, name="Patient User")
    _, admin_headers = auth_headers_factory("admin_access@pillsync.com", UserRole.ADMIN, name="Admin User")

    for headers in [patient_headers, admin_headers]:
        res1 = client.get("/api/v1/caregiver/adherence-reports", headers=headers)
        assert res1.status_code == 403

        res2 = client.get("/api/v1/caregiver/patients/1/adherence", headers=headers)
        assert res2.status_code == 403

        res3 = client.get("/api/v1/caregiver/refill-notifications", headers=headers)
        assert res3.status_code == 403


# =====================================================================
# 2. CAREGIVER ADHERENCE REPORTS & PATIENT ISOLATION
# =====================================================================

def test_caregiver_empty_assigned_patients_adherence(client: TestClient, auth_headers_factory):
    """Caregiver with no assigned patients receives empty report list with zero mock data."""
    caregiver, headers = auth_headers_factory("lonely_cg@pillsync.com", UserRole.CAREGIVER)

    res = client.get("/api/v1/caregiver/adherence-reports", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["caregiver_id"] == caregiver.id
    assert data["total_assigned_patients"] == 0
    assert data["reports"] == []


def test_caregiver_adherence_reports_dynamic_calculation(client: TestClient, db_session: Session, auth_headers_factory):
    """Caregiver retrieves real adherence compliance across assigned patients with accurate percentages."""
    cg, cg_headers = auth_headers_factory("supervisor_cg@pillsync.com", UserRole.CAREGIVER, name="Caregiver Sarah")
    patient, _ = auth_headers_factory("monitored_pt@pillsync.com", UserRole.PATIENT, name="Patient Robert")

    # Assign patient to caregiver
    assign = CaregiverPatientAssignment(
        caregiver_id=cg.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assign)
    db_session.commit()

    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    # Create Medicine & Schedule
    med = Medicine(
        user_id=patient.id,
        name="Lisinopril",
        dosage_amount=10.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=10),
        is_active=True,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["08:00"],
        dose_quantity=1.0,
        start_date=med.start_date,
        is_active=True,
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # 9 doses TAKEN, 1 dose MISSED, 2 FUTURE SCHEDULED (excluded from adherence)
    for i in range(9):
        d = MedicationDose(
            schedule_id=sched.id,
            medicine_id=med.id,
            patient_id=patient.id,
            scheduled_time=now_utc - timedelta(days=i + 1),
            actual_time=now_utc - timedelta(days=i + 1),
            status=DoseStatus.TAKEN,
        )
        db_session.add(d)

    missed_d = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=now_utc - timedelta(hours=3),
        actual_time=None,
        status=DoseStatus.MISSED,
    )
    db_session.add(missed_d)

    future_d = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=now_utc + timedelta(hours=12),
        actual_time=None,
        status=DoseStatus.SCHEDULED,
    )
    db_session.add(future_d)
    db_session.commit()

    # Total expected: 9 + 1 = 10 doses. Taken: 9. Adherence: 90.0% ('Good')
    res = client.get("/api/v1/caregiver/adherence-reports?days=30", headers=cg_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_assigned_patients"] == 1
    assert data["good_standing_count"] == 1
    assert data["overall_adherence_percentage"] == 90.0
    assert data["overall_adherence_status"] == "Good"

    pt_report = data["reports"][0]
    assert pt_report["patient_id"] == patient.id
    assert pt_report["name"] == "Patient Robert"
    assert pt_report["taken_count"] == 9
    assert pt_report["missed_count"] == 1
    assert pt_report["adherence_percentage"] == 90.0
    assert pt_report["adherence_status"] == "Good"


def test_cross_caregiver_patient_access_blocked_403(client: TestClient, db_session: Session, auth_headers_factory):
    """Caregiver A cannot view detailed adherence report for Patient B who is assigned to Caregiver B."""
    cg_a, headers_a = auth_headers_factory("cg_alpha@pillsync.com", UserRole.CAREGIVER, name="Caregiver Alpha")
    cg_b, headers_b = auth_headers_factory("cg_beta@pillsync.com", UserRole.CAREGIVER, name="Caregiver Beta")
    patient_b, _ = auth_headers_factory("pt_beta_only@pillsync.com", UserRole.PATIENT, name="Patient Beta")

    # Assign Patient B strictly to Caregiver B
    assign = CaregiverPatientAssignment(
        caregiver_id=cg_b.id,
        patient_id=patient_b.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assign)
    db_session.commit()

    # Caregiver A attempts to view Patient B's adherence report -> 403 Forbidden
    res_a = client.get(f"/api/v1/caregiver/patients/{patient_b.id}/adherence", headers=headers_a)
    assert res_a.status_code == 403

    # Caregiver B can view Patient B's report -> 200 OK
    res_b = client.get(f"/api/v1/caregiver/patients/{patient_b.id}/adherence", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["patient"]["id"] == patient_b.id
    assert data_b["patient"]["name"] == "Patient Beta"


# =====================================================================
# 3. DYNAMIC & PERSISTENT REFILL NOTIFICATIONS TESTS
# =====================================================================

def test_caregiver_persistent_refill_notifications_and_deduplication(client: TestClient, db_session: Session, auth_headers_factory):
    """Caregiver receives persistent refill notifications stored in DB with deduplication across polling cycles."""
    cg, cg_headers = auth_headers_factory("alert_cg@pillsync.com", UserRole.CAREGIVER, name="Caregiver Alex")
    patient, _ = auth_headers_factory("low_stock_pt@pillsync.com", UserRole.PATIENT, name="Patient Emma")

    # Assign patient to caregiver
    assign = CaregiverPatientAssignment(
        caregiver_id=cg.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assign)
    db_session.commit()

    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    # Initial stock: 6 tablets. 2 tablets/day consumption.
    # Taken doses: 2 doses (2 tablets consumed).
    # Remaining stock: 4 tablets.
    # Remaining days: 4 / 2 = 2 days (<= 3 days -> CRITICAL).
    med = Medicine(
        user_id=patient.id,
        name="Metformin",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=6,
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=2),
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
        is_active=True,
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # 2 taken doses
    for i in range(2):
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

    # 1. First polling request -> creates ONE persistent Notification in DB
    res1 = client.get("/api/v1/caregiver/refill-notifications", headers=cg_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_notifications"] == 1
    assert data1["critical_count"] == 1

    notif = data1["notifications"][0]
    assert notif["patient_name"] == "Patient Emma"
    assert notif["medicine_name"] == "Metformin"
    assert notif["estimated_remaining_days"] == 2
    assert notif["estimated_remaining_quantity"] == 4.0
    assert notif["urgency_level"] == "CRITICAL"
    assert "approximately 2 days" in notif["message"].lower()

    # Verify persistent DB record was created
    db_records = db_session.query(Notification).filter(
        Notification.user_id == cg.id,
        Notification.type == "REFILL_NEEDED",
        Notification.related_medicine_id == med.id,
        Notification.is_read == False
    ).all()
    assert len(db_records) == 1
    assert db_records[0].severity == "CRITICAL"

    # 2. Subsequent 5 polling requests -> MUST NOT create duplicate DB records
    for _ in range(5):
        res_poll = client.get("/api/v1/caregiver/refill-notifications", headers=cg_headers)
        assert res_poll.status_code == 200
        assert res_poll.json()["total_notifications"] == 1

    db_records_after_polling = db_session.query(Notification).filter(
        Notification.user_id == cg.id,
        Notification.type == "REFILL_NEEDED",
        Notification.related_medicine_id == med.id,
        Notification.is_read == False
    ).all()
    assert len(db_records_after_polling) == 1

    # Also verify integrated in /api/v1/caregiver/alerts
    alerts_res = client.get("/api/v1/caregiver/alerts", headers=cg_headers)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    refill_alert = next((a for a in alerts if a["type"] == "REFILL_NEEDED"), None)
    assert refill_alert is not None
    assert refill_alert["medicine_name"] == "Metformin"
    assert refill_alert["severity"] == "CRITICAL"


def test_replenished_medication_clears_persistent_refill_notification(client: TestClient, db_session: Session, auth_headers_factory):
    """When a patient's medication stock is replenished, the persistent refill alert is resolved/cleared in DB."""
    cg, cg_headers = auth_headers_factory("replenish_cg@pillsync.com", UserRole.CAREGIVER, name="Caregiver Rep")
    patient, _ = auth_headers_factory("replenish_pt@pillsync.com", UserRole.PATIENT, name="Patient Rep")

    assign = CaregiverPatientAssignment(
        caregiver_id=cg.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assign)
    db_session.commit()

    today = datetime.now(timezone.utc).date()

    # Step 1: Low stock medicine (4 tablets, 2/day -> 2 days remaining)
    med = Medicine(
        user_id=patient.id,
        name="Atorvastatin",
        dosage_amount=20.0,
        dosage_unit=DosageUnit.MG,
        quantity=4,
        medicine_form=MedicineForm.TABLET,
        start_date=today,
        is_active=True,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.TWICE_DAILY,
        times_per_day=2,
        scheduled_times=["09:00", "21:00"],
        dose_quantity=1.0,
        start_date=med.start_date,
        is_active=True,
    )
    db_session.add(sched)
    db_session.commit()

    # First check: Notification generated and saved to DB
    res1 = client.get("/api/v1/caregiver/refill-notifications", headers=cg_headers)
    assert res1.status_code == 200
    assert res1.json()["total_notifications"] == 1

    active_notifs = db_session.query(Notification).filter(
        Notification.user_id == cg.id,
        Notification.type == "REFILL_NEEDED",
        Notification.related_medicine_id == med.id,
        Notification.is_read == False
    ).count()
    assert active_notifs == 1

    # Step 2: Replenish stock to 60 tablets
    med.quantity = 60
    db_session.commit()

    # Second check: System auto-resolves and clears the warning
    res2 = client.get("/api/v1/caregiver/refill-notifications", headers=cg_headers)
    assert res2.status_code == 200
    assert res2.json()["total_notifications"] == 0
    assert res2.json()["notifications"] == []

    unread_after_replenish = db_session.query(Notification).filter(
        Notification.user_id == cg.id,
        Notification.type == "REFILL_NEEDED",
        Notification.related_medicine_id == med.id,
        Notification.is_read == False
    ).count()
    assert unread_after_replenish == 0


def test_revoked_patient_assignment_clears_refill_notifications(client: TestClient, db_session: Session, auth_headers_factory):
    """When a caregiver-patient assignment is REVOKED, the caregiver immediately stops receiving refill notifications."""
    cg, cg_headers = auth_headers_factory("revoked_cg@pillsync.com", UserRole.CAREGIVER, name="Caregiver Rev")
    patient, _ = auth_headers_factory("revoked_pt@pillsync.com", UserRole.PATIENT, name="Patient Rev")

    assign = CaregiverPatientAssignment(
        caregiver_id=cg.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assign)
    db_session.commit()

    today = datetime.now(timezone.utc).date()

    med = Medicine(
        user_id=patient.id,
        name="Amlodipine",
        dosage_amount=5.0,
        dosage_unit=DosageUnit.MG,
        quantity=3,
        medicine_form=MedicineForm.TABLET,
        start_date=today,
        is_active=True,
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["08:00"],
        dose_quantity=1.0,
        start_date=med.start_date,
        is_active=True,
    )
    db_session.add(sched)
    db_session.commit()

    # Active assignment -> receives notification
    res_active = client.get("/api/v1/caregiver/refill-notifications", headers=cg_headers)
    assert res_active.status_code == 200
    assert res_active.json()["total_notifications"] == 1

    # Revoke assignment
    assign.status = AssignmentStatus.REVOKED
    db_session.commit()

    # Revoked assignment -> immediately stops receiving notification
    res_revoked = client.get("/api/v1/caregiver/refill-notifications", headers=cg_headers)
    assert res_revoked.status_code == 200
    assert res_revoked.json()["total_notifications"] == 0
    assert res_revoked.json()["notifications"] == []


# =====================================================================
# 5. CAREGIVER DASHBOARD AGGREGATE ADHERENCE & BATCH PERFORMANCE TESTS
# =====================================================================

def test_caregiver_dashboard_assigned_patients_and_rbac_isolation(client: TestClient, db_session: Session, auth_headers_factory):
    """Caregiver dashboard returns strictly assigned patients and isolates data between caregivers."""
    cg1, cg1_headers = auth_headers_factory("dash_cg1@pillsync.com", UserRole.CAREGIVER, name="Caregiver One")
    cg2, cg2_headers = auth_headers_factory("dash_cg2@pillsync.com", UserRole.CAREGIVER, name="Caregiver Two")
    pt1, _ = auth_headers_factory("dash_pt1@pillsync.com", UserRole.PATIENT, name="Patient Alpha")
    pt2, _ = auth_headers_factory("dash_pt2@pillsync.com", UserRole.PATIENT, name="Patient Beta")

    # Assign pt1 -> cg1, pt2 -> cg2
    db_session.add_all([
        CaregiverPatientAssignment(caregiver_id=cg1.id, patient_id=pt1.id, status=AssignmentStatus.ACTIVE),
        CaregiverPatientAssignment(caregiver_id=cg2.id, patient_id=pt2.id, status=AssignmentStatus.ACTIVE),
    ])
    db_session.commit()

    # CG1 dashboard
    res1 = client.get("/api/v1/caregiver/dashboard", headers=cg1_headers)
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["total_assigned_patients"] == 1
    assert len(d1["patients"]) == 1
    assert d1["patients"][0]["id"] == pt1.id
    assert d1["patients"][0]["name"] == "Patient Alpha"

    # CG2 dashboard
    res2 = client.get("/api/v1/caregiver/dashboard", headers=cg2_headers)
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["total_assigned_patients"] == 1
    assert len(d2["patients"]) == 1
    assert d2["patients"][0]["id"] == pt2.id
    assert d2["patients"][0]["name"] == "Patient Beta"


def test_caregiver_dashboard_mathematical_adherence_and_zero_handling(client: TestClient, db_session: Session, auth_headers_factory):
    """Overall dashboard adherence is calculated from total taken / total expected across all patients."""
    cg, cg_headers = auth_headers_factory("math_cg@pillsync.com", UserRole.CAREGIVER, name="Math Supervisor")
    pt1, _ = auth_headers_factory("math_pt1@pillsync.com", UserRole.PATIENT, name="Patient 1")
    pt2, _ = auth_headers_factory("math_pt2@pillsync.com", UserRole.PATIENT, name="Patient 2")

    db_session.add_all([
        CaregiverPatientAssignment(caregiver_id=cg.id, patient_id=pt1.id, status=AssignmentStatus.ACTIVE),
        CaregiverPatientAssignment(caregiver_id=cg.id, patient_id=pt2.id, status=AssignmentStatus.ACTIVE),
    ])
    db_session.commit()

    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    # Med for PT1 (10 taken, 0 missed = 100%)
    med1 = Medicine(user_id=pt1.id, name="Med1", dosage_amount=10.0, dosage_unit=DosageUnit.MG, quantity=50, medicine_form=MedicineForm.TABLET, start_date=today - timedelta(days=10), is_active=True)
    # Med for PT2 (0 taken, 10 missed = 0%)
    med2 = Medicine(user_id=pt2.id, name="Med2", dosage_amount=20.0, dosage_unit=DosageUnit.MG, quantity=50, medicine_form=MedicineForm.TABLET, start_date=today - timedelta(days=10), is_active=True)
    db_session.add_all([med1, med2])
    db_session.commit()

    sched1 = MedicationSchedule(medicine_id=med1.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["08:00"], dose_quantity=1.0, start_date=med1.start_date, is_active=True)
    sched2 = MedicationSchedule(medicine_id=med2.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["08:00"], dose_quantity=1.0, start_date=med2.start_date, is_active=True)
    db_session.add_all([sched1, sched2])
    db_session.commit()

    # PT1: 10 TAKEN doses
    for i in range(10):
        d = MedicationDose(schedule_id=sched1.id, medicine_id=med1.id, patient_id=pt1.id, scheduled_time=now_utc - timedelta(days=i + 1), actual_time=now_utc - timedelta(days=i + 1), status=DoseStatus.TAKEN)
        db_session.add(d)

    # PT2: 10 MISSED doses
    for i in range(10):
        d = MedicationDose(schedule_id=sched2.id, medicine_id=med2.id, patient_id=pt2.id, scheduled_time=now_utc - timedelta(days=i + 1), status=DoseStatus.MISSED)
        db_session.add(d)

    db_session.commit()

    res = client.get("/api/v1/caregiver/dashboard", headers=cg_headers)
    assert res.status_code == 200
    data = res.json()

    # PT1 adherence is 100%, PT2 adherence is 0.0%
    pt1_item = next(p for p in data["patients"] if p["id"] == pt1.id)
    pt2_item = next(p for p in data["patients"] if p["id"] == pt2.id)
    assert pt1_item["adherence_percentage"] == 100.0
    assert pt2_item["adherence_percentage"] == 0.0
    assert pt2_item["adherence_status"] == "High Risk"

    # Overall adherence across all doses: 10 taken / 20 expected = 50.0%
    assert data["overall_adherence_percentage"] == 50.0
    assert data["overall_adherence_status"] == "High Risk"


def test_caregiver_alerts_endpoint_batch_loading(client: TestClient, db_session: Session, auth_headers_factory):
    """Alerts endpoint returns missed dose, adherence risk, and refill notifications for assigned patients."""
    cg, cg_headers = auth_headers_factory("alerts_cg@pillsync.com", UserRole.CAREGIVER, name="Alerts Caregiver")
    pt, _ = auth_headers_factory("alerts_pt@pillsync.com", UserRole.PATIENT, name="Alerts Patient")

    db_session.add(CaregiverPatientAssignment(caregiver_id=cg.id, patient_id=pt.id, status=AssignmentStatus.ACTIVE))
    db_session.commit()

    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    med = Medicine(user_id=pt.id, name="Cardevilol", dosage_amount=6.25, dosage_unit=DosageUnit.MG, quantity=2, medicine_form=MedicineForm.TABLET, start_date=today, is_active=True)
    db_session.add(med)
    db_session.commit()

    sched = MedicationSchedule(medicine_id=med.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["08:00"], dose_quantity=1.0, start_date=today, is_active=True)
    db_session.add(sched)
    db_session.commit()

    # Add a missed dose in last 24h
    missed_dose = MedicationDose(schedule_id=sched.id, medicine_id=med.id, patient_id=pt.id, scheduled_time=now_utc - timedelta(hours=2), status=DoseStatus.MISSED)
    db_session.add(missed_dose)
    db_session.commit()

    res = client.get("/api/v1/caregiver/alerts", headers=cg_headers)
    assert res.status_code == 200
    alerts = res.json()
    assert isinstance(alerts, list)
    assert any(a["type"] == "MISSED_DOSE" for a in alerts)
    assert any(a["type"] == "REFILL_NEEDED" for a in alerts)

