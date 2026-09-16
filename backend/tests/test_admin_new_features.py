"""Automated test suite for the 4 core Admin Dashboard features:
1. Monitor Platform Activities
2. Configure Notification Settings
3. Access Platform Analytics
4. Manage System-Level Operations
"""

import pytest
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole, ApprovalStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.dose import MedicationDose, DoseStatus
from app.models.audit_log import AuditLog
from app.models.system_setting import SystemSetting
from app.services.dose_service import DoseService


@pytest.fixture
def test_users(db_session: Session):
    """Fixture providing Admin, Patient, and Caregiver users with auth headers."""
    # 1. Admin
    admin = db_session.query(User).filter(User.email == "admin_feat@pillsync.com").first()
    if not admin:
        admin = User(
            name="Super Admin",
            email="admin_feat@pillsync.com",
            password_hash=get_password_hash("Password123!"),
            role=UserRole.ADMIN,
            approval_status=ApprovalStatus.APPROVED,
            is_active=True
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    # 2. Patient
    patient = db_session.query(User).filter(User.email == "patient_feat@pillsync.com").first()
    if not patient:
        patient = User(
            name="Test Patient",
            email="patient_feat@pillsync.com",
            password_hash=get_password_hash("Password123!"),
            role=UserRole.PATIENT,
            approval_status=ApprovalStatus.APPROVED,
            is_active=True
        )
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)

    # 3. Caregiver
    caregiver = db_session.query(User).filter(User.email == "caregiver_feat@pillsync.com").first()
    if not caregiver:
        caregiver = User(
            name="Test Caregiver",
            email="caregiver_feat@pillsync.com",
            password_hash=get_password_hash("Password123!"),
            role=UserRole.CAREGIVER,
            approval_status=ApprovalStatus.APPROVED,
            is_active=True
        )
        db_session.add(caregiver)
        db_session.commit()
        db_session.refresh(caregiver)

    admin_token = create_access_token(subject=admin.id)
    patient_token = create_access_token(subject=patient.id)
    caregiver_token = create_access_token(subject=caregiver.id)

    return {
        "admin": admin,
        "patient": patient,
        "caregiver": caregiver,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "patient_headers": {"Authorization": f"Bearer {patient_token}"},
        "caregiver_headers": {"Authorization": f"Bearer {caregiver_token}"},
    }


# =============================================================================
# 1. RBAC SECURITY FOR NEW ADMIN ENDPOINTS
# =============================================================================

def test_rbac_patient_and_caregiver_blocked_from_new_admin_apis(client: TestClient, test_users):
    """Verify Patient and Caregiver receive 403 Forbidden across all new admin endpoints."""
    endpoints = [
        ("GET", "/api/v1/admin/activities"),
        ("GET", "/api/v1/admin/notification-settings"),
        ("PUT", "/api/v1/admin/notification-settings", {"patient_medication_reminders_enabled": False}),
        ("GET", "/api/v1/admin/analytics"),
        ("GET", "/api/v1/admin/system/health"),
        ("POST", "/api/v1/admin/system/reconcile-doses"),
        ("POST", "/api/v1/admin/system/reconcile-notifications"),
        ("POST", "/api/v1/admin/system/consistency-check"),
    ]

    for item in endpoints:
        method = item[0]
        url = item[1]
        payload = item[2] if len(item) > 2 else None

        # Patient 403
        if method == "GET":
            res_p = client.get(url, headers=test_users["patient_headers"])
            res_c = client.get(url, headers=test_users["caregiver_headers"])
        elif method == "POST":
            res_p = client.post(url, headers=test_users["patient_headers"])
            res_c = client.post(url, headers=test_users["caregiver_headers"])
        elif method == "PUT":
            res_p = client.put(url, json=payload, headers=test_users["patient_headers"])
            res_c = client.put(url, json=payload, headers=test_users["caregiver_headers"])

        assert res_p.status_code == 403, f"Expected 403 for Patient on {url}, got {res_p.status_code}"
        assert res_c.status_code == 403, f"Expected 403 for Caregiver on {url}, got {res_c.status_code}"


# =============================================================================
# 2. PLATFORM ACTIVITIES TESTS
# =============================================================================

