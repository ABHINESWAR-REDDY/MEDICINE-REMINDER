"""OCR Provider Architecture for PillSync Phase 3.

Provides an extensible abstraction layer separating:
- TesseractProvider (Printed / clear structured text)
- HandwritingOCRProvider (TrOCR / ML handwriting recognition)
- PrescriptionDetectorProvider (Stage 2 Faster R-CNN medicine region detector)
- CompositeOCRProvider (Multi-stage detection -> crop -> TrOCR -> printed fusion)
"""

import os
import sys
import io
import shutil
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Tuple
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError
from app.core.logging import logger

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))




class OCREngineError(Exception):
    """Raised when OCR engine encounters an unrecoverable failure."""
    def __init__(self, message: str = "OCR engine failed to process document.", code: str = "OCR_ENGINE_FAILURE"):
        super().__init__(message)
        self.code = code
        self.message = message


class PDFProcessingError(Exception):
    """Raised when PDF document parsing or rendering fails."""
    def __init__(self, message: str = "Unable to read or parse PDF document.", code: str = "PDF_PROCESSING_FAILURE"):
        super().__init__(message)
        self.code = code
        self.message = message


class BaseOCRProvider(ABC):
    """Abstract interface for all OCR/HTR recognition engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider dependencies and binaries/weights are available."""
        pass

    @abstractmethod
    def extract_text(self, file_bytes: bytes, content_type: str) -> str:
        """Extract text from file bytes (image or PDF)."""
        pass


class TesseractProvider(BaseOCRProvider):
    """Primary OCR provider for printed text and documents using Tesseract & WinOCR fallback."""

    def __init__(self):
        self._tesseract_available = False
        self._configure_tesseract()

    @property
    def name(self) -> str:
        return "tesseract"

    def _configure_tesseract(self):
        try:
            import pytesseract

            which_path = shutil.which("tesseract")
            if which_path:
                self._tesseract_available = True
                pytesseract.pytesseract.tesseract_cmd = which_path
                return

            env_cmd = os.environ.get("TESSERACT_CMD")
            if env_cmd and os.path.exists(env_cmd):
                self._tesseract_available = True
                pytesseract.pytesseract.tesseract_cmd = env_cmd
                return

            if sys.platform == "win32":
                windows_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
                ]
                for path in windows_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        self._tesseract_available = True
                        return
        except ImportError:
            self._tesseract_available = False

    def is_available(self) -> bool:
        return self._tesseract_available or sys.platform == "win32"

    def extract_text(self, file_bytes: bytes, content_type: str) -> str:
        """Process image or PDF bytes via Tesseract."""
        content_type_clean = content_type.lower().strip()
        if "pdf" in content_type_clean:
            return self._extract_from_pdf(file_bytes)
        return self._extract_from_image(file_bytes)

    def _extract_from_image(self, image_bytes: bytes) -> str:
        import pytesseract

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except UnidentifiedImageError:
            raise ValueError("Uploaded file is not a valid or readable image.")
        except Exception as e:
            raise ValueError(f"Could not read image file: {str(e)}")

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        gray = image.convert("L")
        enhanced = ImageEnhance.Contrast(gray).enhance(1.8)
        processed_img = enhanced.filter(ImageFilter.SHARPEN)

        if self._tesseract_available:
            try:
                text = pytesseract.image_to_string(processed_img, config="--psm 6")
                if not text.strip():
                    text = pytesseract.image_to_string(processed_img, config="--psm 3")
                if text.strip():
                    return text.strip()
            except Exception as e:
                logger.warning("Tesseract execution exception: %s", str(e))

        # Windows Native OCR fallback
        if sys.platform == "win32":
            try:
                import winocr

                result = winocr.recognize_pil_sync(processed_img, "en")
                extracted = (result.get("text", "") if isinstance(result, dict) else getattr(result, "text", "") or "").strip()
                if extracted:
                    return extracted
            except Exception as e:
                logger.warning("WinOCR fallback exception: %s", str(e))

        if not self._tesseract_available and sys.platform != "win32":
            raise OCREngineError("OCR Engine (Tesseract) is not installed or configured on the server.")

        return ""

    def _extract_from_pdf(self, pdf_bytes: bytes) -> str:
        import pymupdf

        extracted_texts: List[str] = []
        doc = None
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            for page_index in range(len(doc)):
                page = doc[page_index]
                direct_text = page.get_text().strip()
                if direct_text and len(direct_text) > 20:
                    extracted_texts.append(direct_text)
                    continue

                zoom = 300 / 72
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
                page_text = self._extract_from_image(pix.tobytes("png"))
                if page_text:
                    extracted_texts.append(page_text)

            return "\n\n".join(extracted_texts).strip()
        except (ValueError, OCREngineError):
            raise
        except Exception as e:
            raise PDFProcessingError(f"Unable to read or process PDF document: {str(e)}")
        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass


