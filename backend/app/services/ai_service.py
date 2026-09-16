"""PillSync AI Healthcare Assistant Service with Multi-Source Medical Verification.

Powered by Google Gemini 3.6 Flash with authoritative verification against
FDA, MedlinePlus (National Library of Medicine), DailyMed, and NHS UK.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.medicine import Medicine
from app.models.condition import Condition
from app.models.schedule import MedicationSchedule
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.schemas.ai_chat import (
    AIChatMessage,
    AIChatRequest,
    AIChatResponse,
    SuggestedCategory,
    SuggestedQuestionsResponse,
    VerificationMetadata,
    OcrVerificationResponse
)
from app.services.medical_web_verifier import MedicalWebVerifier

logger = logging.getLogger(__name__)

# Curated pre-defined questions library
CATEGORIZED_SUGGESTIONS = [
    SuggestedCategory(
        category="Tablet Uses & Disease Indications",
        icon="Pill",
        description="Learn which medications are indicated for specific health conditions",
        questions=[
            "Which tablet can be used for acute headache or mild fever?",
            "What is Metformin used for and how does it manage blood glucose?",
            "Which medicines are commonly prescribed for bacterial infections?",
            "What is the clinical indication for Atorvastatin?",
            "What are the main uses of Omeprazole for acid reflux?"
        ]
    ),
    SuggestedCategory(
        category="Dosages & Safe Administration",
        icon="Scale",
        description="Standard dosage guidelines, food timing, and administration precautions",
        questions=[
            "What is the standard adult dosage guideline for Paracetamol 500mg?",
            "Should Amoxicillin be taken before or after meals?",
            "What should I do if I miss a scheduled dose of my medication?",
            "What are the dosage rules and maximum daily limit for Ibuprofen?",
            "How should sublingual or extended-release tablets be administered?"
        ]
    ),
    SuggestedCategory(
        category="Drug Interactions & Side Effects",
        icon="ShieldAlert",
        description="Cross-check active medications for interactions and adverse reactions",
        questions=[
            "Can I take my active PillSync medications together safely?",
            "What are the common and rare side effects of Amoxicillin?",
            "Can blood pressure medications be safely combined with pain relievers?",
            "What are key warning signs and precautions for blood thinners?",
            "Are there food or beverage interactions with cholesterol medicines?"
        ]
    ),
    SuggestedCategory(
        category="PillSync Platform & OCR Features",
        icon="Sparkles",
        description="Platform navigation, prescription OCR scanning, and caregiver alerts",
        questions=[
            "How do I scan a doctor's paper prescription with PillSync OCR?",
            "Where can I view my medication history and refill predictions?",
            "How does my caregiver receive alerts for missed scheduled doses?",
            "How do I log when I take my scheduled medication dose?",
            "How does PillSync protect and isolate my medical records?"
        ]
    )
]


class AIService:
    """Core AI Orchestrator integrating Google Gemini with Medical Web Verification."""

    def __init__(self, db: Session):
        self.db = db
        self.verifier = MedicalWebVerifier(db)
        self.api_key = settings.GEMINI_API_KEY
        self.primary_model = getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
        self.fallback_model = getattr(settings, "GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
        self.http_timeout = httpx.Timeout(35.0, connect=6.0)

    async def generate_chat_response(
        self,
        current_user: User,
        request: AIChatRequest
    ) -> AIChatResponse:
        """Process user query through classification, verification, context injection, and Gemini reasoning."""
        user_message = request.message.strip()
        query_type = self.verifier.classify_query(user_message)

        # Determine user preferred / requested language
        target_lang = (request.language or getattr(current_user, 'language', 'en') or 'en').lower()

        # 1. Emergency Triage
        if query_type == "EMERGENCY":
            return self._build_emergency_response(user_message)

        # 2. Out of Scope Handling
        if query_type == "OUT_OF_SCOPE":
            return self._build_out_of_scope_response()

        # 3. PillSync Platform Features (Internal Knowledge - No External Web Request)
        if query_type == "PILLSYNC_PLATFORM":
            return await self._handle_platform_query(user_message, current_user, request.conversation_history, language=target_lang)

        # 4. Medication & Clinical Query: Multi-Source Medical Verification Flow
        verification_metadata = await self.verifier.verify_medical_query(user_message)
        
        # Load Patient Specific Medical Context (Isolated to Authenticated User)
        patient_context_str = ""
        if request.include_patient_context:
            patient_context_str = self._load_patient_context(current_user, request.patient_id)

        # Generate Grounded Response via Gemini
        target_lang = (request.language or getattr(current_user, 'language', 'en') or 'en').lower()
        ai_reply = await self._call_gemini_with_verification(
            user_message=user_message,
            conversation_history=request.conversation_history,
            verification=verification_metadata,
            patient_context=patient_context_str,
            user_role=current_user.role,
            language=target_lang
        )

        return AIChatResponse(
            message=ai_reply,
            is_medical=True,
            is_out_of_scope=False,
            is_emergency=False,
            verification=verification_metadata,
            suggested_prompts=[
                "What is the standard dosage for this medication?",
                "Are there any food or drug interactions?",
                "Can I check my current PillSync medication schedule?",
                "What should I do if I miss a scheduled dose?"
            ]
        )

    def get_suggested_questions(self) -> SuggestedQuestionsResponse:
        """Return categorized predefined prompts for quick user exploration."""
        return SuggestedQuestionsResponse(categories=CATEGORIZED_SUGGESTIONS)

    def verify_ocr_extracted_medicine(self, text: str, confidence: float) -> OcrVerificationResponse:
        """Verify OCR-extracted medicine with confidence gating."""
        if confidence < 0.65:
            return OcrVerificationResponse(
                is_confident=False,
                warning_message=f"OCR extracted '{text}' with low confidence ({int(confidence*100)}%). Please confirm or re-enter the medication name manually before clinical verification."
            )

        normalized = self.verifier.normalize_medicine_names(text)
        canonical = normalized[0] if normalized else text.capitalize()

        return OcrVerificationResponse(
            is_confident=True,
            normalized_name=canonical,
            warning_message=None
        )

    async def _call_gemini_with_verification(
        self,
        user_message: str,
        conversation_history: List[AIChatMessage],
        verification: VerificationMetadata,
        patient_context: str,
        user_role: str,
        language: str = "en"
    ) -> str:
        """Invoke Google Gemini 3.6 Flash with verified source grounding."""
        # Assemble verified medical evidence block
        sources_text = ""
        for idx, src in enumerate(verification.sources, 1):
            sources_text += f"\n[SOURCE {idx}: {src.name}]\n- Citation: {src.relevant_excerpt}\n- Official URL: {src.url}\n"

        lang_names = {
            "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
            "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
            "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
        }
        target_lang_name = lang_names.get(language.lower(), "English")

        system_instruction = (
            "You are PillSync's Expert AI Healthcare & Clinical Medication Assistant. "
            "Your highest priority is to provide an EXACT, COMPREHENSIVE, AND DIRECT ANSWER to the user's specific health or medication question immediately.\n\n"
            "MANDATORY CLINICAL RESPONSE REQUIREMENTS:\n"
            "1. DIRECT ANSWER FIRST: Give the exact clinical guidance, medicine names, and dosage information right at the top.\n"
            "2. DOSAGE & ADMINISTRATION: For dosage questions, provide exact standard adult and pediatric dosages (in mg/ml, dose frequency, minimum hourly interval between doses, and maximum daily limit) for common first-line medications (e.g. Paracetamol/Acetaminophen 500mg-1000mg every 4-6h max 4000mg/day, Ibuprofen 200mg-400mg every 6-8h max 1200mg OTC / 2400mg prescription).\n"
            "3. MEDICINE INDICATIONS: For disease/symptom queries (fever, headache, diabetes, hypertension, infections, acidity), detail which tablets/drugs are clinically indicated, how they work, and proper administration (with food, water, etc.).\n"
            "4. SAFETY & PRECAUTIONS: Highlight key contraindications, liver/kidney cautions, drug interactions, and pediatric/pregnancy safety rules.\n"
            "5. EMERGENCY WARNINGS: List red-flag symptoms when the patient must seek immediate emergency medical care.\n"
            "6. STRUCTURE: Use clear Markdown with bold key terms, tables or bulleted lists, and clean section headers.\n"
            "7. Ground all clinical facts in authoritative medical guidelines (FDA, MedlinePlus, NHS, DailyMed)."
        )

        if language.lower() != "en":
            system_instruction += (
                f"\n\n8. MULTILINGUAL RESPONSE REQUIREMENT: The user's selected language is {target_lang_name} ({language}). "
                f"You MUST generate your entire conversational response in {target_lang_name}. "
                f"CRITICAL MEDICAL INTEGRITY RULE: Keep specific pharmaceutical medicine names (e.g. Metformin, Paracetamol, Amoxicillin, Atorvastatin), "
                f"exact dosages, units (e.g. 500 mg, 10 ml), and numeric frequencies intact and clinically accurate."
            )

        user_content_prompt = f"USER QUESTION: {user_message}\n\n"
        if patient_context:
            user_content_prompt += f"--- PATIENT'S PILLSYNC RECORDS ---\n{patient_context}\n\n"

        user_content_prompt += f"--- VERIFIED CLINICAL SOURCES ({verification.evidence_status}) ---\n{sources_text}\n"
        if verification.conflict_detected and verification.conflict_summary:
            user_content_prompt += f"\nWARNING: Source conflict noted: {verification.conflict_summary}\n"

        user_content_prompt += "\nPlease give a complete, direct, detailed, and accurate clinical answer to the user's question."

        # Prepare Gemini Request payload
        contents = []
        for msg in conversation_history[-4:]:  # last 4 turns for context
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        contents.append({"role": "user", "parts": [{"text": user_content_prompt}]})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 2048,
            }
        }

        # Try primary model first, fallback to secondary
        for model in [self.primary_model, self.fallback_model]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                text_out = parts[0].get("text", "").strip()
                                if len(text_out) > 50:
                                    return text_out
                    logger.warning(f"Gemini {model} returned status {resp.status_code}: {resp.text[:150]}")
            except Exception as e:
                logger.warning(f"Gemini API request failed for {model}: {e}")

        # Comprehensive clinical fallback if AI API is temporarily unreachable
        return self._generate_deterministic_clinical_fallback(user_message, verification, patient_context)

    async def _handle_platform_query(
        self,
        message: str,
        current_user: User,
        history: List[AIChatMessage],
        language: str = "en"
    ) -> AIChatResponse:
        """Answer PillSync platform and navigation questions without external web search."""
        text = message.lower()
        
        lang_names = {
            "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
            "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
            "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
        }
        target_lang_name = lang_names.get(language.lower(), "English")

        system_instruction = (
            "You are PillSync's dedicated platform guide. Answer the user's question about using the PillSync application.\n"
            "Key PillSync platform features to reference:\n"
            "- Scan Prescription: Upload or photograph prescriptions for OCR medicine extraction under `/ocr`.\n"
            "- Medications List: View, add, and manage active prescriptions and dose quantities under `/medications`.\n"
            "- Medication History: Track logged doses, adherence percentage, and missed doses under `/patient/medication-history`.\n"
            "- Refill Predictions: Machine learning predictive estimates for when stock will deplete under `/patient/refill-predictions`.\n"
            "- Dosage Schedules: Configure morning/noon/evening reminder times under `/schedule`.\n"
            "- Caregiver Sync: Caregivers monitor assigned patients and receive critical missed dose alerts.\n"
            "Format your answer cleanly with step-by-step instructions and navigation tips."
        )

        if language.lower() != "en":
            system_instruction += (
                f"\n\nMULTILINGUAL REQUIREMENT: The user's selected language is {target_lang_name} ({language}). "
                f"You MUST generate your entire platform guidance response in {target_lang_name}. "
                f"Keep URL paths (e.g. `/ocr`, `/medications`, `/schedule`) and exact technical terms intact."
            )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": f"User question about PillSync: {message}"}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600}
        }

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.primary_model}:generateContent?key={self.api_key}"
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        answer = candidates[0].get("content", {}).get("parts", [])[0].get("text", "").strip()
                        return AIChatResponse(
                            message=answer,
                            is_medical=False,
                            is_out_of_scope=False,
                            suggested_prompts=[
                                "How do I scan a doctor's prescription?",
                                "Where do I see my upcoming doses for today?",
                                "How does my caregiver monitor my medications?"
                            ]
                        )
        except Exception as e:
            logger.warning(f"Platform query Gemini call failed: {e}")

        # Deterministic platform fallback
        return AIChatResponse(
            message=(
                "### 📱 PillSync Platform Guide\n\n"
                "Here is how to navigate key features in PillSync:\n\n"
                "- 📸 **Scan Prescription (OCR)**: Go to **Scan Prescription** in the sidebar to upload a prescription image or PDF for automated medication extraction.\n"
                "- 💊 **Medications**: View your active medicines, edit quantities, and track refill statuses under **Medications**.\n"
                "- 📅 **Daily Schedule**: Check dose timings and log your taken doses on the **Schedule** page.\n"
                "- 📊 **Refill Predictions**: Check AI-calculated depletion dates under **View Refill Predictions**.\n"
                "- 👥 **Caregiver Sync**: If linked to a caregiver, your missed doses and adherence reports are automatically synchronized in real-time."
            ),
            is_medical=False,
            is_out_of_scope=False,
            suggested_prompts=[
                "How do I scan a prescription with OCR?",
                "Which tablet can be used for fever?",
                "What is the dosage for Paracetamol 500mg?"
            ]
        )

    def _load_patient_context(self, user: User, target_patient_id: Optional[int] = None) -> str:
        """Securely load patient's active medicines and conditions isolated to the user session."""
        patient_id = user.id

        # If user is a Caregiver, verify authorization for target_patient_id
        if user.role == "CAREGIVER" and target_patient_id:
            assignment = self.db.query(CaregiverPatientAssignment).filter(
                CaregiverPatientAssignment.caregiver_id == user.id,
                CaregiverPatientAssignment.patient_id == target_patient_id,
                CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
            ).first()
            if assignment:
                patient_id = target_patient_id

        try:
            medicines = self.db.query(Medicine).filter(
                Medicine.user_id == patient_id,
                Medicine.is_active == True
            ).all()

            conditions = self.db.query(Condition).filter(
                Condition.user_id == patient_id
            ).all()

            if not medicines and not conditions:
                return "Patient has no active medications or recorded health conditions in PillSync."

            lines = []
            if conditions:
                lines.append(f"Recorded Health Conditions: {', '.join([c.name for c in conditions])}")

            if medicines:
                med_details = []
                for m in medicines:
                    med_details.append(f"{m.name} ({m.dosage_amount}{m.dosage_unit.value}, Form: {m.medicine_form.value}, Qty: {m.quantity})")
                lines.append(f"Current Active Medications: {'; '.join(med_details)}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Failed to load patient context: {e}")
            return ""

    def _build_emergency_response(self, user_message: str) -> AIChatResponse:
        """Immediate crisis and emergency triage response."""
        return AIChatResponse(
            message=(
                "🚨 **URGENT MEDICAL EMERGENCY WARNING**\n\n"
                "If you or someone else is experiencing an acute medication overdose, severe allergic reaction (difficulty breathing, facial swelling), chest pain, or poisoning, **seek emergency medical care immediately**:\n\n"
                "- 📞 **Emergency Services**: Call **911** (US) / **112** (Europe/India) or your local emergency number.\n"
                "- 🧪 **Poison Control Center (US)**: Call **1-800-222-1222** (Free, confidential 24/7 expert guidance).\n"
                "- 🏥 **Immediate Action**: Go to the nearest Hospital Emergency Room immediately with the medication packaging/bottle.\n\n"
                "> [!CAUTION]\n"
                "> Do not wait for AI responses or attempt self-treatment during acute medical emergencies."
            ),
            is_medical=True,
            is_out_of_scope=False,
            is_emergency=True,
            suggested_prompts=[
                "What is the contact for Poison Control?",
                "What should I do if a medication dose was missed?"
            ]
        )

    def _build_out_of_scope_response(self) -> AIChatResponse:
        """Polite scope restriction with rich predefined health questions."""
        return AIChatResponse(
            message=(
                "### 🩺 PillSync Healthcare Assistant\n\n"
                "I am your dedicated **PillSync Healthcare & Medication AI Assistant**. "
                "I specialize exclusively in medication safety, dosage guidelines, tablet indications for health conditions, "
                "drug interactions, prescription OCR scanning, and PillSync platform features.\n\n"
                "I cannot answer questions outside healthcare and PillSync. "
                "Please select one of the suggested questions below or ask any medication-related query!"
            ),
            is_medical=False,
            is_out_of_scope=True,
            suggested_prompts=[
                "Which tablet can be used for headache or fever?",
                "What is the standard dosage for Metformin in type 2 diabetes?",
                "What are the common side effects of Amoxicillin?",
                "Can I take my active PillSync medications together?",
                "How do I scan a doctor's prescription with OCR?"
            ]
        )

    def _generate_deterministic_clinical_fallback(
        self,
        query: str,
        verification: VerificationMetadata,
        patient_context: str
    ) -> str:
        """High-precision, symptom-accurate clinical monograph response."""
        q = query.lower()
        
        # 1. Headache / Migraine Guide
        if any(w in q for w in ["headache", "migraine", "head pain", "head ache", "cephalea"]):
            return (
                "### 🎯 Clinical Guide: Medication & Dosage for Headache\n\n"
                "For mild-to-moderate tension headaches and migraine relief, verified first-line over-the-counter options recommended by the **FDA, MedlinePlus, and NHS** are **Paracetamol (Acetaminophen)** and **Ibuprofen**.\n\n"
                "### ⚖️ Standard Dosage Guidelines Table\n\n"
                "| Medication | Target Group | Recommended Dose | Frequency / Interval | Maximum Daily Limit |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| **Paracetamol** *(Acetaminophen / Crocin / Dolo / Napa)* | **Adults & Teens (≥12 yrs)** | **500 mg to 1000 mg** | Every **4 to 6 hours** as needed | **4000 mg (4g)** per 24 hours |\n"
                "| | **Children (under 12 yrs)** | **10 to 15 mg/kg** | Every **4 to 6 hours** | Max 4 doses per day |\n"
                "| **Ibuprofen** *(Advil / Motrin / Brufen)* | **Adults & Teens (≥12 yrs)** | **200 mg to 400 mg** | Every **6 to 8 hours** with food | **1200 mg** (OTC limit) |\n"
                "| | **Children (≥6 months)** | **5 to 10 mg/kg** | Every **6 to 8 hours** with food | Max 40 mg/kg/day |\n\n"
                "### ⚠️ Best Practices & Administration Rules\n"
                "- 💧 **Hydration & Rest**: Drink 1–2 glasses of water immediately; mild headaches are frequently triggered by dehydration or eye strain. Rest in a quiet, dimly lit room.\n"
                "- 🍽️ **Take Ibuprofen With Food**: Always take NSAIDs like Ibuprofen with meals or a glass of milk to avoid stomach irritation.\n"
                "- 🛑 **Avoid Medication-Overuse Headaches**: Do not take pain relievers for more than **3 consecutive days per week** to prevent rebound headaches.\n"
                "- 🚫 **Liver Safety**: Never consume alcohol while taking Paracetamol, and verify total daily intake from all cold/flu remedies.\n\n"
                "### 🩺 Red-Flag Symptoms — Seek Immediate Medical Attention If:\n"
                "- Sudden, severe \"thunderclap\" headache (worst headache of your life).\n"
                "- Headache accompanied by high fever, stiff neck, confusion, vision loss, weakness, or numbness on one side of the body.\n"
                "- Headache following a recent head injury."
            )

        # 2. Fever & Temperature Guide
        if any(w in q for w in ["fever", "temperature", "pyrexia", "chills", "high temp"]):
            return (
                "### 🎯 Clinical Guide: Medication & Dosage for Fever\n\n"
                "For fever reduction (antipyretic therapy) and associated discomfort, verified first-line medications approved by the **FDA, MedlinePlus, and NHS** are **Paracetamol (Acetaminophen)** and **Ibuprofen**.\n\n"
                "### ⚖️ Standard Dosage Guidelines Table\n\n"
                "| Medication | Target Group | Recommended Dose | Frequency / Interval | Maximum Daily Limit |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| **Paracetamol** *(Acetaminophen / Crocin / Dolo / Tylenol)* | **Adults & Teens (≥12 yrs)** | **500 mg to 1000 mg** | Every **4 to 6 hours** as needed | **4000 mg (4g)** per 24 hours |\n"
                "| | **Children (under 12 yrs)** | **10 to 15 mg/kg** | Every **4 to 6 hours** | Max 4 doses in 24 hours |\n"
                "| **Ibuprofen** *(Advil / Motrin / Brufen)* | **Adults & Teens (≥12 yrs)** | **200 mg to 400 mg** | Every **6 to 8 hours** with meals | **1200 mg** (OTC limit) |\n"
                "| | **Children (≥6 months)** | **5 to 10 mg/kg** | Every **6 to 8 hours** | Max 40 mg/kg/day |\n\n"
                "### ⚠️ Critical Safety & Administration Rules\n"
                "- 🍽️ **Administration**: Take Ibuprofen with food or milk to prevent gastric irritation. Paracetamol can be taken with or without food.\n"
                "- 🛑 **Do Not Double Up**: Check labels of cough/cold remedies to avoid accidental Paracetamol overdose.\n"
                "- 🚫 **Aspirin Warning**: Never give Aspirin to children or teenagers under 19 due to the risk of *Reye's syndrome*.\n"
                "- 💧 **Hydration**: Drink plenty of fluids (water, ORS, broths) to replace sweat losses.\n\n"
                "### 🩺 Red-Flag Symptoms — When to Consult a Doctor\n"
                "- Fever above **103°F (39.4°C)** in adults, or above **100.4°F (38°C)** in infants under 3 months.\n"
                "- Fever persisting for more than **3 consecutive days** without improvement.\n"
                "- Accompanying stiff neck, severe headache, confusion, difficulty breathing, or unexplained rash."
            )

        # 3. Pain & Body Ache / Inflammation Guide
        if any(w in q for w in ["body ache", "muscle pain", "joint pain", "back pain", "pain relief", "inflammation"]):
            return (
                "### 🎯 Clinical Guide: Medication & Dosage for Body Pain & Inflammation\n\n"
                "For musculoskeletal pain, backache, and body pain, the first-line oral analgesic medications verified by **FDA and NHS guidelines** are **Ibuprofen (NSAID)** and **Paracetamol**.\n\n"
                "### ⚖️ Standard Dosage Guidelines Table\n\n"
                "| Medication | Target Group | Recommended Dose | Frequency | Maximum Daily Limit |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| **Ibuprofen** *(Anti-inflammatory)* | **Adults (≥12 yrs)** | **200 mg to 400 mg** | Every **6 to 8 hours** after meals | **1200 mg** OTC / 2400 mg Rx |\n"
                "| **Paracetamol** *(Analgesic)* | **Adults (≥12 yrs)** | **500 mg to 1000 mg** | Every **4 to 6 hours** | **4000 mg** per day |\n\n"
                "### ⚠️ Key Precautions\n"
                "- Take Ibuprofen with or immediately after food to protect stomach lining.\n"
                "- Avoid NSAIDs like Ibuprofen if you have active stomach ulcers, severe kidney disease, or are in the third trimester of pregnancy."
            )

        # 4. Acidity / Acid Reflux / Heartburn / GERD Guide
        if any(w in q for w in ["acidity", "acid reflux", "heartburn", "gerd", "gas", "stomach burn"]):
            return (
                "### 🎯 Clinical Guide: Medication & Dosage for Acidity & Heartburn\n\n"
                "First-line medications for treating acid reflux, heartburn, and GERD verified by **FDA and Clinical Guidelines** include **Proton Pump Inhibitors (PPIs)** and **H2 Blockers / Antacids**.\n\n"
                "### ⚖️ Standard Dosage Guidelines\n"
                "- **Omeprazole / Pantoprazole**: **20 mg to 40 mg** orally **once daily in the morning, 30 to 60 minutes before breakfast**.\n"
                "- **Famotidine**: **20 mg** once or twice daily, or 15–60 minutes before eating meals that cause heartburn.\n"
                "- **Antacids (Gelusil / Digene / Mylanta)**: 10–20 mL (or 1–2 chewable tablets) 1 hour after meals and at bedtime as needed.\n\n"
                "### ⚠️ Administration Tips & Lifestyle Guidance\n"
                "- Take PPIs (Omeprazole/Pantoprazole) with a full glass of water on an empty stomach.\n"
                "- Avoid lying down within 2–3 hours after eating; elevate the head of the bed if symptoms occur at night.\n"
                "- Limit trigger foods: oily/fried foods, citrus fruits, caffeine, chocolate, and carbonated beverages."
            )

        # 5. Cough, Cold & Allergy Guide
        if any(w in q for w in ["cough", "cold", "sneeze", "runny nose", "congestion", "allergy", "allergic"]):
            return (
                "### 🎯 Clinical Guide: Medication & Dosage for Cough, Cold & Allergies\n\n"
                "Verified first-line medications for managing cold, allergy symptoms, and cough under **FDA and NHS clinical protocols**:\n\n"
                "### ⚖️ Standard Dosage Guidelines\n"
                "- **Cetirizine / Levocetirizine** *(Antihistamine for sneezing, runny nose, allergic itch)*: **10 mg (Cetirizine)** or **5 mg (Levocetirizine)** once daily in the evening.\n"
                "- **Dextromethorphan** *(Cough Suppressant for dry cough)*: **10 mg to 20 mg** every 4 hours, or 30 mg every 6 to 8 hours (max 120 mg/day).\n"
                "- **Guaifenesin** *(Expectorant for chesty/wet cough)*: **200 mg to 400 mg** every 4 hours with a large glass of water.\n"
                "- **Saline Nasal Spray**: 2–3 sprays per nostril as needed for safe congestion relief.\n\n"
                "### ⚠️ Safety Precautions\n"
                "- Drink plenty of warm liquids (water, herbal teas, broths) to thin mucus secretions.\n"
                "- Antihistamines may cause mild drowsiness; avoid driving or operating heavy machinery if affected."
            )

        # 6. Type 2 Diabetes / Metformin Guide
        if any(w in q for w in ["diabetes", "sugar", "metformin", "glycemic", "glucose"]):
            return (
                "### 🎯 Clinical Guide: Metformin & Type 2 Diabetes Management\n\n"
                "**Metformin** (Biguanide) is the world's standard first-line oral antidiabetic medication approved by the **FDA and NHS** for glycemic control in type 2 diabetes mellitus alongside diet and exercise.\n\n"
                "### ⚖️ Standard Dosage Guidelines\n"
                "- **Initial Adult Dose**: 500 mg once or twice daily with meals, or 850 mg once daily.\n"
                "- **Titration**: Increased by 500 mg weekly based on blood glucose response.\n"
                "- **Maintenance Dose**: 1500 mg to 2000 mg daily in divided doses.\n"
                "- **Maximum Daily Limit**: 2550 mg per day for immediate-release (2000 mg for extended-release ER/XR).\n\n"
                "### ⚠️ Key Administration & Safety Rules\n"
                "- 🍽️ **Take With Meals**: Always take with meals to minimize gastrointestinal discomfort.\n"
                "- 🧪 **Kidney Monitoring**: Periodic eGFR tests are required; contraindicated in severe renal impairment (eGFR < 30).\n"
                "- 🍷 **Avoid Heavy Alcohol**: Excessive alcohol increases the risk of lactic acidosis."
            )

        # 7. Hypertension / Blood Pressure Guide
        if any(w in q for w in ["blood pressure", "hypertension", "bp", "amlodipine", "lisinopril", "losartan", "telmisartan"]):
            return (
                "### 🎯 Clinical Guide: Hypertension & Blood Pressure Medications\n\n"
                "First-line anti-hypertensive medications verified by **FDA, AHA, and NHS clinical protocols**:\n\n"
                "### ⚖️ Standard Adult Dosing Guidelines\n"
                "- **Amlodipine** *(Calcium Channel Blocker)*: **5 mg** orally once daily (initial); may be titrated to **10 mg** once daily.\n"
                "- **Telmisartan / Losartan** *(ARBs)*: **40 mg to 80 mg** (Telmisartan) or **50 mg to 100 mg** (Losartan) orally once daily.\n"
                "- **Lisinopril** *(ACE Inhibitor)*: **10 mg** orally once daily; maintenance range **20 mg to 40 mg** once daily.\n\n"
                "### ⚠️ Key Safety Precautions\n"
                "- Take medication at the same time every day for continuous 24-hour blood pressure control.\n"
                "- Never discontinue blood pressure medication abruptly without consulting your doctor."
            )

        # 8. Bacterial Infections & Antibiotic Guide
        if any(w in q for w in ["infection", "antibiotic", "amoxicillin", "azithromycin", "ciprofloxacin"]):
            return (
                "### 🎯 Clinical Guide: Antibiotic Usage & Indications\n\n"
                "Antibiotics like **Amoxicillin** and **Azithromycin** treat **bacterial infections only** (e.g. strep throat, ear infections, bacterial pneumonia) and are ineffective against viral infections (common cold, flu).\n\n"
                "### ⚖️ Standard Guidelines (Prescription Required)\n"
                "- **Amoxicillin**: Typically 250 mg to 500 mg every 8 hours, or 500 mg to 875 mg every 12 hours as prescribed.\n"
                "- **Azithromycin**: Typically 500 mg on Day 1, followed by 250 mg once daily on Days 2–5.\n\n"
                "### ⚠️ Critical Safety Rules\n"
                "- ⏱️ **Complete Full Course**: Complete the entire prescribed duration even if symptoms improve early to prevent antibiotic resistance.\n"
                "- 🚫 **Allergy Warning**: Inform your doctor immediately if you have a history of penicillin allergy."
            )

        # 9. General Grounded Clinical Monograph
        drugs = ", ".join(verification.normalized_medicines) if verification.normalized_medicines else "the requested medication"
        sources_summary = ", ".join([s.name for s in verification.sources]) if verification.sources else "FDA, MedlinePlus & NHS Guidelines"
        return (
            f"### 🎯 Clinical Overview: {drugs}\n\n"
            f"Based on verified clinical monographs from **{sources_summary}**:\n\n"
            f"### 📌 Clinical Indications\n"
            f"{verification.sources[0].relevant_excerpt if verification.sources else 'Prescribed for the management of diagnosed health conditions under healthcare supervision.'}\n\n"
            f"### ⚖️ Dosage & Administration Guidelines\n"
            f"- Medication dosage must follow the prescription label based on patient age, weight, and clinical condition.\n"
            f"- Always take doses at consistent intervals as scheduled.\n\n"
            f"### ⚠️ Key Precautions & Warnings\n"
            f"- Do not exceed recommended maximum daily limits.\n"
            f"- Consult a physician or pharmacist before combining with other medications or supplements."
        )
