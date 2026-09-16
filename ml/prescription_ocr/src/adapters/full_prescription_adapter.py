"""Full Prescription Document Dataset Adapter for end-to-end integration and detector evaluation.

Enforces:
- is_training_eligible = False (Full pages are not word-level TrOCR training samples)
- is_evaluation_eligible = True (Used for full-document integration tests & detector evaluation)
"""

import os
from typing import Dict, List, Tuple, Any, Optional
from PIL import Image

from .base import BaseDatasetAdapter, DatasetMetadata


class FullPrescriptionAdapter(BaseDatasetAdapter):
    """Adapter for full-page prescription document images."""

    def __init__(self, data_root: str = "DATA"):
        self.data_root = os.path.abspath(data_root)
        self.images_dir = os.path.join(self.data_root, "prescriptions images")

    def get_metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            dataset_name="FullPrescriptionDocuments",
            image_path=self.images_dir,
            label_path="",
            label_type="full_page_document",
            annotation_type="document_evaluation",
            is_training_eligible=False,
            is_evaluation_eligible=True,
            notes="Full prescription documents for end-to-end integration and detector pipeline testing."
        )

    def list_images(self) -> List[str]:
        """Return list of all valid full prescription image filenames."""
        if not os.path.exists(self.images_dir):
            return []
        return [
            f for f in os.listdir(self.images_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

    def validate_integrity(self) -> Dict[str, Any]:
        imgs = self.list_images()
        valid_count = 0
        corrupt_count = 0

        for f in imgs:
            path = os.path.join(self.images_dir, f)
            try:
                with Image.open(path) as img:
                    img.verify()
                valid_count += 1
            except Exception:
                corrupt_count += 1

        return {
            "dataset": "FullPrescriptionDocuments",
            "total_documents": len(imgs),
            "valid_documents": valid_count,
            "corrupt_documents": corrupt_count,
            "is_training_eligible": False,
            "is_evaluation_eligible": True,
            "status": "VALID" if valid_count > 0 else "EMPTY",
        }
