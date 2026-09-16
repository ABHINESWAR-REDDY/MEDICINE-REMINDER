"""Prescription repository for database persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.prescription import Prescription, PrescriptionStatus
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate


class PrescriptionRepository:
    """Repository handling CRUD operations for prescriptions."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, prescription_id: int, user_id: int) -> Optional[Prescription]:
        """Fetch a prescription by ID strictly scoped to a user."""
        return (
            self.db.query(Prescription)
            .filter(Prescription.id == prescription_id, Prescription.user_id == user_id)
            .first()
        )

    def list_by_user(self, user_id: int, status: Optional[PrescriptionStatus] = None) -> List[Prescription]:
        """List all prescriptions belonging to a user."""
        query = self.db.query(Prescription).filter(Prescription.user_id == user_id)
        if status is not None:
            query = query.filter(Prescription.status == status)
        return query.order_by(Prescription.created_at.desc()).all()

    def create(self, user_id: int, schema: PrescriptionCreate) -> Prescription:
        """Create a new prescription record belonging to user."""
        prescription = Prescription(
            user_id=user_id,
            prescription_number=schema.prescription_number.strip() if schema.prescription_number else None,
            doctor_name=schema.doctor_name.strip() if schema.doctor_name else None,
            issue_date=schema.issue_date,
            expiry_date=schema.expiry_date,
            notes=schema.notes.strip() if schema.notes else None,
            status=schema.status,
        )
        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def update(self, prescription: Prescription, schema: PrescriptionUpdate) -> Prescription:
        """Update an existing prescription record."""
        if schema.prescription_number is not None:
            prescription.prescription_number = schema.prescription_number.strip() if schema.prescription_number else None
        if schema.doctor_name is not None:
            prescription.doctor_name = schema.doctor_name.strip() if schema.doctor_name else None
        if schema.issue_date is not None:
            prescription.issue_date = schema.issue_date
        if schema.expiry_date is not None:
            prescription.expiry_date = schema.expiry_date
        if schema.notes is not None:
            prescription.notes = schema.notes.strip() if schema.notes else None
        if schema.status is not None:
            prescription.status = schema.status

        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def delete(self, prescription: Prescription) -> bool:
        """Delete a prescription record."""
        self.db.delete(prescription)
        self.db.commit()
        return True
