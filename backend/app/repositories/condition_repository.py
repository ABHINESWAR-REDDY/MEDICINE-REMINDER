"""Condition repository for database persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.condition import Condition
from app.schemas.condition import ConditionCreate, ConditionUpdate


class ConditionRepository:
    """Repository handling CRUD operations for medical conditions."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, condition_id: int, user_id: int) -> Optional[Condition]:
        """Fetch a condition by ID strictly scoped to a user."""
        return (
            self.db.query(Condition)
            .filter(Condition.id == condition_id, Condition.user_id == user_id)
            .first()
        )

    def list_by_user(self, user_id: int) -> List[Condition]:
        """List all conditions belonging to a user ordered by creation date."""
        return (
            self.db.query(Condition)
            .filter(Condition.user_id == user_id)
            .order_by(Condition.created_at.desc())
            .all()
        )

    def create(self, user_id: int, schema: ConditionCreate) -> Condition:
        """Create a new condition record belonging to user."""
        condition = Condition(
            user_id=user_id,
            name=schema.name.strip(),
            description=schema.description.strip() if schema.description else None,
        )
        self.db.add(condition)
        self.db.commit()
        self.db.refresh(condition)
        return condition

    def update(self, condition: Condition, schema: ConditionUpdate) -> Condition:
        """Update an existing condition record."""
        if schema.name is not None:
            condition.name = schema.name.strip()
        if schema.description is not None:
            condition.description = schema.description.strip() if schema.description else None

        self.db.commit()
        self.db.refresh(condition)
        return condition

    def delete(self, condition: Condition) -> bool:
        """Delete a condition record."""
        self.db.delete(condition)
        self.db.commit()
        return True
