"""Reproducible image preprocessing pipeline for handwriting recognition.

Ensures non-destructive enhancements (RGB conversion, aspect ratio preservation,
contrast normalization, and tensor transformation) suitable for TrOCR input.
"""

from typing import Tuple, Optional, Union, Any
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class PrescriptionImagePreprocessor:
    """Configurable image preprocessor for medical prescription images."""

    def __init__(
        self,
        target_size: Tuple[int, int] = (384, 384),
        enhance_contrast: bool = True,
        contrast_factor: float = 1.3,
        sharpen: bool = True,
        preserve_aspect_ratio: bool = True,
        pad_color: Tuple[int, int, int] = (255, 255, 255),
    ):
        self.target_size = target_size
        self.enhance_contrast = enhance_contrast
        self.contrast_factor = contrast_factor
        self.sharpen = sharpen
        self.preserve_aspect_ratio = preserve_aspect_ratio
        self.pad_color = pad_color

    def preprocess(self, image: Union[Image.Image, str, bytes]) -> Image.Image:
        """
        Execute full preprocessing on input image:
        1. Open / convert to RGB
        2. Clean orientation
        3. Optional contrast & edge enhancement
        4. Aspect ratio-preserving resize / padding
        """
        pil_img = self._load_image(image)

        # 1. Normalize orientation using EXIF tags
        pil_img = ImageOps.exif_transpose(pil_img)

        # 2. Convert to RGB
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        # 3. Optional Contrast Enhancement
        if self.enhance_contrast and self.contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(self.contrast_factor)

        # 4. Optional mild Sharpening
        if self.sharpen:
            pil_img = pil_img.filter(ImageFilter.SHARPEN)

        # 5. Aspect-ratio preserving resize & padding
        if self.preserve_aspect_ratio:
            pil_img = self._resize_with_padding(pil_img, self.target_size, self.pad_color)
        else:
            pil_img = pil_img.resize(self.target_size, Image.Resampling.BICUBIC)

        return pil_img

    def _load_image(self, image_input: Union[Image.Image, str, bytes]) -> Image.Image:
        if isinstance(image_input, Image.Image):
            return image_input.copy()
        elif isinstance(image_input, str):
            return Image.open(image_input)
        elif isinstance(image_input, (bytes, bytearray)):
            import io
            return Image.open(io.BytesIO(image_input))
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

    @staticmethod
    def _resize_with_padding(
        img: Image.Image,
        target_size: Tuple[int, int],
        pad_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """Resize image to fit within target_size while maintaining aspect ratio, padding the rest."""
        target_w, target_h = target_size
        orig_w, orig_h = img.size

        # Compute scaling ratio
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))

        resized = img.resize((new_w, new_h), Image.Resampling.BICUBIC)

        # Create canvas with padding color
        canvas = Image.new("RGB", target_size, pad_color)
        offset_x = (target_w - new_w) // 2
        offset_y = (target_h - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))

        return canvas

    @staticmethod
    def to_numpy_normalized(img: Image.Image) -> Any:
        """Convert PIL image to float32 NumPy array normalized with standard mean/std."""
        import numpy as np
        arr = np.array(img, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (arr - mean) / std
        return normalized.transpose(2, 0, 1)  # (C, H, W)
