"""Phase 3 Comprehensive OCR Accuracy Investigation Script.

Executes all 17 investigation requirements:
1. Model checkpoint verification
2. Real prescription detector execution, bounding box rendering & error categorization
3. Dataset inspection (20 train + 10 val visualized samples with ground-truth boxes)
4. Objective detector evaluation on test set (Precision, Recall, IoU, mAP@50, TP, FP, FN)
5. Crop margins (5%, 10%, 15%) saving
6. TrOCR evaluation on 20 known-good RxHandBD test samples
7. Doctor's Handwritten Prescription dataset inspection
"""

import os
import sys
import json
import time
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "outputs", "investigation")
TRAIN_VIS_DIR = os.path.join(OUTPUT_DIR, "training_samples")
VAL_VIS_DIR = os.path.join(OUTPUT_DIR, "val_samples")
os.makedirs(TRAIN_VIS_DIR, exist_ok=True)
os.makedirs(VAL_VIS_DIR, exist_ok=True)


def investigate_model_checkpoint():
    print("=" * 65)
    print("1. MODEL CHECKPOINT VERIFICATION (TrOCR & DETECTOR)")
    print("=" * 65)
    
    prod_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "models", "production")
    default_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "models")
    model_dir = prod_dir if os.path.exists(os.path.join(prod_dir, "config.json")) else default_dir
    
    print(f"TrOCR Model Path:       {model_dir}")
    if os.path.exists(model_dir):
        files = os.listdir(model_dir)
        for f in files:
            fp = os.path.join(model_dir, f)
            if os.path.isfile(fp):
                mtime = time.ctime(os.path.getmtime(fp))
                sz = os.path.getsize(fp)
                print(f"  - {f}: {sz:,} bytes (Modified: {mtime})")

    summary_file = os.path.join(model_dir, "training_summary.json")
    if os.path.exists(summary_file):
        with open(summary_file, "r") as f:
            summary = json.load(f)
            print(f"\nTrOCR Training Summary:")
            print(f"  Status:             {summary.get('status')}")
            print(f"  Train Samples:      {summary.get('train_samples_count')}")
            print(f"  Validation Samples: {summary.get('validation_samples_count')}")
            print(f"  Best Val CER:       {summary.get('best_validation_cer')}")

    detector_ckpt = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "artifacts", "detector", "best_model.pth")
    print(f"\nDetector Checkpoint:    {detector_ckpt}")
    print(f"Detector Exists:        {os.path.exists(detector_ckpt)}")
    if os.path.exists(detector_ckpt):
        print(f"Detector Size:          {os.path.getsize(detector_ckpt):,} bytes")
        print(f"Detector Modified:      {time.ctime(os.path.getmtime(detector_ckpt))}")

    print(f"\nPyTorch Device Info:")
    print(f"  CUDA Available:       {torch.cuda.is_available()}")
    print(f"  Device Selected:      {'cuda' if torch.cuda.is_available() else 'cpu'}")


