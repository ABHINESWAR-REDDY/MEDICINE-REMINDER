"""Integration and unit tests for authentication, registration, login, caregiver approval, and OTP flows."""

from datetime import timedelta
from app.models.user import UserRole, ApprovalStatus
from app.models.email_verification import VerificationPurpose
from app.core.security import create_access_token
from app.services.otp_service import OtpService


def test_register_patient_success(client):
    """Verify that a new patient can register successfully, has APPROVED status, and is active."""
    payload = {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "password": "SecurePassword123!",
        "password_confirmation": "SecurePassword123!",
        "role": "PATIENT",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane.doe@example.com"
    assert data["role"] == "PATIENT"
    assert data["approval_status"] == "APPROVED"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_send_and_verify_otp_flow(client, db_session):
    """Verify two-step registration flow: send OTP -> verify OTP -> account created."""
    email = "twostep.patient@example.com"
    send_payload = {
        "name": "TwoStep Patient",
        "email": email,
        "password": "SecurePassword123!",
        "password_confirmation": "SecurePassword123!",
        "role": "PATIENT",
    }

    # 1. Send OTP
    r1 = client.post("/api/v1/auth/register/send-otp", json=send_payload)
    assert r1.status_code == 200
    assert "Verification code sent" in r1.json()["message"]

    # Retrieve stored code hash from db
    otp_service = OtpService(db_session)
    record = otp_service.repo.get_latest_active_code(email, VerificationPurpose.REGISTRATION.value)
    assert record is not None

    # Let's test with a fake OTP -> fail
    r_bad = client.post("/api/v1/auth/register/verify-otp", json={
        **send_payload,
        "otp_code": "000000"
    })
    assert r_bad.status_code == 422
    assert "Invalid verification code" in r_bad.json()["detail"]

    # Now verify with actual matching code by creating and validating
    code = otp_service.send_registration_otp(email, "TwoStep Patient")
    r_good = client.post("/api/v1/auth/register/verify-otp", json={
        **send_payload,
        "otp_code": code
    })
    assert r_good.status_code == 201
    assert r_good.json()["email"] == email
    assert r_good.json()["role"] == "PATIENT"


def test_forgot_password_and_reset_flow(client, db_session, create_user):
    """Verify forgot-password flow: send OTP -> reset password -> login with new credentials."""
    user = create_user(
        name="Reset Test User",
        email="reset.user@example.com",
        password="OldPassword123!",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True
    )

    # 1. Request reset OTP
    r1 = client.post("/api/v1/auth/forgot-password/send-otp", json={"email": "reset.user@example.com"})
    assert r1.status_code == 200

    # 2. Generate and dispatch reset code
    otp_service = OtpService(db_session)
    code = otp_service.send_password_reset_otp(email="reset.user@example.com", name="Reset Test User")

    # 3. Reset password with OTP
    r2 = client.post("/api/v1/auth/forgot-password/reset", json={
        "email": "reset.user@example.com",
        "otp_code": code,
        "new_password": "NewBrandPassword123!",
        "new_password_confirmation": "NewBrandPassword123!"
    })
    assert r2.status_code == 200
    assert "Password has been reset successfully" in r2.json()["message"]

    # 4. Verify old password fails
    r_old_login = client.post("/api/v1/auth/login", json={
        "email": "reset.user@example.com",
        "password": "OldPassword123!"
    })
    assert r_old_login.status_code == 401

    # 5. Verify new password succeeds
    r_new_login = client.post("/api/v1/auth/login", json={
        "email": "reset.user@example.com",
        "password": "NewBrandPassword123!"
    })
    assert r_new_login.status_code == 200
    assert "access_token" in r_new_login.json()


def test_register_caregiver_success_pending_state(client):
    """Verify that a new caregiver registers with role CAREGIVER, approval_status PENDING, and is_active False."""
    payload = {
        "name": "Caregiver Sam",
        "email": "sam.caregiver@example.com",
        "password": "CaregiverPassword123!",
        "password_confirmation": "CaregiverPassword123!",
        "role": "CAREGIVER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Caregiver Sam"
    assert data["email"] == "sam.caregiver@example.com"
    assert data["role"] == "CAREGIVER"
    assert data["approval_status"] == "PENDING"
    assert data["is_active"] is False


def test_pending_caregiver_cannot_login(client, create_user):
    """Verify login attempt by a PENDING caregiver returns 401 with approval required message."""
    create_user(
        name="Pending Caregiver",
        email="pending.caregiver@example.com",
        password="CaregiverPassword123!",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.PENDING,
        is_active=False
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "pending.caregiver@example.com", "password": "CaregiverPassword123!"}
    )
    assert response.status_code == 401
    assert "pending administrator approval" in response.json()["detail"]


def test_rejected_caregiver_cannot_login(client, create_user):
    """Verify login attempt by a REJECTED caregiver returns 401 with rejection message."""
    create_user(
        name="Rejected Caregiver",
        email="rejected.caregiver@example.com",
        password="CaregiverPassword123!",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.REJECTED,
        is_active=False
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "rejected.caregiver@example.com", "password": "CaregiverPassword123!"}
    )
    assert response.status_code == 401
    assert "has not been approved" in response.json()["detail"]


