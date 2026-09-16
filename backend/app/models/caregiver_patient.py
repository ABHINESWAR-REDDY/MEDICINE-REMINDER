"""Caregiver-Patient relationship and assignment model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class AssignmentStatus(str, enum.Enum):
    """Status of caregiver-patient assignment."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class CaregiverPatientAssignment(Base):
    """Database model linking a caregiver to an assigned patient."""
    __tablename__ = "caregiver_patient_assignments"
    __table_args__ = (
        UniqueConstraint("caregiver_id", "patient_id", name="uq_caregiver_patient_assignment"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    caregiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(
        Enum(AssignmentStatus, name="assignment_status_enum", native_enum=False),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
        server_default="ACTIVE"
    )
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    caregiver = relationship("User", foreign_keys=[caregiver_id], backref="patient_assignments")
    patient = relationship("User", foreign_keys=[patient_id], backref="caregiver_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        return f"<CaregiverPatientAssignment id={self.id} caregiver_id={self.caregiver_id} patient_id={self.patient_id} status={self.status}>"
