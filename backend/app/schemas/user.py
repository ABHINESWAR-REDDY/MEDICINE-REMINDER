"""Pydantic schemas for user registration, authentication, OTP verification, and profiles."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRoleEnum(str, Enum):
    """User role enumeration for API schemas."""
    PATIENT = "PATIENT"
    CAREGIVER = "CAREGIVER"
    ADMIN = "ADMIN"


class ApprovalStatusEnum(str, Enum):
    """Account approval status enumeration for API schemas."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class UserRegisterRequest(BaseModel):
    """Payload schema for user registration."""
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 chars)")
    password_confirmation: str = Field(..., min_length=8, max_length=128, description="Password confirmation")
    role: Optional[str] = Field("PATIENT", description="Requested role (PATIENT or CAREGIVER for public registration)")
    employee_id: Optional[str] = Field(None, description="Custom 8-character ID (PT/CG/AD + 6 digits)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Name cannot be empty or blank")
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or blank")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class RegisterSendOtpRequest(BaseModel):
    """Request payload to validate registration data and send 6-digit email OTP."""
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 chars)")
    password_confirmation: str = Field(..., min_length=8, max_length=128, description="Password confirmation")
    role: Optional[str] = Field("PATIENT", description="Requested role (PATIENT or CAREGIVER)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Name cannot be empty or blank")
        return trimmed


class RegisterVerifyOtpRequest(BaseModel):
    """Request payload to verify 6-digit email OTP and persist the user account."""
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password")
    password_confirmation: str = Field(..., min_length=8, max_length=128, description="Password confirmation")
    role: Optional[str] = Field("PATIENT", description="Requested role (PATIENT or CAREGIVER)")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code sent to email")
    employee_id: Optional[str] = Field(None, description="Custom 8-character ID (PT/CG/AD + 6 digits)")

    @field_validator("otp_code")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.isdigit() or len(cleaned) != 6:
            raise ValueError("Verification code must be exactly 6 numeric digits")
        return cleaned


class ForgotPasswordSendOtpRequest(BaseModel):
    """Request payload to send a password reset OTP code."""
    email: EmailStr = Field(..., description="Registered email address")


class ForgotPasswordResetRequest(BaseModel):
    """Request payload to verify OTP and reset password."""
    email: EmailStr = Field(..., description="Registered email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit reset code sent to email")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password (min 8 chars)")
    new_password_confirmation: str = Field(..., min_length=8, max_length=128, description="New password confirmation")

    @field_validator("otp_code")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.isdigit() or len(cleaned) != 6:
            raise ValueError("Verification code must be exactly 6 numeric digits")
        return cleaned


class UserLoginRequest(BaseModel):
    """Payload schema for user login authentication."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserResponse(BaseModel):
    """Safe public user information schema (never exposes password_hash)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: Optional[str] = None
    name: str
    email: str
    role: str
    approval_status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    assigned_caregiver_id: Optional[int] = None
    assigned_caregiver_name: Optional[str] = None
    assigned_caregiver_employee_id: Optional[str] = None
    assigned_caregiver_email: Optional[str] = None
    language: Optional[str] = "en"


class TokenResponse(BaseModel):
    """Authentication response returning JWT access token and safe user payload."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserProfileUpdateRequest(BaseModel):
    """
    Payload for updating user profile.
    Allows safe profile fields (name, language).
    Does NOT permit changing id, email, role, approval_status, password_hash, is_active, or timestamps.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated full name")
    language: Optional[str] = Field(None, min_length=2, max_length=10, description="Preferred UI language code (e.g. en, hi, te, ta, kn, ml, mr, bn, gu, pa, or)")

    @field_validator("name")
    @classmethod
    def validate_update_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Name cannot be empty or blank")
            return trimmed
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            code = v.strip().lower()
            allowed = {"en", "hi", "te", "ta", "kn", "ml", "mr", "bn", "gu", "pa", "or"}
            if code not in allowed:
                raise ValueError(f"Language code '{code}' is not supported. Supported codes: {', '.join(sorted(allowed))}")
            return code
        return v


class PasswordChangeRequest(BaseModel):
    """Payload for secure password change."""
    current_password: str = Field(..., min_length=1, description="Current account password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password (min 8 chars)")
    new_password_confirmation: str = Field(..., min_length=8, max_length=128, description="New password confirmation")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("New password cannot be empty or blank")
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        return v


class AdminRegistrationStatusResponse(BaseModel):
    """Status indicating whether first admin account registration is available."""
    adminRegistrationAvailable: bool = Field(
        ...,
        description="True if no administrator account exists in the system and admin registration is available"
    )

