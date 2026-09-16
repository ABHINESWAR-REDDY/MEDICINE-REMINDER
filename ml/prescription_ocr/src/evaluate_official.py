"""Official Evaluation Script for Baseline vs. Fine-Tuned TrOCR Models on RxHandBD Test Set.

Enforces:
- Evaluation ONLY on the 1,115 official frozen test samples
- Computes Character Error Rate (CER), Word Error Rate (WER), and Exact Match (%)
- Generates outputs/baseline_evaluation.json, outputs/finetuned_evaluation.json, and outputs/model_comparison.json
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.adapters.rxhandbd_adapter import RxHandBDAdapter


def compute_levenshtein(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def compute_cer(gt: str, pred: str) -> float:
    gt_c = gt.strip().lower()
    pr_c = pred.strip().lower()
    if not gt_c:
        return 0.0 if not pr_c else 1.0
    return compute_levenshtein(gt_c, pr_c) / len(gt_c)


def compute_wer(gt: str, pred: str) -> float:
    gt_w = gt.strip().lower().split()
    pr_w = pred.strip().lower().split()
    if not gt_w:
        return 0.0 if not pr_w else 1.0
    return compute_levenshtein(gt_w, pr_w) / len(gt_w)


def evaluate_model_on_test_set(
    model_path_or_name: str,
    max_samples: Optional[int] = None,
    device_str: Optional[str] = None,
) -> Dict[str, Any]:
    if device_str is None:
        device_str = "cuda:0" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_str)

    print(f"\nLoading model from: {model_path_or_name} (on {device})...")
    processor = TrOCRProcessor.from_pretrained(model_path_or_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_path_or_name).to(device)
    model.eval()

    adapter = RxHandBDAdapter(data_root=os.path.join(PROJECT_ROOT, "DATA"))
    _, _, test_samples = adapter.load_splits(validate_images=True)

    if max_samples:
        test_samples = test_samples[:max_samples]

    print(f"Evaluating on {len(test_samples)} Official RxHandBD Test Samples...")

    cer_list = []
    wer_list = []
    exact_matches = 0
    predictions_log = []
    t0 = time.time()

    batch_size = 8
    with torch.no_grad():
        for i in range(0, len(test_samples), batch_size):
            batch = test_samples[i : i + batch_size]
            images = []
            valid_batch = []
            for img_name, gt_text in batch:
                img_path = os.path.join(adapter.images_dir, img_name)
                try:
                    raw_image = Image.open(img_path).convert("RGB")
                    images.append(raw_image)
                    valid_batch.append((img_name, gt_text))
                except Exception:
                    continue

            if not images:
                continue

            pixel_values = processor(images, return_tensors="pt").pixel_values.to(device)
            generated_ids = model.generate(pixel_values, max_new_tokens=20)
            pred_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)

            for (img_name, gt_text), pred_text in zip(valid_batch, pred_texts):
                cer = compute_cer(gt_text, pred_text)
                wer = compute_wer(gt_text, pred_text)
                is_exact = gt_text.strip().lower() == pred_text.strip().lower()

                cer_list.append(cer)
                wer_list.append(wer)
                if is_exact:
                    exact_matches += 1

                predictions_log.append({
                    "image": img_name,
                    "ground_truth": gt_text,
                    "prediction": pred_text,
                    "cer": round(cer, 4),
                    "wer": round(wer, 4),
                    "exact_match": is_exact,
                })

            processed_count = min(i + batch_size, len(test_samples))
            if processed_count % 100 == 0 or processed_count == len(test_samples):
                current_cer = sum(cer_list) / max(1, len(cer_list))
                current_em = (exact_matches / max(1, len(cer_list))) * 100
                print(f"  Processed {processed_count}/{len(test_samples)} | Current CER: {current_cer:.4f} | Exact Match: {current_em:.1f}%")

    total_time = time.time() - t0
    avg_cer = sum(cer_list) / max(1, len(cer_list))
    avg_wer = sum(wer_list) / max(1, len(wer_list))
    exact_match_pct = (exact_matches / max(1, len(test_samples))) * 100.0

    return {
        "model_name": model_path_or_name,
        "total_test_samples": len(test_samples),

        "cer": round(avg_cer, 4),
        "wer": round(avg_wer, 4),
        "exact_match_pct": round(exact_match_pct, 2),
        "evaluation_time_seconds": round(total_time, 2),
        "predictions_sample": predictions_log[:20],
    }


def compare_and_save_benchmarks(
    baseline_metrics: Dict[str, Any],
    finetuned_metrics: Dict[str, Any],
    outputs_dir: str = "ml/prescription_ocr/outputs",
) -> Dict[str, Any]:
    out_path = os.path.join(PROJECT_ROOT, outputs_dir)
    os.makedirs(out_path, exist_ok=True)

    base_cer = baseline_metrics["cer"]
    fine_cer = finetuned_metrics["cer"]
    cer_improvement_pct = ((base_cer - fine_cer) / max(1e-6, base_cer)) * 100.0

    base_wer = baseline_metrics["wer"]
    fine_wer = finetuned_metrics["wer"]
    wer_improvement_pct = ((base_wer - fine_wer) / max(1e-6, base_wer)) * 100.0

    base_em = baseline_metrics["exact_match_pct"]
    fine_em = finetuned_metrics["exact_match_pct"]
    em_improvement = fine_em - base_em

    comparison = {
        "dataset": "RxHandBD Official Test Set (1,115 samples)",
        "baseline": {
            "model": baseline_metrics["model_name"],
            "cer": base_cer,
            "wer": base_wer,
            "exact_match_pct": base_em,
        },
        "finetuned": {
            "model": finetuned_metrics["model_name"],
            "cer": fine_cer,
            "wer": fine_wer,
            "exact_match_pct": fine_em,
        },
        "improvements": {
            "cer_improvement_pct": round(cer_improvement_pct, 2),
            "wer_improvement_pct": round(wer_improvement_pct, 2),
            "exact_match_gain_pct": round(em_improvement, 2),
        },
        "promotion_eligible": fine_cer < base_cer and fine_em > base_em,
    }

    with open(os.path.join(out_path, "baseline_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(baseline_metrics, f, indent=2)

    with open(os.path.join(out_path, "finetuned_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(finetuned_metrics, f, indent=2)

    with open(os.path.join(out_path, "model_comparison.json"), "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("\n==================================================")
    print("           MODEL BENCHMARK COMPARISON             ")
    print("==================================================")
    print(f"Metric          | Baseline   | Fine-Tuned | Improvement")
    print(f"----------------|------------|------------|------------")
    print(f"CER             | {base_cer:<10.4f} | {fine_cer:<10.4f} | {cer_improvement_pct:+.1f}%")
    print(f"WER             | {base_wer:<10.4f} | {fine_wer:<10.4f} | {wer_improvement_pct:+.1f}%")
    print(f"Exact Match     | {base_em:<9.2f}% | {fine_em:<9.2f}% | {em_improvement:+.2f}%")
    print("==================================================")
    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="microsoft/trocr-small-handwritten")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--compare", action="store_true", help="Compare with baseline_evaluation.json")
    args = parser.parse_args()

    res = evaluate_model_on_test_set(args.model_path, max_samples=args.max_samples)
    print(json.dumps(res, indent=2))

    if args.compare:
        base_eval_path = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "outputs", "baseline_evaluation.json")
        if os.path.exists(base_eval_path):
            with open(base_eval_path, "r", encoding="utf-8") as f:
                baseline_metrics = json.load(f)
            compare_and_save_benchmarks(baseline_metrics, res)
        else:
            print(f"Warning: Baseline metrics not found at {base_eval_path}. Saving as finetuned_evaluation.json")
            with open(os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "outputs", "finetuned_evaluation.json"), "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)

