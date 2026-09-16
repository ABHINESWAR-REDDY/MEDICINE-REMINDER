"""Stage 2 Prescription Medicine Region Detector Package."""

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

__all__ = [
    "yolo_to_xyxy",
    "xyxy_to_yolo",
    "expand_box_with_margin",
    "compute_box_iou",
    "sort_boxes_reading_order",
    "PrescriptionDetectorDataset",
    "detection_collate_fn",
    "build_prescription_detector",
    "PrescriptionRegionDetector",
]
