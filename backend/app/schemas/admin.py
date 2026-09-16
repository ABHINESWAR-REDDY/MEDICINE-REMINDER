"""Pydantic schemas for Admin dashboard, caregiver management, and assignments."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class AdminDashboardResponse(BaseModel):
    """System-wide administration metrics."""
    total_patients: int
    total_caregivers: int
    pending_caregivers: int
    active_caregivers: int
    inactive_caregivers: int
    active_assignments: int
    total_medicines: int
    total_prescriptions: int
    today_doses_total: int
    today_doses_taken: int
    today_doses_missed: int

    model_config = ConfigDict(from_attributes=True)


class CaregiverListItem(BaseModel):
    """Caregiver account listing item for admin review."""
    id: int
    employee_id: Optional[str] = None
    name: str
    email: str
    role: str
    approval_status: str
    is_active: bool
    assigned_patients_count: int
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatientListItem(BaseModel):
    """Patient account listing item for admin directory."""
    id: int
    employee_id: Optional[str] = None
    name: str
    email: str
    role: str
    is_active: bool
    approval_status: str
    created_at: Optional[str] = None
    assigned_caregiver_id: Optional[int] = None
    assigned_caregiver_name: Optional[str] = None
    assigned_caregiver_employee_id: Optional[str] = None
    medications_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AssignPatientRequest(BaseModel):
    """Request payload for assigning a patient to a caregiver."""
    caregiver_id: int
    patient_id: int


class AssignmentResponseItem(BaseModel):
    """Item representing an active caregiver-patient assignment."""
    id: int
    caregiver_id: int
    caregiver_employee_id: Optional[str] = None
    caregiver_name: str
    caregiver_email: str
    patient_id: int
    patient_employee_id: Optional[str] = None
    patient_name: str
    patient_email: str
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponseItem(BaseModel):
    """Audit log entry representation."""
    id: int
    actor_id: Optional[int] = None
    actor_name: str
    actor_email: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Platform Activities Schemas ---

class PlatformActivityItem(BaseModel):
    """Real platform activity record for administrator monitoring."""
    id: int
    actor_id: Optional[int] = None
    actor_name: str
    actor_email: Optional[str] = None
    actor_role: str
    action: str
    target_type: str
    target_id: Optional[int] = None
    description: str
    details: Optional[Dict[str, Any]] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PlatformActivitiesResponse(BaseModel):
    """Paginated platform activities list."""
    items: List[PlatformActivityItem]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)


# --- Notification Settings Schemas ---

class NotificationSettingsSchema(BaseModel):
    """Platform-wide persistent notification settings."""
    patient_medication_reminders_enabled: bool = True
    patient_missed_dose_alerts_enabled: bool = True
    patient_refill_alerts_enabled: bool = True
    patient_polling_interval_seconds: int = 30

    caregiver_missed_dose_alerts_enabled: bool = True
    caregiver_refill_alerts_enabled: bool = True
    caregiver_adherence_risk_alerts_enabled: bool = True
    caregiver_patient_chat_alerts_enabled: bool = True

    system_security_alerts_enabled: bool = True
    system_operational_alerts_enabled: bool = True

    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingsUpdate(BaseModel):
    """Payload for updating platform notification settings."""
    patient_medication_reminders_enabled: Optional[bool] = None
    patient_missed_dose_alerts_enabled: Optional[bool] = None
    patient_refill_alerts_enabled: Optional[bool] = None
    patient_polling_interval_seconds: Optional[int] = None

    caregiver_missed_dose_alerts_enabled: Optional[bool] = None
    caregiver_refill_alerts_enabled: Optional[bool] = None
    caregiver_adherence_risk_alerts_enabled: Optional[bool] = None
    caregiver_patient_chat_alerts_enabled: Optional[bool] = None

    system_security_alerts_enabled: Optional[bool] = None
    system_operational_alerts_enabled: Optional[bool] = None


# --- Platform Analytics Schemas ---

class UserAnalytics(BaseModel):
    total_patients: int = 0
    total_caregivers: int = 0
    active_patients: int = 0
    active_caregivers: int = 0
    pending_caregivers: int = 0
    rejected_caregivers: int = 0
    new_patients_in_period: int = 0
    new_caregivers_in_period: int = 0


class MedicationAnalytics(BaseModel):
    total_active_medications: int = 0
    total_tracked_medications: int = 0
    scheduled_doses_in_period: int = 0
    taken_doses: int = 0
    missed_doses: int = 0
    skipped_doses: int = 0


class AdherenceAnalytics(BaseModel):
    overall_adherence_percentage: float = 0.0
    good_adherence_patients: int = 0
    needs_attention_patients: int = 0
    high_risk_patients: int = 0


class CaregiverAnalytics(BaseModel):
    active_assignments: int = 0
    caregivers_with_assignments: int = 0
    unassigned_patients: int = 0


class PrescriptionAnalytics(BaseModel):
    total_prescriptions: int = 0
    total_ocr_jobs: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0


class NotificationAnalytics(BaseModel):
    total_notifications: int = 0
    unread_notifications: int = 0
    patient_notifications: int = 0
    caregiver_alerts: int = 0
    missed_dose_notifications: int = 0
    refill_notifications: int = 0
    chat_notifications: int = 0


class ChatAnalytics(BaseModel):
    total_messages: int = 0
    patient_messages: int = 0
    caregiver_messages: int = 0
    unread_messages: int = 0


class PlatformAnalyticsResponse(BaseModel):
    """Complete platform-wide live analytics metrics calculated from database."""
    period: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    users: UserAnalytics
    medications: MedicationAnalytics
    adherence: AdherenceAnalytics
    caregivers: CaregiverAnalytics
    prescriptions: PrescriptionAnalytics
    notifications: NotificationAnalytics
    chat: ChatAnalytics

    model_config = ConfigDict(from_attributes=True)


# --- System Operations & Health Schemas ---

class SystemHealthComponent(BaseModel):
    name: str
    status: str  # HEALTHY, DEGRADED, ERROR
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SystemHealthResponse(BaseModel):
    status: str  # HEALTHY, DEGRADED, ERROR
    timestamp: str
    components: Dict[str, SystemHealthComponent]

    model_config = ConfigDict(from_attributes=True)


class SystemOperationResponse(BaseModel):
    success: bool
    operation: str
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
