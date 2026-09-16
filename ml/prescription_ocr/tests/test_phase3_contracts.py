"""Unit tests for Phase 3 ML Architecture Contracts, Adapters, and Safety Guards."""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.adapters.rxhandbd_adapter import RxHandBDAdapter
from ml.prescription_ocr.src.adapters.doctor_prescription_adapter import DoctorPrescriptionAdapter
from ml.prescription_ocr.src.adapters.reference_medicine_adapter import ReferenceMedicineAdapter
from ml.prescription_ocr.src.adapters.full_prescription_adapter import FullPrescriptionAdapter
from ml.prescription_ocr.src.evaluate_official import compute_cer, compute_wer, compute_levenshtein


def test_levenshtein_and_metrics():
    # Identical strings
    assert compute_levenshtein("Metformin", "Metformin") == 0
    assert compute_cer("Metformin", "Metformin") == 0.0
    assert compute_wer("Metformin 500mg", "Metformin 500mg") == 0.0

    # 1 character difference
    assert compute_levenshtein("Metformin", "Metfornin") == 1
    assert abs(compute_cer("Metformin", "Metfornin") - (1 / 9)) < 1e-4

    # Empty string edge cases
    assert compute_cer("", "") == 0.0
    assert compute_cer("Amoxicillin", "") == 1.0


def test_rxhandbd_adapter_splits_and_leakage_protection():
    data_root = os.path.join(PROJECT_ROOT, "DATA")
    adapter = RxHandBDAdapter(data_root=data_root)
    train_samples, val_samples, test_samples = adapter.load_splits(validate_images=True)

    # 1. Split counts
    assert len(train_samples) == 4000, f"Expected 4,000 train samples, got {len(train_samples)}"
    assert len(val_samples) == 463, f"Expected 463 val samples, got {len(val_samples)}"
    assert len(test_samples) == 1115, f"Expected 1,115 test samples, got {len(test_samples)}"

    # 2. Complete disjointness / Zero test leakage
    train_imgs = set(img for img, _ in train_samples)
    val_imgs = set(img for img, _ in val_samples)
    test_imgs = set(img for img, _ in test_samples)

    assert len(train_imgs.intersection(val_imgs)) == 0, "Leakage between Train and Val!"
    assert len(train_imgs.intersection(test_imgs)) == 0, "Leakage between Train and Test!"
    assert len(val_imgs.intersection(test_imgs)) == 0, "Leakage between Val and Test!"

    meta = adapter.get_metadata()
    assert meta.is_training_eligible is True
    assert meta.is_evaluation_eligible is True


def test_doctor_dataset_adapter_restriction():
    data_root = os.path.join(PROJECT_ROOT, "DATA")
    adapter = DoctorPrescriptionAdapter(data_root=data_root)
    meta = adapter.get_metadata()

    # Per Phase 3 rule #3, Doctor dataset is restricted from primary TrOCR training
    assert meta.is_training_eligible is False
    assert meta.label_type == "normalized_medicine_name"


def test_reference_medicine_adapter_restriction():
    data_root = os.path.join(PROJECT_ROOT, "DATA")
    adapter = ReferenceMedicineAdapter(data_root=data_root)
    meta = adapter.get_metadata()

    # Must NEVER be eligible as training labels
    assert meta.is_training_eligible is False
    assert meta.is_evaluation_eligible is False

    vocab = adapter.load_vocabulary()
    assert len(vocab) > 100, f"Expected large reference vocabulary, got {len(vocab)}"


def test_full_prescription_adapter():
    data_root = os.path.join(PROJECT_ROOT, "DATA")
    adapter = FullPrescriptionAdapter(data_root=data_root)
    meta = adapter.get_metadata()

    assert meta.is_training_eligible is False
    assert meta.is_evaluation_eligible is True
    imgs = adapter.list_images()
    assert len(imgs) == 309, f"Expected 309 full prescription images, got {len(imgs)}"
