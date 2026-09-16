"""Tests for user language preference persistence and AI assistant language routing."""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.core.security import create_access_token
from app.schemas.ai_chat import VerificationMetadata


def test_user_profile_returns_default_language(client, create_user):
    """Test get_profile returns default language ('en')."""
    user = create_user(
        name="Test Patient Lang",
        email="test_patient_lang@example.com",
        role=UserRole.PATIENT
    )
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    assert data["email"] == "test_patient_lang@example.com"


def test_update_profile_language_persistence(client, create_user, db_session: Session):
    """Test updating language preference persists in database and returns updated response."""
    user = create_user(
        name="Test Patient Lang 2",
        email="test_patient_lang2@example.com",
        role=UserRole.PATIENT
    )
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Update to Hindi
    response = client.put("/api/v1/profile", headers=headers, json={"language": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "hi"

    # Verify directly in DB
    db_session.refresh(user)
    assert user.language == "hi"

    # Update to Telugu
    response = client.put("/api/v1/profile", headers=headers, json={"language": "te"})
    assert response.status_code == 200
    assert response.json()["language"] == "te"

    db_session.refresh(user)
    assert user.language == "te"


def test_user_language_isolation(client, create_user):
    """Test changing Patient language does not affect Caregiver language."""
    patient = create_user(name="Patient User", email="pt_iso@example.com", role=UserRole.PATIENT)
    caregiver = create_user(name="Caregiver User", email="cg_iso@example.com", role=UserRole.CAREGIVER)

    patient_token = create_access_token(subject=patient.id)
    caregiver_token = create_access_token(subject=caregiver.id)

    # Change patient to Tamil
    client.put("/api/v1/profile", headers={"Authorization": f"Bearer {patient_token}"}, json={"language": "ta"})

    # Change caregiver to Marathi
    client.put("/api/v1/profile", headers={"Authorization": f"Bearer {caregiver_token}"}, json={"language": "mr"})

    # Check patient profile
    res_patient = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {patient_token}"})
    assert res_patient.json()["language"] == "ta"

    # Check caregiver profile
    res_cg = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {caregiver_token}"})
    assert res_cg.json()["language"] == "mr"


def test_invalid_language_code_rejected(client, create_user):
    """Test invalid language code is rejected by schema validator."""
    user = create_user(name="Invalid Lang User", email="invalid_lang@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put("/api/v1/profile", headers=headers, json={"language": "invalid_lang"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ai_assistant_accepts_language_payload(client, create_user):
    """Test AI assistant chat endpoint processes request with target language."""
    user = create_user(name="AI Lang User", email="ai_lang@example.com", role=UserRole.PATIENT)
    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.ai_service.MedicalWebVerifier.verify_medical_query", new_callable=AsyncMock) as mock_verify, \
         patch("app.services.ai_service.AIService._call_gemini_with_verification", new_callable=AsyncMock) as mock_call_gemini:

        mock_verify.return_value = VerificationMetadata(
            verified=True,
            evidence_status="VERIFIED",
            sources_checked=1,
            sources=[],
            query_type="MEDICATION_CLINICAL"
        )
        mock_call_gemini.return_value = "Metformin 500 mg रक्त शर्करा को नियंत्रित करने के लिए उपयोग किया जाता है।"

        response = client.post(
            "/api/v1/ai/chat",
            headers=headers,
            json={
                "message": "What is Metformin used for?",
                "language": "hi",
                "include_patient_context": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "Metformin 500 mg" in data["message"]
        _, kwargs = mock_call_gemini.call_args
        assert kwargs.get("language") == "hi"
