"""Medication schedule repository for database persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.schedule import MedicationSchedule
from app.models.medicine import Medicine
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


class ScheduleRepository:
    """Repository handling CRUD operations for medication schedules."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, schedule_id: int, user_id: int) -> Optional[MedicationSchedule]:
        """Fetch a schedule by ID, strictly verifying user ownership via medicine relationship."""
        return (
            self.db.query(MedicationSchedule)
            .join(Medicine, MedicationSchedule.medicine_id == Medicine.id)
            .options(joinedload(MedicationSchedule.medicine))
            .filter(MedicationSchedule.id == schedule_id, Medicine.user_id == user_id)
            .first()
        )

    def list_by_medicine(self, medicine_id: int, user_id: int) -> List[MedicationSchedule]:
        """List all schedules belonging to a specific medicine owned by the user."""
        return (
            self.db.query(MedicationSchedule)
            .join(Medicine, MedicationSchedule.medicine_id == Medicine.id)
            .filter(MedicationSchedule.medicine_id == medicine_id, Medicine.user_id == user_id)
            .order_by(MedicationSchedule.created_at.asc())
            .all()
        )

    def list_by_user(self, user_id: int, is_active: Optional[bool] = None) -> List[MedicationSchedule]:
        """List all schedules across all medicines owned by user."""
        query = (
            self.db.query(MedicationSchedule)
            .join(Medicine, MedicationSchedule.medicine_id == Medicine.id)
            .options(joinedload(MedicationSchedule.medicine))
            .filter(Medicine.user_id == user_id)
        )
        if is_active is not None:
            query = query.filter(MedicationSchedule.is_active == is_active)
        return query.order_by(MedicationSchedule.created_at.asc()).all()

    def create(self, medicine_id: int, schema: ScheduleCreate) -> MedicationSchedule:
        """Create a new schedule for a medicine."""
        schedule = MedicationSchedule(
            medicine_id=medicine_id,
            frequency_type=schema.frequency_type,
            times_per_day=schema.times_per_day,
            scheduled_times=schema.scheduled_times,
            dose_quantity=schema.dose_quantity,
            start_date=schema.start_date,
            end_date=schema.end_date,
            is_active=schema.is_active,
        )
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def update(self, schedule: MedicationSchedule, schema: ScheduleUpdate) -> MedicationSchedule:
        """Update an existing schedule."""
        if schema.frequency_type is not None:
            schedule.frequency_type = schema.frequency_type
        if schema.times_per_day is not None:
            schedule.times_per_day = schema.times_per_day
        if schema.scheduled_times is not None:
            schedule.scheduled_times = schema.scheduled_times
        if schema.dose_quantity is not None:
            schedule.dose_quantity = schema.dose_quantity
        if schema.start_date is not None:
            schedule.start_date = schema.start_date
        if schema.end_date is not None:
            schedule.end_date = schema.end_date
        if schema.is_active is not None:
            schedule.is_active = schema.is_active

        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete(self, schedule: MedicationSchedule) -> bool:
        """Delete a schedule record."""
        self.db.delete(schedule)
        self.db.commit()
        return True
