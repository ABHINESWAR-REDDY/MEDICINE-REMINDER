"""Unit tests for email service Brevo HTTP API delivery, local fallback, timeout handling, and secret masking."""

from unittest.mock import patch, MagicMock
import httpx
import pytest
from fastapi import HTTPException

from app.services.email_service import EmailService
from app.services.otp_service import OtpService


def test_email_service_fallback_when_unconfigured():
    """Verify email service falls back safely in development when unconfigured."""
    service = EmailService()
    service.brevo_api_key = None
    service.user = None
    service.password = None
    service.environment = "development"

    assert service.is_configured() is False

    success = service.send_registration_otp(
        to_email="test.recipient@example.com",
        name="Test Patient",
        otp_code="987654",
        expire_minutes=10
    )
    assert success is True

    reset_success = service.send_password_reset_otp(
        to_email="test.recipient@example.com",
        name="Test Patient",
        otp_code="123456",
        expire_minutes=10
    )
    assert reset_success is True


def test_email_service_production_fails_when_unconfigured():
    """Verify that in production mode, missing BREVO_API_KEY immediately returns False and marks unconfigured."""
    service = EmailService()
    service.brevo_api_key = None
    service.user = "some_user@gmail.com"
    service.password = "secret"
    service.environment = "production"

    assert service.is_configured() is False
    assert service.is_brevo_configured() is False

    success = service.send_email(
        to_email="test@example.com",
        subject="Test Subject",
        html_body="<p>Test</p>",
        text_body="Test"
    )
    assert success is False


def test_brevo_missing_api_key_fails_in_production(caplog):
    """Verify missing BREVO_API_KEY logs safe error without secrets and returns False."""
    service = EmailService()
    service.brevo_api_key = ""
    service.environment = "production"

    assert service.is_brevo_configured() is False
    assert service.is_configured() is False

    success = service.send_email(
        to_email="patient@example.com",
        subject="Verification",
        html_body="<p>123456</p>",
        text_body="123456"
    )
    assert success is False
    assert "BREVO_API_KEY is not configured" in caplog.text
    assert "123456" not in caplog.text


def test_brevo_missing_sender_details_fails_configured_check():
    """Verify is_brevo_configured returns False if sender email is missing."""
    service = EmailService()
    service.brevo_api_key = "xkeysib-some-key"
    service.from_email = ""

    assert service.is_brevo_configured() is False



def test_brevo_api_success():
    """Verify successful transactional email delivery via Brevo HTTPS API."""
    service = EmailService()
    service.brevo_api_key = "xkeysib-mock-valid-key-12345"

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"messageId": "<test-message-id@brevo>"}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        success = service.send_registration_otp(
            to_email="patient@example.com",
            name="Alice Smith",
            otp_code="654321",
            expire_minutes=10
        )
        assert success is True
        assert mock_post.called

        # Inspect call arguments
        url, kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        assert url == service.brevo_api_url
        assert kwargs["headers"]["api-key"] == "xkeysib-mock-valid-key-12345"
        assert kwargs["headers"]["accept"] == "application/json"
        assert kwargs["headers"]["content-type"] == "application/json"

        payload = kwargs["json"]
        assert payload["sender"]["email"] == service.from_email
        assert payload["sender"]["name"] == service.from_name
        assert payload["to"] == [{"email": "patient@example.com", "name": "Alice Smith"}]
        assert "654321" in payload["subject"]
        assert "654321" in payload["htmlContent"]
        assert "654321" in payload["textContent"]


def test_brevo_api_rejection_returns_false_and_does_not_log_secrets(caplog):
    """Verify that when Brevo returns an HTTP error (401/400), it returns False without logging secrets."""
    service = EmailService()
    service.brevo_api_key = "xkeysib-dummy-secret-key-123"

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"code": "unauthorized", "message": "Key not found"}
    mock_resp.text = '{"code":"unauthorized","message":"Key not found"}'

    with patch("httpx.Client.post", return_value=mock_resp):
        success = service.send_email(
            to_email="patient@example.com",
            subject="Verification code",
            html_body="<p>Code is 888999</p>",
            text_body="Code is 888999"
        )
        assert success is False

    # Check logs: API key and OTP must never be leaked
    log_text = caplog.text
    assert "xkeysib-dummy-secret-key-123" not in log_text
    assert "888999" not in log_text


def test_brevo_api_timeout_returns_false(caplog):
    """Verify that Brevo API timeouts are handled gracefully without exceptions or leaking data."""
    service = EmailService()
    service.brevo_api_key = "xkeysib-mock-key"

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        success = service.send_email(
            to_email="patient@example.com",
            subject="Test subject",
            html_body="<p>Timeout test</p>",
            text_body="Timeout test"
        )
        assert success is False

    assert "xkeysib-mock-key" not in caplog.text


def test_otp_service_raises_502_when_brevo_rejects(db_session):
    """Verify that OtpService raises HTTP 502 Bad Gateway if email delivery fails, preventing false success."""
    otp_service = OtpService(db_session)

    # Force email service to return False (simulating Brevo rejection)
    with patch("app.services.email_service.email_service.send_email", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            otp_service.send_registration_otp(email="fail@example.com", name="Fail User")
        assert exc_info.value.status_code == 502
        assert "Failed to send verification email" in exc_info.value.detail

        with pytest.raises(HTTPException) as exc_info_reset:
            otp_service.send_password_reset_otp(email="fail@example.com", name="Fail User")
        assert exc_info_reset.value.status_code == 502
        assert "Failed to send password reset email" in exc_info_reset.value.detail
