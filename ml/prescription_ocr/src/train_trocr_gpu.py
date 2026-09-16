"""Full Fine-Tuning Pipeline for TrOCR Handwriting Recognition on RxHandBD on MX550 GPU.

Enforces:
- Deterministic 4,000 Train / 463 Validation split (RxHandBDAdapter)
- Official 1,115 Test samples strictly untouched
- MX550 2GB VRAM constraints (batch_size=1, grad_accum=8, num_workers=0, FP16, grad checkpointing)
- Epoch validation tracking (Val Loss, Val CER, Val WER, Val Exact Match)
- Safe checkpointing to ml/prescription_ocr/models/trocr_rxhandbd/
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
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    AdamW,
    get_cosine_schedule_with_warmup,
)

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


class TrOCRDataset(Dataset):
    def __init__(self, samples: List[Tuple[str, str]], images_dir: str, processor: TrOCRProcessor, max_target_length: int = 32):
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
            image = Image.new("RGB", (384, 384), color="white")

        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze(0)
        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=self.max_target_length,
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze(0)
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        return {"pixel_values": pixel_values, "labels": labels, "ground_truth": text}


def evaluate_on_val_set(model, processor, val_loader, device, max_eval_samples=463, cuda_available=False) -> Dict[str, float]:
    model.eval()
    total_val_loss = 0.0
    cer_list = []
    wer_list = []
    exact_matches = 0
    total_evaluated = 0

    with torch.no_grad():
        for step, batch in enumerate(val_loader):
            if step >= max_eval_samples:
                break
            pixel_values = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)
            gt_text = batch["ground_truth"][0]

            if cuda_available:
                with torch.cuda.amp.autocast():
                    outputs = model(pixel_values=pixel_values, labels=labels)
                    loss = outputs.loss
            else:
                outputs = model(pixel_values=pixel_values, labels=labels)
                loss = outputs.loss
            total_val_loss += loss.item()


            generated_ids = model.generate(pixel_values)
            pred_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            cer = compute_cer(gt_text, pred_text)
            wer = compute_wer(gt_text, pred_text)
            cer_list.append(cer)
            wer_list.append(wer)
            if gt_text.strip().lower() == pred_text.strip().lower():
                exact_matches += 1
            total_evaluated += 1

    model.train()
    avg_loss = total_val_loss / max(1, total_evaluated)
    avg_cer = sum(cer_list) / max(1, len(cer_list))
    avg_wer = sum(wer_list) / max(1, len(wer_list))
    exact_match_pct = (exact_matches / max(1, total_evaluated)) * 100.0

    return {
        "val_loss": round(avg_loss, 4),
        "val_cer": round(avg_cer, 4),
        "val_wer": round(avg_wer, 4),
        "val_exact_match_pct": round(exact_match_pct, 2),
        "samples_evaluated": total_evaluated,
    }


def train_trocr(
    epochs: int = 5,
    batch_size: int = 1,
    grad_accum_steps: int = 8,
    lr: float = 5e-5,
    max_train_samples: Optional[int] = None,
    output_dir: str = "ml/prescription_ocr/models/trocr_rxhandbd",
):
    print("==================================================")
    print("  TrOCR GPU FINE-TUNING: RxHandBD (PHASE 3)       ")
    print("==================================================")

    cuda_available = torch.cuda.is_available()
    if cuda_available:
        device = torch.device("cuda:0")
        device_name = torch.cuda.get_device_name(0)
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
        print(f"Device:                    {device_name} ({total_vram:.0f} MB VRAM)")
    else:
        device = torch.device("cpu")
        device_name = "CPU (Intel/AMD Host)"
        total_vram = 0.0
        print(f"Device:                    {device_name}")

    print(f"Batch Size:                {batch_size}")
    print(f"Grad Accumulation Steps:   {grad_accum_steps} (Effective Batch Size: {batch_size * grad_accum_steps})")
    print(f"Learning Rate:             {lr}")
    print(f"Epochs:                    {epochs}")

    # 2. Dataset Adapter Setup
    adapter = RxHandBDAdapter(data_root=os.path.join(PROJECT_ROOT, "DATA"))
    train_samples, val_samples, test_samples = adapter.load_splits(validate_images=True)

    if max_train_samples:
        train_samples = train_samples[:max_train_samples]

    print(f"\nDataset Splits:")
    print(f"  - Training:              {len(train_samples)} samples")
    print(f"  - Validation:            {len(val_samples)} samples")
    print(f"  - Official Test:         {len(test_samples)} samples (FROZEN & PROTECTED)")

    # 3. Model & Processor Setup
    model_name = "microsoft/trocr-small-handwritten"
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)

    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.config.eos_token_id = processor.tokenizer.sep_token_id

    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        print("Gradient Checkpointing:    ENABLED")

    model.to(device)
    model.train()

    train_dataset = TrOCRDataset(train_samples, adapter.images_dir, processor)
    val_dataset = TrOCRDataset(val_samples, adapter.images_dir, processor)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, num_workers=0)

    total_steps = (len(train_loader) // grad_accum_steps) * epochs
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=total_steps,
    )
    scaler = torch.cuda.amp.GradScaler() if cuda_available else None

    # 4. Training Loop
    target_output_dir = os.path.join(PROJECT_ROOT, output_dir)
    os.makedirs(target_output_dir, exist_ok=True)

    best_val_cer = 1.0
    history = []
    start_time = time.time()
    if cuda_available:
        torch.cuda.reset_peak_memory_stats()

    print("\n==================================================")
    print("Beginning Training...")
    print("==================================================")

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()
        running_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            pixel_values = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)

            if cuda_available:
                with torch.cuda.amp.autocast():
                    outputs = model(pixel_values=pixel_values, labels=labels)
                    loss = outputs.loss / grad_accum_steps
                scaler.scale(loss).backward()
                running_loss += loss.item() * grad_accum_steps

                if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad()
                    scheduler.step()
            else:
                outputs = model(pixel_values=pixel_values, labels=labels)
                loss = outputs.loss / grad_accum_steps
                loss.backward()
                running_loss += loss.item() * grad_accum_steps

                if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                    optimizer.step()
                    optimizer.zero_grad()
                    scheduler.step()


            if (step + 1) % 500 == 0:
                if cuda_available:
                    cur_vram = torch.cuda.memory_allocated() / (1024 * 1024)
                    peak_vram = torch.cuda.max_memory_allocated() / (1024 * 1024)
                    print(f"  Epoch {epoch}/{epochs} | Step {step+1}/{len(train_loader)} | Loss: {loss.item()*grad_accum_steps:.4f} | VRAM: {cur_vram:.0f}MB (Peak: {peak_vram:.0f}MB)")
                else:
                    print(f"  Epoch {epoch}/{epochs} | Step {step+1}/{len(train_loader)} | Loss: {loss.item()*grad_accum_steps:.4f}")

        train_loss = running_loss / len(train_loader)
        epoch_duration = time.time() - epoch_start

        # Validation Phase
        print(f"\nEvaluating Epoch {epoch} on {len(val_samples)} Validation Samples...")
        val_metrics = evaluate_on_val_set(model, processor, val_loader, device, cuda_available=cuda_available)

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": val_metrics["val_loss"],
            "val_cer": val_metrics["val_cer"],
            "val_wer": val_metrics["val_wer"],
            "val_exact_match_pct": val_metrics["val_exact_match_pct"],
            "duration_seconds": round(epoch_duration, 1),
        }
        history.append(epoch_record)

        print(f"Epoch {epoch}/{epochs} Summary ({epoch_duration:.1f}s):")
        print(f"  - Train Loss:      {train_loss:.4f}")
        print(f"  - Val Loss:        {val_metrics['val_loss']:.4f}")
        print(f"  - Val CER:         {val_metrics['val_cer']:.4f}")
        print(f"  - Val WER:         {val_metrics['val_wer']:.4f}")
        print(f"  - Val Exact Match: {val_metrics['val_exact_match_pct']:.2f}%")

        # Save Checkpoint if best Val CER
        if val_metrics["val_cer"] < best_val_cer:
            best_val_cer = val_metrics["val_cer"]
            print(f"  >>> New Best Model (Val CER: {best_val_cer:.4f})! Saving checkpoint...")
            model.save_pretrained(target_output_dir)
            processor.save_pretrained(target_output_dir)

    total_duration = time.time() - start_time
    peak_vram_final = (torch.cuda.max_memory_allocated() / (1024 * 1024)) if cuda_available else 0.0


    summary = {
        "status": "COMPLETED",
        "model_id": "trocr-rxhandbd-gpu",
        "base_model": model_name,
        "epochs": epochs,
        "batch_size": batch_size,
        "grad_accum_steps": grad_accum_steps,
        "learning_rate": lr,
        "train_samples": len(train_samples),
        "val_samples": len(val_samples),
        "best_val_cer": best_val_cer,
        "history": history,
        "peak_vram_mb": round(peak_vram_final, 1),
        "total_duration_seconds": round(total_duration, 1),
        "device": device_name,
    }

    with open(os.path.join(target_output_dir, "training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n==================================================")
    print(f"Training Complete! Total Time: {total_duration/60:.1f} minutes")
    print(f"Best Validation CER:       {best_val_cer:.4f}")
    print(f"Peak VRAM:                 {peak_vram_final:.1f} MB")
    print(f"Checkpoint saved at:       {target_output_dir}")
    print("==================================================")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max-train-samples", type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="ml/prescription_ocr/models/trocr_rxhandbd")
    args = parser.parse_args()

    train_trocr(
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum,
        lr=args.lr,
        max_train_samples=args.max_train_samples,
        output_dir=args.output_dir,
    )
