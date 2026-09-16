"""Health check endpoint implementation."""

from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.core.database import check_database_connection
from app.schemas.health import HealthResponse, ServiceComponentStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Platform Health & Diagnostics Check",
    description=(
        "Returns system operational state, environment, version, timestamp, "
        "and granular connectivity check for the database."
    ),
)
def get_health() -> HealthResponse:
    """Perform health verification across API process and database connectivity."""
    db_connected, db_details = check_database_connection()

    db_status = "healthy" if db_connected else "unhealthy"
    overall_status = "healthy" if db_connected else "degraded"

    services = {
        "api": ServiceComponentStatus(
            status="healthy",
            details="API process operational"
        ),
        "database": ServiceComponentStatus(
            status=db_status,
            details=db_details
        ),
    }

    return HealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
        services=services,
    )
