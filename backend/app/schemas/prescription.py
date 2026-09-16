"""Pydantic schemas for Prescription management."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.prescription import PrescriptionStatus


class PrescriptionBase(BaseModel):
    """Base prescription schema."""
    prescription_number: Optional[str] = Field(None, max_length=100, description="Reference prescription identifier")
    doctor_name: Optional[str] = Field(None, max_length=255, description="Prescribing physician or provider name")
    issue_date: Optional[date] = Field(None, description="Date prescription was written")
    expiry_date: Optional[date] = Field(None, description="Date prescription expires")
    notes: Optional[str] = Field(None, max_length=2000, description="Physician notes or refill remarks")
    status: PrescriptionStatus = Field(default=PrescriptionStatus.ACTIVE, description="Prescription lifecycle status")


class PrescriptionCreate(PrescriptionBase):
    """Schema for creating a new prescription."""
    @model_validator(mode="after")
    def validate_dates(self):
        if self.issue_date and self.expiry_date and self.expiry_date < self.issue_date:
            raise ValueError("Expiry date cannot be before issue date")
        return self


class PrescriptionUpdate(BaseModel):
    """Schema for updating an existing prescription."""
    prescription_number: Optional[str] = Field(None, max_length=100)
    doctor_name: Optional[str] = Field(None, max_length=255)
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)
    status: Optional[PrescriptionStatus] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.issue_date and self.expiry_date and self.expiry_date < self.issue_date:
            raise ValueError("Expiry date cannot be before issue date")
        return self


class PrescriptionResponse(PrescriptionBase):
    """Schema for returning prescription data to the client."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
