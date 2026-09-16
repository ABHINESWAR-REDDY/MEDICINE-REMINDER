"""Unit tests for OTP generation, hashing, verification, rate limiting, and expiration."""

from datetime import datetime, timedelta, timezone
from app.models.email_verification import VerificationPurpose
from app.services.otp_service import OtpService


def test_otp_generation_format():
    """Verify generated OTP is a 6-digit numeric string."""
    for _ in range(20):
        otp = OtpService.generate_otp(6)
        assert len(otp) == 6
        assert otp.isdigit()


def test_otp_hashing_and_verification():
    """Verify SHA-256 OTP hashing and constant-time verification."""
    code = "123456"
    code_hash = OtpService.hash_otp(code)
    assert isinstance(code_hash, str)
    assert len(code_hash) == 64

    assert OtpService.verify_hash("123456", code_hash) is True
    assert OtpService.verify_hash("654321", code_hash) is False
    assert OtpService.verify_hash("", code_hash) is False


def test_send_and_validate_registration_otp_success(db_session):
    """Verify sending and successfully validating registration OTP."""
    otp_service = OtpService(db_session)
    email = "user.otp@example.com"
    name = "OTP User"

    code = otp_service.send_registration_otp(email=email, name=name)
    assert len(code) == 6

    # Validate correct code
    is_valid, err = otp_service.validate_code(
        email=email,
        purpose=VerificationPurpose.REGISTRATION.value,
        plain_code=code
    )
    assert is_valid is True
    assert err is None

    # Replay attack: Code must not be usable a second time
    is_valid2, err2 = otp_service.validate_code(
        email=email,
        purpose=VerificationPurpose.REGISTRATION.value,
        plain_code=code
    )
    assert is_valid2 is False
    assert "No active verification code found" in err2


def test_otp_invalid_code_decrements_attempts(db_session):
    """Verify invalid code entry increments failed attempts up to limit."""
    otp_service = OtpService(db_session)
    email = "attempts.test@example.com"

    code = otp_service.send_registration_otp(email=email, name="Attempts User")

    # Enter wrong code 1st time
    is_valid, err = otp_service.validate_code(
        email=email,
        purpose=VerificationPurpose.REGISTRATION.value,
        plain_code="000000"
    )
    assert is_valid is False
    assert "Invalid verification code" in err

    # Enter wrong code until exhausted (5 attempts total)
    for _ in range(4):
        otp_service.validate_code(
            email=email,
            purpose=VerificationPurpose.REGISTRATION.value,
            plain_code="000000"
        )

    # Now even correct code should be rejected due to attempt exhaustion
    is_valid_final, err_final = otp_service.validate_code(
        email=email,
        purpose=VerificationPurpose.REGISTRATION.value,
        plain_code=code
    )
    assert is_valid_final is False
    assert "No active verification code found" in err_final or "Too many failed attempts" in err_final


def test_otp_expired_code_rejected(db_session):
    """Verify expired OTP code is rejected."""
    otp_service = OtpService(db_session)
    email = "expired.otp@example.com"

    code = "555555"
    code_hash = OtpService.hash_otp(code)
    # Create record that expired 5 minutes ago
    past_expiry = datetime.now(timezone.utc) - timedelta(minutes=5)
    otp_service.repo.create(
        email=email,
        code_hash=code_hash,
        purpose=VerificationPurpose.REGISTRATION.value,
        expires_at=past_expiry
    )

    is_valid, err = otp_service.validate_code(
        email=email,
        purpose=VerificationPurpose.REGISTRATION.value,
        plain_code="555555"
    )
    assert is_valid is False
    assert "expired" in err.lower()
