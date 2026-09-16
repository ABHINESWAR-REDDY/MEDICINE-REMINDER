"""Full Fine-Tuning and Evaluation Pipeline for TrOCR on RxHandBD Dataset.

Supports epoch-by-epoch training with gradient accumulation, validation metrics,
checkpoint tracking, best-model selection, and held-out test evaluation.
"""

import os
import sys
import argparse
import logging
import json
import time
import random
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from ml.prescription_ocr.src.dataset import RxHandBDDataLoader, DatasetSample
from ml.prescription_ocr.src.preprocess import PrescriptionImagePreprocessor
from ml.prescription_ocr.src.metrics import calculate_cer, calculate_wer, calculate_corpus_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
)
logger = logging.getLogger("pillsync.ml.train")


def parse_args():
    parser = argparse.ArgumentParser(description="Train TrOCR on RxHandBD Prescription Dataset")
    parser.add_argument("--data-dir", type=str, default=None, help="Directory containing RxHandBD data")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save model & processor")
    parser.add_argument("--model-name", type=str, default="microsoft/trocr-small-handwritten",
                        help="HuggingFace TrOCR pretrained model name")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size per step")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--smoke-test", action="store_true", help="Run genuine forward-backward training smoke test")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit number of training samples")
    parser.add_argument("--val-split", type=float, default=0.10, help="Fraction of training data for validation")
    parser.add_argument("--image-size", type=int, default=384, help="Image resolution for TrOCR processor")
    parser.add_argument("--max-target-length", type=int, default=64, help="Max length of transcription sequence")
    return parser.parse_args()


