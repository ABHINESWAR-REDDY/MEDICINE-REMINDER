"""Pydantic schemas for Medicine management."""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.medicine import MedicineForm, DosageUnit
from app.schemas.condition import ConditionResponse
from app.schemas.prescription import PrescriptionResponse
from app.schemas.schedule import ScheduleResponse


class MedicineBase(BaseModel):
    """Base medicine schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Medication or drug brand/generic name")
    dosage_amount: float = Field(..., gt=0, description="Numerical strength per dose (must be > 0)")
    dosage_unit: DosageUnit = Field(..., description="Dosage unit (mg, mcg, g, ml, tablet, capsule, drop, unit)")
    quantity: int = Field(..., gt=0, description="Total unit quantity on hand (must be > 0)")
    medicine_form: MedicineForm = Field(default=MedicineForm.TABLET, description="Pharmaceutical form")
    instructions: Optional[str] = Field(None, max_length=2000, description="Usage instructions (e.g. after meals)")
    start_date: date = Field(..., description="Date medication regimen starts")
    end_date: Optional[date] = Field(None, description="Optional date medication regimen ends")
    is_active: bool = Field(default=True, description="Whether the medicine is currently active")
    condition_id: Optional[int] = Field(None, description="Optional linked condition ID")
    prescription_id: Optional[int] = Field(None, description="Optional linked prescription ID")


class MedicineCreate(MedicineBase):
    """Schema for creating a new medicine record."""
    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        return self


class MedicineUpdate(BaseModel):
    """Schema for updating an existing medicine record."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage_amount: Optional[float] = Field(None, gt=0)
    dosage_unit: Optional[DosageUnit] = None
    quantity: Optional[int] = Field(None, gt=0)
    medicine_form: Optional[MedicineForm] = None
    instructions: Optional[str] = Field(None, max_length=2000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    condition_id: Optional[int] = None
    prescription_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        return self


class MedicineResponse(MedicineBase):
    """Schema for returning medicine data to the client."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    condition: Optional[ConditionResponse] = None
    prescription: Optional[PrescriptionResponse] = None
    schedules: List[ScheduleResponse] = []

    model_config = ConfigDict(from_attributes=True)
