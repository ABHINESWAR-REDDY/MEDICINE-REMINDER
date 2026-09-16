"""Medicine repository for database persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.medicine import Medicine
from app.schemas.medicine import MedicineCreate, MedicineUpdate


class MedicineRepository:
    """Repository handling CRUD operations for patient medicines."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, medicine_id: int, user_id: int) -> Optional[Medicine]:
        """Fetch a medicine by ID strictly scoped to a user with relationships eagerly loaded."""
        return (
            self.db.query(Medicine)
            .options(
                joinedload(Medicine.condition),
                joinedload(Medicine.prescription),
                joinedload(Medicine.schedules),
            )
            .filter(Medicine.id == medicine_id, Medicine.user_id == user_id)
            .first()
        )

    def list_by_user(self, user_id: int, is_active: Optional[bool] = None) -> List[Medicine]:
        """List all medicines belonging to a user, optionally filtered by active status."""
        query = (
            self.db.query(Medicine)
            .options(
                joinedload(Medicine.condition),
                joinedload(Medicine.prescription),
                joinedload(Medicine.schedules),
            )
            .filter(Medicine.user_id == user_id)
        )
        if is_active is not None:
            query = query.filter(Medicine.is_active == is_active)
        return query.order_by(Medicine.created_at.desc()).all()

    def create(self, user_id: int, schema: MedicineCreate) -> Medicine:
        """Create a new medicine record belonging to user."""
        medicine = Medicine(
            user_id=user_id,
            prescription_id=schema.prescription_id,
            condition_id=schema.condition_id,
            name=schema.name.strip(),
            dosage_amount=schema.dosage_amount,
            dosage_unit=schema.dosage_unit,
            quantity=schema.quantity,
            medicine_form=schema.medicine_form,
            instructions=schema.instructions.strip() if schema.instructions else None,
            start_date=schema.start_date,
            end_date=schema.end_date,
            is_active=schema.is_active,
        )
        self.db.add(medicine)
        self.db.commit()
        self.db.refresh(medicine)
        return self.get_by_id(medicine.id, user_id)

    def update(self, medicine: Medicine, schema: MedicineUpdate) -> Medicine:
        """Update an existing medicine record."""
        if schema.name is not None:
            medicine.name = schema.name.strip()
        if schema.dosage_amount is not None:
            medicine.dosage_amount = schema.dosage_amount
        if schema.dosage_unit is not None:
            medicine.dosage_unit = schema.dosage_unit
        if schema.quantity is not None:
            medicine.quantity = schema.quantity
        if schema.medicine_form is not None:
            medicine.medicine_form = schema.medicine_form
        if schema.instructions is not None:
            medicine.instructions = schema.instructions.strip() if schema.instructions else None
        if schema.start_date is not None:
            medicine.start_date = schema.start_date
        if schema.end_date is not None:
            medicine.end_date = schema.end_date
        if schema.is_active is not None:
            medicine.is_active = schema.is_active
        if schema.condition_id is not None:
            medicine.condition_id = schema.condition_id if schema.condition_id != 0 else None
        if schema.prescription_id is not None:
            medicine.prescription_id = schema.prescription_id if schema.prescription_id != 0 else None

        self.db.commit()
        self.db.refresh(medicine)
        return self.get_by_id(medicine.id, medicine.user_id)

    def deactivate(self, medicine: Medicine) -> Medicine:
        """Safely deactivate a medicine without deleting historical records."""
        medicine.is_active = False
        self.db.commit()
        self.db.refresh(medicine)
        return medicine

    def delete(self, medicine: Medicine) -> bool:
        """Permanently delete a medicine and its associated schedules."""
        self.db.delete(medicine)
        self.db.commit()
        return True
