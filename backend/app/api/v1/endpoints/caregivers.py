"""Caregiver supervision API endpoints for assigned patients, clinical/refill alerts, and adherence reports."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_caregiver
from app.core.database import get_db
from app.models.user import User
from app.schemas.caregiver import (
    CaregiverDashboardResponse,
    AssignedPatientSummary,
    CaregiverAlert,
    CaregiverAdherenceReportsResponse,
    PatientAdherenceReportDetail,
    CaregiverRefillNotificationsResponse,
)
from app.services.caregiver_service import CaregiverService

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=CaregiverDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get caregiver dashboard overview",
    description="Returns aggregate adherence, scheduled, taken, missed, and pending doses for assigned patients.",
)
def get_caregiver_dashboard(
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db)
) -> CaregiverDashboardResponse:
    """Retrieve Caregiver Dashboard metrics."""
    service = CaregiverService(db)
    return service.get_dashboard(current_user)


@router.get(
    "/patients",
    response_model=List[AssignedPatientSummary],
    status_code=status.HTTP_200_OK,
    summary="List assigned patients",
    description="Returns only patients explicitly assigned to the authenticated caregiver with live adherence rates.",
)
def get_assigned_patients(
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db)
) -> List[AssignedPatientSummary]:
    """List assigned patients."""
    service = CaregiverService(db)
    return service.get_assigned_patients(current_user)


@router.get(
    "/patients/{patient_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get assigned patient detail",
    description="STRICT RBAC: Returns medical schedules, today's doses, and adherence for assigned patient only.",
)
def get_assigned_patient_detail(
    patient_id: int,
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve assigned patient detail."""
    service = CaregiverService(db)
    return service.get_patient_detail(current_user, patient_id)


@router.get(
    "/alerts",
    response_model=List[CaregiverAlert],
    status_code=status.HTTP_200_OK,
    summary="Get caregiver clinical and refill alerts",
    description="Returns alerts for missed doses, refill shortages, and high adherence risks among assigned patients.",
)
def get_caregiver_alerts(
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db)
) -> List[CaregiverAlert]:
    """Retrieve alerts for assigned patients."""
    service = CaregiverService(db)
    return service.get_alerts(current_user)


@router.post(
    "/alerts/read-all",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Mark all caregiver alerts as read",
    description="Marks all active clinical and refill alerts as read for the authenticated caregiver.",
)
def mark_all_caregiver_alerts_read(
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Mark all alerts as read for caregiver."""
    service = CaregiverService(db)
    return service.mark_all_alerts_read(current_user)


@router.post(
    "/alerts/{alert_id}/read",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Mark specific caregiver alert as read",
    description="Marks a specific alert (missed dose, refill alert, message, or adherence risk) as read/acknowledged.",
)
def mark_caregiver_alert_read(
    alert_id: str,
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Mark individual alert as read."""
    service = CaregiverService(db)
    return service.mark_alert_read(current_user, alert_id)


@router.get(
    "/adherence-reports",
    response_model=CaregiverAdherenceReportsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get adherence reports for assigned patients",
    description="Calculates dynamic adherence compliance across all patients assigned to this caregiver for the requested period.",
)
def get_caregiver_adherence_reports(
    days: int = Query(30, ge=1, le=365, description="Period window in days (e.g. 1, 7, 30, 90)"),
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db),
) -> CaregiverAdherenceReportsResponse:
    """Retrieve multi-patient adherence summary reports."""
    service = CaregiverService(db)
    return service.get_adherence_reports(current_user, days=days)


@router.get(
    "/patients/{patient_id}/adherence",
    response_model=PatientAdherenceReportDetail,
    status_code=status.HTTP_200_OK,
    summary="Get detailed adherence report for specific assigned patient",
    description="STRICT RBAC: Returns comprehensive medication-wise adherence breakdown and recent dose log for assigned patient only.",
)
def get_patient_adherence_report(
    patient_id: int,
    days: int = Query(30, ge=1, le=365, description="Period window in days (e.g. 1, 7, 30, 90)"),
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db),
) -> PatientAdherenceReportDetail:
    """Retrieve patient-specific adherence analysis and dose history."""
    service = CaregiverService(db)
    return service.get_patient_adherence_report(current_user, patient_id=patient_id, days=days)


@router.get(
    "/refill-notifications",
    response_model=CaregiverRefillNotificationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dynamic refill notifications for assigned patients",
    description="Returns low-stock and critical refill notifications calculated from assigned patients' medications and schedules.",
)
def get_caregiver_refill_notifications(
    current_user: User = Depends(require_caregiver),
    db: Session = Depends(get_db),
) -> CaregiverRefillNotificationsResponse:
    """Retrieve active refill shortage alerts for assigned patients."""
    service = CaregiverService(db)
    return service.get_refill_notifications(current_user)
