"""Faster R-CNN MobileNetV3-Large FPN Model Architecture for Prescription Medicine Detection.

Uses torchvision (BSD-3-Clause license) with a single foreground class: 'medicine'.
num_classes = 2 (0: background, 1: medicine).
"""

from typing import Optional
import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection import (
    fasterrcnn_mobilenet_v3_large_fpn,
    FasterRCNN_MobileNet_V3_Large_FPN_Weights,
)


def build_prescription_detector(
    num_classes: int = 2,
    pretrained_backbone: bool = True,
    trainable_backbone_layers: int = 3,
) -> torchvision.models.detection.FasterRCNN:
    """
    Build Faster R-CNN model with MobileNetV3-Large FPN backbone.
    
    Args:
        num_classes: Number of classes including background (default: 2 -> 0: bg, 1: medicine)
        pretrained_backbone: Whether to use ImageNet pretrained backbone weights
        trainable_backbone_layers: Number of trainable backbone blocks (default: 3)
        
    Returns:
        Configured FasterRCNN model.
    """
    if pretrained_backbone:
        try:
            weights = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT
            model = fasterrcnn_mobilenet_v3_large_fpn(
                weights=weights,
                trainable_backbone_layers=trainable_backbone_layers,
            )
        except Exception:
            # Fallback if offline / weights unavailable
            model = fasterrcnn_mobilenet_v3_large_fpn(
                weights=None,
                weights_backbone="DEFAULT",
                trainable_backbone_layers=trainable_backbone_layers,
            )
    else:
        model = fasterrcnn_mobilenet_v3_large_fpn(
            weights=None,
            weights_backbone=None,
            trainable_backbone_layers=trainable_backbone_layers,
        )

    # Replace the classification head for 2 classes (background + medicine)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    return model
