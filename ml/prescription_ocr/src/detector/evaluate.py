"""Evaluation pipeline for Faster R-CNN Prescription Medicine Detector with Post-NMS.

Evaluates on the 30 untouched test prescriptions (165 ground-truth medicine boxes).
Calculates:
- Precision, Recall, Mean IoU on hits, F1 score across confidence thresholds (0.30, 0.40, 0.50, 0.60, 0.70)
- mAP@50 and mAP@50:95 across IoU thresholds 0.50 to 0.95 (step 0.05)
- Raw vs Post-NMS detection counts
- False positives, False negatives (missed), and average detections per prescription
- Generates 10+ visual comparison artifacts with ground truth (green) vs predictions (red).
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image, ImageDraw
import torch
import torchvision.ops as ops
from torch.utils.data import DataLoader

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.prescription_ocr.src.detector.dataset import PrescriptionDetectorDataset, detection_collate_fn
from ml.prescription_ocr.src.detector.model import build_prescription_detector
from ml.prescription_ocr.src.detector.utils import compute_box_iou, sort_boxes_reading_order


def compute_ap(recalls: List[float], precisions: List[float]) -> float:
    """Compute Average Precision using 11-point interpolation or area under PR curve."""
    if not recalls or not precisions:
        return 0.0
    mrec = [0.0] + recalls + [1.0]
    mpre = [0.0] + precisions + [0.0]

    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])

    ap = 0.0
    for i in range(len(mrec) - 1):
        if mrec[i + 1] != mrec[i]:
            ap += (mrec[i + 1] - mrec[i]) * mpre[i + 1]
    return ap


def evaluate_detector(
    checkpoint_path: str,
    dataset_dir: str,
    output_dir: str,
    img_size: int = 640,
    nms_iou_threshold: float = 0.35,
    confidence_thresholds: List[float] = [0.30, 0.40, 0.50, 0.60, 0.70],
    num_visualizations: int = 10,
    device_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Run full evaluation suite on test dataset with Post-NMS."""
    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    vis_dir = os.path.join(output_dir, "visualizations")
    os.makedirs(vis_dir, exist_ok=True)

    print("=" * 65)
    print("STAGE 2 DETECTOR EVALUATION ON UNTOUCHED TEST SET")
    print("=" * 65)
    print(f"Checkpoint:      {checkpoint_path}")
    print(f"Device:          {device}")
    print(f"NMS IoU Filter:  {nms_iou_threshold}")
    print("=" * 65)

    # 1. Load Model
    model = build_prescription_detector(num_classes=2, pretrained_backbone=False)
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    # 2. Load Test Dataset
    test_img_dir = os.path.join(dataset_dir, "test", "images")
    test_lbl_dir = os.path.join(dataset_dir, "test", "labels")

    test_dataset = PrescriptionDetectorDataset(
        images_dir=test_img_dir,
        labels_dir=test_lbl_dir,
        is_train=False,
        target_size=(img_size, img_size),
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=detection_collate_fn,
        num_workers=0,
    )

    print(f"Loaded {len(test_dataset)} test prescriptions.")

    all_gt_boxes: List[List[List[float]]] = []
    all_raw_pred_boxes: List[List[List[float]]] = []
    all_raw_pred_scores: List[List[float]] = []
    all_nms_pred_boxes: List[List[List[float]]] = []
    all_nms_pred_scores: List[List[float]] = []
    all_sample_metadata: List[Dict[str, Any]] = []

    with torch.no_grad():
        for images, targets in test_loader:
            images = [img.to(device) for img in images]
            predictions = model(images)

            for target, pred in zip(targets, predictions):
                gt_b = target["boxes"].cpu().numpy().tolist()
                orig_h, orig_w = target["orig_size"].cpu().numpy().tolist()
                scale_x = orig_w / img_size
                scale_y = orig_h / img_size

                # Map GT back to original pixel coordinates
                orig_gt_b = [[b[0] * scale_x, b[1] * scale_y, b[2] * scale_x, b[3] * scale_y] for b in gt_b]
                all_gt_boxes.append(orig_gt_b)

                # Predictions
                p_boxes = pred["boxes"].cpu()
                p_scores = pred["scores"].cpu()
                p_labels = pred["labels"].cpu()

                # Filter foreground (label == 1)
                fg_mask = (p_labels == 1)
                fg_boxes = p_boxes[fg_mask]
                fg_scores = p_scores[fg_mask]

                # Raw predictions scaled
                raw_scaled_b = [
                    [b[0].item() * scale_x, b[1].item() * scale_y, b[2].item() * scale_x, b[3].item() * scale_y]
                    for b in fg_boxes
                ]
                raw_s = [float(s.item()) for s in fg_scores]
                all_raw_pred_boxes.append(raw_scaled_b)
                all_raw_pred_scores.append(raw_s)

                # Apply Post-NMS
                if len(fg_boxes) > 0:
                    keep = ops.nms(fg_boxes, fg_scores, iou_threshold=nms_iou_threshold)
                    nms_fg_b = fg_boxes[keep]
                    nms_fg_s = fg_scores[keep]
                    nms_scaled_b = [
                        [b[0].item() * scale_x, b[1].item() * scale_y, b[2].item() * scale_x, b[3].item() * scale_y]
                        for b in nms_fg_b
                    ]
                    nms_s = [float(s.item()) for s in nms_fg_s]
                else:
                    nms_scaled_b = []
                    nms_s = []

                all_nms_pred_boxes.append(nms_scaled_b)
                all_nms_pred_scores.append(nms_s)

                all_sample_metadata.append({
                    "image_path": target["image_path"],
                    "base_id": target["base_id"],
                    "orig_size": (orig_w, orig_h),
                })

    # 3. Compute Metrics Across Confidence Thresholds
    threshold_metrics = {}
    total_gt_boxes_count = sum(len(gts) for gts in all_gt_boxes)
    total_raw_proposals = sum(len(r) for r in all_raw_pred_boxes)
    total_nms_proposals = sum(len(n) for n in all_nms_pred_boxes)

    for conf_thresh in confidence_thresholds:
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_detected_conf = 0
        matched_ious = []

        for gt_boxes, pred_boxes, pred_scores in zip(all_gt_boxes, all_nms_pred_boxes, all_nms_pred_scores):
            # Filter by confidence threshold
            active_preds = [b for b, s in zip(pred_boxes, pred_scores) if s >= conf_thresh]
            total_detected_conf += len(active_preds)

            gt_matched = [False] * len(gt_boxes)
            pred_matched = [False] * len(active_preds)

            for p_idx, p_box in enumerate(active_preds):
                best_iou = 0.0
                best_gt_idx = -1
                for g_idx, g_box in enumerate(gt_boxes):
                    if not gt_matched[g_idx]:
                        iou = compute_box_iou(p_box, g_box)
                        if iou > best_iou:
                            best_iou = iou
                            best_gt_idx = g_idx

                if best_iou >= 0.50 and best_gt_idx >= 0:
                    total_tp += 1
                    gt_matched[best_gt_idx] = True
                    pred_matched[p_idx] = True
                    matched_ious.append(best_iou)
                else:
                    total_fp += 1

            total_fn += (len(gt_boxes) - sum(gt_matched))

        precision = total_tp / max(1, total_tp + total_fp)
        recall = total_tp / max(1, total_tp + total_fn)
        mean_iou = sum(matched_ious) / max(1, len(matched_ious))
        f1_score = (2 * precision * recall) / max(1e-6, precision + recall)

        threshold_metrics[f"confidence_{conf_thresh:.2f}"] = {
            "confidence_threshold": conf_thresh,
            "total_detections": total_detected_conf,
            "avg_detections_per_image": round(total_detected_conf / len(test_dataset), 2),
            "true_positives": total_tp,
            "false_positives": total_fp,
            "false_negatives (missed)": total_fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "mean_iou_on_hits": round(mean_iou, 4),
        }

    # 4. Compute mAP@50 and mAP@50:95 across IoU range [0.50, 0.95]
    iou_eval_thresholds = [round(0.50 + i * 0.05, 2) for i in range(10)]
    ap_per_iou = []

    for iou_t in iou_eval_thresholds:
        # Collect all predictions and scores across the dataset
        all_eval_items = []
        for img_idx, (p_boxes, p_scores) in enumerate(zip(all_nms_pred_boxes, all_nms_pred_scores)):
            for b, s in zip(p_boxes, p_scores):
                all_eval_items.append((s, img_idx, b))

        # Sort all predictions by score descending
        all_eval_items.sort(key=lambda x: x[0], reverse=True)

        gt_matched_map = {idx: [False] * len(all_gt_boxes[idx]) for idx in range(len(all_gt_boxes))}
        tps = []
        fps = []

        for score, img_idx, p_box in all_eval_items:
            img_gts = all_gt_boxes[img_idx]
            best_iou = 0.0
            best_gt_i = -1

            for g_i, g_box in enumerate(img_gts):
                if not gt_matched_map[img_idx][g_i]:
                    iou = compute_box_iou(p_box, g_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_i = g_i

            if best_iou >= iou_t and best_gt_i >= 0:
                tps.append(1)
                fps.append(0)
                gt_matched_map[img_idx][best_gt_i] = True
            else:
                tps.append(0)
                fps.append(1)

        # Cumulative sums
        cum_tp = 0
        cum_fp = 0
        prec_curve = []
        rec_curve = []

        for tp, fp in zip(tps, fps):
            cum_tp += tp
            cum_fp += fp
            prec_curve.append(cum_tp / (cum_tp + cum_fp))
            rec_curve.append(cum_tp / max(1, total_gt_boxes_count))

        ap = compute_ap(rec_curve, prec_curve)
        ap_per_iou.append(ap)

    map50 = ap_per_iou[0]
    map50_95 = sum(ap_per_iou) / len(ap_per_iou)

    # 5. Generate Visualizations for 10 test prescriptions
    print(f"Generating visual evaluation artifacts for {min(num_visualizations, len(all_sample_metadata))} prescriptions...")
    for idx in range(min(num_visualizations, len(all_sample_metadata))):
        meta = all_sample_metadata[idx]
        img_p = meta["image_path"]
        base_id = meta["base_id"]
        gt_boxes = all_gt_boxes[idx]
        pred_boxes = all_nms_pred_boxes[idx]
        pred_scores = all_nms_pred_scores[idx]

        img = Image.open(img_p).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Draw Ground Truth in Green
        for g_box in gt_boxes:
            gx1, gy1, gx2, gy2 = map(int, g_box)
            for offset in range(3):
                draw.rectangle([gx1 - offset, gy1 - offset, gx2 + offset, gy2 + offset], outline="green")
            draw.text((gx1 + 2, max(0, gy1 - 12)), "GT Medicine", fill="green")

        # Draw NMS Predictions (>= 0.35 confidence) in Red
        filtered_p = [b for b, s in zip(pred_boxes, pred_scores) if s >= 0.35]
        filtered_s = [s for s in pred_scores if s >= 0.35]
        sorted_preds, sorted_scs = sort_boxes_reading_order(filtered_p, filtered_s)

        for rank, (p_box, score) in enumerate(zip(sorted_preds, sorted_scs or []), 1):
            px1, py1, px2, py2 = map(int, p_box)
            for offset in range(2):
                draw.rectangle([px1 - offset, py1 - offset, px2 + offset, py2 + offset], outline="red")
            draw.text((px1 + 2, max(0, py1 - 12)), f"#{rank} ({score:.2f})", fill="red")

        out_vis_path = os.path.join(vis_dir, f"test_eval_{idx+1}_rx_{base_id}.jpg")
        img.save(out_vis_path, quality=90)

    # 6. Save Full Evaluation Report
    eval_summary = {
        "model": "Faster R-CNN MobileNetV3-Large FPN",
        "num_test_prescriptions": len(test_dataset),
        "total_ground_truth_boxes": total_gt_boxes_count,
        "raw_proposals_total": total_raw_proposals,
        "post_nms_proposals_total": total_nms_proposals,
        "nms_suppression_ratio": round((total_raw_proposals - total_nms_proposals) / max(1, total_raw_proposals), 4),
        "mAP@50": round(map50, 4),
        "mAP@50:95": round(map50_95, 4),
        "metrics_by_threshold": threshold_metrics,
        "visualizations_directory": vis_dir,
    }

    report_path = os.path.join(output_dir, "evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print("\n" + "=" * 65)
    print("DETECTOR TEST EVALUATION SUMMARY (WITH POST-NMS):")
    print("=" * 65)
    print(f"Total Test Prescriptions:   {len(test_dataset)}")
    print(f"Total Ground Truth Boxes:   {total_gt_boxes_count}")
    print(f"Raw Proposals Generated:    {total_raw_proposals}")
    print(f"Post-NMS Proposals:         {total_nms_proposals} (Suppressed {total_raw_proposals - total_nms_proposals} redundant overlapping boxes)")
    print(f"mAP@50:                     {map50*100:.2f}%")
    print(f"mAP@50:95:                  {map50_95*100:.2f}%")
    print("-" * 65)
    for conf_key, m in threshold_metrics.items():
        print(
            f"Confidence >= {m['confidence_threshold']:.2f} -> "
            f"Precision: {m['precision']*100:.1f}% | "
            f"Recall: {m['recall']*100:.1f}% | "
            f"Mean IoU: {m['mean_iou_on_hits']:.3f} | "
            f"Avg Detections/Rx: {m['avg_detections_per_image']} | "
            f"TP: {m['true_positives']}, FP: {m['false_positives']}, FN: {m['false_negatives (missed)']}"
        )
    print("=" * 65 + "\n")

    return eval_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Prescription Medicine Region Detector with NMS")
    parser.add_argument("--checkpoint", type=str, default=r"ml\prescription_ocr\artifacts\detector\best_model.pth", help="Path to checkpoint")
    parser.add_argument("--dataset-dir", type=str, default=r"ml\prescription_ocr\data\detector", help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default=r"ml\prescription_ocr\artifacts\detector\evaluation", help="Evaluation output directory")
    parser.add_argument("--img-size", type=int, default=640, help="Image size")
    parser.add_argument("--nms-iou", type=float, default=0.35, help="NMS IoU threshold")
    parser.add_argument("--num-vis", type=int, default=10, help="Number of visual evaluations to save")

    args = parser.parse_args()
    evaluate_detector(
        checkpoint_path=args.checkpoint,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        img_size=args.img_size,
        nms_iou_threshold=args.nms_iou,
        num_visualizations=args.num_vis,
    )
