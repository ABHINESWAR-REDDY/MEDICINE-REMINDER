"""Dataset loader, validation engine, and statistics generator for RxHandBD Version 3.

RxHandBD Dataset Characteristics:
- 5,578 handwritten medical-word images (512x512 JPG)
- 4,463 training samples, 1,115 test samples
- 1,559 unique transcription vocabulary entries
- Licensed under CC BY 4.0
"""

import os
import csv
import io
import zipfile
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set
from PIL import Image

logger = logging.getLogger("pillsync.ml.dataset")


@dataclass
class DatasetStatistics:
    """Summary statistics for RxHandBD dataset."""
    total_images: int = 0
    train_count: int = 0
    test_count: int = 0
    vocabulary_size: int = 0
    avg_transcription_length: float = 0.0
    min_transcription_length: int = 0
    max_transcription_length: int = 0
    duplicate_count: int = 0
    missing_label_count: int = 0
    missing_image_count: int = 0
    corrupted_image_count: int = 0
    unique_words: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_images": self.total_images,
            "train_count": self.train_count,
            "test_count": self.test_count,
            "vocabulary_size": self.vocabulary_size,
            "avg_transcription_length": round(self.avg_transcription_length, 2),
            "min_transcription_length": self.min_transcription_length,
            "max_transcription_length": self.max_transcription_length,
            "duplicate_count": self.duplicate_count,
            "missing_label_count": self.missing_label_count,
            "missing_image_count": self.missing_image_count,
            "corrupted_image_count": self.corrupted_image_count,
        }


@dataclass
class DatasetSample:
    """Single image-transcription sample."""
    sample_id: str
    image_path: Optional[str]
    transcription: str
    split: str  # 'train' | 'test' | 'val'
    image_bytes: Optional[bytes] = None


