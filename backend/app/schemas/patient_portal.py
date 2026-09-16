"""Pydantic schemas for Patient Portal Medication History and Refill Predictions."""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class MedicationHistoryItem(BaseModel):
    """Individual medication history / dose activity record."""
    id: Optional[int] = None
    dose_id: Optional[int] = None
    medicine_id: int
    medicine_name: str
    strength: Optional[float] = None
    unit: Optional[str] = None
    dosage_form: Optional[str] = None
    instructions: Optional[str] = None
    schedule_description: Optional[str] = None
    dose_quantity: float = 1.0
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True
    scheduled_time: Optional[datetime] = None
    actual_time: Optional[datetime] = None
    status: str  # TAKEN, MISSED, SKIPPED, SCHEDULED, ACTIVE, INACTIVE

    model_config = ConfigDict(from_attributes=True)


class MedicationHistoryResponse(BaseModel):
    """Response containing authenticated patient's medication history timeline."""
    patient_id: int
    total_records: int
    history: List[MedicationHistoryItem]

    model_config = ConfigDict(from_attributes=True)


class RefillPredictionItem(BaseModel):
    """Calculated dynamic refill prediction item for a patient medication."""
    medicine_id: int
    medicine_name: str
    strength: Optional[float] = None
    unit: Optional[str] = None
    dosage_form: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True
    status: str  # "VALID", "INSUFFICIENT_DATA", "ENDED"
    status_message: Optional[str] = None
    current_stock: Optional[int] = None
    daily_consumption: Optional[float] = None
    doses_per_day: Optional[int] = None
    dose_quantity_per_intake: Optional[float] = None
    doses_taken_count: Optional[int] = None
    doses_missed_count: Optional[int] = None
    estimated_remaining_quantity: Optional[float] = None
    estimated_remaining_days: Optional[int] = None
    predicted_refill_date: Optional[date] = None
    urgency_level: Optional[str] = None  # "CRITICAL", "LOW_STOCK", "MODERATE", "GOOD"
    prescription_id: Optional[int] = None
    doctor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RefillPredictionsResponse(BaseModel):
    """Response containing authenticated patient's real refill predictions."""
    patient_id: int
    generated_at: datetime
    total_medications: int
    valid_predictions_count: int
    insufficient_data_count: int
    predictions: List[RefillPredictionItem]

    model_config = ConfigDict(from_attributes=True)
