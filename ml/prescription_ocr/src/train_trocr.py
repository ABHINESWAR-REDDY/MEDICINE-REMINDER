"""Fine-tuning pipeline for TrOCR Handwriting Recognition on RxHandBD-ML.

Trains microsoft/trocr-small-handwritten on 4,463 training images with:
- Deterministic 4,000 train / 463 validation split (1,115 test set kept untouched)
- Proper label masking with -100 on pad tokens
- Metric evaluation per epoch (Validation Loss, CER, WER, Exact Match)
- Checkpointing best model weights (safetensors + config + processor)
"""

import os
import sys
import csv
import json
import time
import random
import argparse
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    AdamW,
    get_cosine_schedule_with_warmup,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def compute_levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
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
    """Compute Character Error Rate (CER)."""
    gt_clean = gt.strip().lower()
    pred_clean = pred.strip().lower()
    if not gt_clean:
        return 0.0 if not pred_clean else 1.0
    dist = compute_levenshtein(gt_clean, pred_clean)
    return dist / len(gt_clean)


def compute_wer(gt: str, pred: str) -> float:
    """Compute Word Error Rate (WER)."""
    gt_words = gt.strip().lower().split()
    pred_words = pred.strip().lower().split()
    if not gt_words:
        return 0.0 if not pred_words else 1.0
    dist = compute_levenshtein(gt_words, pred_words)
    return dist / len(gt_words)


class RxHandBDDataset(Dataset):
    """PyTorch Dataset for RxHandBD handwritten prescription image-label pairs."""

    def __init__(
        self,
        samples: List[Tuple[str, str]],
        images_dir: str,
        processor: TrOCRProcessor,
        max_target_length: int = 32,
    ):
        self.samples = samples
        self.images_dir = images_dir
        self.processor = processor
        self.max_target_length = max_target_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        img_name, text = self.samples[idx]
        img_path = os.path.join(self.images_dir, img_name)

        try:
            image = Image.open(img_path).convert("RGB")
        except Exception:
            # Fallback if image has different extension
            base = os.path.splitext(img_name)[0]
            for ext in [".jpg", ".jpeg", ".png"]:
                alt_path = os.path.join(self.images_dir, base + ext)
                if os.path.exists(alt_path):
                    image = Image.open(alt_path).convert("RGB")
                    break
            else:
                # Blank fallback
                image = Image.new("RGB", (384, 384), color=(255, 255, 255))

        pixel_values = self.processor(image, return_tensors="pt").pixel_values[0]

        # Tokenize target text
        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=self.max_target_length,
            truncation=True,
            return_tensors="pt",
        ).input_ids[0]

        # Mask padding tokens with -100 so CrossEntropyLoss ignores them
        labels[labels == self.processor.tokenizer.pad_token_id] = -100

        return {
            "pixel_values": pixel_values,
            "labels": labels,
            "raw_text": text,
            "img_name": img_name,
        }


def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    labels = torch.stack([item["labels"] for item in batch])
    raw_texts = [item["raw_text"] for item in batch]
    img_names = [item["img_name"] for item in batch]
    return {
        "pixel_values": pixel_values,
        "labels": labels,
        "raw_texts": raw_texts,
        "img_names": img_names,
    }


def verify_gradient_update(model, processor, sample_batch, device):
    """Verify that forward pass, backward pass, and weight updates function correctly."""
    print("\n" + "=" * 60)
    print("CONTROLLED OPTIMIZATION GRADIENT VERIFICATION")
    print("=" * 60)
    model.train()
    optimizer = AdamW(model.parameters(), lr=1e-4)

    pixel_values = sample_batch["pixel_values"].to(device)
    labels = sample_batch["labels"].to(device)

    # Record initial weights of a decoder layer
    decoder_weight_before = model.decoder.output_projection.weight.clone()

    outputs = model(pixel_values=pixel_values, labels=labels)
    loss = outputs.loss
    print(f"Step 0 Verification Loss: {loss.item():.4f}")

    optimizer.zero_grad()
    loss.backward()

    # Check that gradients exist and are non-zero
    grad_norm = 0.0
    for p in model.parameters():
        if p.grad is not None:
            grad_norm += p.grad.norm().item()

    print(f"Total Gradient Norm:     {grad_norm:.4f}")
    assert grad_norm > 0.0, "Gradient norm is zero; model is not computing gradients!"

    optimizer.step()

    decoder_weight_after = model.decoder.output_projection.weight
    weight_diff = (decoder_weight_after - decoder_weight_before).abs().sum().item()
    print(f"Weight Update Magnitude: {weight_diff:.6f}")
    assert weight_diff > 0.0, "Model weights did not update after optimizer step!"

    print("Gradient verification PASSED successfully! Model parameters update properly.")
    print("=" * 60 + "\n")


