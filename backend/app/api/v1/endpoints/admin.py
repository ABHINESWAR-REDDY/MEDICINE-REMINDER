from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Body, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminDashboardResponse,
    CaregiverListItem,
    PatientListItem,
    AssignPatientRequest,
    AssignmentResponseItem,
    AuditLogResponseItem,
    PlatformActivitiesResponse,
    NotificationSettingsSchema,
    NotificationSettingsUpdate,
    PlatformAnalyticsResponse,
    SystemHealthResponse,
    SystemOperationResponse,
)
from app.services.admin_service import AdminService

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get admin dashboard overview metrics",
    description="Returns live system statistics: patients, caregivers, approvals, doses, and assignments.",
)
def get_admin_dashboard(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> AdminDashboardResponse:
    """Retrieve system overview metrics for Admin."""
    service = AdminService(db)
    return service.get_dashboard_stats()


@router.get(
    "/caregivers",
    response_model=List[CaregiverListItem],
    status_code=status.HTTP_200_OK,
    summary="List all caregivers",
    description="Filter caregivers by status (PENDING, APPROVED, REJECTED, ACTIVE, INACTIVE).",
)
def get_caregivers(
    status: Optional[str] = Query(None, description="Optional status filter"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[CaregiverListItem]:
    """Retrieve caregivers list."""
    service = AdminService(db)
    return service.get_caregivers(status_filter=status)


@router.get(
    "/caregivers/pending",
    response_model=List[CaregiverListItem],
    status_code=status.HTTP_200_OK,
    summary="Get pending caregiver approval requests",
    description="Returns all caregiver accounts awaiting administrator approval.",
)
def get_pending_caregivers(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[CaregiverListItem]:
    """Retrieve pending caregivers."""
    service = AdminService(db)
    return service.get_pending_caregivers()


@router.post(
    "/caregivers/{id}/approve",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Approve caregiver account",
    description="Approves a caregiver registration and activates their login permissions.",
)
def approve_caregiver(
    id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Approve caregiver account."""
    service = AdminService(db)
    return service.approve_caregiver(id, current_user)


@router.post(
    "/caregivers/{id}/reject",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reject caregiver registration",
    description="Rejects a pending caregiver account.",
)
def reject_caregiver(
    id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Reject caregiver account."""
    service = AdminService(db)
    return service.reject_caregiver(id, current_user)


@router.post(
    "/caregivers/{id}/activate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Activate caregiver account",
)
def activate_caregiver(
    id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Activate caregiver account."""
    service = AdminService(db)
    return service.activate_caregiver(id, current_user)


@router.post(
    "/caregivers/{id}/deactivate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Deactivate caregiver account",
)
def deactivate_caregiver(
    id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Deactivate caregiver account."""
    service = AdminService(db)
    return service.deactivate_caregiver(id, current_user)


@router.get(
    "/assignments",
    response_model=List[AssignmentResponseItem],
    status_code=status.HTTP_200_OK,
    summary="List caregiver-patient assignments",
)
def get_assignments(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[AssignmentResponseItem]:
    """List active assignments."""
    service = AdminService(db)
    return service.get_assignments()


@router.post(
    "/assignments",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Assign a patient to a caregiver",
)
def assign_patient(
    payload: AssignPatientRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Assign patient to caregiver."""
    service = AdminService(db)
    return service.assign_patient_to_caregiver(payload.caregiver_id, payload.patient_id, current_user)


@router.delete(
    "/assignments/{id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Revoke a caregiver-patient assignment",
)
def revoke_assignment(
    id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Revoke assignment."""
    service = AdminService(db)
    return service.revoke_assignment(id, current_user)


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponseItem],
    status_code=status.HTTP_200_OK,
    summary="Get recent technical audit logs",
)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[AuditLogResponseItem]:
    """Retrieve audit logs."""
    service = AdminService(db)
    return service.get_audit_logs(limit=limit, offset=offset)


@router.get(
    "/patients",
    response_model=List[PatientListItem],
    status_code=status.HTTP_200_OK,
    summary="List all patients with assigned caregiver and medication counts",
    description="Admin-only endpoint returning real registered patient accounts from database.",
)
def get_patients(
    status: Optional[str] = Query(None, description="Optional status filter (ACTIVE, INACTIVE)"),
    search: Optional[str] = Query(None, description="Optional search by name or email"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[PatientListItem]:
    """Retrieve patients directory."""
    service = AdminService(db)
    return service.get_patients(status_filter=status, search_query=search)


@router.post(
    "/patients/{id}/toggle-active",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Toggle patient active/inactive status",
)
def toggle_patient_active(
    id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Toggle patient active status."""
    service = AdminService(db)
    return service.toggle_patient_active(id, current_user)


# =============================================================================
# 1. PLATFORM ACTIVITIES ENDPOINTS
# =============================================================================

@router.get(
    "/activities",
    response_model=PlatformActivitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Monitor real platform activities and audit events",
    description="Retrieve paginated platform activities with role, action, target, date, and keyword search filters.",
)
def get_platform_activities(
    search: Optional[str] = Query(None, description="Search keyword in actor name, email, action, target"),
    role: Optional[str] = Query(None, description="Filter by actor role (PATIENT, CAREGIVER, ADMIN, SYSTEM)"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    target_type: Optional[str] = Query(None, description="Filter by target resource type"),
    start_date: Optional[str] = Query(None, description="Start date ISO timestamp"),
    end_date: Optional[str] = Query(None, description="End date ISO timestamp"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlatformActivitiesResponse:
    """Retrieve platform activities."""
    service = AdminService(db)
    return service.get_platform_activities(
        search=search,
        role=role,
        action=action,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# 2. NOTIFICATION SETTINGS ENDPOINTS
# =============================================================================

@router.get(
    "/notification-settings",
    response_model=NotificationSettingsSchema,
    status_code=status.HTTP_200_OK,
    summary="Get platform notification configuration settings",
    description="Returns persisted system notification parameters and alert rules from database.",
)
def get_notification_settings(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationSettingsSchema:
    """Retrieve platform notification settings."""
    service = AdminService(db)
    return service.get_notification_settings()


@router.put(
    "/notification-settings",
    response_model=NotificationSettingsSchema,
    status_code=status.HTTP_200_OK,
    summary="Update platform notification configuration settings",
    description="Persist changes to platform-wide notification rules in database with validation.",
)
@router.patch(
    "/notification-settings",
    response_model=NotificationSettingsSchema,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def update_notification_settings(
    payload: NotificationSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NotificationSettingsSchema:
    """Update platform notification settings."""
    service = AdminService(db)
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    return service.update_notification_settings(update_data, current_user)


# =============================================================================
# 3. PLATFORM ANALYTICS ENDPOINTS
# =============================================================================

@router.get(
    "/analytics",
    response_model=PlatformAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Access platform analytics and clinical adherence metrics",
    description="Computes live system-level metrics for users, medications, adherence, caregivers, OCR, and messaging.",
)
def get_platform_analytics(
    period: str = Query("30d", description="Time period filter: today, 7d, 30d, 90d, custom"),
    start_date: Optional[str] = Query(None, description="Custom start date ISO timestamp"),
    end_date: Optional[str] = Query(None, description="Custom end date ISO timestamp"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlatformAnalyticsResponse:
    """Retrieve live platform analytics."""
    service = AdminService(db)
    return service.get_platform_analytics(
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


# =============================================================================
# 4. SYSTEM OPERATIONS & HEALTH ENDPOINTS
# =============================================================================

@router.get(
    "/system/health",
    response_model=SystemHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get real-time system health and subsystem diagnostic status",
    description="Tests live database connection latency, API status, notification queue, chat engine, and security layer.",
)
def get_system_health(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SystemHealthResponse:
    """Retrieve live system health."""
    service = AdminService(db)
    return service.get_system_health()


@router.post(
    "/system/reconcile-doses",
    response_model=SystemOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Safely reconcile overdue scheduled doses",
    description="Admin trigger to transition any past scheduled doses to MISSED status idempotently.",
)
def reconcile_doses(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SystemOperationResponse:
    """Trigger dose reconciliation."""
    service = AdminService(db)
    return service.reconcile_system_doses(current_user)


@router.post(
    "/system/reconcile-notifications",
    response_model=SystemOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Safely refresh patient notification state",
    description="Admin trigger to scan active patients and generate missing reminders/refill alerts.",
)
def reconcile_notifications(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SystemOperationResponse:
    """Trigger notification reconciliation."""
    service = AdminService(db)
    return service.reconcile_system_notifications(current_user)


@router.post(
    "/system/consistency-check",
    response_model=SystemOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run non-destructive system data consistency check",
    description="Admin diagnostic check verifying schedule integrity, overdue doses, and unassigned patient counts.",
)
def run_consistency_check(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SystemOperationResponse:
    """Run data consistency check."""
    service = AdminService(db)
    return service.run_data_consistency_check(current_user)

