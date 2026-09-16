# Model Card: PillSync Handwritten Prescription OCR (TrOCR-Small-RxHandBD)

## 1. Model Details
- **Model Name:** `microsoft/trocr-small-handwritten` + PillSync Clinical Normalization Layer
- **Architecture:** Vision Encoder-Decoder (DeiT Vision Transformer Encoder + TrOCR / RoBERTa Autoregressive Causal Decoder)
- **Parameters:** ~62 Million Parameters
- **Input:** $384 \times 384$ RGB / Grayscale Prescription Line & Crop Images
- **Output:** Raw Recognized Text Tokens + Fuzzy-Matched Clinical Entities

---

## 2. Intended Use
- **Primary Domain:** Handwritten & printed doctor prescription digitization.
- **Integration Point:** PillSync Patient Portal (`/patient/scan-prescription` & `/api/v1/ocr/prescription`).
- **Safety Guardrail:** Healthcare-critical human-in-the-loop validation. All predictions require patient review and explicit confirmation before persisting to the database.

---

## 3. Training & Dataset Specifics
- **Dataset:** `RxHandBD` (`DATA/Test_Set`, `DATA/Train_Label.csv`)
- **Training Samples:** 4,000 image-text pairs
- **Validation Samples:** 463 image-text pairs
- **Frozen Test Samples:** 1,115 image-text pairs (zero data leakage)
- **Reference Matcher:** 50,001 items (`medicine_dataset_enhanced.csv`) + 248,219 items (`all_medicine databased.csv`)

---

## 4. Evaluation Performance
- **Exact Match:** `13.09%` (Raw) $\rightarrow$ `48.70%` (Post-Normalization)
- **Medicine Recognition Rate:** `86.4%` (after RapidFuzz pharmaceutical index lookup)
- **CER:** `0.5892` (Raw) $\rightarrow$ `0.3418` (Normalized)
- **WER:** `1.3942` (Raw) $\rightarrow$ `0.5820` (Normalized)

---

## 5. Limitations & Ethical Considerations
- **Severe Distortion:** Extreme cursive doctor slurs may produce lower confidence predictions.
- **Safety Policy:** Predictions with confidence $< 0.75$ are flagged with `"needs_confirmation": true`. The backend never automatically prescribes or modifies dosages without human confirmation.
