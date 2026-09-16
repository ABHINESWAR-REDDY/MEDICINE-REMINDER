"""Repository for email verification codes persistence."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.email_verification import EmailVerificationCode, VerificationPurpose


class EmailVerificationRepository:
    """Repository handling database operations for EmailVerificationCode model."""

    def __init__(self, db: Session):
        self.db = db

    def invalidate_previous_codes(self, email: str, purpose: str) -> None:
        """Mark all existing unused codes for this email and purpose as used/invalidated."""
        self.db.query(EmailVerificationCode).filter(
            EmailVerificationCode.email.ilike(email.strip()),
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.is_used.is_(False)
        ).update({"is_used": True}, synchronize_session=False)
        self.db.commit()

    def create(
        self,
        email: str,
        code_hash: str,
        purpose: str,
        expires_at: datetime
    ) -> EmailVerificationCode:
        """Create and store a new hashed verification code."""
        # First invalidate any pending codes for the same email & purpose
        self.invalidate_previous_codes(email, purpose)

        record = EmailVerificationCode(
            email=email.strip().lower(),
            code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at,
            attempts=0,
            is_used=False
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest_active_code(
        self,
        email: str,
        purpose: str
    ) -> Optional[EmailVerificationCode]:
        """Retrieve the latest unused verification code for this email and purpose."""
        return self.db.query(EmailVerificationCode).filter(
            EmailVerificationCode.email.ilike(email.strip()),
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.is_used.is_(False)
        ).order_by(EmailVerificationCode.created_at.desc()).first()

    def increment_attempts(self, record: EmailVerificationCode) -> EmailVerificationCode:
        """Increment failed verification attempt count."""
        record.attempts += 1
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def mark_as_used(self, record: EmailVerificationCode) -> EmailVerificationCode:
        """Mark verification code as consumed."""
        record.is_used = True
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
