"""Reference Medicine Adapter for post-OCR spelling normalization and candidate matching.

Enforces:
- is_training_eligible = False (Strictly forbidden as TrOCR training ground truth)
- Zero-overwrite rule: Raw OCR string is preserved verbatim.
- Candidate generation with similarity scoring.
"""

import os
import csv
from typing import Dict, List, Tuple, Any, Optional, Set
from .base import BaseDatasetAdapter, DatasetMetadata


class ReferenceMedicineAdapter(BaseDatasetAdapter):
    """Adapter for medicine dictionaries and reference datasets."""

    def __init__(self, data_root: str = "DATA"):
        self.data_root = os.path.abspath(data_root)
        self.med_dir = os.path.join(self.data_root, "medicine names")
        self.enhanced_csv = os.path.join(self.med_dir, "medicine_dataset_enhanced.csv")
        self.all_med_csv = os.path.join(self.med_dir, "all_medicine databased.csv")
        self._vocabulary: Set[str] = set()

    def get_metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            dataset_name="MedicineReferenceDatabase",
            image_path="",
            label_path=f"{self.enhanced_csv} | {self.all_med_csv}",
            label_type="reference_lookup",
            annotation_type="dictionary",
            is_training_eligible=False,
            is_evaluation_eligible=False,
            notes="Reference dataset ONLY for candidate generation. NEVER used as TrOCR training labels."
        )

    def load_vocabulary(self) -> Set[str]:
        """Load unique medicine names from reference CSVs."""
        vocab = set()

        if os.path.exists(self.enhanced_csv):
            with open(self.enhanced_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and len(row) > 0 and row[0].strip():
                        vocab.add(row[0].strip())

        if os.path.exists(self.all_med_csv):
            with open(self.all_med_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and len(row) > 1 and row[1].strip():
                        vocab.add(row[1].strip())

        self._vocabulary = vocab
        return vocab

    def validate_integrity(self) -> Dict[str, Any]:
        vocab = self.load_vocabulary()
        return {
            "dataset": "MedicineReferenceDatabase",
            "enhanced_csv_exists": os.path.exists(self.enhanced_csv),
            "all_med_csv_exists": os.path.exists(self.all_med_csv),
            "unique_medicine_terms": len(vocab),
            "is_training_eligible": False,
            "status": "VALID" if len(vocab) > 0 else "EMPTY",
        }
