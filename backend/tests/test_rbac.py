"""Role-Based Access Control (RBAC) tests verifying permission boundaries across roles."""

import pytest
from fastapi import APIRouter, Depends
from app.api.deps import require_patient, require_caregiver, require_admin
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.main import app

# Create a dedicated RBAC test router attached to the app for testing role guards
rbac_test_router = APIRouter(prefix="/api/v1/test-rbac")


@rbac_test_router.get("/patient-only")
def patient_endpoint(current_user: User = Depends(require_patient)):
    return {"message": "patient_access_granted", "user_id": current_user.id}


@rbac_test_router.get("/caregiver-only")
def caregiver_endpoint(current_user: User = Depends(require_caregiver)):
    return {"message": "caregiver_access_granted", "user_id": current_user.id}


@rbac_test_router.get("/admin-only")
def admin_endpoint(current_user: User = Depends(require_admin)):
    return {"message": "admin_access_granted", "user_id": current_user.id}


# Mount test router for test execution
app.include_router(rbac_test_router)


def test_unauthenticated_access_rejected_401(client):
    """Verify unauthenticated requests to protected RBAC endpoints return 401."""
    assert client.get("/api/v1/test-rbac/patient-only").status_code == 401
    assert client.get("/api/v1/test-rbac/caregiver-only").status_code == 401
    assert client.get("/api/v1/test-rbac/admin-only").status_code == 401


def test_patient_access_boundaries(client, create_user):
    """Verify PATIENT can access patient endpoints but is rejected (403) from CAREGIVER and ADMIN endpoints."""
    patient = create_user(name="Patient User", email="patient.rbac@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=patient.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Patient accessing patient endpoint -> 200 OK
    res_patient = client.get("/api/v1/test-rbac/patient-only", headers=headers)
    assert res_patient.status_code == 200
    assert res_patient.json()["message"] == "patient_access_granted"

    # Patient accessing caregiver endpoint -> 403 Forbidden
    res_caregiver = client.get("/api/v1/test-rbac/caregiver-only", headers=headers)
    assert res_caregiver.status_code == 403
    assert "Insufficient permissions" in res_caregiver.json()["detail"]

    # Patient accessing admin endpoint -> 403 Forbidden
    res_admin = client.get("/api/v1/test-rbac/admin-only", headers=headers)
    assert res_admin.status_code == 403
    assert "Insufficient permissions" in res_admin.json()["detail"]


def test_caregiver_access_boundaries(client, create_user):
    """Verify CAREGIVER can access caregiver endpoints but is rejected (403) from ADMIN and PATIENT endpoints."""
    caregiver = create_user(name="Caregiver User", email="caregiver.rbac@example.com", role=UserRole.CAREGIVER)
    token = create_access_token(subject=caregiver.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Caregiver accessing caregiver endpoint -> 200 OK
    res_caregiver = client.get("/api/v1/test-rbac/caregiver-only", headers=headers)
    assert res_caregiver.status_code == 200
    assert res_caregiver.json()["message"] == "caregiver_access_granted"

    # Caregiver accessing admin endpoint -> 403 Forbidden
    res_admin = client.get("/api/v1/test-rbac/admin-only", headers=headers)
    assert res_admin.status_code == 403
    assert "Insufficient permissions" in res_admin.json()["detail"]

    # Caregiver accessing patient endpoint -> 403 Forbidden
    res_patient = client.get("/api/v1/test-rbac/patient-only", headers=headers)
    assert res_patient.status_code == 403


def test_admin_access_boundaries(client, create_user):
    """Verify ADMIN can access admin-only endpoints."""
    admin = create_user(name="Admin User", email="admin.rbac@example.com", role=UserRole.ADMIN)
    token = create_access_token(subject=admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Admin accessing admin endpoint -> 200 OK
    res_admin = client.get("/api/v1/test-rbac/admin-only", headers=headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["message"] == "admin_access_granted"