class HandwritingOCRProvider(BaseOCRProvider):
    """
    Handwriting Text Recognition (HTR) provider utilizing TrOCR.
    Uses lazy-singleton loading to prevent reloading the model on every API request.
    """

    _inference_engine = None

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._ensure_engine()

    @property
    def name(self) -> str:
        return "handwriting_trocr"

    def _ensure_engine(self):
        if HandwritingOCRProvider._inference_engine is None:
            try:
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)

                from ml.prescription_ocr.src.inference import HandwritingOCRInference
                HandwritingOCRProvider._inference_engine = HandwritingOCRInference.get_instance(self.model_path)
            except Exception as e:
                logger.warning("Could not initialize HandwritingOCRInference: %s", str(e))
                HandwritingOCRProvider._inference_engine = None

    def is_available(self) -> bool:
        self._ensure_engine()
        return (
            HandwritingOCRProvider._inference_engine is not None
            and HandwritingOCRProvider._inference_engine._is_loaded
        )

    def extract_text(self, file_bytes: Union[bytes, Image.Image], content_type: str = "image/png") -> str:
        """Transcribe handwritten text from image patch."""
        self._ensure_engine()
        if not self.is_available() or HandwritingOCRProvider._inference_engine is None:
            logger.warning("Handwriting OCR provider is not available. Falling back to empty text.")
            return ""

        try:
            result = HandwritingOCRProvider._inference_engine.predict(file_bytes)
            return result.get("text", "")
        except Exception as e:
            logger.error("Handwriting provider inference failed: %s", str(e), exc_info=True)
            return ""

    def predict_with_confidence(self, image_input: Union[bytes, Image.Image]) -> Dict[str, Any]:
        """Transcribe and return text with model confidence score."""
        self._ensure_engine()
        if not self.is_available() or HandwritingOCRProvider._inference_engine is None:
            return {"text": "", "confidence_score": 0.0, "confidence_level": "LOW", "raw_text": ""}
        return HandwritingOCRProvider._inference_engine.predict(image_input)


class PrescriptionDetectorProvider:
    """
    Stage 2 Medicine Region Detector provider wrapping Faster R-CNN MobileNetV3.
    """

    _detector_instance = None

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        nms_iou_threshold: Optional[float] = None,
        crop_margin_ratio: Optional[float] = None,
    ):
        self.confidence_threshold = confidence_threshold or float(os.environ.get("DETECTOR_CONFIDENCE", "0.40"))
        self.nms_iou_threshold = nms_iou_threshold or float(os.environ.get("DETECTOR_NMS_IOU", "0.35"))
        self.crop_margin_ratio = crop_margin_ratio or float(os.environ.get("DETECTOR_CROP_MARGIN", "0.08"))

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        default_ckpt = os.path.join(root_dir, "ml", "prescription_ocr", "artifacts", "detector", "best_model.pth")
        self.checkpoint_path = checkpoint_path or os.environ.get("DETECTOR_CHECKPOINT_PATH", default_ckpt)
        self._ensure_detector()

    def _ensure_detector(self):
        if PrescriptionDetectorProvider._detector_instance is None:
            try:
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)

                from ml.prescription_ocr.src.detector.inference import PrescriptionRegionDetector
                PrescriptionDetectorProvider._detector_instance = PrescriptionRegionDetector.get_instance(
                    checkpoint_path=self.checkpoint_path,
                )
            except Exception as e:
                logger.warning("Could not initialize PrescriptionRegionDetector: %s", str(e))
                PrescriptionDetectorProvider._detector_instance = None

    def is_available(self) -> bool:
        self._ensure_detector()
        return (
            PrescriptionDetectorProvider._detector_instance is not None
            and PrescriptionDetectorProvider._detector_instance._is_loaded
        )

    def detect_regions(self, image_input: Union[bytes, Image.Image, str]) -> Dict[str, Any]:
        """Detect medicine regions on prescription with adaptive multi-thresholding."""
        self._ensure_detector()
        if not self.is_available() or PrescriptionDetectorProvider._detector_instance is None:
            return {"total_detected": 0, "regions": [], "status": "UNAVAILABLE"}

        # Adaptive thresholding: try primary threshold, then fallback to sensitive thresholds
        candidate_thresholds = [self.confidence_threshold]
        for t in [0.20, 0.12]:
            if t < self.confidence_threshold:
                candidate_thresholds.append(t)

        last_result = {"total_detected": 0, "regions": [], "status": "NO_DETECTIONS"}
        for threshold in candidate_thresholds:
            result = PrescriptionDetectorProvider._detector_instance.predict(
                image_input,
                confidence_threshold=threshold,
                nms_iou_threshold=self.nms_iou_threshold,
                crop_margin_ratio=self.crop_margin_ratio,
            )
            if len(result.get("regions", [])) > 0:
                return result
            last_result = result

        return last_result


