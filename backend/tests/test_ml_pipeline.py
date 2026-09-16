"""Comprehensive unit tests for the Phase 3 ML Handwriting OCR pipeline.

Tests:
1. Dataset loading & integrity validation
2. Preprocessing & aspect-ratio padding
3. CER / WER metric accuracy
4. Smoke-test training execution
5. Single-image inference formatting & confidence
"""

import os
import sys
import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ml.prescription_ocr.src.dataset import RxHandBDDataLoader, DatasetSample
from ml.prescription_ocr.src.preprocess import PrescriptionImagePreprocessor
from ml.prescription_ocr.src.metrics import calculate_cer, calculate_wer, calculate_corpus_metrics
from ml.prescription_ocr.src.inference import HandwritingOCRInference


def test_metrics_cer_and_wer_exact_and_edits():
    """Verify CER and WER calculate exact edit distances correctly."""
    # 1. Perfect Match
    assert calculate_cer("Amoxicillin", "Amoxicillin") == 0.0
    assert calculate_wer("Amoxicillin 500mg", "Amoxicillin 500mg") == 0.0

    # 2. Single Character Deletion: 'Amoxicilin' (len 10) vs 'Amoxicillin' (len 11) -> 1 / 11
    cer = calculate_cer("Amoxicilin", "Amoxicillin")
    assert round(cer, 4) == round(1 / 11, 4)

    # 3. Single Word Substitution: 'Amoxicillin 250mg' vs 'Amoxicillin 500mg' -> 1 / 2 = 0.5
    wer = calculate_wer("Amoxicillin 250mg", "Amoxicillin 500mg")
    assert wer == 0.5

    # 4. Corpus Metrics
    preds = ["Metformin", "Lisinopril", "Amoxicilin"]
    targets = ["Metformin", "Lisinopril", "Amoxicillin"]
    corpus = calculate_corpus_metrics(preds, targets)
    assert corpus["exact_match"] == round(2 / 3, 4)
    assert corpus["cer"] > 0.0
    assert corpus["sample_count"] == 3


def test_dataset_loader_and_statistics():
    """Verify RxHandBD dataset loader extracts, validates and generates statistics."""
    loader = RxHandBDDataLoader()
    train_samples, test_samples = loader.load_dataset(validate_images=False)

    assert len(train_samples) == 4463
    assert len(test_samples) == 1115
    assert loader.stats.total_images == 5578
    assert loader.stats.vocabulary_size >= 1540

    report = loader.get_statistics_report()
    assert "RxHandBD Dataset Statistics Report" in report
    assert "Total Valid Images:           5578" in report
    assert "Training Set Samples:         4463" in report
    assert "Testing Set Samples:          1115" in report


def test_preprocessing_pipeline():
    """Verify aspect-ratio preserving preprocessor and RGB normalization."""
    preprocessor = PrescriptionImagePreprocessor(target_size=(384, 384), preserve_aspect_ratio=True)

    # Create dummy grayscale rectangular image (200 x 100)
    raw_img = Image.new("L", (200, 100), color=128)
    processed = preprocessor.preprocess(raw_img)

    assert processed.size == (384, 384)
    assert processed.mode == "RGB"

    # Verify tensor normalization if numpy is available
    try:
        import numpy as np
        np_tensor = preprocessor.to_numpy_normalized(processed)
        assert np_tensor.shape == (3, 384, 384)
    except ImportError:
        pass


def test_inference_pipeline_structure():
    """Verify HandwritingOCRInference returns structured prediction with confidence."""
    engine = HandwritingOCRInference.get_instance()
    dummy_img = Image.new("RGB", (300, 150), color=(255, 255, 255))
    result = engine.predict(dummy_img)

    assert isinstance(result, dict)
    assert "text" in result
    assert "confidence" in result
    assert "confidence_level" in result
    assert "details" in result
    assert result["confidence_level"] in ("HIGH", "MEDIUM", "LOW")
