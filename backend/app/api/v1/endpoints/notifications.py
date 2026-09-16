"""Patient Notification & Medication Alert API endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_patient
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    UnreadNotificationCountResponse,
    NotificationActionResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get(
    "/notifications",
    response_model=List[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get patient notifications",
    description="Returns real-time medication reminders, missed doses, and notifications for the authenticated patient.",
)
def get_patient_notifications(
    filter_type: Optional[str] = Query(None, description="Optional filter (MEDICATION_REMINDER, MISSED_DOSE, UNREAD)"),
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
) -> List[NotificationResponse]:
    """Retrieve notifications belonging to the authenticated patient."""
    service = NotificationService(db)
    return service.get_patient_notifications(
        patient_user=current_user,
        filter_type=filter_type,
        unread_only=unread_only
    )


@router.get(
    "/notifications/unread-count",
    response_model=UnreadNotificationCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Returns count of active unread notifications for badge display.",
)
def get_unread_count(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
) -> UnreadNotificationCountResponse:
    """Get active unread count for patient."""
    service = NotificationService(db)
    count = service.get_unread_count(current_user)
    return {"unread_count": count}


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark single notification as read",
    description="Marks a specific patient notification as read.",
)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
) -> NotificationActionResponse:
    """Mark notification as read."""
    service = NotificationService(db)
    return service.mark_as_read(current_user, notification_id)


@router.post(
    "/notifications/read-all",
    response_model=NotificationActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Marks all unread notifications for the patient as read.",
)
def mark_all_notifications_read(
    current_user: User = Depends(require_patient),
    db: Session = Depends(get_db)
) -> NotificationActionResponse:
    """Mark all patient notifications as read."""
    service = NotificationService(db)
    return service.mark_all_as_read(current_user)