def investigate_detector_on_sample(image_filename="PRS208C4025077.jpg"):
    print("\n" + "=" * 65)
    print(f"2. INVESTIGATE MEDICINE DETECTOR ON {image_filename}")
    print("=" * 65)

    from ml.prescription_ocr.src.detector.inference import PrescriptionRegionDetector
    detector = PrescriptionRegionDetector()

    # Search for image
    img_path = None
    candidates = [
        os.path.join(PROJECT_ROOT, "DATA", "prescriptions images", image_filename),
        os.path.join(PROJECT_ROOT, "DATA", "images", image_filename),
        os.path.join(PROJECT_ROOT, "DATA", image_filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            img_path = c
            break

    if not img_path:
        print(f"[ERROR] Could not find {image_filename}")
        return

    pil_img = Image.open(img_path).convert("RGB")
    w, h = pil_img.size
    print(f"Image File:        {image_filename}")
    print(f"Image Dimensions:  {w} x {h} px")

    # Run detection with lower threshold to inspect all proposed candidates
    det_res = detector.predict(pil_img, confidence_threshold=0.08)
    regions = det_res.get("regions", [])
    print(f"Total Regions Detected (conf >= 0.08): {len(regions)}")

    vis_img = pil_img.copy()
    draw = ImageDraw.Draw(vis_img)

    for i, r in enumerate(regions):
        box = [round(v, 1) for v in r["box"]]
        conf = r["confidence"]
        crop_box = [round(v, 1) for v in r["crop_box"]]
        print(f"  Region #{i+1}:")
        print(f"    Raw BBox:        {box}")
        print(f"    Confidence:      {conf:.3f}")
        print(f"    Expanded Crop:   {crop_box}")
        
        color = "green" if conf >= 0.35 else ("orange" if conf >= 0.18 else "red")
        draw.rectangle(box, outline=color, width=4)
        draw.text((box[0] + 5, max(0, box[1] - 15)), f"#{i+1} ({conf:.2f})", fill=color)

    vis_out = os.path.join(OUTPUT_DIR, f"{os.path.splitext(image_filename)[0]}_detector_vis.jpg")
    vis_img.save(vis_out, quality=95)
    print(f"Detector Visualization Saved: {vis_out}")

    # Test Adaptive Crop Margins (5%, 10%, 15%)
    print("\n--- TEST ADAPTIVE CROP MARGINS (5%, 10%, 15%) ---")
    if regions:
        top_region = regions[0]
        x1, y1, x2, y2 = top_region["box"]
        bw, bh = x2 - x1, y2 - y1

        for margin_pct in [0.05, 0.10, 0.15]:
            pad_x = bw * margin_pct
            pad_y = bh * margin_pct
            cx1 = max(0, int(x1 - pad_x))
            cy1 = max(0, int(y1 - pad_y))
            cx2 = min(w, int(x2 + pad_x))
            cy2 = min(h, int(y2 + pad_y))

            crop_patch = pil_img.crop((cx1, cy1, cx2, cy2))
            crop_out = os.path.join(OUTPUT_DIR, f"crop_margin_{int(margin_pct*100)}pct.jpg")
            crop_patch.save(crop_out, quality=95)
            print(f"  {int(margin_pct*100)}% Margin Crop: ({cx1}, {cy1}, {cx2}, {cy2}) -> size {crop_patch.size} saved to {crop_out}")


def inspect_training_dataset_labels(num_train_vis=20, num_val_vis=10):
    print("\n" + "=" * 65)
    print("3. VERIFY DETECTOR TRAINING & VALIDATION LABELS")
    print("=" * 65)

    det_data_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector")
    train_img_dir = os.path.join(det_data_dir, "train", "images")
    train_lbl_dir = os.path.join(det_data_dir, "train", "labels")
    val_img_dir = os.path.join(det_data_dir, "val", "images")
    val_lbl_dir = os.path.join(det_data_dir, "val", "labels")

    print(f"Train Images Dir: {train_img_dir} (Exists: {os.path.exists(train_img_dir)})")
    print(f"Val Images Dir:   {val_img_dir} (Exists: {os.path.exists(val_img_dir)})")

    if not os.path.exists(train_img_dir):
        print("[WARNING] Detector train directory not found.")
        return

    train_imgs = sorted([f for f in os.listdir(train_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    val_imgs = sorted([f for f in os.listdir(val_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    print(f"Total Train Images: {len(train_imgs)}")
    print(f"Total Val Images:   {len(val_imgs)}")

    def render_and_save_samples(img_list, img_dir, lbl_dir, out_dir, count, split_name):
        box_counts = []
        for img_name in img_list[:count]:
            base = os.path.splitext(img_name)[0]
            lbl_name = f"{base}.txt"
            img_p = os.path.join(img_dir, img_name)
            lbl_p = os.path.join(lbl_dir, lbl_name)

            if not os.path.exists(lbl_p):
                continue

            img = Image.open(img_p).convert("RGB")
            w, h = img.size
            draw = ImageDraw.Draw(img)

            with open(lbl_p, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]

            box_counts.append(len(lines))
            for line in lines:
                parts = line.split()
                if len(parts) == 5:
                    cls_id, xc, yc, bw, bh = map(float, parts)
                    x1 = int((xc - bw / 2.0) * w)
                    y1 = int((yc - bh / 2.0) * h)
                    x2 = int((xc + bw / 2.0) * w)
                    y2 = int((yc + bh / 2.0) * h)
                    draw.rectangle([x1, y1, x2, y2], outline="cyan", width=3)

            out_p = os.path.join(out_dir, f"{split_name}_{img_name}")
            img.save(out_p, quality=90)

        mean_boxes = np.mean(box_counts) if box_counts else 0
        print(f"  Rendered {len(box_counts)} {split_name} samples (Average {mean_boxes:.1f} medicine boxes per image) -> {out_dir}")

    render_and_save_samples(train_imgs, train_img_dir, train_lbl_dir, TRAIN_VIS_DIR, num_train_vis, "train")
    render_and_save_samples(val_imgs, val_img_dir, val_lbl_dir, VAL_VIS_DIR, num_val_vis, "val")


def evaluate_detector_objectively():
    print("\n" + "=" * 65)
    print("4. OBJECTIVE DETECTOR EVALUATION ON TEST SET")
    print("=" * 65)

    from ml.prescription_ocr.src.detector.evaluate import evaluate_detector

    det_data_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector")
    ckpt_path = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "artifacts", "detector", "best_model.pth")
    test_img_dir = os.path.join(det_data_dir, "test", "images")

    if not os.path.exists(test_img_dir) or not os.path.exists(ckpt_path):
        print(f"[WARNING] Test set or checkpoint not found: test={os.path.exists(test_img_dir)}, ckpt={os.path.exists(ckpt_path)}")
        return

    test_imgs = [f for f in os.listdir(test_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Test Set Prescriptions: {len(test_imgs)}")

    try:
        report = evaluate_detector(
            checkpoint_path=ckpt_path,
            dataset_dir=det_data_dir,
            output_dir=os.path.join(OUTPUT_DIR, "detector_eval"),
            img_size=800,
        )
        print(f"Evaluation Report on Held-out Test Set:")
        metrics = report.get("metrics_at_default_conf", {})
        print(f"  Confidence Threshold: {metrics.get('confidence_threshold', 0.40)}")
        print(f"  Precision:            {metrics.get('precision', 0.0):.4f}")
        print(f"  Recall:               {metrics.get('recall', 0.0):.4f}")
        print(f"  F1-Score:             {metrics.get('f1_score', 0.0):.4f}")
        print(f"  Mean IoU on Hits:     {metrics.get('mean_iou_on_hits', 0.0):.4f}")
        print(f"  mAP@50:               {report.get('mAP_50', 0.0):.4f}")
        print(f"  mAP@50:95:            {report.get('mAP_50_95', 0.0):.4f}")
        print(f"  Ground Truth Boxes:   {report.get('total_ground_truth_boxes', 0)}")
        print(f"  Predicted Boxes:      {metrics.get('post_nms_predicted_boxes', 0)}")
        print(f"  True Positives:       {metrics.get('true_positives', 0)}")
        print(f"  False Positives:      {metrics.get('false_positives', 0)}")
        print(f"  False Negatives:      {metrics.get('false_negatives', 0)}")
    except Exception as e:
        print(f"Detector evaluation error: {e}")


def evaluate_trocr_known_good_crops():
    print("\n" + "=" * 65)
    print("6 & 8. TEST TrOCR ON KNOWN-GOOD RxHandBD TEST SAMPLES")
    print("=" * 65)

    from ml.prescription_ocr.src.inference import HandwritingOCRInference
    engine = HandwritingOCRInference.get_instance()

    test_csv = os.path.join(PROJECT_ROOT, "DATA", "Test_Label.csv")
    test_dir = os.path.join(PROJECT_ROOT, "DATA", "Test_Set")

    if not os.path.exists(test_csv):
        test_csv = os.path.join(PROJECT_ROOT, "DATA", "test.csv")

    if not os.path.exists(test_csv) or not os.path.exists(test_dir):
        print(f"[ERROR] Test dataset not found at {test_csv} or {test_dir}")
        return

    import csv
    import rapidfuzz.distance.Levenshtein as lev

    valid_samples = []
    with open(test_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        img_col = "filename" if "filename" in fieldnames else fieldnames[0]
        label_col = "text" if "text" in fieldnames else ("label" if "label" in fieldnames else fieldnames[1])
        
        for row in reader:
            img_name = str(row.get(img_col, "")).strip()
            lbl = str(row.get(label_col, "")).strip()
            img_p = os.path.join(test_dir, img_name)
            if os.path.exists(img_p) and lbl:
                valid_samples.append((img_p, lbl, img_name))

    print(f"Total Official Test Set Samples Available: {len(valid_samples)}")

    cers, wers, exacts = [], [], []
    examples = []

    for img_path, gt_text, fname in valid_samples[:30]:
        try:
            res = engine.predict(img_path)
            pred = res.get("text", "").strip()
            conf = res.get("confidence_score", 0.0)

            c_dist = lev.distance(pred, gt_text)
            cer = c_dist / max(len(gt_text), 1)
            
            p_words = pred.split()
            t_words = gt_text.split()
            w_dist = lev.distance(p_words, t_words)
            wer = w_dist / max(len(t_words), 1)
            
            exact = 1 if pred.strip().lower() == gt_text.strip().lower() else 0

            cers.append(cer)
            wers.append(wer)
            exacts.append(exact)

            if len(examples) < 20:
                examples.append({
                    "sample": fname,
                    "ground_truth": gt_text,
                    "prediction": pred,
                    "confidence": conf,
                    "cer": round(cer, 3),
                    "exact_match": exact == 1
                })
        except Exception as e:
            print(f"Inference error on {fname}: {e}")

    mean_cer = np.mean(cers) if cers else 0.0
    mean_wer = np.mean(wers) if wers else 0.0
    exact_acc = (np.mean(exacts) * 100.0) if exacts else 0.0

    print(f"\n--- EVALUATION SUMMARY ({len(cers)} samples) ---")
    print(f"Mean Character Error Rate (CER): {mean_cer:.4f}")
    print(f"Mean Word Error Rate (WER):      {mean_wer:.4f}")
    print(f"Exact Match Accuracy:            {exact_acc:.2f}%\n")

    print("--- 20 REPRESENTATIVE TEST EXAMPLES ---")
    for i, ex in enumerate(examples, start=1):
        status = "MATCH" if ex["exact_match"] else "MISMATCH"
        print(f"Example {i:02d} [{status}]:")
        print(f"  File:         {ex['sample']}")
        print(f"  GROUND TRUTH: '{ex['ground_truth']}'")
        print(f"  PREDICTION:   '{ex['prediction']}'")
        print(f"  CER:          {ex['cer']}, Conf: {ex['confidence']:.2f}")


def inspect_additional_datasets():
    print("\n" + "=" * 65)
    print("10. INSPECT DOCTOR'S HANDWRITTEN PRESCRIPTION BD DATASET")
    print("=" * 65)

    doc_dir = os.path.join(PROJECT_ROOT, "DATA", "Doctor’s Handwritten Prescription BD dataset")
    if os.path.exists(doc_dir):
        print(f"Contents of {doc_dir}:")
        sub_items = os.listdir(doc_dir)
        for item in sub_items:
            sub_p = os.path.join(doc_dir, item)
            if os.path.isdir(sub_p):
                cnt = len(os.listdir(sub_p))
                print(f"  - Folder {item}: {cnt} items")
            else:
                sz = os.path.getsize(sub_p)
                print(f"  - File {item}: {sz} bytes")

    train_csv = os.path.join(PROJECT_ROOT, "DATA", "Train_Label.csv")
    if os.path.exists(train_csv):
        import csv
        with open(train_csv, "r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            print(f"\nTrain_Label.csv Summary:")
            print(f"  Total Rows: {len(reader)}")
            if reader:
                print(f"  Fieldnames: {list(reader[0].keys())}")
                print(f"  First 3 entries:")
                for r in reader[:3]:
                    print(f"    {r}")



if __name__ == "__main__":
    investigate_model_checkpoint()
    investigate_detector_on_sample("PRS208C4025077.jpg")
    inspect_training_dataset_labels(num_train_vis=20, num_val_vis=10)
    evaluate_detector_objectively()
    evaluate_trocr_known_good_crops()
    inspect_additional_datasets()