def detect_device() -> Tuple[Any, str, str]:
    """Detect available hardware (CUDA GPU vs Apple MPS vs CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            logger.info("CUDA GPU detected: %s (%.2f GB VRAM)", device_name, vram_gb)
            return torch.device("cuda"), "CUDA GPU", device_name
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Apple Silicon MPS accelerator detected.")
            return torch.device("mps"), "Apple MPS", "Apple Silicon"
        else:
            logger.info("No CUDA GPU detected. Training will run on CPU.")
            return torch.device("cpu"), "CPU", "Host CPU"
    except ImportError:
        logger.warning("PyTorch not installed. Running in simulation mode.")
        return None, "CPU (Simulated)", "Host CPU"


def evaluate_split(model, processor, preprocessor, samples: List[DatasetSample], device, max_eval_samples: int = 100) -> Dict[str, Any]:
    """Evaluate CER, WER, and exact match on a validation or test split."""
    import torch

    eval_subset = samples[:max_eval_samples] if max_eval_samples else samples
    model.eval()

    preds: List[str] = []
    targets: List[str] = []
    sample_records: List[Dict[str, Any]] = []

    with torch.no_grad():
        for s in eval_subset:
            gt = s.transcription.strip()
            img = Image.open(s.image_path).convert("RGB")
            processed_img = preprocessor.preprocess(img)
            pixel_values = processor(processed_img, return_tensors="pt").pixel_values.to(device)

            generated_ids = model.generate(pixel_values, max_length=64, return_dict_in_generate=True, output_scores=True)
            pred = processor.batch_decode(generated_ids.sequences, skip_special_tokens=True)[0].strip()

            score = 0.50
            if hasattr(generated_ids, "scores") and generated_ids.scores:
                step_probs = [torch.softmax(sc, dim=-1).max().item() for sc in generated_ids.scores]
                if step_probs:
                    score = round(float(sum(step_probs) / len(step_probs)), 4)

            cer = calculate_cer(pred, gt)
            wer = calculate_wer(pred, gt)
            exact = (pred.lower() == gt.lower())

            preds.append(pred)
            targets.append(gt)
            sample_records.append({
                "sample_id": s.sample_id,
                "ground_truth": gt,
                "prediction": pred,
                "cer": round(cer, 4),
                "wer": round(wer, 4),
                "exact_match": exact,
                "confidence_score": score,
            })

    metrics = calculate_corpus_metrics(preds, targets, case_sensitive=False)
    metrics["records"] = sample_records
    return metrics


def run_training():
    args = parse_args()

    default_output_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    output_dir = os.path.abspath(args.output_dir or default_output_dir)
    os.makedirs(output_dir, exist_ok=True)

    logger.info("==================================================")
    logger.info("PillSync Phase 3 - TrOCR Full RxHandBD Fine-Tuning")
    logger.info("==================================================")
    logger.info("Pretrained Model:        %s", args.model_name)
    logger.info("Output Directory:        %s", output_dir)
    logger.info("Smoke Test Mode:         %s", args.smoke_test)
    logger.info("Batch Size:              %d", args.batch_size)
    logger.info("Gradient Accumulation:   %d", args.grad_accum)
    logger.info("Effective Batch Size:    %d", args.batch_size * args.grad_accum)
    logger.info("Learning Rate:           %s", args.lr)
    logger.info("Epochs:                  %d", args.epochs)

    device, device_type, device_details = detect_device()

    # 1. Load Dataset
    logger.info("Loading RxHandBD dataset...")
    loader = RxHandBDDataLoader(data_dir=args.data_dir)
    raw_train_samples, test_samples = loader.load_dataset(validate_images=False)
    logger.info(loader.get_statistics_report())

    if args.smoke_test:
        logger.info("SMOKE TEST: Subsetting to 4 train and 2 test samples.")
        train_samples = raw_train_samples[:4]
        val_samples = raw_train_samples[4:6]
    else:
        # Create deterministic train / validation split from the 4,463 training set
        rng = random.Random(42)
        shuffled = list(raw_train_samples)
        rng.shuffle(shuffled)
        n_val = int(len(shuffled) * args.val_split)
        val_samples = shuffled[:n_val]
        train_samples = shuffled[n_val:]
        if args.max_samples:
            train_samples = train_samples[:args.max_samples]

    logger.info("Training Split: %d images | Validation Split: %d images | Held-out Test Split: %d images",
                len(train_samples), len(val_samples), len(test_samples))

    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    logger.info("Loading TrOCR Processor and Model from %s ...", args.model_name)
    processor = TrOCRProcessor.from_pretrained(args.model_name)
    model = VisionEncoderDecoderModel.from_pretrained(args.model_name)

    # Configure special generation tokens
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.config.eos_token_id = processor.tokenizer.sep_token_id
    model.config.max_length = args.max_target_length

    model.to(device)

    preprocessor = PrescriptionImagePreprocessor(target_size=(args.image_size, args.image_size))

    # Evaluate Baseline Model (Before Fine-Tuning) on Validation Subset
    logger.info("Evaluating Base Pretrained Model baseline on validation split...")
    base_val_metrics = evaluate_split(model, processor, preprocessor, val_samples, device, max_eval_samples=20)
    logger.info("Base Model Baseline -> CER: %.4f (%.2f%%) | Exact Match: %.2f%%",
                base_val_metrics["cer"], base_val_metrics["cer"] * 100, base_val_metrics["exact_match"] * 100)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    epochs_completed = 0
    epoch_train_losses = []
    epoch_val_metrics = []
    best_val_cer = 999.0
    best_checkpoint_dir = os.path.join(output_dir, "best_model")
    os.makedirs(best_checkpoint_dir, exist_ok=True)

    start_training_time = time.time()

    total_epochs = 1 if args.smoke_test else args.epochs

    for epoch in range(total_epochs):
        epoch_idx = epoch + 1
        logger.info("--- Starting Epoch %d/%d ---", epoch_idx, total_epochs)
        model.train()

        epoch_loss = 0.0
        batch_count = 0
        optimizer.zero_grad()

        # Batch iteration
        for i in range(0, len(train_samples), args.batch_size):
            batch_samples = train_samples[i:i + args.batch_size]
            if not batch_samples:
                continue

            pixel_list = []
            label_list = []

            for s in batch_samples:
                img = Image.open(s.image_path).convert("RGB")
                processed_img = preprocessor.preprocess(img)
                pixel_tensor = processor(processed_img, return_tensors="pt").pixel_values.squeeze(0)

                label_ids = processor.tokenizer(
                    s.transcription,
                    padding="max_length",
                    max_length=args.max_target_length,
                    return_tensors="pt",
                    truncation=True
                ).input_ids.squeeze(0)
                label_ids[label_ids == processor.tokenizer.pad_token_id] = -100

                pixel_list.append(pixel_tensor)
                label_list.append(label_ids)

            batch_pixels = torch.stack(pixel_list).to(device)
            batch_labels = torch.stack(label_list).to(device)

            outputs = model(pixel_values=batch_pixels, labels=batch_labels)
            loss = outputs.loss / args.grad_accum
            loss.backward()

            batch_loss_val = outputs.loss.item()
            epoch_loss += batch_loss_val
            batch_count += 1

            if (i // args.batch_size + 1) % args.grad_accum == 0 or (i + args.batch_size >= len(train_samples)):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                optimizer.zero_grad()

            if batch_count % 50 == 0:
                logger.info("Epoch %d | Batch %d/%d | Current Loss: %.4f",
                            epoch_idx, batch_count, (len(train_samples) + args.batch_size - 1) // args.batch_size, batch_loss_val)

        avg_train_loss = epoch_loss / max(batch_count, 1)
        epoch_train_losses.append(round(avg_train_loss, 4))
        epochs_completed += 1

        # Validation at end of epoch
        logger.info("Running validation for Epoch %d...", epoch_idx)
        val_eval = evaluate_split(model, processor, preprocessor, val_samples, device,
                                  max_eval_samples=4 if args.smoke_test else 50)
        epoch_val_metrics.append({
            "epoch": epoch_idx,
            "train_loss": round(avg_train_loss, 4),
            "val_cer": val_eval["cer"],
            "val_wer": val_eval["wer"],
            "val_exact_match": val_eval["exact_match"],
        })

        logger.info("Epoch %d Results -> Train Loss: %.4f | Val CER: %.4f (%.2f%%) | Val Exact Match: %.2f%%",
                    epoch_idx, avg_train_loss, val_eval["cer"], val_eval["cer"] * 100, val_eval["exact_match"] * 100)

        # Track and save best checkpoint
        if val_eval["cer"] < best_val_cer:
            best_val_cer = val_eval["cer"]
            logger.info("New best validation CER: %.4f! Saving best checkpoint to %s", best_val_cer, best_checkpoint_dir)
            model.save_pretrained(best_checkpoint_dir)
            processor.save_pretrained(best_checkpoint_dir)

    training_duration = time.time() - start_training_time

    # Save final model weights in main models/ directory
    logger.info("Saving final model weights and processor to %s ...", output_dir)
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)

    # 4. Final Evaluation on 1,115 Held-out Test Split
    logger.info("==================================================")
    logger.info("Evaluating Final Model on Held-out Test Split (%d images)...", len(test_samples))
    test_eval_subset_count = 20 if args.smoke_test else len(test_samples)
    final_test_metrics = evaluate_split(model, processor, preprocessor, test_samples, device,
                                        max_eval_samples=test_eval_subset_count)

    logger.info("FINAL HELD-OUT TEST RESULTS:")
    logger.info("  Final Test CER:          %.4f (%.2f%%)", final_test_metrics["cer"], final_test_metrics["cer"] * 100)
    logger.info("  Final Test WER:          %.4f (%.2f%%)", final_test_metrics["wer"], final_test_metrics["wer"] * 100)
    logger.info("  Final Test Exact Match:  %.4f (%.2f%%)", final_test_metrics["exact_match"], final_test_metrics["exact_match"] * 100)

    # Calculate Improvement Percentage over baseline
    base_cer = base_val_metrics["cer"]
    final_cer = final_test_metrics["cer"]
    cer_improvement_pct = round(((base_cer - final_cer) / max(base_cer, 1e-6)) * 100, 2)

    training_summary = {
        "status": "COMPLETED",
        "smoke_test": args.smoke_test,
        "model_architecture": "TrOCR (DeiTModel Encoder + TrOCRForCausalLM Decoder)",
        "pretrained_base": args.model_name,
        "device": device_type,
        "device_details": device_details,
        "total_parameters": sum(p.numel() for p in model.parameters()),
        "epochs_completed": epochs_completed,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "effective_batch_size": args.batch_size * args.grad_accum,
        "learning_rate": args.lr,
        "training_duration_seconds": round(training_duration, 2),
        "epoch_train_losses": epoch_train_losses,
        "epoch_val_metrics": epoch_val_metrics,
        "base_model_metrics": {
            "cer": base_val_metrics["cer"],
            "wer": base_val_metrics["wer"],
            "exact_match": base_val_metrics["exact_match"],
        },
        "final_test_metrics": {
            "cer": final_test_metrics["cer"],
            "wer": final_test_metrics["wer"],
            "exact_match": final_test_metrics["exact_match"],
            "samples_evaluated": test_eval_subset_count,
        },
        "cer_improvement_percentage": cer_improvement_pct,
        "best_checkpoint": best_checkpoint_dir,
        "sample_predictions": final_test_metrics.get("records", [])[:25],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    summary_file = os.path.join(output_dir, "training_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(training_summary, f, indent=2)

    # Export outputs/evaluation_results.json
    outputs_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    eval_results_file = os.path.join(outputs_dir, "evaluation_results.json")
    with open(eval_results_file, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": final_test_metrics,
            "base_metrics": base_val_metrics,
            "improvement_pct": cer_improvement_pct,
            "training_summary": training_summary,
        }, f, indent=2)

    logger.info("Training and evaluation completed successfully.")
    logger.info("Saved training summary to %s", summary_file)
    logger.info("Saved evaluation results to %s", eval_results_file)

    return training_summary


if __name__ == "__main__":
    run_training()
