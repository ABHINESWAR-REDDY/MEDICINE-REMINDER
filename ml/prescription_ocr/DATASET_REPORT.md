# PillSync Prescription OCR Dataset Report

## 1. Executive Summary

This report documents the exhaustive dataset audit for the **PillSync Prescription OCR and Handwritten Medicine Extraction** module. All analyses were conducted directly against the on-disk datasets in `DATA/`.

---

## 2. Dataset Inventory

| Dataset / Folder Name | Image Format & Dimensions | Annotation Format | Total Samples | Handwritten vs. Printed | Key Information Available |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DATA/Test_Set`** | JPEG ($512 \times 512$) | CSV (`Train_Label.csv`, `Test_Label.csv`) | **5,578** | **Handwritten** | Word & line level medicine names, dosages, formulations |
| **`Doctor’s Handwritten Prescription BD`** | PNG ($64 \times 128$ to $128 \times 256$) | CSV (`training_labels.csv`, etc.) | **4,680** | **Handwritten** | Brand name, Generic formulation name |
| **`DATA/prescriptions images`** | JPEG (up to $1200 \times 1600$) | Full Prescription Images | **309** | **Handwritten / Mixed** | Real clinical prescription scans with doctor headers, Rx body, signatures |
| **`DATA/images`** | JPEG / PNG | Full Prescription Images | **3,333** | **Mixed** | Full document clinical records |
| **`DATA/data`** | JPEG | Full Prescription Images | **129** | **Mixed** | Full document scans |
| **`medicine_dataset_enhanced.csv`** | Structured CSV | Tabular Reference | **50,001** | Reference Database | Name, Category, Dosage Form, Strength, Manufacturer, Frequency |
| **`all_medicine databased.csv`** | Structured CSV | Tabular Reference | **248,219** | Reference Database | Brand name, Generic name, 5 substitutes, side effects, therapeutic class |

---

## 3. Data Integrity & Leakage Verification

- **Total Test_Set Images**: `5,578`
- **Training Partition (`Train_Label.csv`)**: `4,463`
- **Held-Out Test Partition (`Test_Label.csv`)**: `1,115`
- **Intersection / Overlap**: `0` (Zero data leakage)
- **Deterministic Split**: `4,000` Train / `463` Validation / `1,115` Official Frozen Test

---

## 4. Recommended Training & Inference Strategy

1. **Vision-Encoder-Decoder (TrOCR Small Handwritten)**:
   - Base model: `microsoft/trocr-small-handwritten`
   - Encoder: DeiT / ViT for robust visual feature extraction
   - Decoder: RoBERTa / MiniLM autoregressive sequence generator
2. **Deterministic Preprocessing**:
   - Contrast adjustment (CLAHE) + aspect-ratio preservation
   - Normalization matching TrOCR image processor ($384 \times 384$)
3. **Clinical Post-Processing Layer**:
   - Fast fuzzy lookup against `medicine_dataset_enhanced.csv` (50,000 items)
   - Structured parsing for dosage amounts (`mg`, `ml`, `mcg`), forms (`tablet`, `capsule`), and frequency schedules (`1-0-1`, `BID`, `TDS`).
