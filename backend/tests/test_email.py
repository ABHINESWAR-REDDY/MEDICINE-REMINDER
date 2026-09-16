"""Unit tests for email service formatting, fallback modes, and template generation."""

from app.services.email_service import EmailService


def test_email_service_fallback_when_unconfigured():
    """Verify email service falls back safely without raising when SMTP is unconfigured."""
    service = EmailService()
    # Explicitly test with unconfigured credentials
    service.user = None
    service.password = None

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
