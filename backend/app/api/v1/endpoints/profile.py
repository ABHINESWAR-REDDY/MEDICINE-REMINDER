"""User profile management API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserProfileUpdateRequest,
)
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Retrieve the profile data of the currently authenticated user.",
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get authenticated user profile."""
    user_service = UserService(db)
    return user_service.get_profile(current_user)


@router.put(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="Update allowed profile fields (name only). User role, email, and ID remain strictly immutable.",
)
def update_profile(
    data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update profile attributes for authenticated user."""
    user_service = UserService(db)
    updated_user = user_service.update_profile(current_user, data)
    return updated_user
