"""Prescription management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.prescription import PrescriptionStatus
from app.api.deps import get_current_user
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse
from app.services.prescription_service import PrescriptionService

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new prescription for the authenticated patient."""
    service = PrescriptionService(db)
    return service.create_prescription(current_user, payload)


@router.get("", response_model=List[PrescriptionResponse])
def list_prescriptions(
    status_filter: Optional[PrescriptionStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all prescriptions belonging to the authenticated patient."""
    service = PrescriptionService(db)
    return service.list_prescriptions(current_user, status_filter)


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific prescription by ID."""
    service = PrescriptionService(db)
    return service.get_prescription(current_user, prescription_id)


@router.put("/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(
    prescription_id: int,
    payload: PrescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific prescription by ID."""
    service = PrescriptionService(db)
    return service.update_prescription(current_user, prescription_id, payload)


@router.delete("/{prescription_id}", status_code=status.HTTP_200_OK)
def delete_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a prescription by ID."""
    service = PrescriptionService(db)
    service.delete_prescription(current_user, prescription_id)
    return {"message": "Prescription deleted successfully."}
