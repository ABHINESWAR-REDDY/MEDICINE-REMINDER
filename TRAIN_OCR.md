# Retraining & Running the Prescription OCR Pipeline

This guide outlines the exact commands to run the GPU smoke test, fine-tune the model, evaluate on held-out test data, and run integration tests.

---

## 1. Environment Setup

Activate the project Python virtual environment:

```powershell
cd C:\Users\admin\Desktop\pillsync
.\.venv\Scripts\Activate.ps1
```

---

## 2. Verify Datasets & Leakage Protection

```powershell
python -c "
from ml.prescription_ocr.src.adapters.rxhandbd_adapter import RxHandBDAdapter
adapter = RxHandBDAdapter(data_root='DATA')
train, val, test = adapter.load_splits(validate_images=True)
print(f'Train: {len(train)} | Val: {len(val)} | Test: {len(test)}')
"
```

---

## 3. Run GPU Smoke Test

```powershell
python ml/prescription_ocr/src/smoke_test_gpu.py
```

---

## 4. Retrain TrOCR Model

To launch fine-tuning with 2GB VRAM optimization (batch size 1, gradient accumulation 8, gradient checkpointing):

```powershell
python ml/prescription_ocr/src/train_trocr_gpu.py --epochs 3 --batch-size 1 --grad-accum 8 --lr 5e-5
```

---

## 5. Evaluate on Official Held-Out Test Set (1,115 samples)

```powershell
python ml/prescription_ocr/src/evaluate_official.py --model-path microsoft/trocr-small-handwritten --compare
```

---

## 6. Run Backend & Frontend Automated Tests

```powershell
# Backend pytest suite
python -m pytest backend/tests/test_stage3_trocr_integration.py backend/tests/test_real_prescription_e2e.py -v

# Frontend Vitest suite
cd frontend
npm test -- --run
```
