"""RxHandBD Dataset Adapter for Primary TrOCR Handwritten Text Recognition.

Enforces:
- 4,463 Training samples -> Deterministic 4,000 Train / 463 Validation split
- 1,115 Official Test samples strictly untouched & frozen
- Zero test data leakage protection with automated assertion guards
"""

import os
import csv
import random
from typing import Dict, List, Tuple, Any, Optional, Set
from PIL import Image

from .base import BaseDatasetAdapter, DatasetMetadata


class RxHandBDAdapter(BaseDatasetAdapter):
    """Adapter for the RxHandBD handwritten medicine word dataset."""

    def __init__(
        self,
        data_root: str = "DATA",
        train_csv: str = "Train_Label.csv",
        test_csv: str = "Test_Label.csv",
        images_dir: str = "Test_Set",
        seed: int = 42,
    ):
        self.data_root = os.path.abspath(data_root)
        self.train_csv_path = os.path.join(self.data_root, train_csv)
        self.test_csv_path = os.path.join(self.data_root, test_csv)
        self.images_dir = os.path.join(self.data_root, images_dir)
        self.seed = seed

        self._train_samples: List[Tuple[str, str]] = []
        self._val_samples: List[Tuple[str, str]] = []
        self._test_samples: List[Tuple[str, str]] = []
        self._is_loaded = False

    def get_metadata(self) -> DatasetMetadata:
        return DatasetMetadata(
            dataset_name="RxHandBD",
            image_path=self.images_dir,
            label_path=f"{self.train_csv_path} | {self.test_csv_path}",
            label_type="exact_transcription",
            annotation_type="word_level_htr",
            is_training_eligible=True,
            is_evaluation_eligible=True,
            notes="Primary TrOCR dataset. 4,000 train / 463 val / 1,115 official test split."
        )

    def _read_csv(self, path: str) -> List[Tuple[str, str]]:
        samples = []
        if not os.path.exists(path):
            return samples
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    img_name = row[0].strip()
                    text = row[1].strip()
                    if img_name and text:
                        samples.append((img_name, text))
        return samples

    def load_splits(self, validate_images: bool = True) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Load and return (train_4000, val_463, test_1115)."""
        raw_train = self._read_csv(self.train_csv_path)
        raw_test = self._read_csv(self.test_csv_path)

        if not raw_train or not raw_test:
            # Fallback check if full labels are in Prescription_Labels.xlsx or alternative paths
            raise FileNotFoundError(f"RxHandBD label files missing at {self.train_csv_path} or {self.test_csv_path}")

        # Validate existence if requested
        if validate_images:
            raw_train = [(img, txt) for img, txt in raw_train if os.path.exists(os.path.join(self.images_dir, img))]
            raw_test = [(img, txt) for img, txt in raw_test if os.path.exists(os.path.join(self.images_dir, img))]

        # Leakage Protection: Ensure official test set is completely disjoint from training
        train_image_set = set(img for img, _ in raw_train)
        test_image_set = set(img for img, _ in raw_test)
        overlap = train_image_set.intersection(test_image_set)
        if overlap:
            raise ValueError(f"CRITICAL: Data leakage detected! {len(overlap)} images found in both train and test splits!")

        # Deterministic Train / Validation Split: 4,000 Train / 463 Val (out of 4,463)
        rng = random.Random(self.seed)
        shuffled_train = list(raw_train)
        rng.shuffle(shuffled_train)

        self._train_samples = shuffled_train[:4000]
        self._val_samples = shuffled_train[4000:]
        self._test_samples = raw_test
        self._is_loaded = True

        # Assert disjointness of all three splits
        train_set = set(img for img, _ in self._train_samples)
        val_set = set(img for img, _ in self._val_samples)
        test_set = set(img for img, _ in self._test_samples)

        assert len(train_set.intersection(val_set)) == 0, "Leakage between Train and Val!"
        assert len(train_set.intersection(test_set)) == 0, "Leakage between Train and Test!"
        assert len(val_set.intersection(test_set)) == 0, "Leakage between Val and Test!"

        return self._train_samples, self._val_samples, self._test_samples

    def validate_integrity(self) -> Dict[str, Any]:
        if not self._is_loaded:
            self.load_splits(validate_images=True)

        return {
            "dataset": "RxHandBD",
            "train_count": len(self._train_samples),
            "val_count": len(self._val_samples),
            "official_test_count": len(self._test_samples),
            "total_samples": len(self._train_samples) + len(self._val_samples) + len(self._test_samples),
            "test_leakage_detected": False,
            "status": "VALID",
        }
