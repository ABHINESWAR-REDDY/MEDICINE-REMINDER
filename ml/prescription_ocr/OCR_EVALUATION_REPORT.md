# Prescription OCR Evaluation Report

**Date:** August 26, 2026  
**Evaluated On:** Official Frozen Held-Out Test Set (`DATA/Test_Label.csv` / `DATA/Test_Set`)  
**Total Held-Out Test Samples:** `1,115` samples

---

## 1. Quantitative Benchmark Results

| Model Configuration | Character Error Rate (CER) | Word Error Rate (WER) | Exact Match (%) | Medicine Recognition Accuracy (Post-Fuzzy Normalization) |
| :--- | :--- | :--- | :--- | :--- |
| **Raw TrOCR Small Baseline** | `0.5892` | `1.3942` | `13.09%` | `41.2%` |
| **TrOCR + Post-Processing Normalization** | **`0.3418`** | **`0.5820`** | **`48.70%`** | **`86.4%`** |

---

## 2. Sample Inference & Normalization Breakdown

| Image | Ground Truth | Raw TrOCR Prediction | Normalized Candidate Match | Exact/Normalized Match | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `P0007.jpg` | `Napa` | `Napa` | `Napa 500mg Tablet` | ✅ Exact | `0.98` |
| `P0019.jpg` | `HPR DS` | `FIPR DS` | `HPR DS Tablet` | ✅ Fuzzy Normalized | `0.85` |
| `P0020.jpg` | `palpitation` | `palpitation` | `Palpitation` | ✅ Exact | `0.95` |
| `P0018.jpg` | `Setra` | `setru .` | `Setra 50mg Tablet` | ✅ Fuzzy Normalized | `0.82` |
| `P0015.jpg` | `Monas 10` | `Monas 10` | `Monas 10mg Tablet` | ✅ Exact | `0.96` |
| `P0016.jpg` | `Maxpro 20` | `Maxpro 20` | `Maxpro 20mg Capsule` | ✅ Exact | `0.97` |

---

## 3. Error Analysis & Limitations

1. **Extreme Doctor Handwriting Cursive Slurs**:
   - For heavily slurred doctor signatures or single-stroke loops, character recognition can have high ambiguity.
   - **Mitigation**: The system tags predictions with confidence $< 0.75$ with `"needs_confirmation": true`, requiring patient verification prior to database insertion.
2. **Clinical Provenance**:
   - Clinical fields not explicitly visible in the prescription (e.g. absent duration or instructions) are strictly preserved as `null` with provenance `not_detected` to avoid clinical hallucination.
