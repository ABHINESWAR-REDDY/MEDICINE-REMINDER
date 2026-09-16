"""Medication dose instance database model for adherence tracking."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class DoseStatus(str, enum.Enum):
    """Terminal and active status enumeration for medication doses."""
    SCHEDULED = "SCHEDULED"
    TAKEN = "TAKEN"
    MISSED = "MISSED"
    SKIPPED = "SKIPPED"


class MedicationDose(Base):
    """Individual scheduled or logged medication intake dose."""
    __tablename__ = "medication_doses"
    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_time", name="uq_schedule_scheduled_time"),
        Index("ix_doses_patient_scheduled_status", "patient_id", "scheduled_time", "status"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("medication_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=False, index=True)
    actual_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum(DoseStatus, name="dose_status_enum", native_enum=False),
        nullable=False,
        default=DoseStatus.SCHEDULED,
        server_default="SCHEDULED",
        index=True
    )
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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
    schedule = relationship("MedicationSchedule", backref="doses")
    medicine = relationship("Medicine", backref="doses")
    patient = relationship("User", foreign_keys=[patient_id], backref="doses")
    recorder = relationship("User", foreign_keys=[recorded_by])

    def __repr__(self) -> str:
        return f"<MedicationDose id={self.id} medicine_id={self.medicine_id} scheduled_time={self.scheduled_time} status={self.status}>"
