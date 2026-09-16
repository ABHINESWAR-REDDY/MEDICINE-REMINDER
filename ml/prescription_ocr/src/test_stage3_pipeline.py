"""Real-world validation script for Phase 3 Stage 3 Multi-Stage OCR pipeline."""

import os
import sys
import json
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

if "JWT_SECRET_KEY" not in os.environ:
    os.environ["JWT_SECRET_KEY"] = "super-secret-key-for-testing-1234567890-abcdef"

from app.services.ocr.service import OCRPrescriptionService
from ml.prescription_ocr.src.inference import HandwritingOCRInference

def run_evaluation():
    service = OCRPrescriptionService()

    test_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector", "test", "images")
    test_files = sorted(os.listdir(test_dir))[:10]

    print("=" * 75)
    print("PHASE 3 STAGE 3 — MULTI-STAGE OCR PIPELINE REAL PRESCRIPTION TEST")
    print("=" * 75)

    results = []
    for idx, fname in enumerate(test_files, 1):
        fpath = os.path.join(test_dir, fname)
        with open(fpath, "rb") as f:
            file_bytes = f.read()

        res = service.process_prescription_file(file_bytes, fname, "image/jpeg")
        regs = res.get("regions", [])
        fields = res.get("fields", {})

        print(f"\n[{idx}/10] Prescription: {fname}")
        print(f"  Detector Status:          {res.get('detector_status')}")
        print(f"  Coverage Warning:         {res.get('detector_coverage_warning')}")
        print(f"  Fallback Used:            {res.get('fallback_used')}")
        print(f"  Detected Regions Count:   {len(regs)}")
        print(f"  Extracted Medicine Name:  {fields.get('medicine_name')}")
        print(f"  Extracted Strength:       {fields.get('strength')} (Provenance: {res.get('evidence', {}).get('strength', {}).get('source')})")
        print(f"  Extracted Dosage Form:    {fields.get('dosage_form')} (Provenance: {res.get('evidence', {}).get('dosage_form', {}).get('source')})")

        for r in regs:
            cand = r.get("matched_name")
            cand_conf = r.get("match_confidence", 0.0)
            print(
                f"    Region #{r['region_index']}: Box={r['bbox']} | "
                f"DetConf={r['detector_confidence']:.2f} | "
                f"OCR=\"{r['raw_text']}\" | "
                f"ModelScore={r['model_confidence_score']:.3f} | "
                f"Candidate={cand} ({cand_conf:.2f})"
            )

        results.append({
            "filename": fname,
            "detector_status": res.get("detector_status"),
            "regions_count": len(regs),
            "regions": regs,
            "fields": fields,
        })

    # Test on 5 RxHandBD crops with ground-truth
    print("\n" + "=" * 75)
    print("TESTING TROCR ON 5 RXHANDBD WORD/LINE CROPS WITH GROUND TRUTH")
    print("=" * 75)
    hw_engine = HandwritingOCRInference.get_instance()
    rxhandbd_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "raw", "RxHandBD-ML", "Test_Set")
    rxhandbd_csv = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "raw", "RxHandBD-ML", "Test_Label.csv")
    
    if os.path.exists(rxhandbd_csv) and os.path.exists(rxhandbd_dir):
        import csv
        gt_map = {}
        with open(rxhandbd_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    gt_map[row[0].strip()] = row[1].strip()

        sample_keys = list(gt_map.keys())[:5]
        for key in sample_keys:
            img_path = os.path.join(rxhandbd_dir, key)
            if not os.path.exists(img_path):
                # Try adding .jpg / .png if needed
                for ext in [".jpg", ".jpeg", ".png"]:
                    if os.path.exists(img_path + ext):
                        img_path = img_path + ext
                        break
            if os.path.exists(img_path):
                pred = hw_engine.predict(img_path)
                print(f"  Crop Image:   {key}")
                print(f"    Ground Truth: \"{gt_map[key]}\"")
                print(f"    TrOCR Output: \"{pred.get('text')}\"")
                print(f"    Model Score:  {pred.get('confidence_score'):.3f}")
                print(f"    Conf Level:   {pred.get('confidence_level')}")

    print("=" * 75)


if __name__ == "__main__":
    run_evaluation()
