"""PyTorch Dataset implementation for Prescription Medicine Region Detection.

Converts normalized YOLO labels to pixel bounding boxes [x1, y1, x2, y2]
with class label 1 (medicine) and 0 (background).
Includes conservative augmentations preserving handwriting orientation.
"""

import os
import glob
from typing import Dict, List, Tuple, Any, Optional, Callable
from PIL import Image, ImageEnhance
import torch
from torch.utils.data import Dataset
import torchvision.transforms.functional as TF

from ml.prescription_ocr.src.detector.utils import yolo_to_xyxy


class PrescriptionDetectorDataset(Dataset):
    """Dataset for training and evaluating Faster R-CNN on prescription layouts."""

    def __init__(
        self,
        images_dir: str,
        labels_dir: str,
        is_train: bool = False,
        target_size: Optional[Tuple[int, int]] = (1024, 1024),
    ):
        self.images_dir = images_dir
        self.labels_dir = labels_dir
        self.is_train = is_train
        self.target_size = target_size

        self.samples: List[Tuple[str, str, str]] = []
        self._load_and_validate_index()

    def _load_and_validate_index(self):
        """Verify image and label file pairing and validate annotations."""
        if not os.path.exists(self.images_dir) or not os.path.exists(self.labels_dir):
            raise FileNotFoundError(f"Dataset path not found: images={self.images_dir}, labels={self.labels_dir}")

        image_extensions = (".jpg", ".jpeg", ".png")
        image_files = sorted([
            f for f in os.listdir(self.images_dir)
            if f.lower().endswith(image_extensions) and not f.startswith(".")
        ])

        if len(image_files) == 0:
            raise ValueError(f"No images found in {self.images_dir}")

        for img_file in image_files:
            base_id = os.path.splitext(img_file)[0]
            label_file = f"{base_id}.txt"
            label_path = os.path.join(self.labels_dir, label_file)
            img_path = os.path.join(self.images_dir, img_file)

            if not os.path.exists(label_path):
                raise FileNotFoundError(f"Missing label file for image: {img_path} -> {label_path}")

            # Verify label content
            with open(label_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]

            if len(lines) == 0:
                raise ValueError(f"Label file has no annotations: {label_path}")

            for idx, line in enumerate(lines):
                tokens = line.split()
                if len(tokens) != 5:
                    raise ValueError(f"Invalid annotation in {label_path}:{idx} -> '{line}'")
                cls_id, xc, yc, bw, bh = tokens
                try:
                    xc, yc, bw, bh = float(xc), float(yc), float(bw), float(bh)
                except ValueError:
                    raise ValueError(f"Non-float coordinate in {label_path}:{idx} -> '{line}'")
                if bw <= 0.0 or bh <= 0.0:
                    raise ValueError(f"Zero or negative box dimension in {label_path}:{idx}")
                if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 <= bw <= 1.0 and 0.0 <= bh <= 1.0):
                    raise ValueError(f"Coordinate out of [0, 1] bounds in {label_path}:{idx}")

            self.samples.append((img_path, label_path, base_id))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        img_path, label_path, base_id = self.samples[idx]

        # 1. Load image
        img = Image.open(img_path).convert("RGB")
        orig_w, orig_h = img.size

        # 2. Parse YOLO labels to pixel boxes
        boxes: List[List[float]] = []
        labels: List[int] = []

        with open(label_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                _, xc, yc, bw, bh = map(float, line.split())
                x1, y1, x2, y2 = yolo_to_xyxy(xc, yc, bw, bh, orig_w, orig_h)
                # Ensure x2 > x1 and y2 > y1
                if x2 > x1 and y2 > y1:
                    boxes.append([x1, y1, x2, y2])
                    labels.append(1)  # Class 1 = medicine

        if not boxes:
            # Fallback tiny dummy box if none valid
            boxes = [[0.0, 0.0, 1.0, 1.0]]
            labels = [1]

        # 3. Resize image and scale bounding boxes
        if self.target_size is not None:
            new_w, new_h = self.target_size
            scale_x = new_w / orig_w
            scale_y = new_h / orig_h
            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

            scaled_boxes = []
            for b in boxes:
                sx1 = max(0.0, b[0] * scale_x)
                sy1 = max(0.0, b[1] * scale_y)
                sx2 = min(float(new_w), b[2] * scale_x)
                sy2 = min(float(new_h), b[3] * scale_y)
                scaled_boxes.append([sx1, sy1, sx2, sy2])
            boxes = scaled_boxes
            curr_w, curr_h = new_w, new_h
        else:
            curr_w, curr_h = orig_w, orig_h

        # 4. Conservative data augmentations for training
        if self.is_train:
            # Random slight brightness and contrast variation
            if torch.rand(1).item() > 0.5:
                enh_b = ImageEnhance.Brightness(img)
                factor_b = 0.85 + 0.30 * torch.rand(1).item()
                img = enh_b.enhance(factor_b)
            if torch.rand(1).item() > 0.5:
                enh_c = ImageEnhance.Contrast(img)
                factor_c = 0.85 + 0.30 * torch.rand(1).item()
                img = enh_c.enhance(factor_c)

        # 5. Convert to tensor (normalized to [0.0, 1.0])
        img_tensor = TF.to_tensor(img)

        boxes_tensor = torch.as_tensor(boxes, dtype=torch.float32)
        labels_tensor = torch.as_tensor(labels, dtype=torch.int64)

        # Compute area and iscrowd flags
        area = (boxes_tensor[:, 2] - boxes_tensor[:, 0]) * (boxes_tensor[:, 3] - boxes_tensor[:, 1])
        iscrowd = torch.zeros((len(boxes),), dtype=torch.int64)

        target = {
            "boxes": boxes_tensor,
            "labels": labels_tensor,
            "image_id": torch.tensor([idx]),
            "area": area,
            "iscrowd": iscrowd,
            "orig_size": torch.tensor([orig_h, orig_w]),
            "image_path": img_path,
            "base_id": base_id,
        }

        return img_tensor, target


def detection_collate_fn(batch: List[Tuple[torch.Tensor, Dict[str, Any]]]) -> Tuple[List[torch.Tensor], List[Dict[str, Any]]]:
    """Custom collate function for variable number of bounding boxes per image."""
    images = [item[0] for item in batch]
    targets = [item[1] for item in batch]
    return images, targets
