"""Unit and functional tests for Stage 2 Faster R-CNN Prescription Medicine Detector."""

import os
import sys
import tempfile
import pytest
import torch
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.detector.utils import (
    yolo_to_xyxy,
    xyxy_to_yolo,
    expand_box_with_margin,
    compute_box_iou,
    sort_boxes_reading_order,
)
from ml.prescription_ocr.src.detector.dataset import PrescriptionDetectorDataset, detection_collate_fn
from ml.prescription_ocr.src.detector.model import build_prescription_detector
from ml.prescription_ocr.src.detector.inference import PrescriptionRegionDetector


def test_yolo_to_xyxy_and_inverse_conversion():
    """Verify coordinate conversion between YOLO normalized and absolute pixel boxes."""
    img_w, img_h = 1000, 800
    xc, yc, w, h = 0.5, 0.4, 0.2, 0.1

    x1, y1, x2, y2 = yolo_to_xyxy(xc, yc, w, h, img_w, img_h)
    assert x1 == 400.0
    assert y1 == 280.0
    assert x2 == 600.0
    assert y2 == 360.0

    # Inverse
    r_xc, r_yc, r_w, r_h = xyxy_to_yolo(x1, y1, x2, y2, img_w, img_h)
    assert abs(r_xc - xc) < 1e-5
    assert abs(r_yc - yc) < 1e-5
    assert abs(r_w - w) < 1e-5
    assert abs(r_h - h) < 1e-5


def test_adaptive_8_percent_crop_margin_expansion():
    """Verify adaptive 8% margin expansion with boundary clamping."""
    img_w, img_h = 1000, 1000
    box = (100.0, 100.0, 200.0, 200.0)  # w=100, h=100 -> pad_x=8, pad_y=8
    cx1, cy1, cx2, cy2 = expand_box_with_margin(box, img_w, img_h, margin_ratio=0.08)

    assert cx1 == 92
    assert cy1 == 92
    assert cx2 == 208
    assert cy2 == 208

    # Edge clamping test
    edge_box = (2.0, 2.0, 50.0, 50.0)
    ecx1, ecy1, ecx2, ecy2 = expand_box_with_margin(edge_box, img_w, img_h, margin_ratio=0.08)
    assert ecx1 == 0  # Clamped to 0
    assert ecy1 == 0  # Clamped to 0


def test_sort_boxes_reading_order():
    """Verify that boxes are sorted top-to-bottom and left-to-right within lines."""
    boxes = [
        (100.0, 500.0, 200.0, 550.0),  # Line 2 (bottom)
        (300.0, 100.0, 400.0, 150.0),  # Line 1, right
        (100.0, 105.0, 200.0, 155.0),  # Line 1, left
    ]
    scores = [0.90, 0.85, 0.95]

    sorted_b, sorted_s = sort_boxes_reading_order(boxes, scores, y_threshold=20.0)

    # Expected: Line 1 left (100, 105), Line 1 right (300, 100), Line 2 (100, 500)
    assert sorted_b[0] == (100.0, 105.0, 200.0, 155.0)
    assert sorted_s[0] == 0.95
    assert sorted_b[1] == (300.0, 100.0, 400.0, 150.0)
    assert sorted_s[1] == 0.85
    assert sorted_b[2] == (100.0, 500.0, 200.0, 550.0)
    assert sorted_s[2] == 0.90


def test_compute_box_iou():
    """Verify IoU calculation for identical, disjoint, and partial boxes."""
    b1 = (0.0, 0.0, 10.0, 10.0)
    b2 = (0.0, 0.0, 10.0, 10.0)
    assert compute_box_iou(b1, b2) == 1.0

    b3 = (20.0, 20.0, 30.0, 30.0)
    assert compute_box_iou(b1, b3) == 0.0

    b4 = (5.0, 0.0, 15.0, 10.0)
    # intersection: 5x10 = 50, union: 100+100-50 = 150 -> 50/150 = 0.3333
    assert abs(compute_box_iou(b1, b4) - 0.333333) < 1e-4


def test_detector_dataset_loading_and_collate():
    """Verify loading from actual detector dataset with collate_fn."""
    dataset_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "data", "detector")
    train_img_dir = os.path.join(dataset_dir, "train", "images")
    train_lbl_dir = os.path.join(dataset_dir, "train", "labels")

    dataset = PrescriptionDetectorDataset(
        images_dir=train_img_dir,
        labels_dir=train_lbl_dir,
        is_train=True,
        target_size=(400, 400),
    )

    assert len(dataset) == 140
    img_tensor, target = dataset[0]

    assert img_tensor.shape == (3, 400, 400)
    assert "boxes" in target
    assert "labels" in target
    assert target["boxes"].shape[1] == 4
    assert (target["labels"] == 1).all()

    # Collate
    batch = [dataset[0], dataset[1]]
    images, targets = detection_collate_fn(batch)
    assert len(images) == 2
    assert len(targets) == 2


def test_invalid_annotation_handling_raises_error():
    """Verify that corrupt or out-of-bounds annotations raise ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_dir = os.path.join(tmpdir, "images")
        lbl_dir = os.path.join(tmpdir, "labels")
        os.makedirs(img_dir)
        os.makedirs(lbl_dir)

        # Create dummy image
        im = Image.new("RGB", (100, 100), "white")
        im.save(os.path.join(img_dir, "bad.jpg"))

        # Create corrupt label with 6 tokens
        with open(os.path.join(lbl_dir, "bad.txt"), "w") as f:
            f.write("0 0.5 0.5 0.2 0.2 0.999\n")

        with pytest.raises(ValueError):
            PrescriptionDetectorDataset(images_dir=img_dir, labels_dir=lbl_dir)


def test_detector_model_forward_pass():
    """Verify model instantiation, training mode loss computation, and eval mode prediction format."""
    model = build_prescription_detector(num_classes=2, pretrained_backbone=False)

    # 1. Training mode
    model.train()
    dummy_img = torch.rand(3, 400, 400)
    dummy_target = {
        "boxes": torch.tensor([[50.0, 50.0, 150.0, 150.0]], dtype=torch.float32),
        "labels": torch.tensor([1], dtype=torch.int64),
    }

    losses = model([dummy_img], [dummy_target])
    assert isinstance(losses, dict)
    assert "loss_classifier" in losses
    assert "loss_box_reg" in losses

    # 2. Eval mode
    model.eval()
    with torch.no_grad():
        preds = model([dummy_img])
    assert len(preds) == 1
    assert "boxes" in preds[0]
    assert "scores" in preds[0]
    assert "labels" in preds[0]
