"""Patient Portal Medication History and Refill Predictions API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_patient
from app.core.database import get_db
from app.models.user import User
from app.schemas.patient_portal import (
    MedicationHistoryResponse,
    RefillPredictionsResponse,
)
from app.services.patient_service import PatientService

router = APIRouter()


@router.get(
    "/medication-history",
    response_model=MedicationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient medication history",
    description="Returns complete medication and intake history for the authenticated patient.",
)
def get_medication_history(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
) -> MedicationHistoryResponse:
    """Retrieve full medication history timeline for the logged-in patient."""
    service = PatientService(db)
    return service.get_medication_history(patient_id=current_user.id)


@router.get(
    "/refill-predictions",
    response_model=RefillPredictionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dynamic medication refill predictions",
    description="Calculates remaining stock and predicted refill dates dynamically for the authenticated patient.",
)
def get_refill_predictions(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db),
) -> RefillPredictionsResponse:
    """Calculate and return real-time refill predictions for the logged-in patient."""
    service = PatientService(db)
    return service.get_refill_predictions(patient_id=current_user.id)
