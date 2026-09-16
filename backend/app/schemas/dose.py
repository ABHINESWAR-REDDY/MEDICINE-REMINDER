"""Pydantic schemas for medication doses and adherence monitoring."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class MedicationDoseResponse(BaseModel):
    """Schema for individual dose instance."""
    id: int
    schedule_id: int
    medicine_id: int
    medicine_name: str
    dosage_amount: Optional[float] = None
    dosage_unit: Optional[str] = None
    medicine_form: Optional[str] = None
    instructions: Optional[str] = None
    dose_quantity: float = 1.0
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class AdherenceResponse(BaseModel):
    """Schema for adherence analytics response."""
    patient_id: int
    period_days: int
    adherence_percentage: float
    adherence_status: str
    total_expected_doses: int
    taken_count: int
    missed_count: int
    skipped_count: int
    pending_future_count: int

    model_config = ConfigDict(from_attributes=True)


class DoseActionResponse(BaseModel):
    """Response schema for dose mark taken/skipped actions."""
    success: bool
    message: str
    dose: Optional[dict] = None
