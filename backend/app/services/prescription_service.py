"""Service handling business logic and authorization for prescriptions."""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.prescription import Prescription, PrescriptionStatus
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate
from app.services.audit_service import AuditService


class PrescriptionService:
    """Service providing business logic for patient prescriptions."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PrescriptionRepository(db)
        self.audit = AuditService(db)

    def _verify_patient_access(self, current_user: User):
        """Ensure only authenticated PATIENT role can manage prescriptions in Phase 2."""
        if current_user.role != UserRole.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only patients can manage prescriptions in Phase 2."
            )

    def create_prescription(self, current_user: User, data: PrescriptionCreate) -> Prescription:
        """Create a new prescription for the authenticated patient."""
        self._verify_patient_access(current_user)
        rx = self.repo.create(current_user.id, data)
        self.audit.log(
            action="PRESCRIPTION_UPLOADED",
            target_type="Prescription",
            actor_user_id=current_user.id,
            target_id=rx.id,
            details={"doctor_name": rx.doctor_name, "status": rx.status.value if rx.status else None}
        )
        return rx

    def list_prescriptions(self, current_user: User, status_filter: Optional[PrescriptionStatus] = None) -> List[Prescription]:
        """List all prescriptions belonging strictly to the authenticated patient."""
        self._verify_patient_access(current_user)
        return self.repo.list_by_user(current_user.id, status_filter)

    def get_prescription(self, current_user: User, prescription_id: int) -> Prescription:
        """Get a single prescription by ID verifying ownership."""
        self._verify_patient_access(current_user)
        prescription = self.repo.get_by_id(prescription_id, current_user.id)
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found or access denied."
            )
        return prescription

    def update_prescription(self, current_user: User, prescription_id: int, data: PrescriptionUpdate) -> Prescription:
        """Update an existing prescription verifying ownership."""
        prescription = self.get_prescription(current_user, prescription_id)
        return self.repo.update(prescription, data)

    def delete_prescription(self, current_user: User, prescription_id: int) -> bool:
        """Delete a prescription verifying ownership."""
        prescription = self.get_prescription(current_user, prescription_id)
        rx_id = prescription.id
        deleted = self.repo.delete(prescription)
        self.audit.log(
            action="PRESCRIPTION_DELETED",
            target_type="Prescription",
            actor_user_id=current_user.id,
            target_id=rx_id,
            details={"prescription_id": rx_id}
        )
        return deleted
