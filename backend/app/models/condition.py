"""Condition and disease database model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Condition(Base):
    """Model representing a medical condition or disease tracked by a patient."""
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
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
    user = relationship("User", back_populates="conditions")
    medicines = relationship("Medicine", back_populates="condition", cascade="all, delete-orphan", passive_deletes=False)

    def __repr__(self) -> str:
        return f"<Condition id={self.id} user_id={self.user_id} name={self.name}>"
