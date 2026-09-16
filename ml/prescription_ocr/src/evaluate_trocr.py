"""Official 1,115-test-set evaluation and baseline comparison for TrOCR on RxHandBD."""

import os
import sys
import csv
import json
import time
import argparse
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image

import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from ml.prescription_ocr.src.train_trocr import compute_cer, compute_wer


def evaluate_model_on_dataset(
    model: VisionEncoderDecoderModel,
    processor: TrOCRProcessor,
    dataset_dir: str,
    device: torch.device,
    max_samples: Optional[int] = None,
) -> Dict[str, Any]:
    """Evaluate a TrOCR model on the official 1,115 test set."""
    test_img_dir = os.path.join(dataset_dir, "Test_Set")
    test_csv = os.path.join(dataset_dir, "Test_Label.csv")

    test_samples: List[Tuple[str, str]] = []
    with open(test_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            if len(r) >= 2 and r[1].strip():
                test_samples.append((r[0].strip(), r[1].strip()))

    if max_samples:
        test_samples = test_samples[:max_samples]

    model.eval()
    total_cer = 0.0
    total_wer = 0.0
    exact_matches = 0
    predictions_log = []

    start_time = time.time()

    for idx, (img_name, gt_text) in enumerate(test_samples, 1):
        img_path = os.path.join(test_img_dir, img_name)
        try:
            image = Image.open(img_path).convert("RGB")
        except Exception:
            base = os.path.splitext(img_name)[0]
            for ext in [".jpg", ".jpeg", ".png"]:
                alt_path = os.path.join(test_img_dir, base + ext)
                if os.path.exists(alt_path):
                    image = Image.open(alt_path).convert("RGB")
                    break
            else:
                image = Image.new("RGB", (384, 384), color=(255, 255, 255))

        pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

        with torch.no_grad():
            outputs = model.generate(
                pixel_values,
                max_length=32,
                return_dict_in_generate=True,
                output_scores=True,
            )

        seq = outputs.sequences[0]
        pred_text = processor.decode(seq, skip_special_tokens=True).strip()

        # Compute model confidence score from transition logits
        model_conf = 0.5
        if hasattr(outputs, "scores") and outputs.scores:
            step_confs = []
            for step_logits in outputs.scores:
                step_probs = torch.softmax(step_logits[0], dim=-1)
                max_p = step_probs.max().item()
                step_confs.append(max_p)
            model_conf = sum(step_confs) / max(1, len(step_confs))

        cer_val = compute_cer(gt_text, pred_text)
        wer_val = compute_wer(gt_text, pred_text)
        is_exact = gt_text.strip().lower() == pred_text.strip().lower()

        total_cer += cer_val
        total_wer += wer_val
        if is_exact:
            exact_matches += 1

        predictions_log.append({
            "image": img_name,
            "ground_truth": gt_text,
            "prediction": pred_text,
            "cer": round(cer_val, 4),
            "wer": round(wer_val, 4),
            "exact_match": is_exact,
            "model_confidence_score": round(model_conf, 4),
        })

    elapsed = time.time() - start_time
    total_count = len(test_samples)
    mean_cer = total_cer / max(1, total_count)
    mean_wer = total_wer / max(1, total_count)
    exact_acc = (exact_matches / max(1, total_count)) * 100.0

    return {
        "total_test_samples": total_count,
        "mean_cer": round(mean_cer, 4),
        "mean_wer": round(mean_wer, 4),
        "exact_match_accuracy": round(exact_acc, 2),
        "evaluation_time_seconds": round(elapsed, 1),
        "predictions": predictions_log,
    }


def run_full_evaluation(
    dataset_dir: str,
    fine_tuned_model_dir: str,
    output_dir: str,
    base_model_name: str = "microsoft/trocr-small-handwritten",
    device_str: Optional[str] = None,
):
    """Run evaluation comparing base model and fine-tuned model on the 1,115 test set."""
    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("TrOCR OFFICIAL TEST SET EVALUATION (1,115 RxHandBD IMAGES)")
    print("=" * 70)
    print(f"Fine-tuned Model Dir: {fine_tuned_model_dir}")
    print(f"Base Model Name:      {base_model_name}")
    print(f"Device:               {device}")
    print("=" * 70)

    # 1. Evaluate Fine-Tuned Model
    print("\n[1/2] Evaluating Fine-Tuned RxHandBD Model...")
    ft_processor = TrOCRProcessor.from_pretrained(fine_tuned_model_dir)
    ft_model = VisionEncoderDecoderModel.from_pretrained(fine_tuned_model_dir).to(device)
    ft_results = evaluate_model_on_dataset(ft_model, ft_processor, dataset_dir, device)

    print(f"  --> Fine-Tuned Model: CER={ft_results['mean_cer']*100:.2f}% | WER={ft_results['mean_wer']*100:.2f}% | Exact Match={ft_results['exact_match_accuracy']:.2f}%")

    # 2. Evaluate Base Model on benchmark subset for comparison
    print("\n[2/2] Evaluating Original Pretrained Base Model (microsoft/trocr-small-handwritten)...")
    base_processor = TrOCRProcessor.from_pretrained(base_model_name)
    base_model = VisionEncoderDecoderModel.from_pretrained(base_model_name).to(device)
    base_results = evaluate_model_on_dataset(base_model, base_processor, dataset_dir, device, max_samples=100)

    print(f"  --> Base Pretrained:  CER={base_results['mean_cer']*100:.2f}% | WER={base_results['mean_wer']*100:.2f}% | Exact Match={base_results['exact_match_accuracy']:.2f}%")

    # 3. Save Summary Comparison
    comparison = {
        "dataset": "RxHandBD-ML",
        "official_test_set_size": 1115,
        "base_model": {
            "name": base_model_name,
            "sample_size": base_results["total_test_samples"],
            "cer": base_results["mean_cer"],
            "wer": base_results["mean_wer"],
            "exact_match_accuracy": base_results["exact_match_accuracy"],
        },
        "fine_tuned_model": {
            "checkpoint_path": fine_tuned_model_dir,
            "sample_size": ft_results["total_test_samples"],
            "cer": ft_results["mean_cer"],
            "wer": ft_results["mean_wer"],
            "exact_match_accuracy": ft_results["exact_match_accuracy"],
        },
        "improvements": {
            "cer_reduction": round(base_results["mean_cer"] - ft_results["mean_cer"], 4),
            "exact_match_gain": round(ft_results["exact_match_accuracy"] - base_results["exact_match_accuracy"], 2),
        },
        "sample_predictions": ft_results["predictions"][:25],
    }

    report_path = os.path.join(output_dir, "test_evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("\n" + "=" * 70)
    print("BASELINE VS FINE-TUNED COMPARISON SUMMARY:")
    print("=" * 70)
    print(f"Base Model ({base_model_name}):")
    print(f"  CER:         {base_results['mean_cer']*100:.2f}%")
    print(f"  WER:         {base_results['mean_wer']*100:.2f}%")
    print(f"  Exact Match: {base_results['exact_match_accuracy']:.2f}%")
    print("-" * 70)
    print(f"Fine-Tuned Model ({fine_tuned_model_dir}):")
    print(f"  CER:         {ft_results['mean_cer']*100:.2f}%")
    print(f"  WER:         {ft_results['mean_wer']*100:.2f}%")
    print(f"  Exact Match: {ft_results['exact_match_accuracy']:.2f}%")
    print("=" * 70)

    print("\nFirst 20 Test Predictions (Fine-Tuned Model):")
    for idx, p in enumerate(ft_results["predictions"][:20], 1):
        status = "MATCH" if p["exact_match"] else "DIFF"
        print(f"  [{idx:02d}] {p['image']} -> GT: \"{p['ground_truth']}\" | Pred: \"{p['prediction']}\" | CER: {p['cer']:.2f} | Score: {p['model_confidence_score']:.3f} [{status}]")

    print("=" * 70 + "\n")
    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate TrOCR on 1,115 RxHandBD Test Images")
    parser.add_argument("--dataset-dir", type=str, default=r"ml\prescription_ocr\data\raw\RxHandBD-ML", help="Path to RxHandBD-ML")
    parser.add_argument("--model-dir", type=str, default=r"ml\prescription_ocr\models", help="Path to fine-tuned model")
    parser.add_argument("--output-dir", type=str, default=r"ml\prescription_ocr\artifacts\trocr\evaluation", help="Output directory")

    args = parser.parse_args()
    run_full_evaluation(
        dataset_dir=args.dataset_dir,
        fine_tuned_model_dir=args.model_dir,
        output_dir=args.output_dir,
    )
