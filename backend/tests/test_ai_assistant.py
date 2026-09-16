"""Comprehensive tests for PillSync AI Healthcare Assistant and Multi-Source Medical Verification."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, ApprovalStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.condition import Condition
from app.models.schedule import MedicationSchedule
from app.models.medicine_reference import MedicineReference
from app.services.medical_web_verifier import MedicalWebVerifier
from app.services.ai_service import AIService
from app.schemas.ai_chat import AIChatRequest, MedicalSourceCitation, VerificationMetadata
import datetime


@pytest.fixture
def test_patient_user(db_session: Session) -> User:
    """Create a verified patient with active medication records."""
    user = User(
        email="patient_ai_test@example.com",
        password_hash="hashedpassword123",
        name="Alex River",
        role=UserRole.PATIENT,
        is_active=True,
        approval_status=ApprovalStatus.APPROVED,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add active medicine
    med = Medicine(
        user_id=user.id,
        name="Metformin",
        dosage_amount=500.0,
        dosage_unit=DosageUnit.MG,
        quantity=60,
        medicine_form=MedicineForm.TABLET,
        instructions="Take with meals",
        start_date=datetime.date.today(),
        is_active=True
    )
    db_session.add(med)

    # Add health condition
    cond = Condition(
        user_id=user.id,
        name="Type 2 Diabetes",
        description="Moderate fasting blood sugar elevation"
    )
    db_session.add(cond)
    db_session.commit()

    return user


@pytest.fixture
def patient_auth_headers(test_patient_user: User) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(subject=test_patient_user.id)
    return {"Authorization": f"Bearer {token}"}


def test_query_classification():
    """Verify that user queries are correctly classified into emergency, platform, medical, and out-of-scope."""
    verifier = MedicalWebVerifier()

    # Emergency
    assert verifier.classify_query("I took a double dose of blood pressure pill by mistake") == "EMERGENCY"
    assert verifier.classify_query("Patient has severe allergic reaction and difficulty breathing") == "EMERGENCY"

    # Platform navigation
    assert verifier.classify_query("How do I scan my doctor's prescription with OCR?") == "PILLSYNC_PLATFORM"
    assert verifier.classify_query("Where can I see my medication history?") == "PILLSYNC_PLATFORM"

    # Clinical & medication
    assert verifier.classify_query("What is Metformin used for?") == "MEDICATION_CLINICAL"
    assert verifier.classify_query("What are the common side effects of Amoxicillin?") == "MEDICATION_CLINICAL"
    assert verifier.classify_query("What is the standard dosage for Paracetamol 500mg?") == "MEDICATION_CLINICAL"
    assert verifier.classify_query("Which tablet can be used for acute fever?") == "MEDICATION_CLINICAL"

    # Out of scope
    assert verifier.classify_query("Who won the cricket match today?") == "OUT_OF_SCOPE"
    assert verifier.classify_query("Write a javascript script to sort an array") == "OUT_OF_SCOPE"
    assert verifier.classify_query("What is the capital city of France?") == "OUT_OF_SCOPE"


def test_medicine_normalization(db_session: Session):
    """Verify medicine name fuzzy normalization."""
    verifier = MedicalWebVerifier(db_session)

    # Common spelling normalization
    assert "Metformin" in verifier.normalize_medicine_names("What is metformln used for?")
    assert "Paracetamol" in verifier.normalize_medicine_names("Can I take paracetamal for pain?")
    assert "Amoxicillin" in verifier.normalize_medicine_names("What are the side effects of amoxicllin?")


@pytest.mark.asyncio
async def test_medical_web_verifier_fetches_authoritative_sources(db_session: Session):
    """Verify multi-source verification retrieves FDA, MedlinePlus, and NHS citations."""
    verifier = MedicalWebVerifier(db_session)
    result = await verifier.verify_medical_query("What is Metformin used for in type 2 diabetes?")

    assert result.verified is True
    assert result.sources_checked >= 2
    assert result.evidence_status in ["VERIFIED", "PARTIALLY_VERIFIED"]
    
    source_names = [s.name for s in result.sources]
    assert any("FDA" in name for name in source_names)
    assert any("MedlinePlus" in name for name in source_names)
    
    # Check that URLs are official and non-empty
    for src in result.sources:
        assert src.url.startswith("https://")
        assert len(src.relevant_excerpt) > 10


def test_ai_suggestions_endpoint(client: TestClient, patient_auth_headers: dict):
    """Verify /api/v1/ai/suggestions returns categorized prompt library."""
    response = client.get("/api/v1/ai/suggestions", headers=patient_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) >= 3
    
    category_names = [c["category"] for c in data["categories"]]
    assert any("Tablet Uses" in c for c in category_names)
    assert any("Dosages" in c for c in category_names)


def test_ai_chat_out_of_scope(client: TestClient, patient_auth_headers: dict):
    """Verify off-topic queries return polite refusal with predefined medical suggestions."""
    payload = {
      "message": "Who won today's soccer match?",
      "conversation_history": [],
      "include_patient_context": False
    }
    response = client.post("/api/v1/ai/chat", json=payload, headers=patient_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_out_of_scope"] is True
    assert "suggested_prompts" in data
    assert len(data["suggested_prompts"]) > 0
    # Must not contain API keys
    assert "AQ." not in response.text
    assert "GEMINI_API_KEY" not in response.text


def test_ai_chat_emergency_triage(client: TestClient, patient_auth_headers: dict):
    """Verify emergency symptoms trigger immediate crisis instructions and hotline."""
    payload = {
      "message": "I took a double dose and feel severe chest pain and cannot breathe",
      "conversation_history": [],
      "include_patient_context": False
    }
    response = client.post("/api/v1/ai/chat", json=payload, headers=patient_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_emergency"] is True
    assert "911" in data["message"] or "Emergency" in data["message"]
    assert "1-800-222-1222" in data["message"] or "Poison Control" in data["message"]


def test_ai_chat_platform_question_skips_unnecessary_web(client: TestClient, patient_auth_headers: dict):
    """Verify platform questions are answered with internal knowledge."""
    payload = {
      "message": "How do I scan a doctor's prescription with OCR in PillSync?",
      "conversation_history": [],
      "include_patient_context": False
    }
    response = client.post("/api/v1/ai/chat", json=payload, headers=patient_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_medical"] is False
    assert "OCR" in data["message"] or "Scan" in data["message"]


def test_ai_chat_medical_with_gemini_integration(client: TestClient, patient_auth_headers: dict):
    """Verify real medical chat with multi-source verification and Gemini grounding."""
    payload = {
      "message": "What is Metformin used for and what are its standard precautions?",
      "conversation_history": [],
      "include_patient_context": True
    }
    response = client.post("/api/v1/ai/chat", json=payload, headers=patient_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_medical"] is True
    assert data["verification"] is not None
    assert data["verification"]["verified"] is True
    assert data["verification"]["sources_checked"] >= 2
    assert len(data["verification"]["sources"]) >= 2
    assert "disclaimer" in data
    # Ensure patient context is respected and no secrets leak
    assert "AQ." not in response.text


def test_ocr_verification_confidence_gating(client: TestClient, patient_auth_headers: dict):
    """Verify that low-confidence OCR names trigger a warning rather than blind verification."""
    # Low confidence
    low_res = client.post(
        "/api/v1/ai/verify-ocr",
        json={"extracted_text": "m_tf_rm", "confidence": 0.45},
        headers=patient_auth_headers
    )
    assert low_res.status_code == 200
    assert low_res.json()["is_confident"] is False
    assert low_res.json()["warning_message"] is not None

    # High confidence
    high_res = client.post(
        "/api/v1/ai/verify-ocr",
        json={"extracted_text": "Metformin 500mg", "confidence": 0.95},
        headers=patient_auth_headers
    )
    assert high_res.status_code == 200
    assert high_res.json()["is_confident"] is True
