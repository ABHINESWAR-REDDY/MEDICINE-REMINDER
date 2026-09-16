"""Pydantic schema definitions for health check and diagnostics."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ServiceComponentStatus(BaseModel):
    """Status for an individual subsystem or service component."""
    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        ..., description="Operational status of the component"
    )
    details: str = Field(..., description="Additional diagnostic context or reason")


class HealthResponse(BaseModel):
    """Consolidated health check response."""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall platform status ('healthy' if all dependencies up, 'degraded' if partial)"
    )
    environment: str = Field(..., description="Current running environment (development, staging, production)")
    version: str = Field(..., description="API application version")
    timestamp: datetime = Field(..., description="UTC timestamp of the health check evaluation")
    services: dict[str, ServiceComponentStatus] = Field(
        ..., description="Detailed status breakdown per subsystem"
    )
