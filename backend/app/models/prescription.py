"""Prescription database model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import Base


class PrescriptionStatus(str, enum.Enum):
    """Prescription lifecycle status."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Prescription(Base):
    """Model representing a patient prescription issued by a healthcare provider."""
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prescription_number = Column(String(100), nullable=True)
    doctor_name = Column(String(255), nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(
        Enum(PrescriptionStatus, name="prescription_status_enum", native_enum=False),
        nullable=False,
        default=PrescriptionStatus.ACTIVE,
        server_default="ACTIVE"
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="prescriptions")
    medicines = relationship("Medicine", back_populates="prescription")

    def __repr__(self) -> str:
        return f"<Prescription id={self.id} user_id={self.user_id} number={self.prescription_number} status={self.status}>"
