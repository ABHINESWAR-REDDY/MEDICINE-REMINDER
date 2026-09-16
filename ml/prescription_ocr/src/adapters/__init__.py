"""PillSync ML Dataset Adapters Package.

Provides strictly separated dataset adapters with explicit metadata,
transcription verification, and training/evaluation eligibility guards.
"""

from .base import BaseDatasetAdapter, DatasetMetadata
from .rxhandbd_adapter import RxHandBDAdapter
from .doctor_prescription_adapter import DoctorPrescriptionAdapter
from .reference_medicine_adapter import ReferenceMedicineAdapter
from .full_prescription_adapter import FullPrescriptionAdapter

__all__ = [
    "BaseDatasetAdapter",
    "DatasetMetadata",
    "RxHandBDAdapter",
    "DoctorPrescriptionAdapter",
    "ReferenceMedicineAdapter",
    "FullPrescriptionAdapter",
]