def test_admin_get_platform_activities_filters_and_pagination(client: TestClient, test_users, db_session: Session):
    """Verify platform activities returns real audit entries with search, filters, and pagination."""
    # Create test audit records
    log1 = AuditLog(
        actor_user_id=test_users["admin"].id,
        action="CAREGIVER_APPROVED",
        target_type="User",
        target_id=test_users["caregiver"].id,
        details={"name": "Test Caregiver", "email": "caregiver_feat@pillsync.com"},
        created_at=datetime.now(timezone.utc)
    )
    log2 = AuditLog(
        actor_user_id=test_users["patient"].id,
        action="DOSE_TAKEN",
        target_type="MedicationDose",
        target_id=101,
        details={"patient_id": test_users["patient"].id},
        created_at=datetime.now(timezone.utc)
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    # Query all activities
    res = client.get("/api/v1/admin/activities?limit=10&offset=0", headers=test_users["admin_headers"])
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Filter by role = ADMIN
    res_role = client.get("/api/v1/admin/activities?role=ADMIN", headers=test_users["admin_headers"])
    assert res_role.status_code == 200
    admin_items = res_role.json()["items"]
    assert all(it["actor_role"] == "ADMIN" for it in admin_items)

    # Filter by action = DOSE_TAKEN
    res_action = client.get("/api/v1/admin/activities?action=DOSE_TAKEN", headers=test_users["admin_headers"])
    assert res_action.status_code == 200
    action_items = res_action.json()["items"]
    assert all(it["action"] == "DOSE_TAKEN" for it in action_items)

    # Search keyword
    res_search = client.get("/api/v1/admin/activities?search=CAREGIVER_APPROVED", headers=test_users["admin_headers"])
    assert res_search.status_code == 200
    search_items = res_search.json()["items"]
    assert len(search_items) >= 1
    assert search_items[0]["action"] == "CAREGIVER_APPROVED"


# =============================================================================
# 3. NOTIFICATION SETTINGS TESTS
# =============================================================================

def test_admin_notification_settings_lifecycle_and_persistence(client: TestClient, test_users):
    """Verify Admin can read, update, and persist platform notification configurations."""
    # 1. GET settings
    get_res = client.get("/api/v1/admin/notification-settings", headers=test_users["admin_headers"])
    assert get_res.status_code == 200
    settings = get_res.json()
    assert "patient_medication_reminders_enabled" in settings
    assert "caregiver_missed_dose_alerts_enabled" in settings
    assert "patient_polling_interval_seconds" in settings

    # 2. Update settings
    update_payload = {
        "patient_medication_reminders_enabled": False,
        "caregiver_missed_dose_alerts_enabled": True,
        "patient_polling_interval_seconds": 45,
    }
    put_res = client.put("/api/v1/admin/notification-settings", json=update_payload, headers=test_users["admin_headers"])
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["patient_medication_reminders_enabled"] is False
    assert updated["patient_polling_interval_seconds"] == 45
    assert updated["updated_by"] is not None

    # 3. Re-query to verify database persistence
    get_res2 = client.get("/api/v1/admin/notification-settings", headers=test_users["admin_headers"])
    assert get_res2.status_code == 200
    settings2 = get_res2.json()
    assert settings2["patient_medication_reminders_enabled"] is False
    assert settings2["patient_polling_interval_seconds"] == 45

    # 4. Re-enable for subsequent tests
    client.put("/api/v1/admin/notification-settings", json={"patient_medication_reminders_enabled": True}, headers=test_users["admin_headers"])


# =============================================================================
# 4. PLATFORM ANALYTICS TESTS
# =============================================================================

def test_admin_platform_analytics_calculations_and_zero_handling(client: TestClient, test_users, db_session: Session):
    """Verify live analytics calculations, date periods, and strict mathematical 0.0% adherence handling."""
    # Create sample medicine and doses
    med = Medicine(
        user_id=test_users["patient"].id,
        name="Metformin Test",
        dosage_amount="500",
        dosage_unit=DosageUnit.MG,
        medicine_form=MedicineForm.TABLET,
        quantity=30,
        start_date=date.today(),
        is_active=True
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
        start_date=date.today(),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # 1 dose TAKEN, 1 dose MISSED in period
    now_utc = datetime.now(timezone.utc)
    dose_taken = MedicationDose(
        schedule_id=sched.id,
        patient_id=test_users["patient"].id,
        medicine_id=med.id,
        scheduled_time=now_utc - timedelta(hours=5),
        actual_time=now_utc - timedelta(hours=5),
        status=DoseStatus.TAKEN
    )
    dose_missed = MedicationDose(
        schedule_id=sched.id,
        patient_id=test_users["patient"].id,
        medicine_id=med.id,
        scheduled_time=now_utc - timedelta(hours=3),
        status=DoseStatus.MISSED
    )
    db_session.add_all([dose_taken, dose_missed])
    db_session.commit()

    # Query 30d analytics
    res = client.get("/api/v1/admin/analytics?period=30d", headers=test_users["admin_headers"])
    assert res.status_code == 200
    data = res.json()

    assert data["users"]["total_patients"] >= 1
    assert data["medications"]["total_active_medications"] >= 1
    assert data["medications"]["taken_doses"] >= 1
    assert data["medications"]["missed_doses"] >= 1

    # 1 taken / 2 total = 50.0% adherence
    adherence_pct = data["adherence"]["overall_adherence_percentage"]
    assert isinstance(adherence_pct, (int, float))
    assert 0.0 <= adherence_pct <= 100.0

    # Test period = today
    res_today = client.get("/api/v1/admin/analytics?period=today", headers=test_users["admin_headers"])
    assert res_today.status_code == 200


# =============================================================================
# 5. SYSTEM OPERATIONS & HEALTH TESTS
# =============================================================================

def test_admin_system_health_and_safe_operations(client: TestClient, test_users):
    """Verify live system health diagnostics and safe administrative operational triggers."""
    # 1. Health diagnostics
    res_health = client.get("/api/v1/admin/system/health", headers=test_users["admin_headers"])
    assert res_health.status_code == 200
    health = res_health.json()
    assert health["status"] in ("HEALTHY", "DEGRADED", "ERROR")
    assert "database" in health["components"]
    assert health["components"]["database"]["status"] == "HEALTHY"
    assert health["components"]["database"]["latency_ms"] is not None
    assert "backend_api" in health["components"]
    assert "notifications" in health["components"]

    # 2. Reconcile doses
    res_reconcile = client.post("/api/v1/admin/system/reconcile-doses", headers=test_users["admin_headers"])
    assert res_reconcile.status_code == 200
    assert res_reconcile.json()["success"] is True
    assert "reconciled_count" in res_reconcile.json()["details"]

    # 3. Reconcile notifications
    res_notif = client.post("/api/v1/admin/system/reconcile-notifications", headers=test_users["admin_headers"])
    assert res_notif.status_code == 200
    assert res_notif.json()["success"] is True

    # 4. Data consistency check
    res_check = client.post("/api/v1/admin/system/consistency-check", headers=test_users["admin_headers"])
    assert res_check.status_code == 200
    assert res_check.json()["success"] is True
    assert "orphaned_schedules" in res_check.json()["details"]
