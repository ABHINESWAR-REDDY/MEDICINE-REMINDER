"""Pydantic schemas for Phase 3 OCR extraction, matching, and confirmation."""

from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import BaseModel, Field

from app.models.medicine import MedicineForm, DosageUnit
from app.models.schedule import ScheduleFrequency


class CandidateMatchSchema(BaseModel):
    dataset_name: str
    confidence: float
    match_type: str


class ReferenceDataSchema(BaseModel):
    name: str
    category: Optional[str] = None
    dosage_form: Optional[str] = None
    strength: Optional[str] = None
    categories: Optional[List[str]] = None
    dosage_forms: Optional[List[str]] = None
    strengths: Optional[List[str]] = None


class MedicineMatchResultSchema(BaseModel):
    matched_name: Optional[str] = None
    confidence: float = 0.0
    confidence_level: str = "LOW"  # HIGH, MEDIUM, LOW
    match_type: str = "NONE"
    reference_data: Optional[Dict[str, Any]] = None
    candidates: List[CandidateMatchSchema] = []


class OCRFieldValue(BaseModel):
    value: Optional[Any] = None
    source: str = "not_detected"  # 'ocr', 'ocr_regex', 'ocr_keyword', 'reference_match', 'not_detected'
    confidence: float = 0.0


class OCRMedicationSchema(BaseModel):
    medicine_name: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())
    strength: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())
    unit: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())
    dosage_form: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())
    instructions: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())
    start_date: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())
    end_date: OCRFieldValue = Field(default_factory=lambda: OCRFieldValue())


class OCRExtractedFieldsSchema(BaseModel):
    doctor_name: Optional[str] = None
    prescription_number: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    start_date: Optional[str] = None
    medicine_name: Optional[str] = None
    detected_raw_medicine_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_amount: Optional[float] = None
    dosage_unit: Optional[str] = None
    dosage_form: Optional[str] = None
    frequency: Optional[str] = None
    frequency_raw: Optional[str] = None
    dose_quantity: Optional[float] = None
    scheduled_times: Optional[List[str]] = None
    instructions: Optional[str] = None
    duration_days: Optional[int] = None
    quantity: Optional[int] = None


class OCRExtractionResponse(BaseModel):
    medication: Optional[OCRMedicationSchema] = None
    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    fields: OCRExtractedFieldsSchema
    evidence: Optional[Dict[str, Any]] = None
    ocr_metadata: Optional[Dict[str, Any]] = None
    match: Optional[MedicineMatchResultSchema] = None
    medicine_candidates: Optional[List[Dict[str, Any]]] = None
    regions: Optional[List[Dict[str, Any]]] = None
    detector_status: Optional[str] = "fallback"  # 'full_detection', 'partial_detection', 'fallback'
    detector_coverage_warning: bool = False
    fallback_used: bool = False
    confidence_score: float = 0.0
    confidence_level: str = "LOW"
    message: Optional[str] = None



class OCRConfirmationRequest(BaseModel):
    """Payload sent by patient after reviewing/correcting OCR draft."""

    # Prescription fields (optional)
    create_prescription: bool = False
    prescription_number: Optional[str] = None
    doctor_name: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None

    # Medicine fields (required)
    name: str = Field(..., min_length=1, max_length=255)
    dosage_amount: float = Field(..., gt=0)
    dosage_unit: DosageUnit = DosageUnit.MG
    medicine_form: MedicineForm = MedicineForm.TABLET
    quantity: int = Field(default=30, gt=0)
    instructions: Optional[str] = None
    condition_id: Optional[int] = None
    start_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None

    # Schedule fields (optional)
    create_schedule: bool = True
    frequency_type: ScheduleFrequency = ScheduleFrequency.ONCE_DAILY
    dose_quantity: float = Field(default=1.0, gt=0)
    scheduled_times: List[str] = Field(default_factory=lambda: ["08:00"])


class OCRConfirmationResponse(BaseModel):
    success: bool = True
    prescription_id: Optional[int] = None
    medicine_id: int
    schedule_id: Optional[int] = None
    message: str


class OCRJobCreatedResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: Optional[str] = "Prescription upload received and queued for processing."


class OCRJobErrorSchema(BaseModel):
    code: str
    message: str


class OCRJobStatusResponse(BaseModel):
    job_id: str
    status: str  # 'queued', 'processing', 'completed', 'failed'
    stage: Optional[str] = None
    progress_message: Optional[str] = None
    result: Optional[OCRExtractionResponse] = None
    error: Optional[OCRJobErrorSchema] = None
    created_at: Optional[Any] = None
    completed_at: Optional[Any] = None

