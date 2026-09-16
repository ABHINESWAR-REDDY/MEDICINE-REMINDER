"""Unit and integration tests for Patient Medicine management."""

import pytest
from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus
from app.models.condition import Condition
from app.models.prescription import Prescription


def test_create_and_manage_medicine(client, db_session):
    """Patient can create, list, update, deactivate, and delete medicines."""
    patient = User(
        name="Med Patient",
        email="patient_med@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()

    # Create condition & prescription for patient
    cond = Condition(user_id=patient.id, name="Hypertension")
    rx = Prescription(user_id=patient.id, prescription_number="RX-001")
    db_session.add_all([cond, rx])
    db_session.commit()

    token = create_access_token(subject=patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Medicine
    res = client.post(
        "/api/v1/medicines",
        json={
            "name": "Lisinopril",
            "dosage_amount": 10.0,
            "dosage_unit": "mg",
            "quantity": 30,
            "medicine_form": "TABLET",
            "instructions": "Take 1 tablet every morning",
            "start_date": "2026-08-17",
            "end_date": "2026-09-17",
            "condition_id": cond.id,
            "prescription_id": rx.id,
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Lisinopril"
    assert data["dosage_amount"] == 10.0
    assert data["dosage_unit"] == "mg"
    assert data["quantity"] == 30
    assert data["user_id"] == patient.id
    assert data["condition"]["name"] == "Hypertension"
    assert data["prescription"]["prescription_number"] == "RX-001"
    med_id = data["id"]

    # 2. List Medicines
    res = client.get("/api/v1/medicines", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 3. Update Medicine
    res = client.put(
        f"/api/v1/medicines/{med_id}",
        json={"dosage_amount": 20.0, "quantity": 60},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["dosage_amount"] == 20.0
    assert res.json()["quantity"] == 60

    # 4. Deactivate Medicine
    res = client.post(f"/api/v1/medicines/{med_id}/deactivate", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # 5. List Active Medicines only
    res_active = client.get("/api/v1/medicines?is_active=true", headers=headers)
    assert res_active.status_code == 200
    assert len(res_active.json()) == 0

    # 6. Delete Medicine
    res = client.delete(f"/api/v1/medicines/{med_id}", headers=headers)
    assert res.status_code == 200

    # 7. Verify Deleted
    res = client.get(f"/api/v1/medicines/{med_id}", headers=headers)
    assert res.status_code == 404


def test_medicine_validation_and_cross_user_isolation(client, db_session):
    """Validation checks on dosages, quantities, dates, and foreign key boundaries."""
    patient_a = User(
        name="Patient A Med",
        email="patient_a_med@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    patient_b = User(
        name="Patient B Med",
        email="patient_b_med@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    token_a = create_access_token(subject=patient_a.id)
    token_b = create_access_token(subject=patient_b.id)

    # Validation: Dosage <= 0 rejected
    res_bad_dose = client.post(
        "/api/v1/medicines",
        json={"name": "Aspirin", "dosage_amount": 0, "dosage_unit": "mg", "quantity": 10, "start_date": "2026-08-17"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_bad_dose.status_code == 422

    # Validation: Quantity <= 0 rejected
    res_bad_qty = client.post(
        "/api/v1/medicines",
        json={"name": "Aspirin", "dosage_amount": 500, "dosage_unit": "mg", "quantity": -5, "start_date": "2026-08-17"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_bad_qty.status_code == 422

    # Validation: End date before start date rejected
    res_bad_dates = client.post(
        "/api/v1/medicines",
        json={"name": "Aspirin", "dosage_amount": 500, "dosage_unit": "mg", "quantity": 10, "start_date": "2026-08-17", "end_date": "2026-08-01"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_bad_dates.status_code == 422

    # Patient A creates condition
    cond_a = Condition(user_id=patient_a.id, name="Patient A Condition")
    db_session.add(cond_a)
    db_session.commit()

    # Patient B attempts to reference Patient A's condition -> 400 Bad Request
    res_b_hijack_cond = client.post(
        "/api/v1/medicines",
        json={"name": "Metformin", "dosage_amount": 500, "dosage_unit": "mg", "quantity": 20, "start_date": "2026-08-17", "condition_id": cond_a.id},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_hijack_cond.status_code == 400

    # Patient A creates medicine
    res_a = client.post(
        "/api/v1/medicines",
        json={"name": "Aspirin", "dosage_amount": 81, "dosage_unit": "mg", "quantity": 100, "start_date": "2026-08-17"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 201
    med_a_id = res_a.json()["id"]

    # Patient B cannot view, update, deactivate, or delete Patient A's medicine
    assert client.get(f"/api/v1/medicines/{med_a_id}", headers={"Authorization": f"Bearer {token_b}"}).status_code == 404
    assert client.put(f"/api/v1/medicines/{med_a_id}", json={"quantity": 5}, headers={"Authorization": f"Bearer {token_b}"}).status_code == 404
    assert client.post(f"/api/v1/medicines/{med_a_id}/deactivate", headers={"Authorization": f"Bearer {token_b}"}).status_code == 404
    assert client.delete(f"/api/v1/medicines/{med_a_id}", headers={"Authorization": f"Bearer {token_b}"}).status_code == 404
