"""Inference pipeline for Faster R-CNN Prescription Medicine Region Detection.

Locates medicine entries on a full prescription image, applies confidence filtering
and Post-NMS suppression, sorts them in reading order, and computes expanded 8%
bounding boxes for downstream OCR cropping.
"""

import os
import sys
import argparse
from typing import Dict, List, Tuple, Any, Optional, Union
from PIL import Image, ImageDraw
import torch
import torchvision.transforms.functional as TF
import torchvision.ops as ops

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.detector.model import build_prescription_detector
from ml.prescription_ocr.src.detector.utils import expand_box_with_margin, sort_boxes_reading_order


class PrescriptionRegionDetector:
    """Inference engine for detecting medicine bounding boxes on full prescriptions."""

    _instance: Optional["PrescriptionRegionDetector"] = None

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        img_size: int = 640,
        default_confidence: float = 0.40,
        nms_iou_threshold: float = 0.35,
        device_str: Optional[str] = None,
    ):
        self.img_size = img_size
        self.default_confidence = default_confidence
        self.nms_iou_threshold = nms_iou_threshold

        if device_str:
            self.device = torch.device(device_str)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.checkpoint_path = checkpoint_path or self._resolve_default_checkpoint()
        self.model = None
        self._is_loaded = False
        self._load_model()

    @classmethod
    def get_instance(cls, checkpoint_path: Optional[str] = None) -> "PrescriptionRegionDetector":
        """Lazy singleton instance to avoid reloading detector weights."""
        if cls._instance is None or (checkpoint_path and cls._instance.checkpoint_path != checkpoint_path):
            cls._instance = cls(checkpoint_path=checkpoint_path)
        return cls._instance

    @staticmethod
    def _resolve_default_checkpoint() -> str:
        artifact_path = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "artifacts", "detector", "best_model.pth")
        return artifact_path

    def _load_model(self):
        """Load Faster R-CNN model weights."""
        try:
            self.model = build_prescription_detector(num_classes=2, pretrained_backbone=False)
            if os.path.exists(self.checkpoint_path):
                checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
                self.model.load_state_dict(checkpoint["model_state_dict"])
                self.model.to(self.device)
                self.model.eval()
                self._is_loaded = True
            else:
                self._is_loaded = False
        except Exception as e:
            self._is_loaded = False

    def predict(
        self,
        image_input: Union[Image.Image, str, bytes],
        confidence_threshold: Optional[float] = None,
        nms_iou_threshold: Optional[float] = None,
        crop_margin_ratio: float = 0.08,
    ) -> Dict[str, Any]:
        """
        Detect medicine regions on a full prescription image.
        
        Pipeline:
        Image -> Scale -> Forward Pass -> Confidence Filter -> NMS -> Reading Order Sort -> 8% Margin Expansion
        
        Returns:
            Dict containing:
                - total_detected: Count of detected regions after NMS
                - raw_detected_count: Count before NMS
                - regions: Sorted list of detected boxes with confidence and expanded crop boxes
                - image_dimensions: (orig_w, orig_h)
        """
        conf_thresh = confidence_threshold if confidence_threshold is not None else self.default_confidence
        nms_iou = nms_iou_threshold if nms_iou_threshold is not None else self.nms_iou_threshold

        # 1. Parse Image Input
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, bytes):
            import io
            img = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        else:
            raise TypeError("Unsupported image input type")

        orig_w, orig_h = img.size

        if not self._is_loaded or self.model is None:
            return {
                "total_detected": 0,
                "raw_detected_count": 0,
                "regions": [],
                "image_dimensions": (orig_w, orig_h),
                "status": "MODEL_UNAVAILABLE",
            }

        # 2. Preprocess & Scale
        resized_img = img.resize((self.img_size, self.img_size), Image.Resampling.BILINEAR)
        img_tensor = TF.to_tensor(resized_img).unsqueeze(0).to(self.device)

        scale_x = orig_w / self.img_size
        scale_y = orig_h / self.img_size

        # 3. Model Forward Pass
        with torch.no_grad():
            predictions = self.model(img_tensor)[0]

        boxes = predictions["boxes"].cpu()
        scores = predictions["scores"].cpu()
        labels = predictions["labels"].cpu()

        # 4. Confidence Filtering (label == 1: medicine)
        fg_mask = (labels == 1) & (scores >= conf_thresh)
        filtered_boxes = boxes[fg_mask]
        filtered_scores = scores[fg_mask]
        raw_count = len(filtered_boxes)

        if raw_count == 0:
            return {
                "total_detected": 0,
                "raw_detected_count": 0,
                "regions": [],
                "image_dimensions": (orig_w, orig_h),
                "confidence_threshold": conf_thresh,
                "nms_iou_threshold": nms_iou,
                "status": "SUCCESS",
            }

        # 5. Apply Non-Maximum Suppression (NMS)
        keep_indices = ops.nms(filtered_boxes, filtered_scores, iou_threshold=nms_iou)
        nms_boxes = filtered_boxes[keep_indices]
        nms_scores = filtered_scores[keep_indices]

        # 6. Map back to original image dimensions
        orig_boxes = []
        orig_scores = []
        for b, s in zip(nms_boxes, nms_scores):
            scaled_box = (
                b[0].item() * scale_x,
                b[1].item() * scale_y,
                b[2].item() * scale_x,
                b[3].item() * scale_y,
            )
            orig_boxes.append(scaled_box)
            orig_scores.append(float(s.item()))

        # 7. Sort in Top-to-Bottom Reading Order
        sorted_boxes, sorted_scores = sort_boxes_reading_order(
            orig_boxes,
            orig_scores,
            y_threshold=orig_h * 0.03,  # 3% of image height line grouping
        )

        # 8. Build Structured Region Output with 8% Crop Margin
        regions = []
        for rank, (box, score) in enumerate(zip(sorted_boxes, sorted_scores or []), 1):
            crop_box = expand_box_with_margin(box, orig_w, orig_h, margin_ratio=crop_margin_ratio)
            regions.append({
                "reading_order": rank,
                "box": [round(c, 1) for c in box],
                "crop_box": list(crop_box),
                "confidence": round(score, 4),
                "class_name": "medicine",
            })

        return {
            "total_detected": len(regions),
            "raw_detected_count": raw_count,
            "regions": regions,
            "image_dimensions": (orig_w, orig_h),
            "confidence_threshold": conf_thresh,
            "nms_iou_threshold": nms_iou,
            "status": "SUCCESS",
        }