def test_approved_caregiver_can_login(client, create_user):
    """Verify approved active caregiver logs in successfully and receives JWT."""
    create_user(
        name="Approved Caregiver",
        email="approved.caregiver@example.com",
        password="CaregiverPassword123!",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "approved.caregiver@example.com", "password": "CaregiverPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "CAREGIVER"
    assert data["user"]["approval_status"] == "APPROVED"


def test_admin_registration_status_lifecycle(client):
    """Verify admin registration status returns True when no admin exists, and False after creation."""
    # 1. No admin exists -> available = True
    r1 = client.get("/api/v1/auth/admin-registration-status")
    assert r1.status_code == 200
    assert r1.json()["adminRegistrationAvailable"] is True

    # 2. Register first admin -> succeeds
    r2 = client.post("/api/v1/auth/register", json={
        "name": "First Admin",
        "email": "first.admin@example.com",
        "password": "AdminPassword123!",
        "password_confirmation": "AdminPassword123!",
        "role": "ADMIN",
    })
    assert r2.status_code == 201
    admin_data = r2.json()
    assert admin_data["role"] == "ADMIN"
    assert admin_data["approval_status"] == "APPROVED"
    assert admin_data["is_active"] is True

    # 3. Admin exists -> available = False
    r3 = client.get("/api/v1/auth/admin-registration-status")
    assert r3.status_code == 200
    assert r3.json()["adminRegistrationAvailable"] is False

    # 4. Attempting to register second admin returns 409 ADMIN_ALREADY_EXISTS
    r4 = client.post("/api/v1/auth/register", json={
        "name": "Second Admin",
        "email": "second.admin@example.com",
        "password": "AdminPassword123!",
        "password_confirmation": "AdminPassword123!",
        "role": "ADMIN",
    })
    assert r4.status_code == 409
    detail = r4.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["code"] == "ADMIN_ALREADY_EXISTS"
    assert "administrator account already exists" in detail["message"]

    # 5. Attempting to send OTP for second admin also returns 409 ADMIN_ALREADY_EXISTS
    r5 = client.post("/api/v1/auth/register/send-otp", json={
        "name": "Second Admin",
        "email": "second.admin.otp@example.com",
        "password": "AdminPassword123!",
        "password_confirmation": "AdminPassword123!",
        "role": "ADMIN",
    })
    assert r5.status_code == 409
    detail_otp = r5.json()["detail"]
    assert isinstance(detail_otp, dict)
    assert detail_otp["code"] == "ADMIN_ALREADY_EXISTS"


def test_first_admin_otp_registration_flow(client, db_session):
    """Verify first admin can complete full send OTP -> verify OTP registration flow."""
    email = "admin.otp@example.com"
    send_payload = {
        "name": "OTP Admin",
        "email": email,
        "password": "AdminPassword123!",
        "password_confirmation": "AdminPassword123!",
        "role": "ADMIN",
    }

    # 1. Send OTP for admin
    r1 = client.post("/api/v1/auth/register/send-otp", json=send_payload)
    assert r1.status_code == 200

    # 2. Get code
    otp_service = OtpService(db_session)
    code = otp_service.send_registration_otp(email, "OTP Admin")

    # 3. Verify OTP and create admin
    r2 = client.post("/api/v1/auth/register/verify-otp", json={
        **send_payload,
        "otp_code": code
    })
    assert r2.status_code == 201
    data = r2.json()
    assert data["email"] == email
    assert data["role"] == "ADMIN"
    assert data["approval_status"] == "APPROVED"
    assert data["is_active"] is True


def test_password_hash_never_exposed(client):
    """Verify that neither registration nor login nor /auth/me leak password hash or secrets."""
    payload = {
        "name": "Security Test User",
        "email": "security@example.com",
        "password": "SuperSecretPassword123!",
        "password_confirmation": "SuperSecretPassword123!",
    }
    reg_response = client.post("/api/v1/auth/register", json=payload)
    assert reg_response.status_code == 201
    assert "password_hash" not in reg_response.text
    assert "SuperSecretPassword123!" not in reg_response.text

    # Test login response
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "security@example.com", "password": "SuperSecretPassword123!"}
    )
    assert login_response.status_code == 200
    assert "password_hash" not in login_response.text
    token = login_response.json()["access_token"]

    # Test /auth/me response
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert "password_hash" not in me_response.text