class CompositeOCRProvider(BaseOCRProvider):
    """
    Coordinated multi-stage prescription OCR provider:
    Stage 1: Preprocessing ->
    Stage 2: Faster R-CNN Medicine Region Detector (Adaptive Thresholds) ->
    NMS & 8% Adaptive Crop ->
    Stage 3: TrOCR Handwritten Text Recognition on enhanced crops ->
    Stage 4: Tesseract printed metadata extraction & fusion ->
    Automatic fallback to full-page OCR & horizontal strip scanning.
    """

    def __init__(
        self,
        tesseract_provider: Optional[TesseractProvider] = None,
        handwriting_provider: Optional[HandwritingOCRProvider] = None,
        detector_provider: Optional[PrescriptionDetectorProvider] = None,
    ):
        self.tesseract = tesseract_provider or TesseractProvider()
        self.handwriting = handwriting_provider or HandwritingOCRProvider()
        self.detector = detector_provider or PrescriptionDetectorProvider()

    @property
    def name(self) -> str:
        return "composite_multistage"

    def is_available(self) -> bool:
        return self.tesseract.is_available() or self.handwriting.is_available() or self.detector.is_available()

    def process_prescription_document(
        self,
        file_bytes: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """
        Execute multi-stage prescription extraction pipeline:
        Returns:
            Dict containing:
                - raw_text: Merged exact OCR text
                - regions: List of individual medicine crop recognitions
                - detector_status: 'full_detection', 'partial_detection', or 'fallback'
                - detector_coverage_warning: bool
                - fallback_used: bool
                - technical_trace: Dict of models, devices, and checkpoints
        """
        is_pdf = "pdf" in content_type.lower()
        if is_pdf:
            pdf_text = self.tesseract.extract_text(file_bytes, content_type)
            return {
                "raw_text": pdf_text,
                "regions": [],
                "detector_status": "fallback",
                "detector_coverage_warning": False,
                "fallback_used": True,
                "technical_trace": {
                    "provider": "tesseract_pdf",
                    "device": "cpu",
                    "checkpoint": "none",
                },
            }

        # 1. Load original high-resolution image
        try:
            original_img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        except Exception:
            fallback_text = self.tesseract.extract_text(file_bytes, content_type)
            if not fallback_text.strip() and self.handwriting.is_available():
                fallback_text = self.handwriting.extract_text(file_bytes, content_type)
            return {
                "raw_text": fallback_text,
                "regions": [],
                "detector_status": "fallback",
                "detector_coverage_warning": True,
                "fallback_used": True,
                "technical_trace": {
                    "provider": "tesseract_fallback",
                    "device": "cpu",
                    "checkpoint": "none",
                },
            }

        orig_w, orig_h = original_img.size

        # 2. Stage 2: Adaptive Medicine Region Detection
        detection_result = self.detector.detect_regions(original_img) if self.detector.is_available() else {}
        detected_regions = detection_result.get("regions", [])
        total_detected = len(detected_regions)

        recognized_regions: List[Dict[str, Any]] = []
        crop_texts: List[str] = []

        # 3. Stage 3: Crop, Enhance, and Recognize each detected region (capped to top 8)
        if total_detected > 0 and self.handwriting.is_available():
            # Sort detected regions top-to-bottom, then left-to-right
            sorted_regions = sorted(detected_regions, key=lambda r: (r["box"][1], r["box"][0]))
            regions_to_process = sorted_regions[:8]
            logger.info("Stage 2 Detector identified %d medicine regions. Running Stage 3 TrOCR on top %d crops.", total_detected, len(regions_to_process))

            debug_crop_dir = os.path.join(PROJECT_ROOT, "ml", "prescription_ocr", "outputs", "crops")
            try:
                os.makedirs(debug_crop_dir, exist_ok=True)
            except Exception:
                pass

            for idx, region in enumerate(regions_to_process, start=1):
                cx1, cy1, cx2, cy2 = region["crop_box"]
                cx1 = max(0, min(orig_w - 1, int(cx1)))
                cy1 = max(0, min(orig_h - 1, int(cy1)))
                cx2 = max(cx1 + 1, min(orig_w, int(cx2)))
                cy2 = max(cy1 + 1, min(orig_h, int(cy2)))

                crop_patch = original_img.crop((cx1, cy1, cx2, cy2))
                try:
                    enhancer = ImageEnhance.Contrast(crop_patch)
                    crop_patch = enhancer.enhance(1.4)
                except Exception:
                    pass

                # Save debug crop
                try:
                    crop_patch.save(os.path.join(debug_crop_dir, f"region_{idx}.jpg"), quality=95)
                except Exception:
                    pass

                trocr_res = self.handwriting.predict_with_confidence(crop_patch)
                raw_ocr_text = trocr_res.get("text", "").strip()
                ocr_conf = trocr_res.get("confidence_score", 0.0)

                if raw_ocr_text:
                    crop_texts.append(raw_ocr_text)

                recognized_regions.append({
                    "region_index": idx,
                    "bbox": region["box"],
                    "crop_box": [cx1, cy1, cx2, cy2],
                    "detector_confidence": region["confidence"],
                    "raw_text": raw_ocr_text,
                    "normalized_text": raw_ocr_text,
                    "model_confidence_score": ocr_conf,
                    "source": "trocr",
                })


            printed_header_text = self.tesseract.extract_text(file_bytes, content_type)
            combined_lines = list(crop_texts)
            if printed_header_text:
                combined_lines.append(printed_header_text)

            raw_combined_text = "\n".join(combined_lines).strip()

            detector_status = "partial_detection" if total_detected <= 2 else "full_detection"
            coverage_warning = True if total_detected <= 2 else False

            return {
                "raw_text": raw_combined_text,
                "regions": recognized_regions,
                "detector_status": detector_status,
                "detector_coverage_warning": coverage_warning,
                "fallback_used": False,
                "technical_trace": {
                    "provider": "composite_multistage",
                    "detector_checkpoint": getattr(self.detector, "checkpoint_path", "best_model.pth"),
                    "trocr_model": getattr(self.handwriting, "model_path", "ml/prescription_ocr/models"),
                    "device": getattr(getattr(self.handwriting, "_inference_engine", None), "device", "cpu"),
                    "regions_count": total_detected,
                },
            }

        else:
            logger.info("Detector identified 0 regions. Executing horizontal strip scanning and OCR fallback.")
            strip_texts: List[str] = []
            if self.handwriting.is_available():
                for top_pct in [0.25, 0.38, 0.50, 0.62, 0.74]:
                    sy1 = int(orig_h * top_pct)
                    sy2 = min(orig_h, int(orig_h * (top_pct + 0.15)))
                    sx1 = int(orig_w * 0.10)
                    sx2 = int(orig_w * 0.95)
                    strip_crop = original_img.crop((sx1, sy1, sx2, sy2))
                    try:
                        strip_crop = ImageEnhance.Contrast(strip_crop).enhance(1.4)
                    except Exception:
                        pass
                    st_res = self.handwriting.predict_with_confidence(strip_crop)
                    st_txt = st_res.get("text", "").strip()
                    if st_txt and len(st_txt) >= 3:
                        strip_texts.append(st_txt)

            full_page_text = self.tesseract.extract_text(file_bytes, content_type)
            combined_fallback = list(strip_texts)
            if full_page_text:
                combined_fallback.append(full_page_text)

            merged_text = "\n".join(combined_fallback).strip()

            return {
                "raw_text": merged_text,
                "regions": [],
                "detector_status": "fallback",
                "detector_coverage_warning": True,
                "fallback_used": True,
                "technical_trace": {
                    "provider": "full_page_fallback",
                    "device": getattr(getattr(self.handwriting, "_inference_engine", None), "device", "cpu"),
                    "checkpoint": "none",
                },
            }


    def extract_text(self, file_bytes: bytes, content_type: str, mode: str = "auto") -> str:
        """Route to appropriate extraction method or run multi-stage document processing."""
        clean_mode = (mode or "auto").lower().strip()

        if clean_mode == "tesseract":
            return self.tesseract.extract_text(file_bytes, content_type)
        elif clean_mode == "handwriting":
            hw_text = self.handwriting.extract_text(file_bytes, content_type)
            if hw_text.strip():
                return hw_text
            return self.tesseract.extract_text(file_bytes, content_type)
        else:
            doc_res = self.process_prescription_document(file_bytes, content_type)
            return doc_res.get("raw_text", "")
