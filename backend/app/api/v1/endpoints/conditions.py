"""Condition and disease management endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.condition import ConditionCreate, ConditionUpdate, ConditionResponse
from app.services.condition_service import ConditionService

router = APIRouter(prefix="/conditions", tags=["Conditions"])


@router.post("", response_model=ConditionResponse, status_code=status.HTTP_201_CREATED)
def create_condition(
    payload: ConditionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new medical condition for the authenticated patient."""
    service = ConditionService(db)
    return service.create_condition(current_user, payload)


@router.get("", response_model=List[ConditionResponse])
def list_conditions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all conditions belonging to the authenticated patient."""
    service = ConditionService(db)
    return service.list_conditions(current_user)


@router.get("/{condition_id}", response_model=ConditionResponse)
def get_condition(
    condition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific condition by ID."""
    service = ConditionService(db)
    return service.get_condition(current_user, condition_id)


@router.put("/{condition_id}", response_model=ConditionResponse)
def update_condition(
    condition_id: int,
    payload: ConditionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific condition by ID."""
    service = ConditionService(db)
    return service.update_condition(current_user, condition_id, payload)


@router.delete("/{condition_id}", status_code=status.HTTP_200_OK)
def delete_condition(
    condition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a condition by ID."""
    service = ConditionService(db)
    service.delete_condition(current_user, condition_id)
    return {"message": "Condition deleted successfully."}
