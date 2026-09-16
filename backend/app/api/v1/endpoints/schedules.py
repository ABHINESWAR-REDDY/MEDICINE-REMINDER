"""Medication Schedule management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.schedule import ScheduleUpdate, ScheduleResponse
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=List[ScheduleResponse])
def list_user_schedules(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all schedules across all medicines owned by the authenticated patient."""
    service = ScheduleService(db)
    return service.list_user_schedules(current_user, is_active)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific schedule by ID, validating full ownership."""
    service = ScheduleService(db)
    return service.get_schedule(current_user, schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific schedule by ID."""
    service = ScheduleService(db)
    return service.update_schedule(current_user, schedule_id, payload)


@router.delete("/{schedule_id}", status_code=status.HTTP_200_OK)
def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific schedule by ID."""
    service = ScheduleService(db)
    service.delete_schedule(current_user, schedule_id)
    return {"message": "Schedule deleted successfully."}
