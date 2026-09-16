"""RBAC tests for Medication Management (Patient-only scope in Phase 2)."""

import pytest
from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus


def test_unauthenticated_requests_rejected(client):
    """Unauthenticated requests to medication endpoints return 401."""
    assert client.get("/api/v1/conditions").status_code == 401
    assert client.get("/api/v1/prescriptions").status_code == 401
    assert client.get("/api/v1/medicines").status_code == 401
    assert client.get("/api/v1/schedules").status_code == 401


def test_caregiver_and_admin_rejected_in_phase_2(client, db_session):
    """Caregiver and Admin roles are forbidden from managing patient medication in Phase 2."""
    caregiver = User(
        name="Nurse Joy",
        email="joy_caregiver@example.com",
        password_hash="fakehash",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    admin = User(
        name="Admin Boss",
        email="boss_admin@example.com",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True,
    )
    db_session.add_all([caregiver, admin])
    db_session.commit()

    token_cg = create_access_token(subject=caregiver.id)
    token_adm = create_access_token(subject=admin.id)

    # Caregiver 403 checks
    assert client.get("/api/v1/conditions", headers={"Authorization": f"Bearer {token_cg}"}).status_code == 403
    assert client.post("/api/v1/conditions", json={"name": "Flu"}, headers={"Authorization": f"Bearer {token_cg}"}).status_code == 403
    assert client.get("/api/v1/prescriptions", headers={"Authorization": f"Bearer {token_cg}"}).status_code == 403
    assert client.get("/api/v1/medicines", headers={"Authorization": f"Bearer {token_cg}"}).status_code == 403
    assert client.get("/api/v1/schedules", headers={"Authorization": f"Bearer {token_cg}"}).status_code == 403

    # Admin 403 checks
    assert client.get("/api/v1/conditions", headers={"Authorization": f"Bearer {token_adm}"}).status_code == 403
    assert client.get("/api/v1/prescriptions", headers={"Authorization": f"Bearer {token_adm}"}).status_code == 403
    assert client.get("/api/v1/medicines", headers={"Authorization": f"Bearer {token_adm}"}).status_code == 403
    assert client.get("/api/v1/schedules", headers={"Authorization": f"Bearer {token_adm}"}).status_code == 403
