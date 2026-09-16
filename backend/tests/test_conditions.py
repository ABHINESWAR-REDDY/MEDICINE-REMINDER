"""Unit and integration tests for Patient Conditions / Disease tracking."""

import pytest
from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus


def test_create_and_list_condition(client, db_session):
    """Patient can create and list their own conditions."""
    patient = User(
        name="John Patient",
        email="patient_cond@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()

    token = create_access_token(subject=patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Condition
    res = client.post(
        "/api/v1/conditions",
        json={"name": "Hypertension", "description": "High blood pressure stage 1"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Hypertension"
    assert data["description"] == "High blood pressure stage 1"
    assert data["user_id"] == patient.id
    cond_id = data["id"]

    # 2. List Conditions
    res = client.get("/api/v1/conditions", headers=headers)
    assert res.status_code == 200
    conds = res.json()
    assert len(conds) == 1
    assert conds[0]["id"] == cond_id

    # 3. Get Single Condition
    res = client.get(f"/api/v1/conditions/{cond_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Hypertension"

    # 4. Update Condition
    res = client.put(
        f"/api/v1/conditions/{cond_id}",
        json={"description": "Controlled with medication"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Controlled with medication"

    # 5. Delete Condition
    res = client.delete(f"/api/v1/conditions/{cond_id}", headers=headers)
    assert res.status_code == 200

    # 6. Verify Deleted
    res = client.get(f"/api/v1/conditions/{cond_id}", headers=headers)
    assert res.status_code == 404


def test_cross_user_condition_isolation(client, db_session):
    """Patient B cannot view, edit, or delete Patient A's conditions."""
    patient_a = User(
        name="Patient A",
        email="patient_a_cond@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    patient_b = User(
        name="Patient B",
        email="patient_b_cond@example.com",
        password_hash="fakehash",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add_all([patient_a, patient_b])
    db_session.commit()

    token_a = create_access_token(subject=patient_a.id)
    token_b = create_access_token(subject=patient_b.id)

    # Patient A creates condition
    res_a = client.post(
        "/api/v1/conditions",
        json={"name": "Type 2 Diabetes", "description": "Patient A private condition"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 201
    cond_a_id = res_a.json()["id"]

    # Patient B lists conditions -> should be empty
    res_b = client.get("/api/v1/conditions", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert len(res_b.json()) == 0

    # Patient B attempts to get Patient A's condition -> 404
    res_b_get = client.get(f"/api/v1/conditions/{cond_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_get.status_code == 404

    # Patient B attempts to update Patient A's condition -> 404
    res_b_put = client.put(
        f"/api/v1/conditions/{cond_a_id}",
        json={"name": "Hacked Condition"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_put.status_code == 404

    # Patient B attempts to delete Patient A's condition -> 404
    res_b_del = client.delete(f"/api/v1/conditions/{cond_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b_del.status_code == 404
