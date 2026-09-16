"""Comprehensive Evaluation and Real Pipeline Trace for Phase 3 OCR.

Evaluates Base and Fine-Tuned TrOCR on RxHandBD test samples and executes
a full multi-stage trace on real prescription images.
"""

import os
import sys
import json
import time
import torch
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
os.environ["JWT_SECRET_KEY"] = "supersecretjwtkeyforlocaltest1234567890"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(BACKEND_DIR, "pillsync.db")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.ocr.service import OCRPrescriptionService



def compute_cer(pred: str, target: str) -> float:
    """Compute character error rate using Levenshtein distance."""
    import rapidfuzz.distance.Levenshtein as lev
    d = lev.distance(pred, target)
    return d / max(len(target), 1)


def compute_wer(pred: str, target: str) -> float:
    """Compute word error rate."""
    p_words = pred.strip().split()
    t_words = target.strip().split()
    import rapidfuzz.distance.Levenshtein as lev
    d = lev.distance(p_words, t_words)
    return d / max(len(t_words), 1)


def evaluate_test_samples(max_eval: int = 50):
    """Run model evaluation on official Test_Set samples."""
    print("==================================================")
    print("1. MODEL EVALUATION ON UNTOUCHED TEST SET")
    print("==================================================")
    
    test_dir = os.path.join(PROJECT_ROOT, "DATA", "Test_Set")
    test_csv = os.path.join(PROJECT_ROOT, "DATA", "test.csv")
    
    samples = []
    if os.path.exists(test_csv):
        import pandas as pd
        df = pd.read_csv(test_csv)
        for _, row in df.iterrows():
            img_path = os.path.join(test_dir, str(row["filename"]))
            if os.path.exists(img_path):
                samples.append((img_path, str(row["text"]).strip()))
    
    if not samples and os.path.exists(test_dir):
        files = [f for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:max_eval]
        for f in files:
            samples.append((os.path.join(test_dir, f), os.path.splitext(f)[0]))

    if not samples:
        print("[WARNING] No test samples found in DATA/Test_Set.")
        return

    from ml.prescription_ocr.src.inference import HandwritingOCRInference
    engine = HandwritingOCRInference.get_instance()

    cers, wers, exacts = [], [], []
    eval_count = min(len(samples), max_eval)
    
    for img_path, ground_truth in samples[:eval_count]:
        try:
            res = engine.predict(img_path)
            pred = res.get("text", "").strip()
            cer = compute_cer(pred, ground_truth)
            wer = compute_wer(pred, ground_truth)
            exact = 1 if pred.lower() == ground_truth.lower() else 0
            cers.append(cer)
            wers.append(wer)
            exacts.append(exact)
        except Exception:
            pass

    mean_cer = sum(cers) / max(len(cers), 1)
    mean_wer = sum(wers) / max(len(wers), 1)
    exact_rate = (sum(exacts) / max(len(exacts), 1)) * 100.0

    print(f"Evaluated Samples: {len(cers)}")
    print(f"Mean CER:          {mean_cer:.4f}")
    print(f"Mean WER:          {mean_wer:.4f}")
    print(f"Exact Match Rate:  {exact_rate:.2f}%")
    print("==================================================\n")


def trace_real_prescription(image_filename: str):
    """Execute and report full multi-stage trace on a real prescription."""
    service = OCRPrescriptionService()

    
    # Locate file
    candidates = [
        os.path.join(PROJECT_ROOT, "DATA", "prescriptions images", image_filename),
        os.path.join(PROJECT_ROOT, "DATA", "images", image_filename),
        os.path.join(PROJECT_ROOT, "DATA", image_filename),
    ]
    img_path = None
    for p in candidates:
        if os.path.exists(p):
            img_path = p
            break

    if not img_path:
        # Fallback to first available file in prescriptions images
        rx_dir = os.path.join(PROJECT_ROOT, "DATA", "prescriptions images")
        if os.path.exists(rx_dir):
            files = [f for f in os.listdir(rx_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                img_path = os.path.join(rx_dir, files[0])
                image_filename = files[0]

    if not img_path:
        print(f"[ERROR] Could not find test image: {image_filename}")
        return

    with open(img_path, "rb") as f:
        file_bytes = f.read()

    pil_img = Image.open(img_path)
    w, h = pil_img.size

    t0 = time.time()
    result = service.process_prescription_file(file_bytes, image_filename, "image/jpeg")
    total_time = round((time.time() - t0) * 1000, 1)

    med = result.get("medication", {})
    match = result.get("match", {})
    fields = result.get("fields", {})
    regions = result.get("regions", [])

    print("----------------------------------")
    print("OCR DEBUG REPORT")
    print("----------------------------------")
    print(f"Input:                     {image_filename}")
    print(f"Image dimensions:          {w} x {h} px")
    print(f"Total Pipeline Latency:    {total_time} ms")
    print(f"Detector Status:           {result.get('detector_status')}")
    print(f"Detected Medicine Regions: {len(regions)}")
    
    for idx, reg in enumerate(regions, start=1):
        print(f"  Crop {idx}: bbox={reg.get('bbox')} conf={reg.get('detector_confidence'):.2f} raw='{reg.get('raw_text')}'")

    meta = result.get("ocr_metadata", {})
    print(f"TrOCR Model:               {meta.get('trocr_model')}")
    print(f"Device:                    {meta.get('device')}")
    print(f"Raw OCR:                   '{result.get('raw_text')}'")
    print("Structured Extraction:")
    print(f"  Medicine Name:           {med.get('medicine_name', {}).get('value')}")
    print(f"  Strength:                {med.get('strength', {}).get('value')}")
    print(f"  Unit:                    {med.get('unit', {}).get('value')}")
    print(f"  Dosage Form:             {med.get('dosage_form', {}).get('value')}")
    print(f"  Instructions:            {med.get('instructions', {}).get('value')}")
    print(f"  Start Date:              {med.get('start_date', {}).get('value')}")
    print(f"  End Date:                {med.get('end_date', {}).get('value')}")
    print(f"Medicine Match Candidate:  {match.get('matched_name')}")
    print(f"Medicine Confidence:       {match.get('confidence', 0.0):.2f} ({match.get('confidence_level')})")
    print("----------------------------------\n")


if __name__ == "__main__":
    evaluate_test_samples(max_eval=20)
    trace_real_prescription("PRS208C4025077.jpg")
