"""Service handling business logic and authorization for patient medications."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.medicine import Medicine
from app.repositories.medicine_repository import MedicineRepository
from app.repositories.condition_repository import ConditionRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.medicine import MedicineCreate, MedicineUpdate
from app.services.audit_service import AuditService


class MedicineService:
    """Service providing business logic and security validation for patient medicines."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = MedicineRepository(db)
        self.condition_repo = ConditionRepository(db)
        self.prescription_repo = PrescriptionRepository(db)
        self.audit = AuditService(db)

    def _verify_patient_access(self, current_user: User):
        """Ensure only authenticated PATIENT role can manage medications in Phase 2."""
        if current_user.role != UserRole.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only patients can manage medications in Phase 2."
            )

    def _validate_foreign_keys(self, user_id: int, condition_id: Optional[int], prescription_id: Optional[int]):
        """Ensure any referenced condition or prescription belongs to the authenticated user."""
        if condition_id is not None and condition_id > 0:
            cond = self.condition_repo.get_by_id(condition_id, user_id)
            if not cond:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced condition does not exist or does not belong to you."
                )

        if prescription_id is not None and prescription_id > 0:
            rx = self.prescription_repo.get_by_id(prescription_id, user_id)
            if not rx:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced prescription does not exist or does not belong to you."
                )

    def create_medicine(self, current_user: User, data: MedicineCreate) -> Medicine:
        """Create a new medicine strictly scoped to the authenticated patient."""
        self._verify_patient_access(current_user)
        self._validate_foreign_keys(current_user.id, data.condition_id, data.prescription_id)
        med = self.repo.create(current_user.id, data)
        self.audit.log(
            action="MEDICATION_CREATED",
            target_type="Medicine",
            actor_user_id=current_user.id,
            target_id=med.id,
            details={"name": med.name, "dosage_amount": med.dosage_amount, "dosage_unit": str(med.dosage_unit) if med.dosage_unit else None}
        )
        return med

    def list_medicines(self, current_user: User, is_active: Optional[bool] = None) -> List[Medicine]:
        """List medicines belonging strictly to the authenticated patient."""
        self._verify_patient_access(current_user)
        return self.repo.list_by_user(current_user.id, is_active)

    def get_medicine(self, current_user: User, medicine_id: int) -> Medicine:
        """Get a single medicine by ID, enforcing ownership."""
        self._verify_patient_access(current_user)
        medicine = self.repo.get_by_id(medicine_id, current_user.id)
        if not medicine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicine not found or access denied."
            )
        return medicine

    def update_medicine(self, current_user: User, medicine_id: int, data: MedicineUpdate) -> Medicine:
        """Update an existing medicine, enforcing ownership."""
        medicine = self.get_medicine(current_user, medicine_id)
        self._validate_foreign_keys(
            current_user.id,
            data.condition_id if data.condition_id is not None else medicine.condition_id,
            data.prescription_id if data.prescription_id is not None else medicine.prescription_id
        )
        updated = self.repo.update(medicine, data)
        self.audit.log(
            action="MEDICATION_UPDATED",
            target_type="Medicine",
            actor_user_id=current_user.id,
            target_id=updated.id,
            details={"name": updated.name}
        )
        return updated

    def deactivate_medicine(self, current_user: User, medicine_id: int) -> Medicine:
        """Safely deactivate a medicine without deleting historical records."""
        medicine = self.get_medicine(current_user, medicine_id)
        deactivated = self.repo.deactivate(medicine)
        self.audit.log(
            action="MEDICATION_DEACTIVATED",
            target_type="Medicine",
            actor_user_id=current_user.id,
            target_id=deactivated.id,
            details={"name": deactivated.name}
        )
        return deactivated

    def delete_medicine(self, current_user: User, medicine_id: int) -> bool:
        """Permanently delete a medicine."""
        medicine = self.get_medicine(current_user, medicine_id)
        med_name = medicine.name
        med_id = medicine.id
        deleted = self.repo.delete(medicine)
        self.audit.log(
            action="MEDICATION_DELETED",
            target_type="Medicine",
            actor_user_id=current_user.id,
            target_id=med_id,
            details={"name": med_name}
        )
        return deleted
