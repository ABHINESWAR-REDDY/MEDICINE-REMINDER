# Training Data Verification Report

**Date & Time:** August 26, 2026  
**Status:** ✅ VERIFIED & APPROVED FOR TRAINING (ZERO LEAKAGE)

---

## 1. Summary of Primary Dataset (`RxHandBD` / `Test_Set`)

| Metric | Measured Value | Verification Status |
| :--- | :--- | :--- |
| **Total Images in `DATA/Test_Set`** | `5,578` | ✅ Exact disk match |
| **Rows in `DATA/Train_Label.csv`** | `4,463` | ✅ Exact disk match |
| **Rows in `DATA/Test_Label.csv`** | `1,115` | ✅ Exact disk match |
| **Sum (`Train` + `Test`)** | `5,578` | ✅ `4,463 + 1,115 = 5,578` |
| **Missing Image References** | `0` | ✅ All images exist |
| **Duplicate Image References** | `0` | ✅ All keys unique |
| **Overlap / Data Leakage** | `0` | ✅ Train & Test are 100% disjoint |
| **Unreferenced Images** | `0` | ✅ 100% dataset utilized |

---

## 2. Training Split Allocation

To maintain strict evaluation discipline:

- **Training Split**: `4,000` samples (deterministic random shuffle with seed `42`)
- **Validation Split**: `463` samples (for per-epoch loss and CER monitoring)
- **Held-Out Test Split**: `1,115` samples (strictly frozen for final evaluation)

---

## 3. Secondary & Reference Datasets

- **`Doctor’s Handwritten Prescription BD dataset`**:
  - Training: `3,120` word crops
  - Validation: `780` word crops
  - Testing: `780` word crops
- **Full Prescription Scans**:
  - `DATA/prescriptions images`: `309` full clinical prescription scans
  - `DATA/images`: `3,333` multi-format prescription images
  - `DATA/data`: `129` scans
- **Pharmaceutical Reference Databases**:
  - `DATA/medicine names/medicine_dataset_enhanced.csv`: `50,001` drug formulations
  - `DATA/medicine names/all_medicine databased.csv`: `248,219` brand names, generic formulations, and substitutes
