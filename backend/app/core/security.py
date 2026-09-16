"""Security utilities: bcrypt password hashing and JWT token handling."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union
import bcrypt
import jwt
from app.core.config import settings

SPECIAL_CHARACTERS_REGEX = r"[!@#$%^&*()_+\-=\[\]{};':\",.<>/?\\|`~]"


def get_password_hash(password: str) -> str:
    """
    Hash a password securely using bcrypt with salt generation.
    Returns the hashed password as a string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Returns True if valid, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def validate_password_rules(password: str, confirmation: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    r"""
    Validate all 5 password security requirements:
    1. Minimum 8 characters
    2. At least one uppercase letter (A-Z)
    3. At least one lowercase letter (a-z)
    4. At least one number (0-9)
    5. At least one special character (!@#$%^&*()_+-=[]{};':",.<>/?\|`~)
    6. Must match confirmation if provided
    """
    if not password or not password.strip():
        return False, "Password cannot be empty or blank."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number (0-9)."
    if not re.search(SPECIAL_CHARACTERS_REGEX, password):
        return False, "Password must contain at least one special character."
    if confirmation is not None and password != confirmation:
        return False, "Password and confirmation do not match."
    return True, None


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a signed JWT access token containing minimal claims:
    - sub: stable user identifier
    - iat: issuance timestamp (UTC)
    - exp: expiration timestamp (UTC)
    """
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(subject),
        "iat": int(now_utc.timestamp()),
        "exp": int(expire.timestamp()),
    }

    # Strict encoding with server-configured algorithm and secret
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Enforces server-side configured JWT_ALGORITHM to prevent algorithm confusion attacks.
    Returns payload dictionary if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]}
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