class RxHandBDDataLoader:
    """
    Loader and validator for the RxHandBD dataset.
    Can read from unpacked directories or directly from the zip archive.
    """

    DEFAULT_ZIP_SEARCH_PATHS = [
        os.path.join(os.path.dirname(__file__), "..", "data", "raw", "RxHandBD-ML.zip"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "data",
                     "RxHandBD A Handwritten Prescription Word Image Dat",
                     "RxHandBD A Handwritten Prescription Word Image Dat", "RxHandBD-ML.zip"),
    ]

    def __init__(self, data_dir: Optional[str] = None, zip_path: Optional[str] = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "..", "data", "raw")
        self.zip_path = zip_path or self._find_zip_archive()
        self.train_samples: List[DatasetSample] = []
        self.test_samples: List[DatasetSample] = []
        self.stats = DatasetStatistics()

    def _find_zip_archive(self) -> Optional[str]:
        for p in self.DEFAULT_ZIP_SEARCH_PATHS:
            normalized = os.path.abspath(p)
            if os.path.exists(normalized):
                return normalized
        return None

    def extract_dataset(self, target_dir: Optional[str] = None) -> str:
        """Extract RxHandBD zip archive to raw data directory if not yet unpacked."""
        out_dir = target_dir or self.data_dir
        os.makedirs(out_dir, exist_ok=True)

        if not self.zip_path or not os.path.exists(self.zip_path):
            raise FileNotFoundError(
                f"RxHandBD-ML.zip archive not found. Looked in: {self.DEFAULT_ZIP_SEARCH_PATHS}"
            )

        # Check if already extracted
        extracted_train_csv = os.path.join(out_dir, "RxHandBD-ML", "Train_Label.csv")
        direct_train_csv = os.path.join(out_dir, "Train_Label.csv")
        if os.path.exists(extracted_train_csv) or os.path.exists(direct_train_csv):
            logger.info("RxHandBD dataset already extracted in %s", out_dir)
            return out_dir

        logger.info("Extracting %s to %s ...", self.zip_path, out_dir)
        with zipfile.ZipFile(self.zip_path, "r") as z:
            z.extractall(out_dir)
        logger.info("Dataset extraction complete.")
        return out_dir

    def load_dataset(self, validate_images: bool = True) -> Tuple[List[DatasetSample], List[DatasetSample]]:
        """
        Load and validate train and test splits from filesystem or zip archive.
        Returns:
            (train_samples, test_samples)
        """
        # Ensure data is extracted or accessible
        train_csv_path = None
        test_csv_path = None
        train_img_dir = None
        test_img_dir = None

        candidate_dirs = [
            os.path.join(self.data_dir, "RxHandBD-ML"),
            self.data_dir,
        ]

        for d in candidate_dirs:
            tr_c = os.path.join(d, "Train_Label.csv")
            te_c = os.path.join(d, "Test_Label.csv")
            if os.path.exists(tr_c) and os.path.exists(te_c):
                train_csv_path = tr_c
                test_csv_path = te_c
                train_img_dir = os.path.join(d, "Train_Set")
                test_img_dir = os.path.join(d, "Test_Set")
                break

        if not train_csv_path:
            # Attempt auto-extract from zip
            if self.zip_path and os.path.exists(self.zip_path):
                self.extract_dataset(self.data_dir)
                return self.load_dataset(validate_images=validate_images)
            else:
                raise FileNotFoundError(
                    f"Could not locate Train_Label.csv / Test_Label.csv in {candidate_dirs} and zip not found."
                )

        self.train_samples = self._read_split(train_csv_path, train_img_dir, "train", validate_images)
        self.test_samples = self._read_split(test_csv_path, test_img_dir, "test", validate_images)

        self._compute_statistics()
        return self.train_samples, self.test_samples

    def _read_split(
        self,
        csv_path: str,
        image_dir: str,
        split_name: str,
        validate_images: bool
    ) -> List[DatasetSample]:
        samples: List[DatasetSample] = []
        seen_ids: Set[str] = set()

        with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return samples

            for row in reader:
                if not row or len(row) < 2:
                    self.stats.missing_label_count += 1
                    continue

                img_name = row[0].strip()
                text = row[1].strip()

                if not img_name:
                    continue

                if img_name in seen_ids:
                    self.stats.duplicate_count += 1
                seen_ids.add(img_name)

                if not text:
                    self.stats.missing_label_count += 1
                    continue

                img_path = os.path.join(image_dir, img_name)
                if not os.path.exists(img_path):
                    self.stats.missing_image_count += 1
                    continue

                if validate_images:
                    try:
                        # Fast verification of image header
                        with Image.open(img_path) as img:
                            img.verify()
                    except Exception:
                        self.stats.corrupted_image_count += 1
                        continue

                samples.append(DatasetSample(
                    sample_id=img_name,
                    image_path=img_path,
                    transcription=text,
                    split=split_name,
                ))

        return samples

    def _compute_statistics(self):
        all_samples = self.train_samples + self.test_samples
        self.stats.total_images = len(all_samples)
        self.stats.train_count = len(self.train_samples)
        self.stats.test_count = len(self.test_samples)

        lengths: List[int] = []
        vocab: Set[str] = set()

        for s in all_samples:
            vocab.add(s.transcription.strip())
            lengths.append(len(s.transcription))

        self.stats.unique_words = vocab
        self.stats.vocabulary_size = len(vocab)

        if lengths:
            self.stats.avg_transcription_length = sum(lengths) / len(lengths)
            self.stats.min_transcription_length = min(lengths)
            self.stats.max_transcription_length = max(lengths)

    def get_statistics_report(self) -> str:
        """Generate human-readable dataset statistics report."""
        s = self.stats
        report = (
            "==================================================\n"
            "RxHandBD Dataset Statistics Report\n"
            "==================================================\n"
            f"Total Valid Images:           {s.total_images}\n"
            f"Training Set Samples:         {s.train_count}\n"
            f"Testing Set Samples:          {s.test_count}\n"
            f"Unique Vocabulary Entries:    {s.vocabulary_size}\n"
            f"Avg Transcription Length:     {s.avg_transcription_length:.2f} chars\n"
            f"Min Transcription Length:     {s.min_transcription_length} chars\n"
            f"Max Transcription Length:     {s.max_transcription_length} chars\n"
            f"Duplicate Image IDs:          {s.duplicate_count}\n"
            f"Missing / Empty Labels:       {s.missing_label_count}\n"
            f"Missing Image Files:          {s.missing_image_count}\n"
            f"Corrupted Images:             {s.corrupted_image_count}\n"
            "=================================================="
        )
        return report


# Optional PyTorch Dataset Implementation
try:
    import torch
    from torch.utils.data import Dataset

    class TrOCRPrescriptionDataset(Dataset):
        """PyTorch Dataset wrapper for TrOCR handwriting recognition."""

        def __init__(self, samples: List[DatasetSample], processor, max_target_length: int = 64):
            self.samples = samples
            self.processor = processor
            self.max_target_length = max_target_length

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            sample = self.samples[idx]
            image = Image.open(sample.image_path).convert("RGB")
            pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze(0)

            labels = self.processor.tokenizer(
                sample.transcription,
                padding="max_length",
                max_length=self.max_target_length,
                return_tensors="pt",
                truncation=True
            ).input_ids.squeeze(0)

            # Replace padding token id with -100 to ignore loss on padding tokens
            labels[labels == self.processor.tokenizer.pad_token_id] = -100

            return {"pixel_values": pixel_values, "labels": labels}

except ImportError:
    TrOCRPrescriptionDataset = None
