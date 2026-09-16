"""OTP generation, hashing, verification, and rate limiting service."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_verification import EmailVerificationCode, VerificationPurpose
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.services.email_service import email_service


class OtpService:
    """Service encapsulating secure OTP lifecycle and validation."""

    MAX_ATTEMPTS = 5

    def __init__(self, db: Session):
        self.db = db
        self.repo = EmailVerificationRepository(db)

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a cryptographically secure numeric OTP."""
        return f"{secrets.randbelow(10**length):0{length}d}"

    @staticmethod
    def hash_otp(code: str) -> str:
        """Hash OTP with SHA-256 for secure database storage."""
        return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def verify_hash(plain_code: str, stored_hash: str) -> bool:
        """Compare plaintext code hash with stored hash."""
        computed = hashlib.sha256(plain_code.strip().encode("utf-8")).hexdigest()
        return secrets.compare_digest(computed, stored_hash)

    def send_registration_otp(self, email: str, name: str) -> str:
        """Generate, persist, and dispatch email registration OTP code."""
        code = self.generate_otp()
        code_hash = self.hash_otp(code)
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES)

        self.repo.create(
            email=email,
            code_hash=code_hash,
            purpose=VerificationPurpose.REGISTRATION.value,
            expires_at=expires_at
        )

        email_service.send_registration_otp(
            to_email=email,
            name=name,
            otp_code=code,
            expire_minutes=settings.EMAIL_OTP_EXPIRE_MINUTES
        )
        return code

    def send_password_reset_otp(self, email: str, name: str) -> str:
        """Generate, persist, and dispatch password reset OTP code."""
        code = self.generate_otp()
        code_hash = self.hash_otp(code)
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES)

        self.repo.create(
            email=email,
            code_hash=code_hash,
            purpose=VerificationPurpose.PASSWORD_RESET.value,
            expires_at=expires_at
        )

        email_service.send_password_reset_otp(
            to_email=email,
            name=name,
            otp_code=code,
            expire_minutes=settings.EMAIL_OTP_EXPIRE_MINUTES
        )
        return code

    def validate_code(
        self,
        email: str,
        purpose: str,
        plain_code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an entered OTP code against stored records.
        Enforces expiration, attempt bounds, and single-use consumption.
        """
        record = self.repo.get_latest_active_code(email=email, purpose=purpose)
        if not record:
            return False, "No active verification code found. Please request a new one."

        # Check expiration
        now_utc = datetime.now(timezone.utc)
        # Handle naive datetime from SQLite / timezone-aware from Postgres
        record_expiry = record.expires_at
        if record_expiry.tzinfo is None:
            record_expiry = record_expiry.replace(tzinfo=timezone.utc)

        if now_utc > record_expiry:
            self.repo.mark_as_used(record)
            return False, "Verification code has expired. Please request a new one."

        # Check attempt limits
        if record.attempts >= self.MAX_ATTEMPTS:
            self.repo.mark_as_used(record)
            return False, "Too many failed attempts. This code has been invalidated. Please request a new one."

        # Validate code hash
        if not self.verify_hash(plain_code, record.code_hash):
            self.repo.increment_attempts(record)
            remaining = self.MAX_ATTEMPTS - record.attempts
            if remaining <= 0:
                self.repo.mark_as_used(record)
                return False, "Too many failed attempts. Please request a new verification code."
            return False, f"Invalid verification code. {remaining} attempt(s) remaining."

        # Success - mark code as consumed
        self.repo.mark_as_used(record)
        return True, None
