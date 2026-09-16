"""Pydantic schemas for Medication Dosage Schedule management."""

import re
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from app.models.schedule import ScheduleFrequency

TIME_24H_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class ScheduleBase(BaseModel):
    """Base dosage schedule schema."""
    frequency_type: ScheduleFrequency = Field(..., description="Frequency pattern")
    times_per_day: int = Field(default=1, gt=0, description="Number of intake occurrences per day")
    scheduled_times: List[str] = Field(..., min_length=1, description="List of 24h 'HH:MM' time strings")
    dose_quantity: float = Field(default=1.0, gt=0, description="Dose amount to take per occurrence")
    start_date: date = Field(..., description="Schedule effective start date")
    end_date: Optional[date] = Field(None, description="Optional schedule end date")
    is_active: bool = Field(default=True, description="Whether schedule is active")

    @field_validator("scheduled_times")
    @classmethod
    def validate_times(cls, times: List[str]) -> List[str]:
        for t in times:
            if not isinstance(t, str) or not TIME_24H_REGEX.match(t.strip()):
                raise ValueError(f"Invalid 24-hour time format '{t}'. Expected 'HH:MM' (e.g. '08:00', '20:30').")
        return [t.strip() for t in times]

    @model_validator(mode="after")
    def validate_frequency_and_dates(self):
        # Validate date consistency
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")

        # Validate frequency count vs scheduled_times length
        expected_counts = {
            ScheduleFrequency.ONCE_DAILY: 1,
            ScheduleFrequency.TWICE_DAILY: 2,
            ScheduleFrequency.THREE_TIMES_DAILY: 3,
            ScheduleFrequency.FOUR_TIMES_DAILY: 4,
        }

        if self.frequency_type in expected_counts:
            expected = expected_counts[self.frequency_type]
            if len(self.scheduled_times) != expected:
                raise ValueError(
                    f"Frequency '{self.frequency_type.value}' requires exactly {expected} scheduled time(s), "
                    f"but received {len(self.scheduled_times)}."
                )
            self.times_per_day = expected
        elif self.frequency_type == ScheduleFrequency.CUSTOM:
            if len(self.scheduled_times) != self.times_per_day:
                raise ValueError(
                    f"Custom frequency 'times_per_day' ({self.times_per_day}) must match count of scheduled_times ({len(self.scheduled_times)})."
                )

        return self


class ScheduleCreate(ScheduleBase):
    """Schema for creating a dosage schedule."""
    pass


class ScheduleUpdate(BaseModel):
    """Schema for updating an existing schedule."""
    frequency_type: Optional[ScheduleFrequency] = None
    times_per_day: Optional[int] = Field(None, gt=0)
    scheduled_times: Optional[List[str]] = Field(None, min_length=1)
    dose_quantity: Optional[float] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

    @field_validator("scheduled_times")
    @classmethod
    def validate_times(cls, times: Optional[List[str]]) -> Optional[List[str]]:
        if times is not None:
            for t in times:
                if not isinstance(t, str) or not TIME_24H_REGEX.match(t.strip()):
                    raise ValueError(f"Invalid 24-hour time format '{t}'. Expected 'HH:MM'.")
            return [t.strip() for t in times]
        return times

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        return self


class ScheduleResponse(ScheduleBase):
    """Schema for returning schedule data."""
    id: int
    medicine_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
