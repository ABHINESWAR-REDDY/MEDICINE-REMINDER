"""Medicine management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.medicine import MedicineCreate, MedicineUpdate, MedicineResponse
from app.schemas.schedule import ScheduleCreate, ScheduleResponse
from app.services.medicine_service import MedicineService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.post("", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
def create_medicine(
    payload: MedicineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new medicine record for the authenticated patient."""
    service = MedicineService(db)
    return service.create_medicine(current_user, payload)


@router.get("", response_model=List[MedicineResponse])
def list_medicines(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List medicines belonging to the authenticated patient."""
    service = MedicineService(db)
    return service.list_medicines(current_user, is_active)


@router.get("/{medicine_id}", response_model=MedicineResponse)
def get_medicine(
    medicine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific medicine by ID."""
    service = MedicineService(db)
    return service.get_medicine(current_user, medicine_id)


@router.put("/{medicine_id}", response_model=MedicineResponse)
def update_medicine(
    medicine_id: int,
    payload: MedicineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific medicine by ID."""
    service = MedicineService(db)
    return service.update_medicine(current_user, medicine_id, payload)


@router.post("/{medicine_id}/deactivate", response_model=MedicineResponse)
def deactivate_medicine(
    medicine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Safely deactivate a medicine without deleting historical records."""
    service = MedicineService(db)
    return service.deactivate_medicine(current_user, medicine_id)


@router.delete("/{medicine_id}", status_code=status.HTTP_200_OK)
def delete_medicine(
    medicine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a medicine by ID."""
    service = MedicineService(db)
    service.delete_medicine(current_user, medicine_id)
    return {"message": "Medicine deleted successfully."}


# Nested schedule endpoints for a medicine
@router.post("/{medicine_id}/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_medicine_schedule(
    medicine_id: int,
    payload: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a dosage schedule for a medicine owned by the patient."""
    schedule_service = ScheduleService(db)
    return schedule_service.create_schedule(current_user, medicine_id, payload)


@router.get("/{medicine_id}/schedules", response_model=List[ScheduleResponse])
def list_medicine_schedules(
    medicine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all dosage schedules for a medicine owned by the patient."""
    schedule_service = ScheduleService(db)
    return schedule_service.list_schedules_for_medicine(current_user, medicine_id)
