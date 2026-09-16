"""Comprehensive Phase 4 test suite: RBAC security, Caregiver approval, Dose tracking, and Adherence calculations."""

import pytest
from unittest.mock import patch
from datetime import datetime, date, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole, ApprovalStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.dose import MedicationDose, DoseStatus
from app.models.audit_log import AuditLog
from app.services.dose_service import DoseService
from app.services.adherence_service import AdherenceService
from app.services.admin_service import AdminService
from app.services.caregiver_service import CaregiverService


@pytest.fixture
def auth_headers_factory(db_session: Session):
    """Factory creating authentication bearer headers for test users with specific roles and approval statuses."""
    def _create_user_and_headers(
        email: str,
        role: UserRole,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        is_active: bool = True,
        name: str = "Test User"
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
# 1. RBAC & PERMISSION SECURITY TESTS
# =====================================================================

def test_patient_cannot_access_admin_api(client: TestClient, auth_headers_factory):
    """Verify that a Patient user receives HTTP 403 on Admin endpoints."""
    _, headers = auth_headers_factory("patient_rbac@pillsync.com", UserRole.PATIENT)
    response = client.get("/api/v1/admin/dashboard", headers=headers)
    assert response.status_code == 403


def test_patient_cannot_access_caregiver_api(client: TestClient, auth_headers_factory):
    """Verify that a Patient user receives HTTP 403 on Caregiver endpoints."""
    _, headers = auth_headers_factory("patient_caregiver_rbac@pillsync.com", UserRole.PATIENT)
    response = client.get("/api/v1/caregiver/dashboard", headers=headers)
    assert response.status_code == 403


def test_caregiver_cannot_access_admin_api(client: TestClient, auth_headers_factory):
    """Verify that a Caregiver user receives HTTP 403 on Admin endpoints."""
    _, headers = auth_headers_factory("cg_admin_rbac@pillsync.com", UserRole.CAREGIVER)
    response = client.get("/api/v1/admin/dashboard", headers=headers)
    assert response.status_code == 403


def test_unapproved_caregiver_blocked(client: TestClient, auth_headers_factory):
    """Verify that a PENDING or REJECTED caregiver cannot access the caregiver dashboard."""
    _, pending_headers = auth_headers_factory(
        "cg_pending@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False
    )
    # Inactive user fails token authentication (401) or role check (403)
    response = client.get("/api/v1/caregiver/dashboard", headers=pending_headers)
    assert response.status_code in (401, 403)


# =====================================================================
# 2. CAREGIVER APPROVAL & ACTIVATION WORKFLOWS
# =====================================================================

def test_admin_approve_and_reject_caregiver(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify Admin can approve and reject caregiver registration requests."""
    admin, admin_headers = auth_headers_factory("admin_approver@pillsync.com", UserRole.ADMIN)
    cg_pending, _ = auth_headers_factory(
        "cg_to_approve@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False
    )

    # 1. Approve
    resp = client.post(f"/api/v1/admin/caregivers/{cg_pending.id}/approve", headers=admin_headers)
    assert resp.status_code == 200
    db_session.refresh(cg_pending)
    assert cg_pending.approval_status == ApprovalStatus.APPROVED
    assert cg_pending.is_active is True

    # 2. Reject
    cg_reject, _ = auth_headers_factory(
        "cg_to_reject@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False
    )
    resp_reject = client.post(f"/api/v1/admin/caregivers/{cg_reject.id}/reject", headers=admin_headers)
    assert resp_reject.status_code == 200
    db_session.refresh(cg_reject)
    assert cg_reject.approval_status == ApprovalStatus.REJECTED
    assert cg_reject.is_active is False


def test_admin_activate_deactivate_caregiver(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify Admin can toggle caregiver account active status."""
    _, admin_headers = auth_headers_factory("admin_toggle@pillsync.com", UserRole.ADMIN)
    cg, _ = auth_headers_factory("cg_toggle@pillsync.com", UserRole.CAREGIVER, is_active=True)

    # Deactivate
    resp_deact = client.post(f"/api/v1/admin/caregivers/{cg.id}/deactivate", headers=admin_headers)
    assert resp_deact.status_code == 200
    db_session.refresh(cg)
    assert cg.is_active is False

    # Reactivate
    resp_act = client.post(f"/api/v1/admin/caregivers/{cg.id}/activate", headers=admin_headers)
    assert resp_act.status_code == 200
    db_session.refresh(cg)
    assert cg.is_active is True


# =====================================================================
# 3. PATIENT-CAREGIVER ASSIGNMENT & ACCESS ISOLATION
# =====================================================================

def test_caregiver_patient_assignment_and_isolation(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify assignment creation, duplicate prevention, and strict patient isolation."""
    _, admin_headers = auth_headers_factory("admin_assigner@pillsync.com", UserRole.ADMIN)
    cg1, cg1_headers = auth_headers_factory("cg_assigned1@pillsync.com", UserRole.CAREGIVER)
    cg2, cg2_headers = auth_headers_factory("cg_unassigned2@pillsync.com", UserRole.CAREGIVER)
    pt, _ = auth_headers_factory("patient_assigned@pillsync.com", UserRole.PATIENT)

    # Admin assigns Patient -> Caregiver 1
    resp_assign = client.post(
        "/api/v1/admin/assignments",
        json={"caregiver_id": cg1.id, "patient_id": pt.id},
        headers=admin_headers
    )
    assert resp_assign.status_code == 201
    assignment_id = resp_assign.json()["assignment_id"]

    # Duplicate assignment should return 409
    resp_dup = client.post(
        "/api/v1/admin/assignments",
        json={"caregiver_id": cg1.id, "patient_id": pt.id},
        headers=admin_headers
    )
    assert resp_dup.status_code == 409

    # Caregiver 1 CAN access assigned patient
    resp_cg1_pt = client.get(f"/api/v1/caregiver/patients/{pt.id}", headers=cg1_headers)
    assert resp_cg1_pt.status_code == 200

    # Caregiver 2 CANNOT access unassigned patient (403)
    resp_cg2_pt = client.get(f"/api/v1/caregiver/patients/{pt.id}", headers=cg2_headers)
    assert resp_cg2_pt.status_code == 403

    # Admin revokes assignment
    resp_revoke = client.delete(f"/api/v1/admin/assignments/{assignment_id}", headers=admin_headers)
    assert resp_revoke.status_code == 200

    # Caregiver 1 now CANNOT access the patient
    resp_cg1_after = client.get(f"/api/v1/caregiver/patients/{pt.id}", headers=cg1_headers)
    assert resp_cg1_after.status_code == 403


# =====================================================================
# 4. DOSE GENERATION & IDEMPOTENCY
# =====================================================================

def test_dose_generation_and_idempotency(db_session: Session, auth_headers_factory):
    """Verify dose instances are deterministically generated without duplicates."""
    pt, _ = auth_headers_factory("dose_gen_pt@pillsync.com", UserRole.PATIENT)

    # Create medicine and schedule (Twice daily at 08:00 and 20:00)
    med = Medicine(
        user_id=pt.id,
        name="Metformin",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=30.0,
        start_date=date(2026, 8, 1),
        medicine_form=MedicineForm.TABLET
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.TWICE_DAILY,
        times_per_day=2,
        scheduled_times=["08:00", "20:00"],
        start_date=date(2026, 8, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    dose_service = DoseService(db_session)
    target = date(2026, 8, 20)

    # First generation -> should create 2 doses
    doses1 = dose_service.generate_doses_for_patient(pt.id, target_date=target)
    assert len(doses1) == 2

    # Second generation on same date -> MUST NOT duplicate
    doses2 = dose_service.generate_doses_for_patient(pt.id, target_date=target)
    assert len(doses2) == 2

    all_doses = db_session.query(MedicationDose).filter(
        MedicationDose.patient_id == pt.id,
        MedicationDose.schedule_id == sched.id
    ).all()
    assert len(all_doses) == 2


# =====================================================================
# 5. DOSE STATE TRANSITIONS & OVERDUE RECONCILIATION
# =====================================================================

def test_dose_state_transitions_and_adherence(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify Scheduled -> Taken, Scheduled -> Skipped, Overdue -> Missed, and Adherence rate."""
    pt, pt_headers = auth_headers_factory("pt_actions@pillsync.com", UserRole.PATIENT)
    other_pt, other_headers = auth_headers_factory("pt_other@pillsync.com", UserRole.PATIENT)

    med = Medicine(
        user_id=pt.id,
        name="Atorvastatin",
        dosage_amount=20.0,
        dosage_unit=DosageUnit.MG,
        quantity=30.0,
        start_date=date(2026, 8, 1),
        medicine_form=MedicineForm.TABLET
    )
    db_session.add(med)
    db_session.commit()

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["09:00"],
        start_date=date(2026, 8, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    dose_service = DoseService(db_session)
    adherence_service = AdherenceService(db_session)

    # Create 3 past doses:
    # Dose 1: Marked Taken
    # Dose 2: Marked Skipped
    # Dose 3: Left Scheduled (will become Missed because scheduled_time is in the past)
    past_time1 = datetime.now(timezone.utc) - timedelta(days=3, hours=2)
    past_time2 = datetime.now(timezone.utc) - timedelta(days=2, hours=2)
    past_time3 = datetime.now(timezone.utc) - timedelta(days=1, hours=2)

    d1 = MedicationDose(schedule_id=sched.id, medicine_id=med.id, patient_id=pt.id, scheduled_time=past_time1, status=DoseStatus.SCHEDULED)
    d2 = MedicationDose(schedule_id=sched.id, medicine_id=med.id, patient_id=pt.id, scheduled_time=past_time2, status=DoseStatus.SCHEDULED)
    d3 = MedicationDose(schedule_id=sched.id, medicine_id=med.id, patient_id=pt.id, scheduled_time=past_time3, status=DoseStatus.SCHEDULED)
    db_session.add_all([d1, d2, d3])
    db_session.commit()

    # 1. Patient marks d1 as TAKEN
    resp_take = client.post(f"/api/v1/patient/doses/{d1.id}/take", headers=pt_headers)
    assert resp_take.status_code == 200
    db_session.refresh(d1)
    assert d1.status == DoseStatus.TAKEN
    assert d1.actual_time is not None

    # 2. Other patient cannot modify d1 (403)
    resp_unauth = client.post(f"/api/v1/patient/doses/{d2.id}/take", headers=other_headers)
    assert resp_unauth.status_code == 403

    # 3. Patient marks d2 as SKIPPED
    resp_skip = client.post(f"/api/v1/patient/doses/{d2.id}/skip", headers=pt_headers)
    assert resp_skip.status_code == 200
    db_session.refresh(d2)
    assert d2.status == DoseStatus.SKIPPED

    # 4. Reconcile overdue doses -> d3 must automatically become MISSED
    missed_count = dose_service.reconcile_missed_doses(patient_id=pt.id)
    assert missed_count >= 1
    db_session.refresh(d3)
    assert d3.status == DoseStatus.MISSED

    # 5. Adherence calculation:
    # Taken = 1, Skipped = 1, Missed = 1, Total Expected = 3
    # Adherence = (1 / 3) * 100 = 33.3% -> 'High Risk'
    adherence = adherence_service.calculate_adherence(patient_id=pt.id, days=30)
    assert adherence["taken_count"] == 1
    assert adherence["skipped_count"] == 1
    assert adherence["missed_count"] == 1
    assert adherence["total_expected_doses"] == 3
    assert adherence["adherence_percentage"] == 33.3
    assert adherence["adherence_status"] == "High Risk"


# =====================================================================
# 6. AUDIT LOGGING SECURITY
# =====================================================================

def test_audit_logging_and_sanitization(db_session: Session, auth_headers_factory):
    """Verify audit logs are recorded and do not store sensitive credentials."""
    admin, _ = auth_headers_factory("audit_admin@pillsync.com", UserRole.ADMIN)
    admin_service = AdminService(db_session)

    cg, _ = auth_headers_factory("cg_audit@pillsync.com", UserRole.CAREGIVER, approval_status=ApprovalStatus.PENDING, is_active=False)
    admin_service.approve_caregiver(cg.id, admin)

    logs = admin_service.get_audit_logs(limit=10)
    assert len(logs) > 0
    approve_log = next((l for l in logs if l["action"] == "CAREGIVER_APPROVED"), None)
    assert approve_log is not None
    assert approve_log["actor_name"] == admin.name
    # Ensure details do not include passwords
    details = approve_log["details"] or {}
    assert "password" not in details
    assert "password_hash" not in details


# =====================================================================
# 7. ADMIN DASHBOARD METRICS & REAL DB INTEGRATION
# =====================================================================

def test_admin_dashboard_endpoint_success_and_metrics(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify Admin Dashboard returns 200 and accurate live metrics from database."""
    admin, admin_headers = auth_headers_factory("admin_dashboard_test@pillsync.com", UserRole.ADMIN)
    
    # Create test patients and caregivers
    auth_headers_factory("patient_db_1@pillsync.com", UserRole.PATIENT)
    auth_headers_factory("patient_db_2@pillsync.com", UserRole.PATIENT)
    auth_headers_factory("cg_pending_db@pillsync.com", UserRole.CAREGIVER, approval_status=ApprovalStatus.PENDING, is_active=False)
    auth_headers_factory("cg_approved_db@pillsync.com", UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED, is_active=True)

    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_patients"] >= 2
    assert data["total_caregivers"] >= 2
    assert data["pending_caregivers"] >= 1
    assert data["active_caregivers"] >= 1
    assert "today_doses_total" in data
    assert "total_medicines" in data


def test_admin_pending_caregivers_endpoint(client: TestClient, auth_headers_factory):
    """Verify /api/v1/admin/caregivers/pending returns all pending caregivers."""
    admin, admin_headers = auth_headers_factory("admin_pending_test@pillsync.com", UserRole.ADMIN)
    auth_headers_factory("cg_pending_item@pillsync.com", UserRole.CAREGIVER, approval_status=ApprovalStatus.PENDING, is_active=False, name="Pending Dr")

    response = client.get("/api/v1/admin/caregivers/pending", headers=admin_headers)
    assert response.status_code == 200
    pending_list = response.json()
    assert isinstance(pending_list, list)
    assert any(c["email"] == "cg_pending_item@pillsync.com" for c in pending_list)


# =====================================================================
# 8. ADMIN PATIENT MANAGEMENT & RBAC
# =====================================================================

def test_admin_get_patients_endpoint_success_and_metrics(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify Admin can retrieve all registered patients with real db data."""
    admin, admin_headers = auth_headers_factory("admin_patients_admin@pillsync.com", UserRole.ADMIN)
    pt1, _ = auth_headers_factory("pt1_managed@pillsync.com", UserRole.PATIENT, name="Patient One")
    pt2, _ = auth_headers_factory("pt2_managed@pillsync.com", UserRole.PATIENT, name="Patient Two")
    cg, _ = auth_headers_factory("cg_managed@pillsync.com", UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED, is_active=True, name="Dr. Supervisor")

    # Assign cg to pt1
    assign = CaregiverPatientAssignment(
        caregiver_id=cg.id,
        patient_id=pt1.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assign)

    # Add medication for pt1
    med = Medicine(
        user_id=pt1.id,
        name="Amoxicillin",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=20.0,
        start_date=date(2026, 8, 1),
        medicine_form=MedicineForm.CAPSULE,
        is_active=True
    )
    db_session.add(med)
    db_session.commit()

    # Query /api/v1/admin/patients
    response = client.get("/api/v1/admin/patients", headers=admin_headers)
    assert response.status_code == 200
    patients = response.json()
    assert isinstance(patients, list)
    assert len(patients) >= 2

    # Check pt1 details
    p1_item = next((p for p in patients if p["email"] == "pt1_managed@pillsync.com"), None)
    assert p1_item is not None
    assert p1_item["name"] == "Patient One"
    assert p1_item["assigned_caregiver_name"] == "Dr. Supervisor"
    assert p1_item["medications_count"] == 1
    assert p1_item["created_at"] is not None

    # Check pt2 details (unassigned)
    p2_item = next((p for p in patients if p["email"] == "pt2_managed@pillsync.com"), None)
    assert p2_item is not None
    assert p2_item["assigned_caregiver_name"] is None
    assert p2_item["medications_count"] == 0


def test_patient_cannot_access_admin_patients_endpoint(client: TestClient, auth_headers_factory):
    """Verify PATIENT role cannot access /api/v1/admin/patients (403 Forbidden)."""
    pt, pt_headers = auth_headers_factory("regular_pt@pillsync.com", UserRole.PATIENT)
    response = client.get("/api/v1/admin/patients", headers=pt_headers)
    assert response.status_code == 403


def test_caregiver_cannot_access_admin_patients_endpoint(client: TestClient, auth_headers_factory):
    """Verify CAREGIVER role cannot access /api/v1/admin/patients (403 Forbidden)."""
    cg, cg_headers = auth_headers_factory("cg_unauth@pillsync.com", UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED, is_active=True)
    response = client.get("/api/v1/admin/patients", headers=cg_headers)
    assert response.status_code == 403


def test_admin_toggle_patient_active(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify Admin can toggle a patient's active status."""
    admin, admin_headers = auth_headers_factory("admin_toggle@pillsync.com", UserRole.ADMIN)
    pt, _ = auth_headers_factory("pt_toggle@pillsync.com", UserRole.PATIENT, is_active=True)

    # Deactivate
    res1 = client.post(f"/api/v1/admin/patients/{pt.id}/toggle-active", headers=admin_headers)
    assert res1.status_code == 200
    assert res1.json()["is_active"] is False

    # Reactivate
    res2 = client.post(f"/api/v1/admin/patients/{pt.id}/toggle-active", headers=admin_headers)
    assert res2.status_code == 200
    assert res2.json()["is_active"] is True


# =====================================================================
# 9. CAREGIVER APPROVAL & REJECTION EMAIL NOTIFICATIONS
# =====================================================================

def test_caregiver_approval_and_rejection_email_notifications(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify approval and rejection trigger the appropriate emails with exact recipient."""
    admin, admin_headers = auth_headers_factory("admin_email_approver@pillsync.com", UserRole.ADMIN)
    cg1, _ = auth_headers_factory(
        "notify_approve@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False,
        name="Nurse Nancy"
    )
    cg2, _ = auth_headers_factory(
        "notify_reject@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False,
        name="Doctor Dan"
    )

    with patch("app.services.email_service.email_service.send_caregiver_approval_email", return_value=True) as mock_approve_email, \
         patch("app.services.email_service.email_service.send_caregiver_rejection_email", return_value=True) as mock_reject_email:

        # 1. Approve caregiver
        resp1 = client.post(f"/api/v1/admin/caregivers/{cg1.id}/approve", headers=admin_headers)
        assert resp1.status_code == 200
        assert resp1.json()["email_notification"] == "SENT"
        mock_approve_email.assert_called_once_with(to_email="notify_approve@pillsync.com", name="Nurse Nancy")

        # 2. Reject caregiver
        resp2 = client.post(f"/api/v1/admin/caregivers/{cg2.id}/reject", headers=admin_headers)
        assert resp2.status_code == 200
        assert resp2.json()["email_notification"] == "SENT"
        mock_reject_email.assert_called_once_with(to_email="notify_reject@pillsync.com", name="Doctor Dan", reason=None)


def test_email_delivery_failure_does_not_revert_database_state(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify that SMTP failure leaves DB state as APPROVED and reports FAILED notification."""
    admin, admin_headers = auth_headers_factory("admin_smtp_fail@pillsync.com", UserRole.ADMIN)
    cg, _ = auth_headers_factory(
        "smtp_fail_cg@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False,
        name="Fail Tester"
    )

    with patch("app.services.email_service.email_service.send_caregiver_approval_email", side_effect=Exception("SMTP Connection Timeout")):
        resp = client.post(f"/api/v1/admin/caregivers/{cg.id}/approve", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_notification"] == "FAILED"
        assert data["status"] == "APPROVED"

        # Verify DB is updated to APPROVED
        db_session.refresh(cg)
        assert cg.approval_status == ApprovalStatus.APPROVED
        assert cg.is_active is True


def test_repeated_approval_does_not_send_duplicate_email(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify already approved caregiver does not trigger duplicate emails."""
    admin, admin_headers = auth_headers_factory("admin_dup_test@pillsync.com", UserRole.ADMIN)
    cg, _ = auth_headers_factory(
        "already_approved_cg@pillsync.com",
        UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
        name="Approved Caregiver"
    )

    with patch("app.services.email_service.email_service.send_caregiver_approval_email") as mock_approve_email:
        resp = client.post(f"/api/v1/admin/caregivers/{cg.id}/approve", headers=admin_headers)
        assert resp.status_code == 200
        mock_approve_email.assert_not_called()


# =====================================================================
# 10. DOSE TAKEN TIME ACCURACY & TIMEZONE AWARENESS
# =====================================================================

def test_dose_actual_time_timezone_and_persistence(client: TestClient, auth_headers_factory, db_session: Session):
    """Verify actual_time records exact moment of intake, uses ISO UTC with Z, and remains immutable."""
    pt, pt_headers = auth_headers_factory("pt_time_test@pillsync.com", UserRole.PATIENT)

    med = Medicine(
        user_id=pt.id,
        name="Paracetamol",
        dosage_amount=650.0,
        dosage_unit=DosageUnit.MG,
        quantity=10.0,
        start_date=date(2026, 8, 1),
        medicine_form=MedicineForm.TABLET
    )
    db_session.add(med)
    db_session.commit()

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["20:00"],
        start_date=date(2026, 8, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # Scheduled for 20:00 on future/today time
    scheduled_dt = datetime(2026, 8, 20, 20, 0, 0, tzinfo=timezone.utc)
    dose = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=pt.id,
        scheduled_time=scheduled_dt,
        status=DoseStatus.SCHEDULED
    )
    db_session.add(dose)
    db_session.commit()
    db_session.refresh(dose)

    # 1. Mark as TAKEN
    before_take = datetime.now(timezone.utc)
    resp = client.post(f"/api/v1/patient/doses/{dose.id}/take", headers=pt_headers)
    after_take = datetime.now(timezone.utc)

    assert resp.status_code == 200
    data = resp.json()["dose"]
    assert data["status"] == "TAKEN"
    assert data["actual_time"] is not None
    assert data["actual_time"].endswith("Z")

    # Verify actual_time is distinct from scheduled_time
    assert data["actual_time"] != data["scheduled_time"]

    # Verify stored actual_time in database is within the execution window
    db_session.refresh(dose)
    actual_utc = dose.actual_time
    if actual_utc.tzinfo is None:
        actual_utc = actual_utc.replace(tzinfo=timezone.utc)
    assert before_take <= actual_utc <= after_take

    # 2. Repeated call should return same actual_time and not overwrite
    original_actual_time = data["actual_time"]
    resp2 = client.post(f"/api/v1/patient/doses/{dose.id}/take", headers=pt_headers)
    assert resp2.status_code == 200
    assert resp2.json()["dose"]["actual_time"] == original_actual_time




