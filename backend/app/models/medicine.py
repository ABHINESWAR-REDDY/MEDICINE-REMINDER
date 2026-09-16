"""Medicine database model."""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, Date, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import Base


class MedicineForm(str, enum.Enum):
    """Pharmaceutical dosage form."""
    TABLET = "TABLET"
    CAPSULE = "CAPSULE"
    SYRUP = "SYRUP"
    INJECTION = "INJECTION"
    DROPS = "DROPS"
    CREAM = "CREAM"
    OTHER = "OTHER"


class DosageUnit(str, enum.Enum):
    """Measurement unit for medication dosage."""
    MG = "mg"
    MCG = "mcg"
    G = "g"
    ML = "ml"
    TABLET = "tablet"
    CAPSULE = "capsule"
    DROP = "drop"
    UNIT = "unit"


class Medicine(Base):
    """Model representing an individual medication record belonging to a patient."""
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    condition_id = Column(Integer, ForeignKey("conditions.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    dosage_amount = Column(Float, nullable=False)
    dosage_unit = Column(
        Enum(DosageUnit, name="dosage_unit_enum", native_enum=False),
        nullable=False
    )
    quantity = Column(Integer, nullable=False)
    medicine_form = Column(
        Enum(MedicineForm, name="medicine_form_enum", native_enum=False),
        nullable=False,
        default=MedicineForm.TABLET,
        server_default="TABLET"
    )
    instructions = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="medicines")
    condition = relationship("Condition", back_populates="medicines")
    prescription = relationship("Prescription", back_populates="medicines")
    schedules = relationship("MedicationSchedule", back_populates="medicine", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Medicine id={self.id} user_id={self.user_id} name={self.name} is_active={self.is_active}>"
