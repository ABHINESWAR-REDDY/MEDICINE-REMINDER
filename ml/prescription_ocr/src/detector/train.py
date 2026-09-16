"""Training pipeline for Faster R-CNN Prescription Medicine Detector.

Trains on 140 train prescriptions and evaluates on 30 validation prescriptions.
Saves best_model.pth and latest_model.pth under ml/prescription_ocr/artifacts/detector/.
"""

import os
import sys
import time
import json
import argparse
from typing import Dict, List, Any, Optional
import torch
from torch.utils.data import DataLoader

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.detector.dataset import PrescriptionDetectorDataset, detection_collate_fn
from ml.prescription_ocr.src.detector.model import build_prescription_detector


def train_detector(
    dataset_dir: str,
    output_dir: str,
    epochs: int = 10,
    batch_size: int = 2,
    learning_rate: float = 0.0005,
    patience: int = 5,
    img_size: int = 800,
    device_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute training pipeline for the medicine region detector."""
    start_time = time.time()

    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 65)
    print("STAGE 2 MEDICINE REGION DETECTOR TRAINING")
    print("=" * 65)
    print(f"Device:            {device}")
    print(f"Model:             Faster R-CNN MobileNetV3-Large FPN")
    print(f"Classes:           1 Foreground (medicine) + 1 Background")
    print(f"Dataset Directory: {dataset_dir}")
    print(f"Target Resolution: {img_size}x{img_size}")
    print(f"Epochs:            {epochs}")
    print(f"Batch Size:        {batch_size}")
    print(f"Learning Rate:     {learning_rate}")
    print(f"Early Stopping:    Patience = {patience}")
    print("=" * 65)

    # 1. Load Train and Validation Datasets
    train_img_dir = os.path.join(dataset_dir, "train", "images")
    train_lbl_dir = os.path.join(dataset_dir, "train", "labels")
    val_img_dir = os.path.join(dataset_dir, "val", "images")
    val_lbl_dir = os.path.join(dataset_dir, "val", "labels")

    train_dataset = PrescriptionDetectorDataset(
        images_dir=train_img_dir,
        labels_dir=train_lbl_dir,
        is_train=True,
        target_size=(img_size, img_size),
    )
    val_dataset = PrescriptionDetectorDataset(
        images_dir=val_img_dir,
        labels_dir=val_lbl_dir,
        is_train=False,
        target_size=(img_size, img_size),
    )

    print(f"Train samples:     {len(train_dataset)} prescriptions")
    print(f"Val samples:       {len(val_dataset)} prescriptions")

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=detection_collate_fn,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=detection_collate_fn,
        num_workers=0,
    )

    # 2. Build Model
    model = build_prescription_detector(num_classes=2, pretrained_backbone=True)
    model.to(device)

    # 3. Optimizer & Scheduler
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=learning_rate, weight_decay=1e-4)
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    history = []

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()
        model.train()
        train_loss_accum = 0.0
        train_batches = 0

        for images, targets in train_loader:
            images = [img.to(device) for img in images]
            targets = [{k: (v.to(device) if isinstance(v, torch.Tensor) else v) for k, v in t.items()} for t in targets]

            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())

            optimizer.zero_grad()
            losses.backward()
            torch.nn.utils.clip_grad_norm_(params, max_norm=10.0)
            optimizer.step()

            train_loss_accum += losses.item()
            train_batches += 1

        avg_train_loss = train_loss_accum / max(1, train_batches)

        # Validation Loss (Faster R-CNN computes loss when targets are passed in training mode)
        val_loss_accum = 0.0
        val_batches = 0
        with torch.no_grad():
            for val_images, val_targets in val_loader:
                val_images = [img.to(device) for img in val_images]
                val_targets = [{k: (v.to(device) if isinstance(v, torch.Tensor) else v) for k, v in t.items()} for t in val_targets]

                val_loss_dict = model(val_images, val_targets)
                val_losses = sum(loss for loss in val_loss_dict.values())
                val_loss_accum += val_losses.item()
                val_batches += 1

        avg_val_loss = val_loss_accum / max(1, val_batches)
        lr_scheduler.step()
        epoch_duration = time.time() - epoch_start

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "val_loss": round(avg_val_loss, 4),
            "lr": round(optimizer.param_groups[0]["lr"], 6),
            "duration_sec": round(epoch_duration, 2),
        }
        history.append(epoch_record)

        print(
            f"Epoch [{epoch:02d}/{epochs:02d}] "
            f"Train Loss: {avg_train_loss:.4f} | "
            f"Val Loss: {avg_val_loss:.4f} | "
            f"Time: {epoch_duration:.1f}s"
        )

        # Save Latest Checkpoint
        latest_path = os.path.join(output_dir, "latest_model.pth")
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": avg_val_loss,
                "config": {
                    "num_classes": 2,
                    "img_size": img_size,
                },
            },
            latest_path,
        )

        # Save Best Checkpoint
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0
            best_path = os.path.join(output_dir, "best_model.pth")
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "val_loss": best_val_loss,
                    "config": {
                        "num_classes": 2,
                        "img_size": img_size,
                    },
                },
                best_path,
            )
            print(f"  --> Saved new best model checkpoint (Val Loss: {best_val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered after {epoch} epochs (patience={patience}).")
                break

    total_time = time.time() - start_time
    summary = {
        "model": "fasterrcnn_mobilenet_v3_large_fpn",
        "device": str(device),
        "total_epochs": epoch,
        "best_epoch": best_epoch,
        "best_val_loss": round(best_val_loss, 4),
        "final_train_loss": round(avg_train_loss, 4),
        "total_training_time_sec": round(total_time, 2),
        "history": history,
        "best_checkpoint": os.path.join(output_dir, "best_model.pth"),
        "latest_checkpoint": os.path.join(output_dir, "latest_model.pth"),
    }

    summary_path = os.path.join(output_dir, "training_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("=" * 65)
    print(f"TRAINING COMPLETE in {total_time:.1f}s. Best Epoch: {best_epoch} (Val Loss: {best_val_loss:.4f})")
    print(f"Checkpoints saved to: {output_dir}")
    print("=" * 65)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Faster R-CNN Prescription Medicine Detector")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size for training and validation")
    parser.add_argument("--lr", type=float, default=0.0005, help="Initial learning rate")
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience")
    parser.add_argument("--img-size", type=int, default=800, help="Target image dimension (square)")
    parser.add_argument("--dataset-dir", type=str, default=r"ml\prescription_ocr\data\detector", help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default=r"ml\prescription_ocr\artifacts\detector", help="Output directory")

    args = parser.parse_args()
    train_detector(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        patience=args.patience,
        img_size=args.img_size,
    )
