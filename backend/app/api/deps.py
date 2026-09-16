"""FastAPI dependency injection utilities for authentication and RBAC."""

from typing import Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

# HTTPBearer scheme for clear Swagger UI token entry & OAuth2 compatibility
http_bearer = HTTPBearer(
    auto_error=False,
    description="Enter your JWT access token (obtained from POST /api/v1/auth/login)"
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    oauth2_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate request via Bearer JWT token.
    Validates token signature, expiration, and queries PostgreSQL for user record.
    """
    token = auth_credentials.credentials if auth_credentials else oauth2_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise credentials_exception

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """
    Factory creating a role-enforcement dependency.
    Raises HTTP 403 Forbidden if current user role is not in allowed roles.
    Robust to both Enum instances and case-insensitive string representations.
    """
    allowed_role_names = {
        (r.value if isinstance(r, UserRole) else str(r)).upper()
        for r in allowed_roles
    }

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role_name = (
            current_user.role.value
            if isinstance(current_user.role, UserRole)
            else str(current_user.role)
        ).upper()

        if user_role_name not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access this resource."
            )
        return current_user

    return role_dependency


# Pre-configured RBAC dependencies
require_patient = require_role(UserRole.PATIENT)
require_caregiver = require_role(UserRole.CAREGIVER)
require_admin = require_role(UserRole.ADMIN)
