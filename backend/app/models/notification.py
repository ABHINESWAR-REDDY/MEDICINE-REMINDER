"""Notification database model for patient medication alerts, reminders, caregiver refill warnings, and updates."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class Notification(Base):
    """Persistent notification record for patients and caregivers."""
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_type_medicine", "user_id", "type", "related_medicine_id"),
        UniqueConstraint("user_id", "type", "related_dose_id", name="uq_user_type_dose"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # MEDICATION_REMINDER, MISSED_DOSE, CHAT_MESSAGE, GENERAL, REFILL_NEEDED
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False, default="INFO")  # INFO, WARNING, CRITICAL
    related_dose_id = Column(Integer, ForeignKey("medication_doses.id", ondelete="SET NULL"), nullable=True, index=True)
    related_medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=True, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", backref="notifications")
    related_dose = relationship("MedicationDose", foreign_keys=[related_dose_id])
    related_medicine = relationship("Medicine", foreign_keys=[related_medicine_id])

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} type={self.type} read={self.is_read}>"