def test_register_duplicate_email_conflict(client, create_user):
    """Verify attempting to register with an existing email returns 409 Conflict."""
    create_user(name="Existing User", email="duplicate@example.com")

    payload = {
        "name": "Another User",
        "email": "duplicate@example.com",
        "password": "Password123!",
        "password_confirmation": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_password_mismatch(client):
    """Verify registration fails with 422 if password confirmation does not match."""
    payload = {
        "name": "Mismatch User",
        "email": "mismatch@example.com",
        "password": "Password123!",
        "password_confirmation": "DifferentPass123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_weak_password_variations(client):
    """Verify registration fails with 422 for each missing password requirement."""
    base_payload = {
        "name": "Validation User",
        "email": "validation@example.com",
    }

    # Short (< 8)
    r = client.post("/api/v1/auth/register", json={**base_payload, "password": "Sh1!", "password_confirmation": "Sh1!"})
    assert r.status_code == 422

    # No uppercase
    r = client.post("/api/v1/auth/register", json={**base_payload, "password": "password123!", "password_confirmation": "password123!"})
    assert r.status_code == 422

    # No lowercase
    r = client.post("/api/v1/auth/register", json={**base_payload, "password": "PASSWORD123!", "password_confirmation": "PASSWORD123!"})
    assert r.status_code == 422

    # No number
    r = client.post("/api/v1/auth/register", json={**base_payload, "password": "Password!!!!", "password_confirmation": "Password!!!!"})
    assert r.status_code == 422

    # No special char
    r = client.post("/api/v1/auth/register", json={**base_payload, "password": "Password1234", "password_confirmation": "Password1234"})
    assert r.status_code == 422


def test_login_success(client, create_user):
    """Verify valid login returns JWT access token and user payload."""
    create_user(
        name="Login User",
        email="login.test@example.com",
        password="MyPassword123!",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED,
        is_active=True
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login.test@example.com", "password": "MyPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login.test@example.com"
    assert data["user"]["role"] == "PATIENT"


def test_login_invalid_password(client, create_user):
    """Verify login with invalid password returns generic 401 Unauthorized."""
    create_user(email="user@example.com", password="CorrectPassword123!")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "WrongPassword123!"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_unknown_account(client):
    """Verify login with non-existent email returns generic 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "AnyPassword123!"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_inactive_account(client, create_user):
    """Verify login with inactive account returns 401 Unauthorized."""
    create_user(
        email="inactive@example.com",
        password="Password123!",
        is_active=False
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"}
    )
    assert response.status_code == 401
    assert "inactive" in response.json()["detail"]


def test_auth_me_success(client, create_user):
    """Verify /auth/me returns current user profile when valid Bearer token is provided."""
    user = create_user(
        name="Me User",
        email="me@example.com",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    token = create_access_token(subject=user.id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["name"] == "Me User"
    assert data["email"] == "me@example.com"
    assert data["approval_status"] == "APPROVED"


def test_missing_token_returns_401(client):
    """Verify /auth/me without Authorization header returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    """Verify /auth/me with an invalid token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_malformed_jwt_token"}
    )
    assert response.status_code == 401


def test_expired_token_returns_401(client, create_user):
    """Verify /auth/me with an expired token returns 401."""
    user = create_user(email="expired@example.com")
    expired_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(seconds=-10)
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
