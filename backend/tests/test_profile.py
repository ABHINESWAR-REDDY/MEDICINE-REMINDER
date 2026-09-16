"""Integration tests for user profile retrieval, profile updates, and secure password change."""

from app.core.security import create_access_token
from app.models.user import UserRole


def test_get_profile_returns_own_data(client, create_user):
    """Verify that authenticated user retrieves their own profile without sensitive fields."""
    user = create_user(
        name="Alex Profile",
        email="alex.profile@example.com",
        role=UserRole.PATIENT
    )
    token = create_access_token(subject=user.id)

    response = client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["name"] == "Alex Profile"
    assert data["email"] == "alex.profile@example.com"
    assert data["role"] == "PATIENT"
    assert "password_hash" not in data


def test_unauthenticated_profile_returns_401(client):
    """Verify unauthenticated profile access returns 401."""
    assert client.get("/api/v1/profile").status_code == 401
    assert client.put("/api/v1/profile", json={"name": "New Name"}).status_code == 401


def test_update_profile_name_success(client, create_user):
    """Verify user can update their name via PUT /api/v1/profile."""
    user = create_user(name="Original Name", email="edit.name@example.com")
    token = create_access_token(subject=user.id)

    response = client.put(
        "/api/v1/profile",
        json={"name": "Updated Full Name"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Full Name"
    assert data["email"] == "edit.name@example.com"


def test_user_cannot_modify_role_or_restricted_fields(client, create_user):
    """Verify attempting to inject role, email, or id updates via profile API is rejected with 422."""
    user = create_user(name="Strict User", email="strict@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=user.id)

    # Attempt to inject extra forbidden fields
    response = client.put(
        "/api/v1/profile",
        json={"name": "New Name", "role": "ADMIN", "email": "newemail@example.com", "id": 9999},
        headers={"Authorization": f"Bearer {token}"}
    )
    # Extra forbidden fields must be rejected by Pydantic extra='forbid'
    assert response.status_code == 422

    # Verify user profile remained unchanged
    check_response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert check_response.json()["role"] == "PATIENT"
    assert check_response.json()["email"] == "strict@example.com"


def test_password_change_success(client, create_user):
    """Verify authenticated password change flow with correct current password."""
    user = create_user(
        name="Pass User",
        email="pass.change@example.com",
        password="OldPassword123!"
    )
    token = create_access_token(subject=user.id)

    payload = {
        "current_password": "OldPassword123!",
        "new_password": "NewSecurePassword456!",
        "new_password_confirmation": "NewSecurePassword456!",
    }
    response = client.post(
        "/api/v1/auth/change-password",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]


def test_password_change_incorrect_current_password(client, create_user):
    """Verify password change fails with 400 when current password is wrong."""
    user = create_user(
        name="Pass User 2",
        email="pass.wrong@example.com",
        password="CorrectPassword123!"
    )
    token = create_access_token(subject=user.id)

    payload = {
        "current_password": "WrongCurrentPassword123!",
        "new_password": "NewSecurePassword456!",
        "new_password_confirmation": "NewSecurePassword456!",
    }
    response = client.post(
        "/api/v1/auth/change-password",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"]


def test_password_change_mismatch(client, create_user):
    """Verify password change fails with 422 when new password confirmation mismatches."""
    user = create_user(
        name="Pass User 3",
        email="pass.mismatch@example.com",
        password="OldPassword123!"
    )
    token = create_access_token(subject=user.id)

    payload = {
        "current_password": "OldPassword123!",
        "new_password": "NewSecurePassword456!",
        "new_password_confirmation": "DifferentPassword456!",
    }
    response = client.post(
        "/api/v1/auth/change-password",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


def test_old_password_invalid_after_change(client, create_user):
    """Verify that after password change, old password fails login and new password succeeds."""
    user = create_user(
        name="Pass Invalidation User",
        email="invalidate.test@example.com",
        password="InitialPassword123!"
    )
    token = create_access_token(subject=user.id)

    # Change password
    change_payload = {
        "current_password": "InitialPassword123!",
        "new_password": "BrandNewPassword789!",
        "new_password_confirmation": "BrandNewPassword789!",
    }
    client.post(
        "/api/v1/auth/change-password",
        json=change_payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    # Attempt login with OLD password -> 401 Unauthorized
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "invalidate.test@example.com", "password": "InitialPassword123!"}
    )
    assert old_login.status_code == 401

    # Attempt login with NEW password -> 200 OK
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "invalidate.test@example.com", "password": "BrandNewPassword789!"}
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()
