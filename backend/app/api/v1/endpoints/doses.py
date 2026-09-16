"""Patient medication dose tracking and adherence API endpoints."""

from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_patient, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dose import (
    MedicationDoseResponse,
    AdherenceResponse,
    DoseActionResponse,
)
from app.services.dose_service import DoseService
from app.services.adherence_service import AdherenceService

router = APIRouter()


@router.get(
    "/doses",
    response_model=List[MedicationDoseResponse],
    status_code=status.HTTP_200_OK,
    summary="Get patient medication doses for a date",
    description="Returns all scheduled, taken, missed, and skipped doses for the authenticated patient.",
)
def get_patient_doses(
    target_date: Optional[date] = Query(None, description="Date for doses, defaults to today"),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
) -> List[MedicationDoseResponse]:
    """Retrieve today's dose tracker list."""
    service = DoseService(db)
    return service.get_patient_doses(current_user.id, target_date=target_date)


@router.post(
    "/doses/{id}/take",
    response_model=DoseActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark medication dose as taken",
    description="Transitions dose status to TAKEN with the current UTC timestamp.",
)
def mark_dose_taken(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DoseActionResponse:
    """Mark dose as taken."""
    service = DoseService(db)
    return service.mark_dose_taken(id, current_user)


@router.post(
    "/doses/{id}/skip",
    response_model=DoseActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark medication dose as skipped",
    description="Transitions dose status to SKIPPED.",
)
def mark_dose_skipped(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DoseActionResponse:
    """Mark dose as skipped."""
    service = DoseService(db)
    return service.mark_dose_skipped(id, current_user)



@router.get(
    "/adherence",
    response_model=AdherenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient adherence metrics",
    description="Calculates strict mathematical adherence rate over past 30 days (excluding future doses).",
)
def get_patient_adherence(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
) -> AdherenceResponse:
    """Retrieve patient adherence analytics."""
    service = AdherenceService(db)
    return service.calculate_adherence(current_user.id, days=days)
