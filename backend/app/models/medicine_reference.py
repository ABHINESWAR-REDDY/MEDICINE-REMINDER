"""Medicine Reference database model for Phase 3 OCR normalization and validation."""

from sqlalchemy import Column, Integer, String
from app.core.database import Base
from app.models.base import TimestampMixin


class MedicineReference(Base, TimestampMixin):
    """
    Global reference dataset for medicine candidate matching, normalization,
    and validation. This is separate from authenticated patient medications.
    """
    __tablename__ = "medicine_references"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=True)
    strength = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    indication = Column(String(255), nullable=True)
    classification = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<MedicineReference(id={self.id}, name='{self.name}', form='{self.dosage_form}', strength='{self.strength}')>"
