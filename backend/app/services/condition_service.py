"""Service handling business logic and authorization for medical conditions."""

from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.condition import Condition
from app.repositories.condition_repository import ConditionRepository
from app.schemas.condition import ConditionCreate, ConditionUpdate


class ConditionService:
    """Service providing business logic for patient medical conditions."""

    def __init__(self, db: Session):
        self.repo = ConditionRepository(db)

    def _verify_patient_access(self, current_user: User):
        """Ensure only authenticated PATIENT role can manage conditions in Phase 2."""
        if current_user.role != UserRole.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only patients can manage medical conditions in Phase 2."
            )

    def create_condition(self, current_user: User, data: ConditionCreate) -> Condition:
        """Create a new condition for the authenticated patient."""
        self._verify_patient_access(current_user)
        return self.repo.create(current_user.id, data)

    def list_conditions(self, current_user: User) -> List[Condition]:
        """List all conditions belonging strictly to the authenticated patient."""
        self._verify_patient_access(current_user)
        return self.repo.list_by_user(current_user.id)

    def get_condition(self, current_user: User, condition_id: int) -> Condition:
        """Get a single condition by ID verifying ownership."""
        self._verify_patient_access(current_user)
        condition = self.repo.get_by_id(condition_id, current_user.id)
        if not condition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Condition not found or access denied."
            )
        return condition

    def update_condition(self, current_user: User, condition_id: int, data: ConditionUpdate) -> Condition:
        """Update an existing condition verifying ownership."""
        condition = self.get_condition(current_user, condition_id)
        return self.repo.update(condition, data)

    def delete_condition(self, current_user: User, condition_id: int) -> bool:
        """Delete a condition verifying ownership and safely detaching from medicines."""
        condition = self.get_condition(current_user, condition_id)
        return self.repo.delete(condition)
