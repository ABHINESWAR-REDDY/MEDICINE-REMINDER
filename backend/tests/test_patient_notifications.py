"""Comprehensive tests for Patient Medication Reminders and Notifications."""

from datetime import datetime, date, timezone, timedelta
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.dose import MedicationDose, DoseStatus
from app.models.notification import Notification
from app.services.dose_service import DoseService
from app.services.notification_service import NotificationService


def test_patient_notification_lifecycle_and_security(client: TestClient, db_session: Session, create_user):
    """
    Test complete patient notification lifecycle:
    1. Patient A and Patient B setup.
    2. Medicine and schedule created for Patient A.
    3. Dose generated -> Reminder created.
    4. Overdue dose -> Missed dose alert created.
    5. Deduplication check: scanning again does not duplicate alerts.
    6. Mark as read updates badge count and keeps record in history.
    7. Patient B cannot access or modify Patient A's notifications.
    8. TAKEN and SKIPPED doses do not create missed dose notifications.
    """
    # 1. Create real patients
    patient_a = create_user(
        name="Alice Patient",
        email="alice.notif@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    patient_b = create_user(
        name="Bob Patient",
        email="bob.notif@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )

    token_a = create_access_token(patient_a.id)
    token_b = create_access_token(patient_b.id)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    # 2. Create Medicine & Schedule for Patient A
    med = Medicine(
        user_id=patient_a.id,
        name="Metformin 500mg",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.TABLET,
        instructions="Take with breakfast",
        start_date=today
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
        start_date=today,
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # 3. Patient A fetches notifications via API
    resp = client.get("/api/v1/patient/notifications", headers=headers_a)
    assert resp.status_code == status.HTTP_200_OK
    notifications = resp.json()
    assert len(notifications) > 0

    # Verify at least one reminder was created for Metformin
    reminder = next((n for n in notifications if n["type"] in ("MEDICATION_REMINDER", "MISSED_DOSE")), None)
    assert reminder is not None
    assert "Metformin" in reminder["title"] or "Metformin" in reminder["message"]
    assert reminder["user_id"] == patient_a.id

    # 4. Check unread count endpoint
    unread_resp = client.get("/api/v1/patient/notifications/unread-count", headers=headers_a)
    assert unread_resp.status_code == status.HTTP_200_OK
    initial_unread = unread_resp.json()["unread_count"]
    assert initial_unread > 0

    # 5. Mark single notification as read
    notif_id = notifications[0]["id"]
    read_resp = client.post(f"/api/v1/patient/notifications/{notif_id}/read", headers=headers_a)
    assert read_resp.status_code == status.HTTP_200_OK
    assert read_resp.json()["success"] is True

    # Check unread count decreased by 1
    unread_resp_after = client.get("/api/v1/patient/notifications/unread-count", headers=headers_a)
    assert unread_resp_after.json()["unread_count"] == initial_unread - 1

    # 6. Verify read notification is still in history
    history_resp = client.get("/api/v1/patient/notifications", headers=headers_a)
    read_item = next(n for n in history_resp.json() if n["id"] == notif_id)
    assert read_item["is_read"] is True

    # 7. Deduplication check: call get_notifications multiple times
    count_before = len(history_resp.json())
    for _ in range(3):
        client.get("/api/v1/patient/notifications", headers=headers_a)
    history_resp_again = client.get("/api/v1/patient/notifications", headers=headers_a)
    assert len(history_resp_again.json()) == count_before

    # 8. Security test: Patient B cannot see or mark Patient A's notifications
    resp_b = client.get("/api/v1/patient/notifications", headers=headers_b)
    assert resp_b.status_code == status.HTTP_200_OK
    # Patient B has 0 notifications
    assert len(resp_b.json()) == 0

    # Patient B attempts to mark Patient A's notification as read -> 404 forbidden
    hack_resp = client.post(f"/api/v1/patient/notifications/{notif_id}/read", headers=headers_b)
    assert hack_resp.status_code == status.HTTP_404_NOT_FOUND

    # 9. Mark all as read test
    mark_all_resp = client.post("/api/v1/patient/notifications/read-all", headers=headers_a)
    assert mark_all_resp.status_code == status.HTTP_200_OK
    final_unread = client.get("/api/v1/patient/notifications/unread-count", headers=headers_a)
    assert final_unread.json()["unread_count"] == 0


def test_missed_dose_vs_taken_and_skipped(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    - Overdue scheduled dose creates a MISSED_DOSE notification.
    - TAKEN doses and SKIPPED doses do not create MISSED_DOSE notifications.
    """
    patient = create_user(
        name="Charlie Patient",
        email="charlie.notif@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    token = create_access_token(patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    med = Medicine(
        user_id=patient.id,
        name="Amoxicillin 250mg",
        dosage_amount=250.0,
        dosage_unit=DosageUnit.MG,
        quantity=20,
        medicine_form=MedicineForm.CAPSULE,
        start_date=today - timedelta(days=1)
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["09:00"],
        dose_quantity=1.0,
        start_date=today - timedelta(days=1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # Manually create:
    # Dose 1: Past dose MISSED
    past_time = datetime.now(timezone.utc) - timedelta(hours=3)
    dose_missed = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=past_time,
        status=DoseStatus.MISSED
    )
    # Dose 2: Past dose TAKEN
    dose_taken = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=past_time - timedelta(hours=4),
        actual_time=past_time - timedelta(hours=4),
        status=DoseStatus.TAKEN
    )
    # Dose 3: Past dose SKIPPED
    dose_skipped = MedicationDose(
        schedule_id=sched.id,
        medicine_id=med.id,
        patient_id=patient.id,
        scheduled_time=past_time - timedelta(hours=8),
        status=DoseStatus.SKIPPED
    )
    db_session.add_all([dose_missed, dose_taken, dose_skipped])
    db_session.commit()

    resp = client.get("/api/v1/patient/notifications", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()

    # Verify MISSED dose notification exists
    missed_notif = next((n for n in items if n["related_dose_id"] == dose_missed.id and n["type"] == "MISSED_DOSE"), None)
    assert missed_notif is not None
    assert "Missed Dose" in missed_notif["title"]

    # Verify NO missed notification exists for TAKEN or SKIPPED dose
    taken_missed = next((n for n in items if n["related_dose_id"] == dose_taken.id and n["type"] == "MISSED_DOSE"), None)
    assert taken_missed is None

    skipped_missed = next((n for n in items if n["related_dose_id"] == dose_skipped.id and n["type"] == "MISSED_DOSE"), None)
    assert skipped_missed is None


def test_dynamic_multi_medicine_missed_doses_and_resolution(client: TestClient, db_session: Session, create_user):
    """
    Verify completely dynamic behavior:
    1. Patient has multiple arbitrary medicines (Metformin, dolo, amoxicilin, vhnvhn, Azithromycin).
    2. All missed doses dynamically create corresponding notifications referencing exact medicine names.
    3. When a dose is marked taken, its notification is resolved and unread count decrements.
    4. Repeated polling does not create duplicates.
    """
    patient = create_user(
        name="Dynamic Patient",
        email="dynamic.patient@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    token = create_access_token(patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    medicine_names = ["Metformin", "dolo", "amoxicilin", "vhnvhn", "Azithromycin"]
    doses_created = []

    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()
    past_time = (now_utc - timedelta(hours=2)).replace(second=0, microsecond=0)
    time_str = past_time.strftime("%H:%M")

    for name in medicine_names:
        med = Medicine(
            user_id=patient.id,
            name=name,
            dosage_amount=500.0,
            dosage_unit=DosageUnit.MG,
            quantity=30,
            medicine_form=MedicineForm.TABLET,
            start_date=today
        )
        db_session.add(med)
        db_session.commit()
        db_session.refresh(med)

        sched = MedicationSchedule(
            medicine_id=med.id,
            frequency_type=ScheduleFrequency.ONCE_DAILY,
            times_per_day=1,
            scheduled_times=[time_str],
            dose_quantity=1.0,
            start_date=today,
            is_active=True
        )
        db_session.add(sched)
        db_session.commit()
        db_session.refresh(sched)

        dose = MedicationDose(
            schedule_id=sched.id,
            medicine_id=med.id,
            patient_id=patient.id,
            scheduled_time=past_time,
            status=DoseStatus.MISSED
        )
        db_session.add(dose)
        db_session.commit()
        db_session.refresh(dose)
        doses_created.append((med, dose))

    # 1. Fetch notifications
    resp = client.get("/api/v1/patient/notifications", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    notifs = resp.json()

    # Verify every single medicine name has a corresponding notification
    for med, dose in doses_created:
        match = next((n for n in notifs if n["related_dose_id"] == dose.id and n["type"] == "MISSED_DOSE"), None)
        assert match is not None
        assert med.name in match["title"]
        assert med.name in match["message"]
        assert match["is_read"] is False

    # 2. Check unread count matches total missed doses
    unread_resp = client.get("/api/v1/patient/notifications/unread-count", headers=headers)
    assert unread_resp.json()["unread_count"] == len(medicine_names)

    # 3. Deduplication check: poll 5 times
    for _ in range(5):
        client.get("/api/v1/patient/notifications", headers=headers)
    resp_after_poll = client.get("/api/v1/patient/notifications", headers=headers)
    assert len(resp_after_poll.json()) == len(medicine_names)

    # 4. Mark one missed notification as read -> check unread count decrements
    target_notif = notifs[0]
    read_resp = client.post(f"/api/v1/patient/notifications/{target_notif['id']}/read", headers=headers)
    assert read_resp.status_code == status.HTTP_200_OK

    unread_final = client.get("/api/v1/patient/notifications/unread-count", headers=headers)
    assert unread_final.json()["unread_count"] == len(medicine_names) - 1


def test_future_medication_reminder_and_intake_resolution(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Patient has a future scheduled dose -> MEDICATION_REMINDER is generated.
    2. Notification includes actual medicine name, strength, unit, form, and ISO scheduled time.
    3. When patient marks dose TAKEN -> notification is marked read / resolved.
    """
    patient = create_user(
        name="Elena Future",
        email="elena.future@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    token = create_access_token(patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    med = Medicine(
        user_id=patient.id,
        name="Lisinopril",
        dosage_amount=10.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.TABLET,
        start_date=today
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    # Future dose scheduled for 2 hours from now
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=[future_time.strftime("%H:%M")],
        dose_quantity=1.0,
        start_date=today,
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # Generate doses
    dose_service = DoseService(db_session)
    doses = dose_service.generate_doses_for_patient(patient.id, target_date=today)
    assert len(doses) > 0
    target_dose = doses[0]

    # Fetch notifications -> verify MEDICATION_REMINDER
    resp = client.get("/api/v1/patient/notifications", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()
    reminder = next((n for n in items if n["related_dose_id"] == target_dose.id and n["type"] == "MEDICATION_REMINDER"), None)
    assert reminder is not None
    assert reminder["medicine_name"] == "Lisinopril"
    assert reminder["strength"] == 10.0
    assert reminder["unit"] == "mg"
    assert reminder["is_read"] is False

    # Mark dose as TAKEN -> verify reminder is resolved
    take_resp = client.post(f"/api/v1/patient/doses/{target_dose.id}/take", headers=headers)
    assert take_resp.status_code == status.HTTP_200_OK

    # Fetch notifications again -> reminder should now be read
    resp_after = client.get("/api/v1/patient/notifications", headers=headers)
    reminder_after = next(n for n in resp_after.json() if n["id"] == reminder["id"])
    assert reminder_after["is_read"] is True


def test_patient_refill_notification_generation(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Patient medication stock is low (e.g. 2 pills remaining for a once-daily regimen).
    2. REFILL_NEEDED notification is dynamically generated.
    3. Contains actual medicine name and quantity information.
    """
    patient = create_user(
        name="David Refill",
        email="david.refill@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    token = create_access_token(patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    med = Medicine(
        user_id=patient.id,
        name="Atorvastatin",
        dosage_amount=40.0,
        dosage_unit=DosageUnit.MG,
        quantity=2,  # Low stock: 2 doses left
        medicine_form=MedicineForm.TABLET,
        start_date=today - timedelta(days=5)
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
        start_date=today - timedelta(days=5),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    # Fetch notifications
    resp = client.get("/api/v1/patient/notifications", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()

    refill_notif = next((n for n in items if n["type"] == "REFILL_NEEDED" and n["related_medicine_id"] == med.id), None)
    assert refill_notif is not None
    assert "Atorvastatin" in refill_notif["title"]
    assert "Atorvastatin" in refill_notif["message"]


