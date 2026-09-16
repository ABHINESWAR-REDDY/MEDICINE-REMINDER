"""Medication adherence calculation engine based on real dose logs."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dose import MedicationDose, DoseStatus
from app.services.dose_service import DoseService


class AdherenceService:
    """Service computing mathematical adherence rates and status categories."""

    def __init__(self, db: Session):
        self.db = db
        self.dose_service = DoseService(db)

    def calculate_adherence(self, patient_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Calculate adherence percentage for a patient over the given time window (default 30 days).
        
        Formula:
          Adherence Rate = (TAKEN / (TAKEN + MISSED + SKIPPED)) * 100
        
        Rules:
          - Only past/expected doses participate.
          - Future SCHEDULED doses are strictly excluded.
          - Status Thresholds:
              >= 90%: 'Good'
              75% - 89.9%: 'Needs Attention'
              < 75%: 'High Risk'
        """
        # Ensure overdue doses are marked MISSED first
        self.dose_service.reconcile_missed_doses(patient_id=patient_id)

        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=days)

        # Query all past doses in window (scheduled_time <= now_utc)
        base_query = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id == patient_id,
            MedicationDose.scheduled_time >= start_utc,
            MedicationDose.scheduled_time <= now_utc
        )

        taken_count = base_query.filter(MedicationDose.status == DoseStatus.TAKEN).count()
        missed_count = base_query.filter(MedicationDose.status == DoseStatus.MISSED).count()
        skipped_count = base_query.filter(MedicationDose.status == DoseStatus.SKIPPED).count()
        
        # Future scheduled doses inside the date window (if any)
        pending_scheduled_count = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id == patient_id,
            MedicationDose.scheduled_time > now_utc,
            MedicationDose.status == DoseStatus.SCHEDULED
        ).count()

        total_expected = taken_count + missed_count + skipped_count

        if total_expected == 0:
            adherence_percentage = 100.0
            adherence_status = "Good"
        else:
            adherence_percentage = round((taken_count / total_expected) * 100.0, 1)
            if adherence_percentage >= 90.0:
                adherence_status = "Good"
            elif adherence_percentage >= 75.0:
                adherence_status = "Needs Attention"
            else:
                adherence_status = "High Risk"

        return {
            "patient_id": patient_id,
            "period_days": days,
            "adherence_percentage": adherence_percentage,
            "adherence_status": adherence_status,
            "total_expected_doses": total_expected,
            "taken_count": taken_count,
            "missed_count": missed_count,
            "skipped_count": skipped_count,
            "pending_future_count": pending_scheduled_count,
        }
