"""Comprehensive Evaluation and Verification Suite for Fine-Tuned TrOCR Pipeline.

Executes:
1. Checkpoint Reload Verification
2. Full Official 1,115 Test Set Evaluation (CER, WER, Exact Match)
3. Base Model Baseline Comparison
4. 20+ Test Sample Detailed Breakdowns (including failures)
5. Real Prescription Crops Qualitative Validation (104, 105, 106, 122, 124, 130, 144, 149)
"""

import os
import sys
import gc
import csv
import json
import time
import torch
from PIL import Image
from typing import Dict, List, Tuple, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from ml.prescription_ocr.src.train_trocr import compute_cer, compute_wer
from ml.prescription_ocr.src.detector.inference import PrescriptionMedicineDetector


def test_reload_checkpoint(checkpoint_dir: str, test_image_path: str, gt_label: str) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("STEP 12: CHECKPOINT RELOAD VERIFICATION")
    print("=" * 70)
    print(f"Loading freshly from disk: {checkpoint_dir}")
    
    gc.collect()
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    # Fresh load
    processor = TrOCRProcessor.from_pretrained(checkpoint_dir)
    model = VisionEncoderDecoderModel.from_pretrained(checkpoint_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    image = Image.open(test_image_path).convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad():
        outputs = model.generate(pixel_values, max_length=32, return_dict_in_generate=True, output_scores=True)
    
    pred_text = processor.decode(outputs.sequences[0], skip_special_tokens=True).strip()
    
    # Model confidence score
    confs = []
    if hasattr(outputs, "scores") and outputs.scores:
        for sc in outputs.scores:
            p = torch.softmax(sc[0], dim=-1).max().item()
            confs.append(p)
    conf_score = sum(confs) / max(1, len(confs)) if confs else 0.5

    cer = compute_cer(gt_label, pred_text)
    wer = compute_wer(gt_label, pred_text)

    print(f"  Test Image:             {os.path.basename(test_image_path)}")
    print(f"  Ground Truth:           \"{gt_label}\"")
    print(f"  Reloaded TrOCR Pred:    \"{pred_text}\"")
    print(f"  CER:                    {cer:.4f}")
    print(f"  Model Confidence Score: {conf_score:.4f}")
    print(f"  Reload Status:          SUCCESS (Model loaded from disk and executed inference)")
    print("=" * 70)

    return {
        "status": "PASSED",
        "image": os.path.basename(test_image_path),
        "ground_truth": gt_label,
        "prediction": pred_text,
        "cer": cer,
        "confidence_score": round(conf_score, 4),
    }


def evaluate_test_set(
    checkpoint_dir: str,
    dataset_dir: str,
    base_model_name: str = "microsoft/trocr-small-handwritten",
) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("STEP 13 & 14 & 15: OFFICIAL 1,115 TEST SET EVALUATION & BASELINE COMPARISON")
    print("=" * 70)

    test_img_dir = os.path.join(dataset_dir, "Test_Set")
    test_csv = os.path.join(dataset_dir, "Test_Label.csv")

    test_samples: List[Tuple[str, str]] = []
    with open(test_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            if len(r) >= 2 and r[1].strip():
                test_samples.append((r[0].strip(), r[1].strip()))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device:                 {device}")
    print(f"Total Test Samples:     {len(test_samples)}")

    # 1. Evaluate Fine-Tuned Model on all 1,115
    print("\nEvaluating Fine-Tuned Model on full test set (1,115 images)...")
    ft_processor = TrOCRProcessor.from_pretrained(checkpoint_dir)
    ft_model = VisionEncoderDecoderModel.from_pretrained(checkpoint_dir).to(device)
    ft_model.eval()

    ft_cer_sum = 0.0
    ft_wer_sum = 0.0
    ft_exact = 0
    detailed_samples = []

    start_t = time.time()
    for idx, (img_name, gt_text) in enumerate(test_samples, 1):
        img_path = os.path.join(test_img_dir, img_name)
        try:
            image = Image.open(img_path).convert("RGB")
        except Exception:
            image = Image.new("RGB", (384, 384), color=(255, 255, 255))

        pixel_values = ft_processor(image, return_tensors="pt").pixel_values.to(device)

        with torch.no_grad():
            outputs = ft_model.generate(pixel_values, max_length=32, return_dict_in_generate=True, output_scores=True)

        pred_text = ft_processor.decode(outputs.sequences[0], skip_special_tokens=True).strip()

        confs = []
        if hasattr(outputs, "scores") and outputs.scores:
            for sc in outputs.scores:
                p = torch.softmax(sc[0], dim=-1).max().item()
                confs.append(p)
        conf_score = sum(confs) / max(1, len(confs)) if confs else 0.5

        cer = compute_cer(gt_text, pred_text)
        wer = compute_wer(gt_text, pred_text)
        is_exact = gt_text.strip().lower() == pred_text.strip().lower()

        ft_cer_sum += cer
        ft_wer_sum += wer
        if is_exact:
            ft_exact += 1

        detailed_samples.append({
            "image": img_name,
            "ground_truth": gt_text,
            "prediction": pred_text,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "exact_match": is_exact,
            "model_confidence_score": round(conf_score, 4),
        })

        if idx % 200 == 0 or idx == len(test_samples):
            print(f"  Processed [{idx}/{len(test_samples)}] -> Current CER: {(ft_cer_sum / idx)*100:.2f}% | Exact Match: {(ft_exact / idx)*100:.2f}%")

    ft_duration = time.time() - start_t
    n_test = len(test_samples)
    final_ft_cer = ft_cer_sum / n_test
    final_ft_wer = ft_wer_sum / n_test
    final_ft_acc = (ft_exact / n_test) * 100.0

    # 2. Evaluate Base Model Baseline on test subset (100 samples)
    print("\nEvaluating Pretrained Base Model (microsoft/trocr-small-handwritten) baseline...")
    base_processor = TrOCRProcessor.from_pretrained(base_model_name)
    base_model = VisionEncoderDecoderModel.from_pretrained(base_model_name).to(device)
    base_model.eval()

    base_cer_sum = 0.0
    base_wer_sum = 0.0
    base_exact = 0
    base_sample_subset = test_samples[:100]

    for idx, (img_name, gt_text) in enumerate(base_sample_subset, 1):
        img_path = os.path.join(test_img_dir, img_name)
        try:
            image = Image.open(img_path).convert("RGB")
        except Exception:
            image = Image.new("RGB", (384, 384), color=(255, 255, 255))

        pixel_values = base_processor(image, return_tensors="pt").pixel_values.to(device)
        with torch.no_grad():
            outputs = base_model.generate(pixel_values, max_length=32)

        pred_text = base_processor.decode(outputs[0], skip_special_tokens=True).strip()
        cer = compute_cer(gt_text, pred_text)
        wer = compute_wer(gt_text, pred_text)
        if gt_text.strip().lower() == pred_text.strip().lower():
            base_exact += 1
        base_cer_sum += cer
        base_wer_sum += wer

    base_count = len(base_sample_subset)
    base_cer = base_cer_sum / base_count
    base_wer = base_wer_sum / base_count
    base_acc = (base_exact / base_count) * 100.0

    print("\n" + "=" * 70)
    print("EVALUATION COMPARISON REPORT")
    print("=" * 70)
    print(f"BASE PRETRAINED MODEL ({base_model_name}):")
    print(f"  CER:         {base_cer*100:.2f}%")
    print(f"  WER:         {base_wer*100:.2f}%")
    print(f"  Exact Match: {base_acc:.2f}%")
    print("-" * 70)
    print(f"FINE-TUNED MODEL ({checkpoint_dir}):")
    print(f"  CER:         {final_ft_cer*100:.2f}%")
    print(f"  WER:         {final_ft_wer*100:.2f}%")
    print(f"  Exact Match: {final_ft_acc:.2f}%")
    print("=" * 70)

    # Save detailed JSON report
    outputs_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    report_file = os.path.join(outputs_dir, "test_evaluation_report.json")
    
    report_data = {
        "dataset": "RxHandBD-ML",
        "total_test_samples": n_test,
        "base_model": {
            "name": base_model_name,
            "eval_samples": base_count,
            "cer": round(base_cer, 4),
            "wer": round(base_wer, 4),
            "exact_match_accuracy": round(base_acc, 2),
        },
        "fine_tuned_model": {
            "checkpoint": checkpoint_dir,
            "eval_samples": n_test,
            "cer": round(final_ft_cer, 4),
            "wer": round(final_ft_wer, 4),
            "exact_match_accuracy": round(final_ft_acc, 2),
            "duration_seconds": round(ft_duration, 1),
        },
        "improvements": {
            "cer_reduction_percentage": round(((base_cer - final_ft_cer) / max(base_cer, 1e-6)) * 100, 2),
            "exact_match_gain_percentage": round(final_ft_acc - base_acc, 2),
        },
        "detailed_predictions": detailed_samples,
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return report_data


def test_real_prescriptions(checkpoint_dir: str) -> List[Dict[str, Any]]:
    print("\n" + "=" * 70)
    print("STEP 19: REAL PRESCRIPTION CROPS QUALITATIVE VALIDATION")
    print("=" * 70)
    
    target_files = ["104.jpeg", "105.jpeg", "106.jpeg", "122.jpg", "124.jpeg", "130.jpeg", "144.jpeg", "149.jpeg"]
    img_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector", "test", "images")
    
    detector_ckpt = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "artifacts", "detector", "best_model.pth")
    if not os.path.exists(detector_ckpt):
        print(f"Warning: Detector checkpoint not found at {detector_ckpt}")
        return []

    detector = PrescriptionMedicineDetector(checkpoint_path=detector_ckpt, score_threshold=0.40, nms_iou_threshold=0.35)
    
    processor = TrOCRProcessor.from_pretrained(checkpoint_dir)
    model = VisionEncoderDecoderModel.from_pretrained(checkpoint_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    results = []

    for fname in target_files:
        fpath = os.path.join(img_dir, fname)
        if not os.path.exists(fpath):
            print(f"File {fname} not found in {img_dir}")
            continue

        det_result = detector.detect(fpath, crop_margin=0.08)
        boxes = det_result.get("boxes", [])
        scores = det_result.get("scores", [])

        img = Image.open(fpath).convert("RGB")
        w, h = img.size

        crops_text = []
        for b_idx, (box, score) in enumerate(zip(boxes, scores)):
            x1, y1, x2, y2 = [int(v) for v in box]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = img.crop((x1, y1, x2, y2))
            px = processor(crop, return_tensors="pt").pixel_values.to(device)

            with torch.no_grad():
                out = model.generate(px, max_length=32, return_dict_in_generate=True, output_scores=True)

            text = processor.decode(out.sequences[0], skip_special_tokens=True).strip()

            confs = []
            if hasattr(out, "scores") and out.scores:
                for sc in out.scores:
                    p = torch.softmax(sc[0], dim=-1).max().item()
                    confs.append(p)
            model_conf = sum(confs) / max(1, len(confs)) if confs else 0.5

            crops_text.append({
                "region_index": b_idx + 1,
                "bbox": [x1, y1, x2, y2],
                "detector_confidence": round(float(score), 4),
                "trocr_transcription": text,
                "model_confidence_score": round(model_conf, 4),
            })

        print(f"\nPrescription: {fname} (Detected Regions: {len(crops_text)})")
        for ct in crops_text:
            print(f"  Region #{ct['region_index']}: Box={ct['bbox']} | DetConf={ct['detector_confidence']:.2f} | TrOCR=\"{ct['trocr_transcription']}\" | ModelConf={ct['model_confidence_score']:.3f}")

        results.append({
            "filename": fname,
            "regions_count": len(crops_text),
            "regions": crops_text,
        })

    print("=" * 70)
    return results


if __name__ == "__main__":
    ckpt_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "models")
    rx_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "raw", "RxHandBD-ML")
    sample_img = os.path.join(rx_dir, "Test_Set", "P0001.jpg")

    test_reload_checkpoint(ckpt_dir, sample_img, "Nexcital")
    evaluate_test_set(ckpt_dir, rx_dir)
    test_real_prescriptions(ckpt_dir)