def train_trocr(
    dataset_dir: str,
    output_dir: str,
    base_model_name: str = "microsoft/trocr-small-handwritten",
    epochs: int = 5,
    batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 5e-5,
    val_split_size: int = 463,
    seed: int = 42,
    device_str: Optional[str] = None,
    max_train_samples: Optional[int] = None,
    max_val_samples: Optional[int] = None,
):
    """Execute full fine-tuning on RxHandBD dataset."""
    random.seed(seed)
    torch.manual_seed(seed)

    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if device.type == "cpu" and hasattr(os, "cpu_count"):
        threads = max(1, (os.cpu_count() or 4) - 1)
        torch.set_num_threads(threads)
        print(f"Configured PyTorch CPU execution threads: {threads}")

    os.makedirs(output_dir, exist_ok=True)
    artifacts_trocr_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "artifacts", "trocr")
    os.makedirs(artifacts_trocr_dir, exist_ok=True)

    # 1. Load Labels & Images
    train_img_dir = os.path.join(dataset_dir, "Train_Set")
    train_csv = os.path.join(dataset_dir, "Train_Label.csv")

    train_samples: List[Tuple[str, str]] = []
    with open(train_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # Header
        for r in reader:
            if len(r) >= 2 and r[1].strip():
                train_samples.append((r[0].strip(), r[1].strip()))

    print("=" * 70)
    print("TrOCR RxHandBD FINE-TUNING PIPELINE")
    print("=" * 70)
    print(f"Base Model:             {base_model_name}")
    print(f"Device:                 {device}")
    print(f"Total Training Samples: {len(train_samples)}")
    print(f"Epochs:                 {epochs}")
    print(f"Batch Size:             {batch_size} (Effective: {batch_size * gradient_accumulation_steps})")
    print(f"Learning Rate:          {learning_rate}")
    print(f"Output Directory:       {output_dir}")
    print("=" * 70)

    # Shuffle deterministically and split into train / val
    random.shuffle(train_samples)
    val_samples = train_samples[:val_split_size]
    actual_train_samples = train_samples[val_split_size:]

    if max_train_samples is not None and max_train_samples > 0:
        actual_train_samples = actual_train_samples[:max_train_samples]
    if max_val_samples is not None and max_val_samples > 0:
        val_samples = val_samples[:max_val_samples]

    print(f"Train subset:           {len(actual_train_samples)} images")
    print(f"Validation subset:      {len(val_samples)} images")

    # 2. Initialize Processor and Model
    print(f"\nLoading processor and model from {base_model_name}...")
    processor = TrOCRProcessor.from_pretrained(base_model_name)
    model = VisionEncoderDecoderModel.from_pretrained(base_model_name)

    # Set special token IDs
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size

    # Set generation parameters on generation_config for fast/clean decoding
    if hasattr(model, "generation_config") and model.generation_config is not None:
        model.generation_config.decoder_start_token_id = processor.tokenizer.cls_token_id
        model.generation_config.pad_token_id = processor.tokenizer.pad_token_id
        model.generation_config.max_length = 32
        model.generation_config.num_beams = 1
        model.generation_config.early_stopping = False
        model.generation_config.length_penalty = 1.0
        model.generation_config.no_repeat_ngram_size = 0
    model.config.max_length = 32

    model.to(device)

    # 3. Create Datasets & Loaders
    train_dataset = RxHandBDDataset(actual_train_samples, train_img_dir, processor)
    val_dataset = RxHandBDDataset(val_samples, train_img_dir, processor)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
    )

    # Run controlled gradient verification
    sample_batch = next(iter(train_loader))
    verify_gradient_update(model, processor, sample_batch, device)

    # 4. Optimizer & Scheduler
    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = (len(train_loader) // gradient_accumulation_steps) * epochs
    warmup_steps = int(total_steps * 0.1)
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    best_val_cer = float("inf")
    best_val_loss = float("inf")
    best_epoch = 1
    training_history = []

    print("Beginning fine-tuning...")
    start_total_time = time.time()

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()
        model.train()
        train_loss_accum = 0.0
        train_batches = 0

        optimizer.zero_grad()
        for step, batch in enumerate(train_loader, 1):
            pixel_values = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss / gradient_accumulation_steps
            loss.backward()

            train_loss_accum += (loss.item() * gradient_accumulation_steps)
            train_batches += 1

            if step % gradient_accumulation_steps == 0 or step == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

        avg_train_loss = train_loss_accum / max(1, train_batches)

        # 5. Validation Evaluation
        model.eval()
        val_loss_accum = 0.0
        val_batches = 0
        total_cer = 0.0
        total_wer = 0.0
        exact_matches = 0
        val_sample_count = 0

        with torch.no_grad():
            for val_batch in val_loader:
                pixel_values = val_batch["pixel_values"].to(device)
                labels = val_batch["labels"].to(device)
                raw_gt_texts = val_batch["raw_texts"]

                outputs = model(pixel_values=pixel_values, labels=labels)
                val_loss_accum += outputs.loss.item()
                val_batches += 1

                # Generate predictions
                generated_ids = model.generate(pixel_values, max_length=32)
                pred_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)

                for gt, pred in zip(raw_gt_texts, pred_texts):
                    pred_clean = pred.strip()
                    gt_clean = gt.strip()
                    c_err = compute_cer(gt_clean, pred_clean)
                    w_err = compute_wer(gt_clean, pred_clean)

                    total_cer += c_err
                    total_wer += w_err
                    if gt_clean.lower() == pred_clean.lower():
                        exact_matches += 1
                    val_sample_count += 1

        avg_val_loss = val_loss_accum / max(1, val_batches)
        avg_val_cer = total_cer / max(1, val_sample_count)
        avg_val_wer = total_wer / max(1, val_sample_count)
        exact_match_acc = (exact_matches / max(1, val_sample_count)) * 100.0
        epoch_time = time.time() - epoch_start

        epoch_stat = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "val_loss": round(avg_val_loss, 4),
            "val_cer": round(avg_val_cer, 4),
            "val_wer": round(avg_val_wer, 4),
            "exact_match_accuracy": round(exact_match_acc, 2),
            "time_seconds": round(epoch_time, 1),
        }
        training_history.append(epoch_stat)

        print(
            f"Epoch [{epoch:02d}/{epochs:02d}] "
            f"Train Loss: {avg_train_loss:.4f} | "
            f"Val Loss: {avg_val_loss:.4f} | "
            f"Val CER: {avg_val_cer:.4f} | "
            f"Val WER: {avg_val_wer:.4f} | "
            f"Exact Match: {exact_match_acc:.1f}% | "
            f"Time: {epoch_time:.1f}s"
        )

        # Save Best Checkpoint based on Validation CER
        if avg_val_cer < best_val_cer:
            best_val_cer = avg_val_cer
            best_val_loss = avg_val_loss
            best_epoch = epoch

            print(f"  --> Saved new best TrOCR checkpoint (Val CER: {avg_val_cer:.4f})")
            # Save to production model directory
            model.save_pretrained(output_dir)
            processor.save_pretrained(output_dir)
            # Also save to artifacts/trocr/best_model
            model.save_pretrained(os.path.join(artifacts_trocr_dir, "best_model"))
            processor.save_pretrained(os.path.join(artifacts_trocr_dir, "best_model"))

    total_training_duration = time.time() - start_total_time

    # 6. Save Training Summary
    summary = {
        "status": "COMPLETED",
        "model_id": "trocr-small-handwritten-rxhandbd",
        "base_model": base_model_name,
        "dataset": "RxHandBD-ML",
        "train_count": len(actual_train_samples),
        "validation_count": len(val_samples),
        "train_samples_count": len(actual_train_samples),
        "validation_samples_count": len(val_samples),
        "epochs": epochs,
        "batch_size": batch_size,
        "effective_batch_size": batch_size * gradient_accumulation_steps,
        "learning_rate": learning_rate,
        "best_epoch": best_epoch,
        "best_validation_metric": round(best_val_cer, 4),
        "training_loss": round(training_history[best_epoch - 1]["train_loss"], 4),
        "validation_loss": round(best_val_loss, 4),
        "CER": round(best_val_cer, 4),
        "WER": round(training_history[best_epoch - 1]["val_wer"], 4),
        "exact_match": round(training_history[best_epoch - 1]["exact_match_accuracy"], 2),
        "total_training_duration_seconds": round(total_training_duration, 1),
        "device": str(device),
        "history": training_history,
    }

    with open(os.path.join(output_dir, "training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(artifacts_trocr_dir, "training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"TrOCR TRAINING COMPLETE in {total_training_duration:.1f}s")
    print(f"Best Epoch: {best_epoch} (Val CER: {best_val_cer:.4f}, Val Loss: {best_val_loss:.4f})")
    print(f"Checkpoints saved to: {output_dir}")
    print("=" * 70 + "\n")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune TrOCR on RxHandBD")
    parser.add_argument("--dataset-dir", type=str, default=r"ml\prescription_ocr\data\raw\RxHandBD-ML", help="Path to RxHandBD-ML")
    parser.add_argument("--output-dir", type=str, default=r"ml\prescription_ocr\models", help="Output directory for best model")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--max-train-samples", type=int, default=None, help="Limit train samples")
    parser.add_argument("--max-val-samples", type=int, default=None, help="Limit validation samples")

    args = parser.parse_args()
    train_trocr(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        max_train_samples=args.max_train_samples,
        max_val_samples=args.max_val_samples,
    )
