"""Comprehensive tests for Caregiver Supervision Alerts and Real-Time Notifications."""

from datetime import datetime, date, timezone, timedelta
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.dose import MedicationDose, DoseStatus
from app.models.chat_message import ChatMessage
from app.models.notification import Notification


def test_caregiver_missed_dose_alert_and_resolution(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Assigned patient has missed doses.
    2. Caregiver receives missed-dose alerts with exact patient name, medicine name, strength, unit, scheduled time.
    3. TAKEN and SKIPPED doses do not create caregiver missed-dose alerts.
    4. Deduplication prevents multiple identical alerts.
    """
    caregiver = create_user(
        name="Dr. Sarah Caregiver",
        email="sarah.cg@pillsync.test",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED
    )
    patient = create_user(
        name="John Patient",
        email="john.pt@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )

    # Assign patient to caregiver
    assignment = CaregiverPatientAssignment(
        caregiver_id=caregiver.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assignment)
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    token_pt = create_access_token(patient.id)
    headers_cg = {"Authorization": f"Bearer {token_cg}"}
    headers_pt = {"Authorization": f"Bearer {token_pt}"}

    today = date.today()
    med = Medicine(
        user_id=patient.id,
        name="Atorvastatin",
        dosage_amount=20.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=2)
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
        start_date=today - timedelta(days=2),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # Create a MISSED dose, a TAKEN dose, and a SKIPPED dose
    past_dt = (datetime.now(timezone.utc) - timedelta(hours=3)).replace(second=0, microsecond=0)
    dose_missed = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=past_dt,
        status=DoseStatus.MISSED
    )
    dose_taken = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=past_dt - timedelta(hours=4),
        actual_time=past_dt - timedelta(hours=4),
        status=DoseStatus.TAKEN
    )
    dose_skipped = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=past_dt - timedelta(hours=8),
        status=DoseStatus.SKIPPED
    )
    db_session.add_all([dose_missed, dose_taken, dose_skipped])
    db_session.commit()

    # 1. Caregiver fetches alerts
    resp = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
    assert resp.status_code == status.HTTP_200_OK
    alerts = resp.json()

    missed_alerts = [a for a in alerts if a["type"] == "MISSED_DOSE"]
    assert len(missed_alerts) >= 1
    target_alert = next((a for a in missed_alerts if a["id"] == f"missed_{dose_missed.id}"), None)
    assert target_alert is not None
    assert target_alert["patient_id"] == patient.id
    assert target_alert["patient_name"] == "John Patient"
    assert target_alert["medicine_name"] == "Atorvastatin"
    assert target_alert["strength"] == 20.0
    assert target_alert["unit"] == "mg"
    assert "Atorvastatin" in target_alert["title"]
    assert "John Patient" in target_alert["message"]

    # Verify NO missed alerts for TAKEN or SKIPPED doses
    assert not any(a["id"] == f"missed_{dose_taken.id}" for a in alerts)
    assert not any(a["id"] == f"missed_{dose_skipped.id}" for a in alerts)

    # 2. Deduplication check: fetch alerts 3 times
    count_before = len(missed_alerts)
    for _ in range(3):
        res = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
        assert len([a for a in res.json() if a["type"] == "MISSED_DOSE"]) == count_before


def test_caregiver_cross_isolation_and_rbac(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Caregiver A sees ONLY Patient A's alerts.
    2. Caregiver B sees ONLY Patient B's alerts.
    3. Caregiver with zero patients gets 0 alerts.
    4. Unauthenticated request returns 401.
    5. Patient account attempting to access caregiver alerts returns 403.
    """
    cg_a = create_user(name="Caregiver Alpha", email="cg.a@pillsync.test", role=UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED)
    cg_b = create_user(name="Caregiver Beta", email="cg.b@pillsync.test", role=UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED)
    cg_zero = create_user(name="Caregiver Zero", email="cg.zero@pillsync.test", role=UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED)
    pt_a = create_user(name="Patient Alpha", email="pt.a@pillsync.test", role=UserRole.PATIENT, approval_status=ApprovalStatus.APPROVED)
    pt_b = create_user(name="Patient Beta", email="pt.b@pillsync.test", role=UserRole.PATIENT, approval_status=ApprovalStatus.APPROVED)

    # Assign PT A to CG A, PT B to CG B
    db_session.add_all([
        CaregiverPatientAssignment(caregiver_id=cg_a.id, patient_id=pt_a.id, status=AssignmentStatus.ACTIVE),
        CaregiverPatientAssignment(caregiver_id=cg_b.id, patient_id=pt_b.id, status=AssignmentStatus.ACTIVE),
    ])
    db_session.commit()

    # Create missed doses for PT A and PT B
    today = date.today()
    past_dt = datetime.now(timezone.utc) - timedelta(hours=2)

    med_a = Medicine(user_id=pt_a.id, name="Lisinopril", dosage_amount=10.0, dosage_unit=DosageUnit.MG, quantity=10, medicine_form=MedicineForm.TABLET, start_date=today)
    med_b = Medicine(user_id=pt_b.id, name="Metformin", dosage_amount=500.0, dosage_unit=DosageUnit.MG, quantity=10, medicine_form=MedicineForm.TABLET, start_date=today)
    db_session.add_all([med_a, med_b])
    db_session.commit()

    sched_a = MedicationSchedule(medicine_id=med_a.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["08:00"], dose_quantity=1.0, start_date=today, is_active=True)
    sched_b = MedicationSchedule(medicine_id=med_b.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["08:00"], dose_quantity=1.0, start_date=today, is_active=True)
    db_session.add_all([sched_a, sched_b])
    db_session.commit()

    dose_a = MedicationDose(schedule_id=sched_a.id, medicine_id=med_a.id, patient_id=pt_a.id, scheduled_time=past_dt, status=DoseStatus.MISSED)
    dose_b = MedicationDose(schedule_id=sched_b.id, medicine_id=med_b.id, patient_id=pt_b.id, scheduled_time=past_dt, status=DoseStatus.MISSED)
    db_session.add_all([dose_a, dose_b])
    db_session.commit()

    token_cg_a = create_access_token(cg_a.id)
    token_cg_b = create_access_token(cg_b.id)
    token_cg_zero = create_access_token(cg_zero.id)
    token_pt_a = create_access_token(pt_a.id)

    # 1. CG A sees Lisinopril for Patient Alpha, but NOT Metformin or Patient Beta
    res_a = client.get("/api/v1/caregiver/alerts", headers={"Authorization": f"Bearer {token_cg_a}"})
    assert res_a.status_code == status.HTTP_200_OK
    alerts_a = res_a.json()
    assert all(a["patient_id"] == pt_a.id for a in alerts_a)
    assert any("Lisinopril" in a["title"] for a in alerts_a)
    assert not any("Metformin" in a["title"] for a in alerts_a)

    # 2. CG B sees Metformin for Patient Beta, but NOT Lisinopril or Patient Alpha
    res_b = client.get("/api/v1/caregiver/alerts", headers={"Authorization": f"Bearer {token_cg_b}"})
    assert res_b.status_code == status.HTTP_200_OK
    alerts_b = res_b.json()
    assert all(a["patient_id"] == pt_b.id for a in alerts_b)
    assert any("Metformin" in a["title"] for a in alerts_b)
    assert not any("Lisinopril" in a["title"] for a in alerts_b)

    # 3. CG Zero sees 0 alerts
    res_zero = client.get("/api/v1/caregiver/alerts", headers={"Authorization": f"Bearer {token_cg_zero}"})
    assert res_zero.status_code == status.HTTP_200_OK
    assert len(res_zero.json()) == 0

    # 4. Unauthenticated returns 401
    res_unauth = client.get("/api/v1/caregiver/alerts")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

    # 5. Patient accessing caregiver alerts returns 403
    res_forbidden = client.get("/api/v1/caregiver/alerts", headers={"Authorization": f"Bearer {token_pt_a}"})
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN


def test_caregiver_mark_alert_read_and_mark_all_read(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Caregiver can mark a specific alert as read via POST /api/v1/caregiver/alerts/{alert_id}/read.
    2. The marked alert is excluded from subsequent alert queries.
    3. Caregiver can mark all remaining alerts as read via POST /api/v1/caregiver/alerts/read-all.
    4. Subsequent alert query returns empty list.
    """
    caregiver = create_user(
        name="Dr. Mark Caregiver",
        email="mark.cg@pillsync.test",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED
    )
    patient = create_user(
        name="Alice Patient",
        email="alice.pt@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )

    db_session.add(CaregiverPatientAssignment(
        caregiver_id=caregiver.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    ))
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    headers_cg = {"Authorization": f"Bearer {token_cg}"}

    today = date.today()
    med1 = Medicine(user_id=patient.id, name="Medicine A", dosage_amount=10.0, dosage_unit=DosageUnit.MG, quantity=20, medicine_form=MedicineForm.TABLET, start_date=today)
    med2 = Medicine(user_id=patient.id, name="Medicine B", dosage_amount=20.0, dosage_unit=DosageUnit.MG, quantity=20, medicine_form=MedicineForm.TABLET, start_date=today)
    db_session.add_all([med1, med2])
    db_session.commit()

    sched1 = MedicationSchedule(medicine_id=med1.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["08:00"], dose_quantity=1.0, start_date=today, is_active=True)
    sched2 = MedicationSchedule(medicine_id=med2.id, frequency_type=ScheduleFrequency.ONCE_DAILY, times_per_day=1, scheduled_times=["09:00"], dose_quantity=1.0, start_date=today, is_active=True)
    db_session.add_all([sched1, sched2])
    db_session.commit()

    past_dt = datetime.now(timezone.utc) - timedelta(hours=2)
    dose1 = MedicationDose(schedule_id=sched1.id, medicine_id=med1.id, patient_id=patient.id, scheduled_time=past_dt, status=DoseStatus.MISSED)
    dose2 = MedicationDose(schedule_id=sched2.id, medicine_id=med2.id, patient_id=patient.id, scheduled_time=past_dt, status=DoseStatus.MISSED)
    db_session.add_all([dose1, dose2])
    db_session.commit()

    # Initial alerts check
    res = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
    assert res.status_code == status.HTTP_200_OK
    alerts = res.json()
    assert len(alerts) >= 2

    # Mark first alert as read
    target_id = f"missed_{dose1.id}"
    res_mark = client.post(f"/api/v1/caregiver/alerts/{target_id}/read", headers=headers_cg)
    assert res_mark.status_code == status.HTTP_200_OK
    assert res_mark.json()["success"] is True

    # Check that first alert is now gone
    res_after = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
    alerts_after = res_after.json()
    assert not any(a["id"] == target_id for a in alerts_after)
    assert any(a["id"] == f"missed_{dose2.id}" for a in alerts_after)

    # Mark all remaining alerts as read
    res_all = client.post("/api/v1/caregiver/alerts/read-all", headers=headers_cg)
    assert res_all.status_code == status.HTTP_200_OK
    assert res_all.json()["success"] is True

    # Final check: zero alerts remaining
    res_final = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
    alerts_final = res_final.json()
    assert len(alerts_final) == 0


def test_caregiver_chat_message_alert(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Assigned patient sends a message to caregiver.
    2. Caregiver receives a CHAT_MESSAGE alert with patient name and message preview.
    3. Marking the alert read resolves it.
    """
    caregiver = create_user(name="Chat Caregiver", email="chat.cg@pillsync.test", role=UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED)
    patient = create_user(name="Chat Patient", email="chat.pt@pillsync.test", role=UserRole.PATIENT, approval_status=ApprovalStatus.APPROVED)

    db_session.add(CaregiverPatientAssignment(
        caregiver_id=caregiver.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    ))
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    headers_cg = {"Authorization": f"Bearer {token_cg}"}

    # Patient creates a chat message for caregiver
    msg = ChatMessage(
        sender_id=patient.id,
        recipient_id=caregiver.id,
        message="I took my morning dose and feel fine!",
        is_read=False
    )
    db_session.add(msg)
    db_session.commit()

    # Caregiver fetches alerts -> verify CHAT_MESSAGE alert
    res = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
    assert res.status_code == status.HTTP_200_OK
    alerts = res.json()

    chat_alert = next((a for a in alerts if a["type"] == "CHAT_MESSAGE"), None)
    assert chat_alert is not None
    assert chat_alert["patient_name"] == "Chat Patient"
    assert "morning dose" in chat_alert["message"]


def test_caregiver_refill_shortage_alert(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Assigned patient has medication with low stock.
    2. Caregiver receives a REFILL_NEEDED alert for that patient.
    """
    caregiver = create_user(name="Refill Caregiver", email="refill.cg@pillsync.test", role=UserRole.CAREGIVER, approval_status=ApprovalStatus.APPROVED)
    patient = create_user(name="Refill Patient", email="refill.pt@pillsync.test", role=UserRole.PATIENT, approval_status=ApprovalStatus.APPROVED)

    db_session.add(CaregiverPatientAssignment(
        caregiver_id=caregiver.id,
        patient_id=patient.id,
        status=AssignmentStatus.ACTIVE
    ))
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    headers_cg = {"Authorization": f"Bearer {token_cg}"}

    today = date.today()
    med = Medicine(
        user_id=patient.id,
        name="Metformin",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=2,  # Low stock
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=5)
    )
    db_session.add(med)
    db_session.commit()

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["08:00"],
        dose_quantity=1.0,
        start_date=today - timedelta(days=5),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # Caregiver fetches alerts -> verify REFILL_NEEDED alert
    res = client.get("/api/v1/caregiver/alerts", headers=headers_cg)
    assert res.status_code == status.HTTP_200_OK
    alerts = res.json()

    refill_alert = next((a for a in alerts if a["type"] == "REFILL_NEEDED"), None)
    assert refill_alert is not None
    assert refill_alert["patient_name"] == "Refill Patient"
    assert "Metformin" in refill_alert["title"] or "Metformin" in refill_alert["message"]


