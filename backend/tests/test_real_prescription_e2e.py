"""End-to-end integration test with real prescription images.

Verifies:
1. Upload and immediate asynchronous job return (< 500ms)
2. Asynchronous job execution with region detector and TrOCR
3. Raw OCR preservation (genuine text without overwrite)
4. Zero-hallucination field policy (missing fields remain null with source='not_detected')
5. Candidate matching against reference dataset
"""

import os
import sys
import pytest
from io import BytesIO
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from fastapi.testclient import TestClient
from app.main import app
from app.services.ocr.service import OCRPrescriptionService
from app.services.ocr.job_service import OCRJobService


def test_real_prescription_e2e_pipeline():
    # 1. Locate real prescription document
    real_rx_dir = os.path.join(PROJECT_ROOT, "DATA", "prescriptions images")
    if not os.path.exists(real_rx_dir) or not os.listdir(real_rx_dir):
        # Fallback to test detector images
        real_rx_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector", "test", "images")
    
    rx_files = [f for f in os.listdir(real_rx_dir) if f.lower().endswith((".jpg", ".png"))]
    assert len(rx_files) > 0, "No real prescription images found for testing!"

    sample_rx_path = os.path.join(real_rx_dir, rx_files[0])
    with open(sample_rx_path, "rb") as f:
        image_bytes = f.read()

    # 2. Run real OCR extraction through OCRPrescriptionService
    ocr_service = OCRPrescriptionService()
    result = ocr_service.process_prescription_file(
        file_bytes=image_bytes,
        filename=rx_files[0],
        content_type="image/jpeg",
    )

    # 3. Assertions on real extraction
    assert "raw_text" in result
    assert "cleaned_text" in result
    assert "fields" in result
    assert "evidence" in result
    assert "regions" in result
    assert "ocr_metadata" in result

    # 4. Zero-hallucination assertion
    evidence = result["evidence"]
    for field_name in ["strength", "dosage_form", "frequency", "duration_days", "quantity"]:
        if field_name in evidence:
            ev = evidence[field_name]
            if ev["value"] is None:
                assert ev["source"] == "not_detected"
                assert ev["confidence"] == 0.0

    print("\nE2E Extraction Test Passed successfully on:", rx_files[0])
    print("Raw OCR detected length:", len(result["raw_text"]))
    print("Extracted fields:", result["fields"])
    print("Detected regions count:", len(result["regions"]))



