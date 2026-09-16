"""Unit and integration tests for Patient Prescription management."""

import pytest
from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus


def test_create_and_manage_prescription(client, db_session):
    """Patient can create, view, update, and delete prescriptions."""
    patient = User(
        name="Rx Patient",
        email="patient_rx@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()

    token = create_access_token(subject=patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Prescription
    res = client.post(
        "/api/v1/prescriptions",
        json={
            "prescription_number": "RX-2026-9901",
            "doctor_name": "Dr. Meredith Grey",
            "issue_date": "2026-08-01",
            "expiry_date": "2026-12-31",
            "status": "ACTIVE",
            "notes": "Take with breakfast",
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["prescription_number"] == "RX-2026-9901"
    assert data["doctor_name"] == "Dr. Meredith Grey"
    assert data["user_id"] == patient.id
    rx_id = data["id"]

    # 2. List Prescriptions
    res = client.get("/api/v1/prescriptions", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 3. Filter by Status
    res = client.get("/api/v1/prescriptions?status=ACTIVE", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 4. Update Prescription
    res = client.put(
        f"/api/v1/prescriptions/{rx_id}",
        json={"status": "EXPIRED"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "EXPIRED"

    # 5. Delete Prescription
    res = client.delete(f"/api/v1/prescriptions/{rx_id}", headers=headers)
    assert res.status_code == 200

    # 6. Verify Deleted
    res = client.get(f"/api/v1/prescriptions/{rx_id}", headers=headers)
    assert res.status_code == 404


def test_prescription_validation_and_cross_user_isolation(client, db_session):
    """Validation errors on invalid dates and cross-user isolation."""
    patient_a = User(
        name="Rx Patient A",
        email="patient_a_rx@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    patient_b = User(
        name="Rx Patient B",
        email="patient_b_rx@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    token_a = create_access_token(subject=patient_a.id)
    token_b = create_access_token(subject=patient_b.id)

    # Validation: Expiry date before issue date -> 422
    res_bad = client.post(
        "/api/v1/prescriptions",
        json={
            "prescription_number": "RX-BAD",
            "issue_date": "2026-10-01",
            "expiry_date": "2026-01-01",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_bad.status_code == 422

    # Patient A creates valid prescription
    res_a = client.post(
        "/api/v1/prescriptions",
        json={"prescription_number": "RX-A", "doctor_name": "Dr. House"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 201
    rx_a_id = res_a.json()["id"]

    # Patient B cannot view Patient A's prescription
    res_b_get = client.get(f"/api/v1/prescriptions/{rx_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_get.status_code == 404
