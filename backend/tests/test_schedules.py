"""Unit and integration tests for Medication Dosage Schedules."""

from datetime import date
import pytest
from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus
from app.models.medicine import Medicine, DosageUnit, MedicineForm


def test_create_and_manage_schedule(client, db_session):
    """Patient can create and manage schedules for their own medicine."""
    patient = User(
        name="Schedule Patient",
        email="patient_sched@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()

    med = Medicine(
        user_id=patient.id,
        name="Metformin",
        dosage_amount=500,
        dosage_unit=DosageUnit.MG,
        quantity=60,
        medicine_form=MedicineForm.TABLET,
        start_date=date(2026, 8, 17),
    )
    db_session.add(med)
    db_session.commit()

    token = create_access_token(subject=patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create TWICE_DAILY schedule
    res = client.post(
        f"/api/v1/medicines/{med.id}/schedules",
        json={
            "frequency_type": "TWICE_DAILY",
            "times_per_day": 2,
            "scheduled_times": ["08:00", "20:00"],
            "dose_quantity": 1.0,
            "start_date": "2026-08-17",
            "end_date": "2026-09-17",
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["frequency_type"] == "TWICE_DAILY"
    assert data["scheduled_times"] == ["08:00", "20:00"]
    assert data["medicine_id"] == med.id
    sched_id = data["id"]

    # 2. List schedules for medicine
    res_list = client.get(f"/api/v1/medicines/{med.id}/schedules", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 3. List all user schedules
    res_all = client.get("/api/v1/schedules", headers=headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) == 1

    # 4. Get single schedule
    res_get = client.get(f"/api/v1/schedules/{sched_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == sched_id

    # 5. Update schedule
    res_put = client.put(
        f"/api/v1/schedules/{sched_id}",
        json={"dose_quantity": 2.0},
        headers=headers,
    )
    assert res_put.status_code == 200
    assert res_put.json()["dose_quantity"] == 2.0

    # 6. Delete schedule
    res_del = client.delete(f"/api/v1/schedules/{sched_id}", headers=headers)
    assert res_del.status_code == 200

    # 7. Verify deleted
    assert client.get(f"/api/v1/schedules/{sched_id}", headers=headers).status_code == 404


def test_schedule_validations_and_cross_user_isolation(client, db_session):
    """Validation checks on time format, count matching frequency, and cross-user ownership."""
    patient_a = User(
        name="Patient A Sched",
        email="patient_a_sched@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    patient_b = User(
        name="Patient B Sched",
        email="patient_b_sched@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    med_a = Medicine(
        user_id=patient_a.id,
        name="Atorvastatin",
        dosage_amount=20,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        start_date=date(2026, 8, 17),
    )
    db_session.add(med_a)
    db_session.commit()

    token_a = create_access_token(subject=patient_a.id)
    token_b = create_access_token(subject=patient_b.id)

    # Validation: Invalid time format "25:00" -> 422
    res_bad_time = client.post(
        f"/api/v1/medicines/{med_a.id}/schedules",
        json={
            "frequency_type": "ONCE_DAILY",
            "times_per_day": 1,
            "scheduled_times": ["25:00"],
            "start_date": "2026-08-17",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_bad_time.status_code == 422

    # Validation: Frequency count mismatch (TWICE_DAILY with 3 times) -> 422
    res_mismatch = client.post(
        f"/api/v1/medicines/{med_a.id}/schedules",
        json={
            "frequency_type": "TWICE_DAILY",
            "times_per_day": 2,
            "scheduled_times": ["08:00", "14:00", "20:00"],
            "start_date": "2026-08-17",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_mismatch.status_code == 422

    # Patient B attempts to create schedule for Patient A's medicine -> 404
    res_b_create = client.post(
        f"/api/v1/medicines/{med_a.id}/schedules",
        json={
            "frequency_type": "ONCE_DAILY",
            "times_per_day": 1,
            "scheduled_times": ["09:00"],
            "start_date": "2026-08-17",
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_create.status_code == 404
