"""Unit and integration tests for application health check and configuration."""

from unittest.mock import patch
from app.core.config import Settings
from app.schemas.health import HealthResponse


def test_app_root_discovery(client):
    """Verify application starts and root endpoint returns service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["health_url"] == "/api/v1/health"


def test_health_check_healthy_state(client):
    """Verify health endpoint when database connectivity succeeds."""
    with patch("app.api.v1.endpoints.health.check_database_connection", return_value=(True, "connected")):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        # Validate with Pydantic schema
        validated = HealthResponse(**data)
        assert validated.status == "healthy"
        assert validated.services["api"].status == "healthy"
        assert validated.services["database"].status == "healthy"
        assert validated.services["database"].details == "connected"
        assert validated.version == "0.1.0"


def test_health_check_degraded_database_failure(client):
    """Verify health endpoint gracefully returns 'degraded' when database is unreachable."""
    with patch("app.api.v1.endpoints.health.check_database_connection", return_value=(False, "unreachable: OperationalError")):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        validated = HealthResponse(**data)
        assert validated.status == "degraded"
        assert validated.services["api"].status == "healthy"
        assert validated.services["database"].status == "unhealthy"
        assert "unreachable" in validated.services["database"].details


def test_health_check_schema_fields(client):
    """Ensure response has all mandatory fields and no extraneous secrets."""
    with patch("app.api.v1.endpoints.health.check_database_connection", return_value=(True, "connected")):
        response = client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert "environment" in data
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data
        # Ensure database password/URL is never leaked
        raw_text = response.text
        assert "password" not in raw_text.lower()
        assert "pillsync_secure_password" not in raw_text


def test_configuration_loading():
    """Verify settings load cleanly with defaults and dynamic database URL generation."""
    custom_settings = Settings(
        POSTGRES_SERVER="db.example.internal",
        POSTGRES_PORT=5433,
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_DB="test_db",
        DATABASE_URL=None,
        JWT_SECRET_KEY="test_jwt_secret_key_12345",
        _env_file=None
    )
    assert custom_settings.POSTGRES_PORT == 5433
    assert custom_settings.sync_database_url == "postgresql://test_user:test_password@db.example.internal:5433/test_db"


