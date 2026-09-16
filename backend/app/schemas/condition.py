"""Pydantic schemas for Condition / Disease management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ConditionBase(BaseModel):
    """Base condition schema with name and optional description."""
    name: str = Field(..., min_length=1, max_length=255, description="Medical condition or disease name")
    description: Optional[str] = Field(None, max_length=2000, description="Optional condition details")


class ConditionCreate(ConditionBase):
    """Schema for creating a new condition."""
    pass


class ConditionUpdate(BaseModel):
    """Schema for updating an existing condition."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ConditionResponse(ConditionBase):
    """Schema for returning condition data to the client."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
