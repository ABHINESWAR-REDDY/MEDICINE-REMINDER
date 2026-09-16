"""Security unit tests covering password hashing, JWT operations, and configuration safety."""

from datetime import timedelta
import pytest
from pydantic import ValidationError
import jwt

from app.core.config import Settings
from app.core.security import (
    get_password_hash,
    verify_password,
    validate_password_rules,
    create_access_token,
    decode_access_token,
)


def test_missing_jwt_secret_fails_startup():
    """Verify that empty or missing JWT_SECRET_KEY raises a validation error on configuration load."""
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY="", _env_file=None)

    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY="   ", _env_file=None)


def test_bcrypt_hashing_and_verification():
    """Verify bcrypt password hashing produces unique salted hashes and verifies accurately."""
    password = "MySecurePassword123!"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Hashes must differ due to unique salts
    assert hash1 != hash2
    assert hash1.startswith("$2b$") or hash1.startswith("$2a$")

    # Verification must succeed for exact password
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True

    # Verification must fail for incorrect password
    assert verify_password("WrongPassword123!", hash1) is False
    assert verify_password("", hash1) is False
    assert verify_password(password, "invalid_hash_string") is False


def test_password_rules_validation():
    """Verify all 5 password requirements: length, uppercase, lowercase, number, special char, confirmation."""
    # Valid strong password
    valid, err = validate_password_rules("Abhi@1234", "Abhi@1234")
    assert valid is True
    assert err is None

    # Empty
    valid, err = validate_password_rules("", "")
    assert valid is False
    assert "empty" in err

    # Length < 8
    valid, err = validate_password_rules("Ab1@xyz", "Ab1@xyz")
    assert valid is False
    assert "8 characters" in err

    # Missing uppercase
    valid, err = validate_password_rules("abhi@1234", "abhi@1234")
    assert valid is False
    assert "uppercase" in err

    # Missing lowercase
    valid, err = validate_password_rules("ABHI@1234", "ABHI@1234")
    assert valid is False
    assert "lowercase" in err

    # Missing number
    valid, err = validate_password_rules("Abhi@word", "Abhi@word")
    assert valid is False
    assert "number" in err

    # Missing special character
    valid, err = validate_password_rules("Abhi12345", "Abhi12345")
    assert valid is False
    assert "special character" in err

    # Confirmation mismatch
    valid, err = validate_password_rules("Abhi@1234", "Different@1234")
    assert valid is False
    assert "match" in err


def test_jwt_creation_and_decoding():
    """Verify JWT contains minimal claims and decodes cleanly with server-side algorithm."""
    user_id = 42
    token = create_access_token(subject=user_id)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_jwt_expired_token_rejected():
    """Verify expired JWT tokens return None during decoding."""
    expired_token = create_access_token(
        subject=100,
        expires_delta=timedelta(seconds=-10)
    )
    payload = decode_access_token(expired_token)
    assert payload is None


def test_jwt_algorithm_confusion_prevention():
    """Verify tokens signed with invalid/unsupported algorithms are strictly rejected."""
    # Attempt to sign with different algorithm and untrusted key
    untrusted_token = jwt.encode(
        {"sub": "99", "iat": 1000, "exp": 9999999999},
        key="a" * 64,
        algorithm="HS384"
    )
    payload = decode_access_token(untrusted_token)
    assert payload is None
