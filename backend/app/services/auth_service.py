"""Authentication, user onboarding, and email OTP verification business service."""

from typing import Dict, Any, Optional, Union, List
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    validate_password_rules,
)
from app.models.user import User, UserRole, ApprovalStatus
from app.models.email_verification import VerificationPurpose
from app.repositories.user_repository import UserRepository
from app.services.otp_service import OtpService
from app.services.audit_service import AuditService
from app.schemas.user import (
    UserRegisterRequest,
    RegisterSendOtpRequest,
    RegisterVerifyOtpRequest,
    ForgotPasswordSendOtpRequest,
    ForgotPasswordResetRequest,
    UserLoginRequest,
    PasswordChangeRequest,
)


class AuthService:
    """Service encapsulating authentication, registration, OTP email verification, and credential security."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.otp_service = OtpService(db)
        self.audit = AuditService(db)

    def get_admin_registration_status(self) -> Dict[str, bool]:
        """
        Check whether initial administrator account registration is available.
        Returns adminRegistrationAvailable=True when zero admin accounts exist.
        Exposes only the availability boolean without leaking user information.
        """
        has_admin = self.user_repo.has_admin()
        return {"adminRegistrationAvailable": not has_admin}

    def send_registration_otp(self, data: RegisterSendOtpRequest) -> Dict[str, str]:
        """
        Validate registration fields and dispatch a 6-digit email OTP verification code.
        """
        # Validate password rules and confirmation match
        is_valid, error_msg = validate_password_rules(
            data.password,
            confirmation=data.password_confirmation
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_msg
            )

        # Enforce registration role policy
        role_str = (data.role or "PATIENT").strip().upper()
        if role_str == UserRole.ADMIN.value:
            if self.user_repo.has_admin():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ADMIN_ALREADY_EXISTS",
                        "message": "An administrator account already exists."
                    }
                )
        elif role_str not in [UserRole.PATIENT.value, UserRole.CAREGIVER.value]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid account type '{data.role}'. Please select Patient, Caregiver, or Admin."
            )

        # Check for existing email
        existing_user = self.user_repo.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists."
            )

        # Generate, store, and send OTP via Google SMTP
        self.otp_service.send_registration_otp(
            email=data.email,
            name=data.name
        )

        return {
            "message": f"Verification code sent to {data.email}",
            "email": str(data.email)
        }

    @staticmethod
    def validate_employee_id(employee_id: Optional[str], role: str) -> str:
        """
        Validate custom employee/member ID format and role prefix:
        - PATIENT: Must start with 'PT' followed by exactly 6 digits (e.g., PT123456)
        - CAREGIVER: Must start with 'CG' followed by exactly 6 digits (e.g., CG123456)
        - ADMIN: Must start with 'AD' followed by exactly 6 digits (e.g., AD123456)
        """
        if not employee_id or not str(employee_id).strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Employee ID is required."
            )
        clean_id = str(employee_id).strip().upper()
        role_str = (role or "PATIENT").strip().upper()
        expected_prefix = "PT" if role_str == UserRole.PATIENT.value else ("CG" if role_str == UserRole.CAREGIVER.value else "AD")

        if not clean_id.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"ID for {role_str.capitalize()} must start with '{expected_prefix}' (e.g. {expected_prefix}123456)."
            )

        digits_part = clean_id[len(expected_prefix):]
        if not digits_part.isdigit() or len(digits_part) != 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"ID must contain exactly 6 digits after '{expected_prefix}' (e.g., {expected_prefix}123456)."
            )

        return clean_id

    def check_employee_id_availability(self, employee_id: str, role: str) -> Dict[str, Any]:
        """Check if custom ID format is valid and not already taken."""
        clean_id = self.validate_employee_id(employee_id, role)
        existing = self.user_repo.get_by_employee_id(clean_id)
        if existing:
            return {
                "available": False,
                "employee_id": clean_id,
                "message": "This ID is already taken. Please choose another ID."
            }
        return {
            "available": True,
            "employee_id": clean_id,
            "message": "ID is available."
        }

    def verify_registration_otp_and_register(self, data: RegisterVerifyOtpRequest) -> User:
        """
        Verify the 6-digit email OTP code and persist the user account into PostgreSQL.
        """
        # Validate OTP code first
        is_valid_otp, otp_err = self.otp_service.validate_code(
            email=data.email,
            purpose=VerificationPurpose.REGISTRATION.value,
            plain_code=data.otp_code
        )
        if not is_valid_otp:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=otp_err
            )

        # Proceed with account registration
        register_payload = UserRegisterRequest(
            name=data.name,
            email=data.email,
            password=data.password,
            password_confirmation=data.password_confirmation,
            role=data.role,
            employee_id=data.employee_id
        )
        return self.register_user(register_payload)

    def send_forgot_password_otp(self, data: ForgotPasswordSendOtpRequest) -> Dict[str, str]:
        """
        Send a 6-digit password reset OTP to the registered user's email.
        Returns generic success message to prevent account enumeration.
        """
        user = self.user_repo.get_by_email(data.email)
        if user and user.is_active:
            self.otp_service.send_password_reset_otp(
                email=user.email,
                name=user.name
            )

        return {
            "message": "If an account with this email exists, a password reset code has been sent to your inbox."
        }

    def verify_otp_and_reset_password(self, data: ForgotPasswordResetRequest) -> Dict[str, str]:
        """
        Verify the password reset OTP code and update user credentials with a new bcrypt password hash.
        """
        # Validate password rules and confirmation match
        is_valid, error_msg = validate_password_rules(
            data.new_password,
            confirmation=data.new_password_confirmation
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_msg
            )

        # Verify OTP code
        is_valid_otp, otp_err = self.otp_service.validate_code(
            email=data.email,
            purpose=VerificationPurpose.PASSWORD_RESET.value,
            plain_code=data.otp_code
        )
        if not is_valid_otp:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=otp_err
            )

        user = self.user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found."
            )

        # Hash new password and commit update
        user.password_hash = get_password_hash(data.new_password)
        self.user_repo.update(user)

        return {
            "message": "Password has been reset successfully. You may now log in with your new password."
        }

    def register_user(self, data: UserRegisterRequest) -> User:
        """
        Register a new user account.
        Rules:
        - PATIENT: role = PATIENT, approval_status = APPROVED, is_active = True
        - CAREGIVER: role = CAREGIVER, approval_status = PENDING, is_active = False
        - ADMIN: allowed if and only if no ADMIN exists; approval_status = APPROVED, is_active = True
        - employee_id: Custom role-prefixed 8-character ID (PT/CG/AD + 6 digits) verified unique.
        """
        # Validate password rules and confirmation match
        is_valid, error_msg = validate_password_rules(
            data.password,
            confirmation=data.password_confirmation
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_msg
            )

        # Enforce registration role policy
        role_str = (data.role or "PATIENT").strip().upper()

        if role_str == UserRole.ADMIN.value:
            if self.user_repo.has_admin():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ADMIN_ALREADY_EXISTS",
                        "message": "An administrator account already exists."
                    }
                )
            assigned_role = UserRole.ADMIN
            assigned_approval = ApprovalStatus.APPROVED
            assigned_is_active = True
        elif role_str == UserRole.CAREGIVER.value:
            assigned_role = UserRole.CAREGIVER
            assigned_approval = ApprovalStatus.PENDING
            assigned_is_active = False
        elif role_str == UserRole.PATIENT.value:
            assigned_role = UserRole.PATIENT
            assigned_approval = ApprovalStatus.APPROVED
            assigned_is_active = True
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid account type '{data.role}'. Please select Patient, Caregiver, or Admin."
            )

        # Validate and check employee_id uniqueness
        clean_emp_id = None
        if data.employee_id:
            clean_emp_id = self.validate_employee_id(data.employee_id, role_str)
            existing_emp = self.user_repo.get_by_employee_id(clean_emp_id)
            if existing_emp:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ID_ALREADY_EXISTS",
                        "message": "This ID is already taken. Please choose another ID."
                    }
                )

        # Check for existing email
        existing_user = self.user_repo.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists."
            )

        # Hash password securely via bcrypt
        password_hash = get_password_hash(data.password)

        # Persist user with assigned role, approval_status, active flag, and employee_id
        try:
            user = self.user_repo.create(
                name=data.name,
                email=data.email,
                password_hash=password_hash,
                role=assigned_role,
                approval_status=assigned_approval,
                is_active=assigned_is_active,
                employee_id=clean_emp_id
            )

            # Audit log registration
            action_name = f"{assigned_role.value}_REGISTERED"
            self.audit.log(
                action=action_name,
                target_type="User",
                actor_user_id=user.id,
                target_id=user.id,
                details={
                    "email": user.email,
                    "name": user.name,
                    "role": user.role.value,
                    "employee_id": user.employee_id,
                    "approval_status": user.approval_status.value
                }
            )

            return user
        except IntegrityError as exc:
            self.db.rollback()
            err_str = str(exc).lower()
            if "uq_single_admin_role" in err_str or (assigned_role == UserRole.ADMIN and ("unique" in err_str or "constraint" in err_str)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ADMIN_ALREADY_EXISTS",
                        "message": "An administrator account already exists."
                    }
                )
            if "employee_id" in err_str or "users_employee_id" in err_str:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ID_ALREADY_EXISTS",
                        "message": "This ID is already taken. Please choose another ID."
                    }
                )
            if "ix_users_email" in err_str or "users.email" in err_str or "unique" in err_str:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email address already exists."
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account creation conflicted with an existing record."
            )

    def authenticate_user(self, data: UserLoginRequest) -> Dict[str, Any]:
        """
        Authenticate user with email and password.
        Returns access token and safe user payload.
        Enforces caregiver approval checks and account active states.
        """
        user = self.user_repo.get_by_email(data.email)

        # Generic auth failure response to avoid user enumeration
        auth_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not user:
            raise auth_exception

        if not verify_password(data.password, user.password_hash):
            raise auth_exception

        # Check role-specific approval status
        if user.role == UserRole.CAREGIVER:
            if user.approval_status == ApprovalStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Your caregiver account is pending administrator approval.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif user.approval_status == ApprovalStatus.REJECTED:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Your caregiver account has not been approved.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Check general active flag and approval status
        if not user.is_active or user.approval_status != ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive. Please contact support.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        from app.services.user_service import UserService
        enriched_user = UserService(self.db).get_profile(user)

        access_token = create_access_token(subject=user.id)

        # Audit log login
        self.audit.log(
            action="USER_LOGIN",
            target_type="User",
            actor_user_id=user.id,
            target_id=user.id,
            details={
                "email": user.email,
                "role": user.role.value,
                "employee_id": user.employee_id
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": enriched_user,
        }

    def change_password(self, user: User, data: PasswordChangeRequest) -> Dict[str, str]:
        """
        Change password for an authenticated user.
        Verifies current password before applying new bcrypt hash.
        """
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect."
            )

        is_valid, error_msg = validate_password_rules(
            data.new_password,
            confirmation=data.new_password_confirmation
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_msg
            )

        # Hash new password and update record
        user.password_hash = get_password_hash(data.new_password)
        self.user_repo.update(user)

        return {"message": "Password changed successfully."}
