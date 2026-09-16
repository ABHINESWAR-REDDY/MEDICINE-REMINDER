"""Patient-caregiver chat messaging API endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatContact,
    ChatDeleteResponse,
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.get(
    "/contacts",
    response_model=List[ChatContact],
    status_code=status.HTTP_200_OK,
    summary="Get authorized chat contacts",
    description="Returns authorized chat contacts (Caregiver for Patient; Supervised Patients for Caregiver).",
)
def get_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ChatContact]:
    """Retrieve chat contact cards with unread counts."""
    service = ChatService(db)
    return service.get_contacts(current_user)


@router.get(
    "/conversation/{other_user_id}",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get conversation history",
    description="Returns conversation history and marks unread incoming messages as read.",
)
def get_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ChatMessageResponse]:
    """Retrieve full conversation thread."""
    service = ChatService(db)
    return service.get_conversation(current_user, other_user_id)


@router.post(
    "/send",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a chat message",
    description="Sends a direct chat message to an authorized recipient.",
)
def send_message(
    data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatMessageResponse:
    """Send a new direct message."""
    service = ChatService(db)
    return service.send_message(current_user, data)


@router.post(
    "/read/{other_user_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Mark messages as read",
    description="Marks all incoming messages from sender as read.",
)
def mark_read(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Mark incoming messages as read."""
    service = ChatService(db)
    return service.mark_read(current_user, other_user_id)


@router.delete(
    "/messages/{message_id}",
    response_model=ChatDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete chat message",
    description="Soft-deletes an individual chat message. Only the sender can delete their own message.",
)
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatDeleteResponse:
    """Soft-delete a message (sender ownership enforced)."""
    service = ChatService(db)
    return service.delete_message(current_user, message_id)


@router.delete(
    "/conversation/{other_user_id}",
    response_model=ChatDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete conversation",
    description="Clears the conversation for the requesting user only. Preserves the other user's view and all medical records.",
)
def delete_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatDeleteResponse:
    """Clear conversation history for the current user."""
    service = ChatService(db)
    return service.delete_conversation(current_user, other_user_id)

