"""Inference engine for handwriting recognition on medical prescription images.

Provides programmatic Python interface and CLI entry point for single image
transcription with model confidence scoring (mean token softmax probabilities).
"""

import os
import sys
import argparse
import logging
import json
from typing import Dict, Any, Optional, Union
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from ml.prescription_ocr.src.preprocess import PrescriptionImagePreprocessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
)
logger = logging.getLogger("pillsync.ml.inference")


class HandwritingOCRInference:
    """Singleton-capable TrOCR inference pipeline for handwritten prescription words."""

    _instance: Optional["HandwritingOCRInference"] = None

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._resolve_model_path()
        self.preprocessor = PrescriptionImagePreprocessor()
        self.processor = None
        self.model = None
        self.device = "cpu"
        self._is_loaded = False
        self._load_model()

    @classmethod
    def get_instance(cls, model_path: Optional[str] = None) -> "HandwritingOCRInference":
        """Lazy singleton instance to avoid reloading heavy model on every request."""
        if cls._instance is None or (model_path and cls._instance.model_path != model_path):
            cls._instance = cls(model_path)
        return cls._instance

    @staticmethod
    def _resolve_model_path() -> str:
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
        config_path = os.path.join(local_dir, "config.json")
        if os.path.exists(config_path):
            return local_dir
        return "microsoft/trocr-small-handwritten"

    def _load_model(self):
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            logger.info("Loading TrOCR model from: %s", self.model_path)
            self.processor = TrOCRProcessor.from_pretrained(self.model_path)
            self.model = VisionEncoderDecoderModel.from_pretrained(self.model_path)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            self.model.eval()
            self._is_loaded = True
            logger.info("TrOCR handwriting inference engine initialized on [%s]", self.device)
        except Exception as e:
            logger.warning("TrOCR model unavailable for local inference (%s). Fallback mode active.", str(e))
            self._is_loaded = False

    def predict(
        self,
        image_input: Union[Image.Image, str, bytes],
        max_length: int = 64
    ) -> Dict[str, Any]:
        """
        Transcribe handwritten text from input image.

        Returns:
            Dict containing:
                - text: Transcribed clean text string
                - confidence_score: Float score [0.0 - 1.0] representing mean token softmax probability
                - confidence_level: 'HIGH' (>0.85), 'MEDIUM' (0.65-0.85), or 'LOW' (<0.65)
                - raw_text: Raw decoded output before whitespace normalization
                - details: Model metadata, device, and score definition
        """
        processed_img = self.preprocessor.preprocess(image_input)

        if not self._is_loaded or self.model is None or self.processor is None:
            return {
                "text": "",
                "confidence_score": 0.0,
                "confidence_level": "LOW",
                "raw_text": "",
                "details": {
                    "model": "unavailable",
                    "reason": "Handwriting ML model weights not loaded or PyTorch/transformers unavailable",
                    "device": self.device,
                }
            }

        try:
            import torch

            pixel_values = self.processor(processed_img, return_tensors="pt").pixel_values.to(self.device)

            with torch.no_grad():
                generated_outputs = self.model.generate(
                    pixel_values,
                    max_new_tokens=min(max_length, 25),
                    early_stopping=True,
                    num_beams=1,
                    return_dict_in_generate=True,
                    output_scores=True
                )


                transcription = self.processor.batch_decode(
                    generated_outputs.sequences,
                    skip_special_tokens=True
                )[0].strip()

                # Calculate model confidence score from token softmax probabilities
                confidence = 0.50
                if hasattr(generated_outputs, "scores") and generated_outputs.scores:
                    step_probs = [torch.softmax(s, dim=-1).max().item() for s in generated_outputs.scores]
                    if step_probs:
                        confidence = round(float(sum(step_probs) / len(step_probs)), 4)

            # Assign confidence tier based on uncalibrated softmax score thresholds
            if confidence >= 0.85:
                confidence_level = "HIGH"
            elif confidence >= 0.65:
                confidence_level = "MEDIUM"
            else:
                confidence_level = "LOW"

            return {
                "text": transcription,
                "confidence_score": confidence,
                "confidence": confidence,  # backwards compatibility alias
                "confidence_level": confidence_level,
                "raw_text": transcription,
                "details": {
                    "model": os.path.basename(self.model_path),
                    "device": self.device,
                    "target_size": self.preprocessor.target_size,
                    "score_description": "Model confidence score: Mean output token softmax probability over the generated sequence (uncalibrated).",
                }
            }

        except Exception as e:
            logger.error("Handwriting inference failure: %s", str(e), exc_info=True)
            return {
                "text": "",
                "confidence_score": 0.0,
                "confidence": 0.0,
                "confidence_level": "LOW",
                "raw_text": "",
                "error": str(e),
                "details": {
                    "model": os.path.basename(self.model_path),
                    "device": self.device,
                }
            }


def main():
    parser = argparse.ArgumentParser(description="Transcribe a handwritten medicine image using TrOCR")
    parser.add_argument("image_path", type=str, help="Path to handwritten image file")
    parser.add_argument("--model-path", type=str, default=None, help="Path to TrOCR model directory")
    args = parser.parse_args()

    if not os.path.exists(args.image_path):
        print(json.dumps({"error": f"Image file '{args.image_path}' not found."}))
        sys.exit(1)

    engine = HandwritingOCRInference.get_instance(args.model_path)
    result = engine.predict(args.image_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
