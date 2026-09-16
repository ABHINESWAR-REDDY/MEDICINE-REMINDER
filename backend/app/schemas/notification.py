"""Pydantic schemas for patient and user notifications and medication alerts."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """Schema representing a single patient notification."""
    id: int
    user_id: int
    type: str  # MEDICATION_REMINDER, MISSED_DOSE, CHAT_MESSAGE, GENERAL, REFILL_NEEDED
    title: str
    message: str
    severity: str  # INFO, WARNING, CRITICAL
    related_dose_id: Optional[int] = None
    related_medicine_id: Optional[int] = None
    medicine_id: Optional[int] = None
    medicine_name: Optional[str] = None
    strength: Optional[float] = None
    unit: Optional[str] = None
    dosage_form: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class UnreadNotificationCountResponse(BaseModel):
    """Schema returning unread notifications count."""
    unread_count: int


class NotificationActionResponse(BaseModel):
    """Schema for notification mutation responses."""
    success: bool
    message: str
