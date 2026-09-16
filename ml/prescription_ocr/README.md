# PillSync Prescription Handwriting OCR (HTR) Machine Learning Pipeline

## Overview
This package implements a dedicated **Handwritten Text Recognition (HTR)** machine learning pipeline designed to improve PillSync's capability to recognize handwritten medicine names, strengths, and dosages from prescription images.

---

## 1. Dataset Separation Architecture

| Dataset Source | Primary Purpose | Format & Scope |
| :--- | :--- | :--- |
| **RxHandBD Version 3** | **Handwriting OCR / HTR Training** | 5,578 word-level handwritten images (512x512 JPG), 1,559 unique vocabulary entries, 4,463 train / 1,115 test split. (CC BY 4.0) |
| **Curated Bangladesh Prescriptions V2** | **Full Document Evaluation** | Full prescription document images with annotated bounding boxes for document-level integration tests. |
| **medicine_dataset_enhanced.csv** | **Medicine Reference / Validation** | Reference dataset for fuzzy normalization, active status verification, and safety confirmation. |

> [!IMPORTANT]
> These three data sources serve distinct roles and must not be mixed. RxHandBD is used solely for training and evaluating word-level HTR, while the medicine reference database normalizes OCR predictions before user review.

---

## 2. Directory Structure

```
ml/prescription_ocr/
├── data/
│   ├── raw/                 # RxHandBD dataset archives & unpacked images
│   ├── processed/           # Normalized / augmented images (transient)
│   └── splits/              # Custom cross-validation splits
├── notebooks/
│   └── 01_rxhandbd_exploration.ipynb
├── src/
│   ├── __init__.py
│   ├── dataset.py           # Dataset loader, integrity validator & statistics
│   ├── preprocess.py        # Aspect-ratio preserving preprocessor
│   ├── metrics.py           # CER, WER, and Exact Match calculations
│   ├── train.py             # TrOCR fine-tuning script with --smoke-test
│   ├── evaluate.py          # CER/WER benchmark & error analysis exporter
│   └── inference.py         # Single image inference & calibrated confidence
├── models/                  # Saved checkpoints & processor (gitignored)
├── outputs/                 # evaluation_results.json & error_analysis.json
├── requirements.txt         # ML training dependencies (isolated from backend)
└── README.md
```

---

## 3. Model Architecture
- **Base Architecture**: Transformer-based OCR (`TrOCR` - Vision Transformer Encoder + RoBERTa/DeBERTa Decoder).
- **Target Task**: Image $\rightarrow$ Transcribed Text sequence (Sequence-to-Sequence), preserving raw text characters rather than discrete classification IDs.
- **Pretrained Baseline**: `microsoft/trocr-small-handwritten` or `microsoft/trocr-base-handwritten`.

---

## 4. Environment & Installation

The ML training environment is kept separate from the lightweight production backend:

```bash
# Create dedicated ML environment (optional)
python -m venv .venv_ml
source .venv_ml/bin/activate  # Or on Windows: .venv_ml\Scripts\activate

# Install training dependencies
pip install -r ml/prescription_ocr/requirements.txt
```

---

## 5. Dataset Loading & Validation

The dataset loader automatically extracts and verifies the RxHandBD archive:

```python
from ml.prescription_ocr.src.dataset import RxHandBDDataLoader

loader = RxHandBDDataLoader()
train_samples, test_samples = loader.load_dataset(validate_images=True)
print(loader.get_statistics_report())
```

**Dataset Statistics:**
- **Total Valid Images**: 5,578
- **Training Samples**: 4,463
- **Testing Samples**: 1,115
- **Unique Vocabulary Entries**: 1,559

---

## 6. Training & Smoke-Testing

### Smoke Test (Low-Resource / CPU verification):
To verify the entire data loading, tokenization, model configuration, and forward-backward pipeline in seconds without high compute resources:
```bash
python ml/prescription_ocr/src/train.py --smoke-test
```

### Full Fine-Tuning:
```bash
python ml/prescription_ocr/src/train.py \
    --model-name microsoft/trocr-small-handwritten \
    --epochs 5 \
    --batch-size 8 \
    --grad-accum 2 \
    --lr 5e-5
```

The script automatically detects available hardware (`CUDA GPU`, `Apple MPS`, or `CPU`) and configures mixed precision (`fp16`) accordingly.

---

## 7. Evaluation & Metrics

The pipeline calculates:
- **Character Error Rate (CER)**: $\frac{\text{Levenshtein Distance}(P, T)}{\text{Length}(T)}$
- **Word Error Rate (WER)**: $\frac{\text{Word Edits}(P, T)}{\text{Word Count}(T)}$
- **Exact Match Accuracy**: Fraction of predictions identically matching ground truth.

Run evaluation on the held-out test split:
```bash
python ml/prescription_ocr/src/evaluate.py --smoke-test
```
Evaluation metrics are saved to `outputs/evaluation_results.json` and error breakdowns (correct vs. incorrect vs. low-confidence) are exported to `outputs/error_analysis.json`.

---

## 8. Single-Image Inference

To run inference on an image:
```bash
python ml/prescription_ocr/src/inference.py path/to/handwritten_word.jpg
```

Output:
```json
{
  "text": "Amoxicillin",
  "confidence": 0.92,
  "confidence_level": "HIGH",
  "raw_text": "Amoxicillin",
  "details": {
    "model": "trocr-small-handwritten",
    "device": "cpu",
    "confidence_description": "Mean output token softmax probability over the generated sequence"
  }
}
```

---

## 9. Backend OCR Provider Architecture

In the PillSync backend (`backend/app/services/ocr/`), a modular OCR Provider pattern is used:
- **`TesseractProvider`**: Primary engine for printed/structured prescriptions and PDF text.
- **`HandwritingOCRProvider`**: TrOCR engine for handwritten medicine word/line recognition.
- **`CompositeOCRProvider`**: Seamlessly delegates and combines printed OCR with handwriting recognition and reference normalization.

---

## 10. Limitations & Safety Disclaimers

> [!WARNING]
> 1. **Model Scope**: This handwriting model is trained on medical word images. It is not an end-to-end full prescription document extractor.
> 2. **Vocabulary Limitation**: Handwriting models may struggle with unseen drug brand names or heavily distorted physician signatures.
> 3. **Mandatory Human-in-the-Loop Review**: Predictions are matched against `medicine_reference` and **MUST ALWAYS** be reviewed and confirmed by the patient/clinician before any medication or dosage schedule record is persisted in the PostgreSQL database.
