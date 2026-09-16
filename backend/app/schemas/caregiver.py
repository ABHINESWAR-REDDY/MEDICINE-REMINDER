"""Pydantic schemas for Caregiver supervision, dashboard, adherence reports, and refill notifications."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.schemas.patient_portal import RefillPredictionItem


class AssignedPatientSummary(BaseModel):
    """Summary of patient assigned to a caregiver."""
    id: int
    employee_id: Optional[str] = None
    name: str
    email: str
    medications_count: int
    today_doses_total: int
    today_doses_taken: int
    today_doses_missed: int
    adherence_percentage: float
    adherence_status: str

    model_config = ConfigDict(from_attributes=True)


class CaregiverDashboardResponse(BaseModel):
    """Caregiver dashboard metrics across assigned patients."""
    total_assigned_patients: int
    today_doses_scheduled: int
    today_doses_taken: int
    today_doses_missed: int
    today_doses_pending: int
    overall_adherence_percentage: float
    overall_adherence_status: str
    patients: List[AssignedPatientSummary]

    model_config = ConfigDict(from_attributes=True)


class CaregiverAlert(BaseModel):
    """Real-time clinical alert, refill warning, or live message notification for caregiver."""
    id: str
    patient_id: int
    patient_employee_id: Optional[str] = None
    patient_name: str
    severity: str  # INFO, WARNING, CRITICAL
    type: Optional[str] = "CLINICAL"  # CLINICAL, ADHERENCE_RISK, MISSED_DOSE, CHAT_MESSAGE, REFILL_NEEDED
    title: str
    message: str
    timestamp: str
    medicine_name: Optional[str] = None
    strength: Optional[float] = None
    unit: Optional[str] = None
    dosage_form: Optional[str] = None
    estimated_remaining_days: Optional[int] = None
    estimated_remaining_quantity: Optional[float] = None
    urgency_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class CaregiverAdherencePatientItem(BaseModel):
    """Adherence report line item for an assigned patient over a specific period."""
    patient_id: int
    employee_id: Optional[str] = None
    name: str
    email: str
    account_created_at: Optional[datetime] = None
    adherence_percentage: float
    adherence_status: str
    total_expected_doses: int
    taken_count: int
    missed_count: int
    skipped_count: int
    active_medications_count: int

    model_config = ConfigDict(from_attributes=True)


class CaregiverAdherenceReportsResponse(BaseModel):
    """Response containing adherence reports across all assigned patients."""
    caregiver_id: int
    period_days: int
    total_assigned_patients: int
    overall_adherence_percentage: float
    overall_adherence_status: str
    high_risk_count: int
    needs_attention_count: int
    good_standing_count: int
    reports: List[CaregiverAdherencePatientItem]

    model_config = ConfigDict(from_attributes=True)


class MedicationAdherenceBreakdown(BaseModel):
    """Medication-specific adherence breakdown for a patient."""
    medicine_id: int
    medicine_name: str
    strength: Optional[float] = None
    unit: Optional[str] = None
    dosage_form: Optional[str] = None
    total_expected: int
    taken_count: int
    missed_count: int
    skipped_count: int
    adherence_percentage: float
    current_stock: Optional[int] = None
    estimated_remaining_days: Optional[int] = None
    refill_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatientAdherenceReportDetail(BaseModel):
    """Detailed adherence report and medication analysis for a single assigned patient."""
    patient: Dict[str, Any]
    period_days: int
    adherence_summary: Dict[str, Any]
    medication_breakdown: List[MedicationAdherenceBreakdown]
    recent_dose_events: List[Dict[str, Any]]
    refill_predictions: List[RefillPredictionItem]

    model_config = ConfigDict(from_attributes=True)


class CaregiverRefillNotification(BaseModel):
    """Caregiver refill alert item for an assigned patient's medication."""
    id: str
    patient_id: int
    patient_employee_id: Optional[str] = None
    patient_name: str
    medicine_id: int
    medicine_name: str
    strength: Optional[float] = None
    unit: Optional[str] = None
    current_stock: Optional[int] = None
    estimated_remaining_quantity: Optional[float] = None
    estimated_remaining_days: Optional[int] = None
    predicted_refill_date: Optional[date] = None
    urgency_level: str  # CRITICAL, LOW_STOCK
    severity: str  # CRITICAL, WARNING
    title: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class CaregiverRefillNotificationsResponse(BaseModel):
    """Response containing active refill notifications for caregiver's assigned patients."""
    caregiver_id: int
    total_notifications: int
    critical_count: int
    low_stock_count: int
    notifications: List[CaregiverRefillNotification]

    model_config = ConfigDict(from_attributes=True)
