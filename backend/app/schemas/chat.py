"""Pydantic schemas for patient-caregiver chat messaging."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ChatMessageCreate(BaseModel):
    """Payload for sending a chat message."""
    recipient_id: int = Field(..., description="ID of the recipient user")
    message: str = Field(..., min_length=1, max_length=2000, description="Chat message body")


class ChatMessageResponse(BaseModel):
    """Schema for returning a chat message."""
    id: int
    sender_id: int
    sender_name: str
    sender_role: str
    sender_employee_id: Optional[str] = None
    recipient_id: int
    recipient_name: str
    recipient_role: str
    recipient_employee_id: Optional[str] = None
    message: str
    is_read: bool
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatContact(BaseModel):
    """Contact card summary for chat participants."""
    user_id: int
    employee_id: Optional[str] = None
    name: str
    email: str
    role: str
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatDeleteResponse(BaseModel):
    """Response schema for chat message and conversation deletion operations."""
    success: bool
    message: str
    deleted_id: Optional[int] = None

