"""Base Dataset Adapter interface and Metadata contract for PillSync OCR."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
from abc import ABC, abstractmethod


@dataclass
class DatasetMetadata:
    """Explicit metadata contract for all dataset sources in PillSync."""
    dataset_name: str
    image_path: str
    label_path: str
    label_type: str                  # e.g., 'exact_transcription', 'normalized_name', 'yolo_bbox', 'reference_lookup'
    annotation_type: str             # e.g., 'word_level_htr', 'full_document', 'dictionary'
    is_training_eligible: bool
    is_evaluation_eligible: bool
    total_records: int = 0
    valid_records: int = 0
    notes: str = ""


class BaseDatasetAdapter(ABC):
    """Abstract base class for all dataset adapters in PillSync."""

    @abstractmethod
    def get_metadata(self) -> DatasetMetadata:
        """Return declared metadata contract."""
        pass

    @abstractmethod
    def validate_integrity(self) -> Dict[str, Any]:
        """Perform validation (checking files, corrupt images, missing labels)."""
        pass
