"""Service handling business logic and authorization for medication dosage schedules."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.schedule import MedicationSchedule
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.medicine_repository import MedicineRepository
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


class ScheduleService:
    """Service providing business logic and ownership validation for medication schedules."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ScheduleRepository(db)
        self.medicine_repo = MedicineRepository(db)

    def _verify_patient_access(self, current_user: User):
        """Ensure only authenticated PATIENT role can manage schedules in Phase 2."""
        if current_user.role != UserRole.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only patients can manage medication schedules in Phase 2."
            )

    def create_schedule(self, current_user: User, medicine_id: int, data: ScheduleCreate) -> MedicationSchedule:
        """Create a new dosage schedule for a medicine owned by the patient."""
        self._verify_patient_access(current_user)
        medicine = self.medicine_repo.get_by_id(medicine_id, current_user.id)
        if not medicine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicine not found or access denied."
            )
        return self.repo.create(medicine_id, data)

    def list_schedules_for_medicine(self, current_user: User, medicine_id: int) -> List[MedicationSchedule]:
        """List all schedules for a specific medicine owned by the patient."""
        self._verify_patient_access(current_user)
        medicine = self.medicine_repo.get_by_id(medicine_id, current_user.id)
        if not medicine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicine not found or access denied."
            )
        return self.repo.list_by_medicine(medicine_id, current_user.id)

    def list_user_schedules(self, current_user: User, is_active: Optional[bool] = None) -> List[MedicationSchedule]:
        """List all schedules across all medicines owned by the patient."""
        self._verify_patient_access(current_user)
        return self.repo.list_by_user(current_user.id, is_active)

    def get_schedule(self, current_user: User, schedule_id: int) -> MedicationSchedule:
        """Get a single schedule by ID verifying the full ownership chain."""
        self._verify_patient_access(current_user)
        schedule = self.repo.get_by_id(schedule_id, current_user.id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found or access denied."
            )
        return schedule

    def update_schedule(self, current_user: User, schedule_id: int, data: ScheduleUpdate) -> MedicationSchedule:
        """Update an existing schedule verifying ownership."""
        schedule = self.get_schedule(current_user, schedule_id)
        return self.repo.update(schedule, data)

    def delete_schedule(self, current_user: User, schedule_id: int) -> bool:
        """Delete a schedule verifying ownership."""
        schedule = self.get_schedule(current_user, schedule_id)
        return self.repo.delete(schedule)