def run_cli():
    parser = argparse.ArgumentParser(description="Inference for Prescription Medicine Region Detector")
    parser.add_argument("--image", type=str, required=True, help="Path to input prescription image")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to model checkpoint")
    parser.add_argument("--confidence", type=float, default=0.40, help="Confidence threshold (default: 0.40)")
    parser.add_argument("--nms-iou", type=float, default=0.35, help="NMS IoU threshold (default: 0.35)")
    parser.add_argument("--output-vis", type=str, default=None, help="Optional output visualization path")

    args = parser.parse_args()

    detector = PrescriptionRegionDetector(
        checkpoint_path=args.checkpoint,
        default_confidence=args.confidence,
        nms_iou_threshold=args.nms_iou,
    )

    result = detector.predict(
        args.image,
        confidence_threshold=args.confidence,
        nms_iou_threshold=args.nms_iou,
    )

    print("=" * 60)
    print(f"Raw detections before NMS:   {result['raw_detected_count']}")
    print(f"Final detections after NMS:  {result['total_detected']}")
    print("=" * 60)

    for r in result["regions"]:
        box = r["box"]
        crop = r["crop_box"]
        print(
            f"Region {r['reading_order']}: "
            f"x1={box[0]}, y1={box[1]}, x2={box[2]}, y2={box[3]} | "
            f"confidence={r['confidence']:.4f} | "
            f"crop_box={crop}"
        )

    if args.output_vis and os.path.exists(args.image):
        img = Image.open(args.image).convert("RGB")
        draw = ImageDraw.Draw(img)
        for r in result["regions"]:
            bx1, by1, bx2, by2 = map(int, r["box"])
            for offset in range(2):
                draw.rectangle([bx1 - offset, by1 - offset, bx2 + offset, by2 + offset], outline="red")
            draw.text((bx1 + 2, max(0, by1 - 12)), f"#{r['reading_order']} ({r['confidence']:.2f})", fill="red")
        img.save(args.output_vis, quality=90)
        print(f"\nVisualization saved to: {args.output_vis}")


if __name__ == "__main__":
    run_cli()
