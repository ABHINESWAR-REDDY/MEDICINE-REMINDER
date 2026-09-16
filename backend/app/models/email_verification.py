"""Email verification code database model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.models.base import Base


class VerificationPurpose(str, enum.Enum):
    """Purpose of the email verification code."""
    REGISTRATION = "REGISTRATION"
    PASSWORD_RESET = "PASSWORD_RESET"


class EmailVerificationCode(Base):
    """Model storing hashed email verification codes (OTP) and expiration states."""
    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), index=True, nullable=False)
    code_hash = Column(String(255), nullable=False)
    purpose = Column(String(50), nullable=False, default=VerificationPurpose.REGISTRATION.value)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationCode id={self.id} email={self.email} purpose={self.purpose} used={self.is_used}>"
