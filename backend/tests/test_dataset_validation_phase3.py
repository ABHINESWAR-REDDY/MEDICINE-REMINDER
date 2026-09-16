"""Test suite for Phase 3 Multi-Dataset Validation, Provenance, and Extraction Safeties."""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.ocr.extractor import PrescriptionFieldExtractor
from app.services.ocr.matcher import MedicineMatcher
from ml.prescription_ocr.src.prepare_detector_dataset import (
    compute_image_hash,
    compute_perceptual_hash,
    prepare_detector_dataset,
)


def test_image_hashing_exact_and_perceptual():
    """Verify exact SHA256 and perceptual hashing for duplicate detection."""
    im1 = Image.new("RGB", (100, 100), color="white")
    im2 = Image.new("RGB", (100, 100), color="white")
    im3 = Image.new("RGB", (100, 100), color="black")

    import io
    b1 = io.BytesIO()
    im1.save(b1, format="JPEG")
    bytes1 = b1.getvalue()

    b2 = io.BytesIO()
    im2.save(b2, format="JPEG")
    bytes2 = b2.getvalue()

    # Exact hash equality
    assert compute_image_hash(bytes1) == compute_image_hash(bytes2)
    # Perceptual hash equality
    assert compute_perceptual_hash(im1) == compute_perceptual_hash(im2)
    # Different image perceptual hash inequality
    assert compute_perceptual_hash(im1) != compute_perceptual_hash(im3)


def test_detector_dataset_structure_and_labels():
    """Verify generated detector dataset has valid splits, YAML, class 0 mapping, and 0-1 bounds."""
    dataset_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector")
    yaml_path = os.path.join(dataset_dir, "dataset.yaml")
    
    assert os.path.exists(yaml_path), "dataset.yaml must exist"
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        yaml_text = f.read()
    assert "0: medicine" in yaml_text, "Class mapping must have 0: medicine"

    for split in ["train", "val", "test"]:
        img_dir = os.path.join(dataset_dir, split, "images")
        lbl_dir = os.path.join(dataset_dir, split, "labels")

        assert os.path.exists(img_dir)
        assert os.path.exists(lbl_dir)

        imgs = os.listdir(img_dir)
        lbls = os.listdir(lbl_dir)
        assert len(imgs) == len(lbls), f"Image and label counts must match in {split}"

        for lf in lbls:
            lp = os.path.join(lbl_dir, lf)
            with open(lp, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            for line in lines:
                parts = line.split()
                assert len(parts) == 5, f"YOLO annotation must have 5 tokens: {line}"
                c_id, xc, yc, w, h = parts
                assert c_id == "0", f"Class ID must be mapped to '0', got {c_id}"
                xc, yc, w, h = float(xc), float(yc), float(w), float(h)
                assert 0.0 <= xc <= 1.0, f"xc out of bounds: {xc}"
                assert 0.0 <= yc <= 1.0, f"yc out of bounds: {yc}"
                assert 0.0 < w <= 1.0, f"width invalid: {w}"
                assert 0.0 < h <= 1.0, f"height invalid: {h}"


def test_no_split_leakage():
    """Verify zero overlap/leakage between train, val, and test image stems."""
    dataset_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector")
    train_stems = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(dataset_dir, "train", "images")))
    val_stems = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(dataset_dir, "val", "images")))
    test_stems = set(os.path.splitext(f)[0] for f in os.listdir(os.path.join(dataset_dir, "test", "images")))

    assert len(train_stems.intersection(val_stems)) == 0, "Train-Val stem leakage detected!"
    assert len(train_stems.intersection(test_stems)) == 0, "Train-Test stem leakage detected!"
    assert len(val_stems.intersection(test_stems)) == 0, "Val-Test stem leakage detected!"


def test_field_provenance_and_no_hallucination():
    """Verify that undetected fields strictly evaluate to None/not_detected with 0 confidence."""
    extractor = PrescriptionFieldExtractor(db=None)

    # Empty/vague input
    res = extractor.extract_fields("Patient Name: John Doe Date: 2026-08-19")
    fields = res["fields"]
    evidence = res["evidence"]

    # When medicine or clinical details are not found in OCR text, they MUST remain None
    assert fields["medicine_name"] is None
    assert fields["strength"] is None
    assert fields["dosage_form"] is None
    assert fields["quantity"] is None
    assert fields["frequency"] is None

    # Evidence provenance checks
    assert evidence["medicine_name"]["source"] == "not_detected"
    assert evidence["medicine_name"]["confidence"] == 0.0
    assert evidence["strength"]["source"] == "not_detected"
    assert evidence["quantity"]["source"] == "not_detected"


def test_matcher_does_not_autofill_missing_fields():
    """Verify that reference matching does not force false high-confidence matches on unknown OCR text."""
    matcher = MedicineMatcher(db=None)
    # Inject reference cache
    matcher._reference_cache = [
        {"name": "Paracetamol", "normalized_name": "paracetamol", "categories": ["Analgesic"], "dosage_forms": ["Tablet"], "strengths": ["500 mg"]},
        {"name": "Amoxicillin", "normalized_name": "amoxicillin", "categories": ["Antibiotic"], "dosage_forms": ["Capsule"], "strengths": ["250 mg"]},
    ]

    # Low-confidence or gibberish input
    match_result = matcher.match_medicine_name("unknown gibberish 12345")
    assert match_result["confidence"] < 0.65
    assert match_result["confidence_level"] == "LOW"
    assert match_result["auto_select_eligible"] is False
    assert match_result["requires_user_review"] is True
