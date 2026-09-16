"""Main entrypoint for the PillSync FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.config import settings
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events handler."""
    logger.info(
        "Starting %s v%s in [%s] mode...",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    
    # Ensure database schema is created
    try:
        from app.core.database import engine, Base
        import app.models  # Ensure all models are registered
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';"))
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Could not auto-create database tables on startup: %s", str(e))

    # Initialize OCR Model Manager singleton at startup
    try:
        from app.services.ocr.model_manager import OCRModelManager
        OCRModelManager.get_instance()
    except Exception as e:
        logger.warning("Could not pre-load OCR models at startup: %s", str(e))

    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


openapi_tags = [
    {
        "name": "Health",
        "description": "System health, database connectivity checks, and operational diagnostics.",
    },
    {
        "name": "Authentication",
        "description": "User registration, email OTP dispatch & verification, login authentication, password reset, and JWT issuance.",
    },
    {
        "name": "Profile",
        "description": "Authenticated user profile retrieval and management.",
    },
    {
        "name": "Patient Doses & Adherence",
        "description": "Patient dose tracking, marking doses as taken/skipped, and adherence calculations.",
    },
    {
        "name": "Patient Notifications & Alerts",
        "description": "Patient reminders, dose alerts, and notification state management.",
    },
    {
        "name": "Patient Portal History & Refills",
        "description": "Patient medication intake history, refill predictions, and inventory tracking.",
    },
    {
        "name": "Caregiver",
        "description": "Caregiver dashboard, assigned patient supervision, adherence reports, refill alerts, and patient alerts.",
    },
    {
        "name": "Admin",
        "description": "System administrator operations: caregiver approvals/rejections, patient-caregiver assignments, audit logs, notification settings, platform activities, and analytics.",
    },
    {
        "name": "Medicines",
        "description": "Medication inventory management, dosage units, forms, and medicine reference database.",
    },
    {
        "name": "Schedules",
        "description": "Medication timing schedules, daily frequencies, and dose time configurations.",
    },
    {
        "name": "Prescriptions",
        "description": "Prescription records, doctor information, issue/expiry dates, and notes.",
    },
    {
        "name": "Conditions",
        "description": "Patient medical conditions and diagnostic categories.",
    },
    {
        "name": "Chat Messaging",
        "description": "Real-time communication between patients and assigned caregivers.",
    },
    {
        "name": "OCR Prescriptions",
        "description": "Machine Learning OCR pipeline: prescription image text detection, TrOCR recognition, entity extraction, and structured medicine digitization.",
    },
]

app = FastAPI(
    title="PillSync Backend API",
    version=settings.VERSION,
    description="""
# PillSync API - Intelligent Medicine Reminder & Medication Tracking Platform

Welcome to the **PillSync Backend API Live Demonstration & Documentation Hub**.

### Platform Capabilities:
- 🔐 **Multi-Role Authentication**: JWT access tokens for **Patient**, **Caregiver**, and **Admin** with strict Role-Based Access Control (RBAC).
- 💊 **Medication & Adherence**: Real-time dose logging (taken/skipped), dynamic adherence calculation, refill predictions, and schedule management.
- 👨‍⚕️ **Caregiver Supervision**: Multi-patient supervision, adherence oversight, refill warnings, and direct patient chat.
- 🛡️ **Administrator Hub**: Caregiver verification, patient assignment management, immutable audit logging, notification controls, and platform analytics.
- 🤖 **AI/ML Prescription OCR**: PyTorch & TrOCR deep learning pipeline for automated handwritten prescription digitization.
- 🗄️ **PostgreSQL ACID Store**: High-integrity relational database storage.

### How to Authenticate in Swagger UI:
1. Scroll to **`POST /api/v1/auth/login`** under **Authentication**.
2. Click **Try it out**, enter your registered email and password, and click **Execute**.
3. Copy the `access_token` from the response.
4. Click the green **Authorize 🔓** button at the top right of this page.
5. Paste your token into the **Value** field and click **Authorize**.
6. All secured endpoints will now automatically execute with your authenticated credentials.
    """,
    openapi_tags=openapi_tags,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "persistAuthorization": True},
    lifespan=lifespan,
)

# CORS Configuration
origins = list(set(settings.ALLOWED_ORIGINS + [settings.FRONTEND_URL]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router)


@app.get("/", tags=["Root"], include_in_schema=False)
def root():
    """Root endpoint for quick API discovery."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "health_url": f"{settings.API_V1_STR}/health",
    }
