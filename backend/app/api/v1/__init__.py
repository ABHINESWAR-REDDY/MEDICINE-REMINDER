"""API v1 routing module."""

from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.conditions import router as conditions_router
from app.api.v1.endpoints.prescriptions import router as prescriptions_router
from app.api.v1.endpoints.medicines import router as medicines_router
from app.api.v1.endpoints.schedules import router as schedules_router
from app.api.v1.endpoints.ocr import router as ocr_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.caregivers import router as caregivers_router
from app.api.v1.endpoints.doses import router as doses_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.patient import router as patient_router
from app.api.v1.endpoints.ai_assistant import router as ai_assistant_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_v1_router.include_router(conditions_router, tags=["Conditions"])
api_v1_router.include_router(prescriptions_router, tags=["Prescriptions"])
api_v1_router.include_router(medicines_router, tags=["Medicines"])
api_v1_router.include_router(schedules_router, tags=["Schedules"])
api_v1_router.include_router(ocr_router, tags=["OCR Prescriptions"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_v1_router.include_router(caregivers_router, prefix="/caregiver", tags=["Caregiver"])
api_v1_router.include_router(doses_router, prefix="/patient", tags=["Patient Doses & Adherence"])
api_v1_router.include_router(notifications_router, prefix="/patient", tags=["Patient Notifications & Alerts"])
api_v1_router.include_router(patient_router, prefix="/patient", tags=["Patient Portal History & Refills"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat Messaging"])
api_v1_router.include_router(ai_assistant_router, prefix="/ai", tags=["AI Healthcare Assistant"])




