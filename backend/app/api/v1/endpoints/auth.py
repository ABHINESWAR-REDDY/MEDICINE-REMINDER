"""Authentication API endpoints supporting password security, JWT, and email OTP verification."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserRegisterRequest,
    RegisterSendOtpRequest,
    RegisterVerifyOtpRequest,
    ForgotPasswordSendOtpRequest,
    ForgotPasswordResetRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    PasswordChangeRequest,
    AdminRegistrationStatusResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.get(
    "/admin-registration-status",
    response_model=AdminRegistrationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check administrator registration availability",
    description="Returns whether the initial administrator account registration is available (true if 0 admins exist, false otherwise).",
)
def get_admin_registration_status(
    db: Session = Depends(get_db)
) -> AdminRegistrationStatusResponse:
    """Check whether initial admin registration is available."""
    auth_service = AuthService(db)
    return auth_service.get_admin_registration_status()


@router.get(
    "/check-employee-id",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Check employee/member ID format and availability",
    description="Validates custom ID format (PT/CG/AD + 6 digits) and checks if it is available in the database.",
)
def check_employee_id(
    employee_id: str,
    role: str = "PATIENT",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Check ID validity and availability."""
    auth_service = AuthService(db)
    return auth_service.check_employee_id_availability(employee_id, role)



@router.post(
    "/register/send-otp",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Send email verification code for new user registration",
    description="Validates registration inputs and dispatches a 6-digit verification code to the provided email address via Google SMTP.",
)
def send_register_otp(
    data: RegisterSendOtpRequest,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Validate registration payload and send 6-digit email OTP."""
    auth_service = AuthService(db)
    return auth_service.send_registration_otp(data)


@router.post(
    "/register/verify-otp",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Verify email OTP and create user account",
    description="Verifies the 6-digit email OTP code and registers the user account into PostgreSQL (PATIENT=APPROVED, CAREGIVER=PENDING).",
)
def verify_register_otp(
    data: RegisterVerifyOtpRequest,
    db: Session = Depends(get_db)
) -> UserResponse:
    """Verify email OTP code and persist new user."""
    auth_service = AuthService(db)
    return auth_service.verify_registration_otp_and_register(data)


@router.post(
    "/forgot-password/send-otp",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Send password reset OTP code",
    description="Sends a 6-digit password reset code to the user's email address if an active account exists.",
)
def forgot_password_send_otp(
    data: ForgotPasswordSendOtpRequest,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Send 6-digit password reset OTP to email."""
    auth_service = AuthService(db)
    return auth_service.send_forgot_password_otp(data)


@router.post(
    "/forgot-password/reset",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and reset password",
    description="Verifies the 6-digit reset code and applies a new password hashed via bcrypt.",
)
def forgot_password_reset(
    data: ForgotPasswordResetRequest,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Verify reset OTP and commit new password."""
    auth_service = AuthService(db)
    return auth_service.verify_otp_and_reset_password(data)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user account (Direct)",
    description="Direct account creation endpoint (PATIENT=APPROVED, CAREGIVER=PENDING, ADMIN=rejected).",
)
def register(
    data: UserRegisterRequest,
    db: Session = Depends(get_db)
) -> UserResponse:
    """Direct account registration."""
    auth_service = AuthService(db)
    return auth_service.register_user(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT token",
    description="Authenticates email and password, returning a stateless JWT access token.",
)
def login(
    data: UserLoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Authenticate with credentials and receive access token."""
    auth_service = AuthService(db)
    return auth_service.authenticate_user(data)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user",
    description="Returns the currently authenticated user's safe profile information with assigned caregiver details. Does not expose password hashes.",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Retrieve details for the currently authenticated user."""
    from app.services.user_service import UserService
    return UserService(db).get_profile(current_user)


@router.post(
    "/change-password",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Change account password",
    description="Requires verification of current password before applying new bcrypt-hashed password.",
)
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Change password for the current authenticated user."""
    auth_service = AuthService(db)
    return auth_service.change_password(current_user, data)
