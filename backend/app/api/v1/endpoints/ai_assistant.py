"""AI Healthcare Assistant API endpoints with Multi-Source Medical Verification."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ai_chat import (
    AIChatRequest,
    AIChatResponse,
    SuggestedQuestionsResponse,
    OcrVerificationRequest,
    OcrVerificationResponse,
    VerificationMetadata
)
from app.services.ai_service import AIService
from app.services.medical_web_verifier import MedicalWebVerifier

router = APIRouter()


@router.post(
    "/chat",
    response_model=AIChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with PillSync AI Healthcare Assistant",
    description="Processes questions with multi-source medical verification (FDA, MedlinePlus, NHS) and patient context grounding.",
)
async def chat_with_ai(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AIChatResponse:
    """Send a query to the AI Healthcare Assistant."""
    service = AIService(db)
    return await service.generate_chat_response(current_user, request)


@router.get(
    "/suggestions",
    response_model=SuggestedQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get categorized predefined questions",
    description="Returns pre-defined medical, dosage, interaction, and platform guidance prompts.",
)
def get_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SuggestedQuestionsResponse:
    """Retrieve categorized predefined prompt chips."""
    service = AIService(db)
    return service.get_suggested_questions()


@router.get(
    "/pill-lookup/{medicine_name}",
    response_model=VerificationMetadata,
    status_code=status.HTTP_200_OK,
    summary="Lookup verified drug monograph",
    description="Returns multi-source clinical monograph data for a specific medication name.",
)
async def lookup_pill(
    medicine_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VerificationMetadata:
    """Perform instant multi-source medical verification on a medication name."""
    verifier = MedicalWebVerifier(db)
    return await verifier.verify_medical_query(medicine_name)


@router.post(
    "/verify-ocr",
    response_model=OcrVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OCR extracted medication name",
    description="Normalizes and confidence-checks OCR scanned text before clinical verification.",
)
def verify_ocr(
    request: OcrVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OcrVerificationResponse:
    """Verify confidence of OCR scanned text."""
    service = AIService(db)
    return service.verify_ocr_extracted_medicine(request.extracted_text, request.confidence)
