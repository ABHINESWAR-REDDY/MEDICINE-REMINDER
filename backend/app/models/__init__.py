"""Database models initialization and exports."""

from app.models.base import Base, TimestampMixin
from app.models.user import User, UserRole, ApprovalStatus
from app.models.email_verification import EmailVerificationCode, VerificationPurpose
from app.models.condition import Condition
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.prescription import Prescription, PrescriptionStatus
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.medicine_reference import MedicineReference
from app.models.ocr_job import OCRJob
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.dose import MedicationDose, DoseStatus
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.notification import Notification
from app.models.system_setting import SystemSetting, DEFAULT_NOTIFICATION_SETTINGS

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "ApprovalStatus",
    "EmailVerificationCode",
    "VerificationPurpose",
    "Condition",
    "Prescription",
    "PrescriptionStatus",
    "Medicine",
    "MedicineForm",
    "DosageUnit",
    "MedicationSchedule",
    "ScheduleFrequency",
    "MedicineReference",
    "OCRJob",
    "CaregiverPatientAssignment",
    "AssignmentStatus",
    "MedicationDose",
    "DoseStatus",
    "AuditLog",
    "ChatMessage",
    "Notification",
    "SystemSetting",
    "DEFAULT_NOTIFICATION_SETTINGS",
]

