"""Utility functions for Prescription Medicine Region Detection.

Includes:
- Coordinate conversions (YOLO <-> [x1, y1, x2, y2])
- Adaptive crop margin expansion (8% ascender/descender preservation)
- Top-to-bottom reading-order sorting
- Intersection over Union (IoU) computation
"""

from typing import List, Tuple, Dict, Any, Optional
import torch
import numpy as np


def yolo_to_xyxy(
    xc: float,
    yc: float,
    w: float,
    h: float,
    img_w: int,
    img_h: int,
) -> Tuple[float, float, float, float]:
    """Convert normalized YOLO [xc, yc, w, h] to pixel coordinates [x1, y1, x2, y2]."""
    x1 = max(0.0, (xc - w / 2.0) * img_w)
    y1 = max(0.0, (yc - h / 2.0) * img_h)
    x2 = min(float(img_w), (xc + w / 2.0) * img_w)
    y2 = min(float(img_h), (yc + h / 2.0) * img_h)
    return x1, y1, x2, y2


def xyxy_to_yolo(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    img_w: int,
    img_h: int,
) -> Tuple[float, float, float, float]:
    """Convert pixel coordinates [x1, y1, x2, y2] to normalized YOLO [xc, yc, w, h]."""
    w = max(0.0, (x2 - x1) / img_w)
    h = max(0.0, (y2 - y1) / img_h)
    xc = (x1 + x2) / (2.0 * img_w)
    yc = (y1 + y2) / (2.0 * img_h)
    return xc, yc, w, h


def expand_box_with_margin(
    box: Tuple[float, float, float, float],
    img_w: int,
    img_h: int,
    margin_ratio: float = 0.08,
) -> Tuple[int, int, int, int]:
    """
    Expand bounding box by adaptive margin ratio (default 8%) to ensure
    handwriting ascenders and descenders are preserved without clipping.
    Clamps coordinates within image boundary [0, 0, img_w, img_h].
    """
    x1, y1, x2, y2 = box
    bw = x2 - x1
    bh = y2 - y1

    pad_x = bw * margin_ratio
    pad_y = bh * margin_ratio

    new_x1 = max(0, int(round(x1 - pad_x)))
    new_y1 = max(0, int(round(y1 - pad_y)))
    new_x2 = min(img_w, int(round(x2 + pad_x)))
    new_y2 = min(img_h, int(round(y2 + pad_y)))

    return new_x1, new_y1, new_x2, new_y2


def compute_box_iou(
    box1: Tuple[float, float, float, float],
    box2: Tuple[float, float, float, float],
) -> float:
    """Calculate Intersection over Union (IoU) between two [x1, y1, x2, y2] boxes."""
    x1_i = max(box1[0], box2[0])
    y1_i = max(box1[1], box2[1])
    x2_i = min(box1[2], box2[2])
    y2_i = min(box1[3], box2[3])

    inter_w = max(0.0, x2_i - x1_i)
    inter_h = max(0.0, y2_i - y1_i)
    inter_area = inter_w * inter_h

    area1 = max(0.0, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    area2 = max(0.0, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    union_area = area1 + area2 - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def sort_boxes_reading_order(
    boxes: List[Tuple[float, float, float, float]],
    scores: Optional[List[float]] = None,
    y_threshold: float = 20.0,
) -> Tuple[List[Tuple[float, float, float, float]], Optional[List[float]]]:
    """
    Sort bounding boxes in natural prescription reading order (top-to-bottom, left-to-right).
    Groups boxes on the same line if their y_centers differ by less than y_threshold.
    """
    if not boxes:
        return [], (scores if scores is not None else None)

    items = []
    for idx, b in enumerate(boxes):
        s = scores[idx] if scores is not None and idx < len(scores) else 1.0
        yc = (b[1] + b[3]) / 2.0
        xc = (b[0] + b[2]) / 2.0
        items.append((yc, xc, b, s))

    # Sort primarily by y-center
    items.sort(key=lambda item: item[0])

    # Cluster into horizontal lines
    lines = []
    current_line = []
    current_y = None

    for item in items:
        yc, xc, box, score = item
        if current_y is None or abs(yc - current_y) <= y_threshold:
            current_line.append(item)
            current_y = yc if current_y is None else (current_y + yc) / 2.0
        else:
            # Sort current line left to right by x-center
            current_line.sort(key=lambda it: it[1])
            lines.extend(current_line)
            current_line = [item]
            current_y = yc

    if current_line:
        current_line.sort(key=lambda it: it[1])
        lines.extend(current_line)

    sorted_boxes = [item[2] for item in lines]
    sorted_scores = [item[3] for item in lines] if scores is not None else None

    return sorted_boxes, sorted_scores
