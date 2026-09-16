"""Medication dosage schedule database model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Date, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class ScheduleFrequency(str, enum.Enum):
    """Frequency pattern for dosage schedule."""
    ONCE_DAILY = "ONCE_DAILY"
    TWICE_DAILY = "TWICE_DAILY"
    THREE_TIMES_DAILY = "THREE_TIMES_DAILY"
    FOUR_TIMES_DAILY = "FOUR_TIMES_DAILY"
    CUSTOM = "CUSTOM"


class MedicationSchedule(Base):
    """Model representing an intake schedule for a specific medication."""
    __tablename__ = "medication_schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False, index=True)
    frequency_type = Column(
        Enum(ScheduleFrequency, name="schedule_frequency_enum", native_enum=False),
        nullable=False
    )
    times_per_day = Column(Integer, nullable=False, default=1)
    scheduled_times = Column(JSON, nullable=False)  # List of "HH:MM" 24-hr time strings
    dose_quantity = Column(Float, nullable=False, default=1.0)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
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
    medicine = relationship("Medicine", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<MedicationSchedule id={self.id} medicine_id={self.medicine_id} frequency={self.frequency_type} active={self.is_active}>"
