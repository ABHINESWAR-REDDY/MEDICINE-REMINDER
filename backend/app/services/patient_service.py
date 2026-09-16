"""Patient portal domain services for Medication History and dynamic Refill Predictions."""

from datetime import datetime, date, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.medicine import Medicine
from app.models.schedule import MedicationSchedule
from app.models.dose import MedicationDose, DoseStatus
from app.models.prescription import Prescription
from app.schemas.patient_portal import (
    MedicationHistoryItem,
    MedicationHistoryResponse,
    RefillPredictionItem,
    RefillPredictionsResponse,
)
from app.services.dose_service import DoseService


def _format_schedule_desc(sched: Optional[MedicationSchedule]) -> Optional[str]:
    """Format human-readable schedule description from schedule model."""
    if not sched:
        return None
    freq = (sched.frequency_type.value if hasattr(sched.frequency_type, "value") else str(sched.frequency_type or "")).replace("_", " ").title()
    times = ", ".join(sched.scheduled_times) if isinstance(sched.scheduled_times, list) else ""
    return f"{freq} ({times})" if times else freq


class PatientService:
    """Service handling patient medication history timeline and real-data refill predictions."""

    def __init__(self, db: Session):
        self.db = db
        self.dose_service = DoseService(db)

    def get_medication_history(self, patient_id: int) -> MedicationHistoryResponse:
        """
        Retrieve complete medication history and dose log for the authenticated patient.
        Ensures strictly zero records from other patients and zero mock data.
        """
        # Reconcile overdue doses to ensure accurate historical status
        self.dose_service.reconcile_missed_doses(patient_id=patient_id)

        # 1. Fetch all medications for this patient
        medicines = self.db.query(Medicine).filter(
            Medicine.user_id == patient_id
        ).order_by(Medicine.start_date.desc(), Medicine.created_at.desc()).all()

        if not medicines:
            return MedicationHistoryResponse(
                patient_id=patient_id,
                total_records=0,
                history=[]
            )

        med_map = {m.id: m for m in medicines}
        med_ids = list(med_map.keys())

        # 2. Fetch all recorded doses for these medications
        doses = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id == patient_id,
            MedicationDose.medicine_id.in_(med_ids)
        ).order_by(MedicationDose.scheduled_time.desc()).all()

        history_items: List[MedicationHistoryItem] = []
        dosed_medicine_ids = set()

        for d in doses:
            med = med_map.get(d.medicine_id)
            if not med:
                continue
            dosed_medicine_ids.add(med.id)
            sched = d.schedule

            history_items.append(
                MedicationHistoryItem(
                    id=d.id,
                    dose_id=d.id,
                    medicine_id=med.id,
                    medicine_name=med.name,
                    strength=med.dosage_amount,
                    unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                    dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                    instructions=med.instructions,
                    schedule_description=_format_schedule_desc(sched),
                    dose_quantity=sched.dose_quantity if sched else 1.0,
                    start_date=med.start_date,
                    end_date=med.end_date,
                    is_active=med.is_active,
                    scheduled_time=d.scheduled_time,
                    actual_time=d.actual_time,
                    status=d.status.value if hasattr(d.status, "value") else str(d.status),
                )
            )

        # 3. For medications with no dose instances yet, include top-level medicine entry
        for med in medicines:
            if med.id not in dosed_medicine_ids:
                sched = med.schedules[0] if med.schedules else None
                status_str = "ACTIVE" if med.is_active else "INACTIVE"
                history_items.append(
                    MedicationHistoryItem(
                        id=None,
                        dose_id=None,
                        medicine_id=med.id,
                        medicine_name=med.name,
                        strength=med.dosage_amount,
                        unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                        dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                        instructions=med.instructions,
                        schedule_description=_format_schedule_desc(sched),
                        dose_quantity=sched.dose_quantity if sched else 1.0,
                        start_date=med.start_date,
                        end_date=med.end_date,
                        is_active=med.is_active,
                        scheduled_time=None,
                        actual_time=None,
                        status=status_str,
                    )
                )

        return MedicationHistoryResponse(
            patient_id=patient_id,
            total_records=len(history_items),
            history=history_items
        )

    def get_refill_predictions(self, patient_id: int) -> RefillPredictionsResponse:
        """
        Dynamically calculate refill predictions based on real patient medication, schedule, and dose data.
        Returns explicit 'INSUFFICIENT_DATA' if stock, dosage, or frequency are incomplete.
        """
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        # Reconcile doses to get up to date intake numbers
        self.dose_service.reconcile_missed_doses(patient_id=patient_id)

        medicines = self.db.query(Medicine).filter(
            Medicine.user_id == patient_id
        ).order_by(Medicine.created_at.asc()).all()

        predictions: List[RefillPredictionItem] = []
        valid_count = 0
        insufficient_count = 0

        for med in medicines:
            doctor = med.prescription.doctor_name if med.prescription else None
            active_schedules = [s for s in med.schedules if s.is_active]

            # 1. Check if medication regimen has ended
            if not med.is_active or (med.end_date and med.end_date < today):
                predictions.append(
                    RefillPredictionItem(
                        medicine_id=med.id,
                        medicine_name=med.name,
                        strength=med.dosage_amount,
                        unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                        dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                        instructions=med.instructions,
                        start_date=med.start_date,
                        end_date=med.end_date,
                        is_active=med.is_active,
                        status="ENDED",
                        status_message="Medication regimen has ended.",
                        current_stock=med.quantity,
                        prescription_id=med.prescription_id,
                        doctor_name=doctor,
                    )
                )
                continue

            # 2. Check stock quantity
            if med.quantity is None or med.quantity <= 0:
                insufficient_count += 1
                predictions.append(
                    RefillPredictionItem(
                        medicine_id=med.id,
                        medicine_name=med.name,
                        strength=med.dosage_amount,
                        unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                        dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                        instructions=med.instructions,
                        start_date=med.start_date,
                        end_date=med.end_date,
                        is_active=med.is_active,
                        status="INSUFFICIENT_DATA",
                        status_message="Refill prediction unavailable — insufficient medication data (stock quantity missing or zero).",
                        current_stock=med.quantity,
                        prescription_id=med.prescription_id,
                        doctor_name=doctor,
                    )
                )
                continue

            # 3. Check active schedules
            if not active_schedules:
                insufficient_count += 1
                predictions.append(
                    RefillPredictionItem(
                        medicine_id=med.id,
                        medicine_name=med.name,
                        strength=med.dosage_amount,
                        unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                        dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                        instructions=med.instructions,
                        start_date=med.start_date,
                        end_date=med.end_date,
                        is_active=med.is_active,
                        status="INSUFFICIENT_DATA",
                        status_message="Refill prediction unavailable — insufficient medication data (no active schedule configured).",
                        current_stock=med.quantity,
                        prescription_id=med.prescription_id,
                        doctor_name=doctor,
                    )
                )
                continue

            # 4. Calculate daily consumption
            primary_sched = active_schedules[0]
            times_list = primary_sched.scheduled_times if isinstance(primary_sched.scheduled_times, list) else []
            doses_per_day = len(times_list)
            dose_qty = primary_sched.dose_quantity if primary_sched.dose_quantity and primary_sched.dose_quantity > 0 else 1.0

            if doses_per_day <= 0:
                insufficient_count += 1
                predictions.append(
                    RefillPredictionItem(
                        medicine_id=med.id,
                        medicine_name=med.name,
                        strength=med.dosage_amount,
                        unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                        dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                        instructions=med.instructions,
                        start_date=med.start_date,
                        end_date=med.end_date,
                        is_active=med.is_active,
                        status="INSUFFICIENT_DATA",
                        status_message="Refill prediction unavailable — insufficient medication data (no scheduled intake times).",
                        current_stock=med.quantity,
                        prescription_id=med.prescription_id,
                        doctor_name=doctor,
                    )
                )
                continue

            daily_consumption = doses_per_day * dose_qty
            if daily_consumption <= 0:
                insufficient_count += 1
                predictions.append(
                    RefillPredictionItem(
                        medicine_id=med.id,
                        medicine_name=med.name,
                        strength=med.dosage_amount,
                        unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                        dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                        instructions=med.instructions,
                        start_date=med.start_date,
                        end_date=med.end_date,
                        is_active=med.is_active,
                        status="INSUFFICIENT_DATA",
                        status_message="Refill prediction unavailable — insufficient medication data (daily usage rate is 0).",
                        current_stock=med.quantity,
                        prescription_id=med.prescription_id,
                        doctor_name=doctor,
                    )
                )
                continue

            # 5. Consider recorded dose activity
            taken_count = self.db.query(MedicationDose).filter(
                MedicationDose.medicine_id == med.id,
                MedicationDose.status == DoseStatus.TAKEN
            ).count()

            missed_count = self.db.query(MedicationDose).filter(
                MedicationDose.medicine_id == med.id,
                MedicationDose.status == DoseStatus.MISSED
            ).count()

            total_consumed = taken_count * dose_qty
            remaining_quantity = max(0.0, float(med.quantity) - total_consumed)
            estimated_remaining_days = max(0, int(remaining_quantity / daily_consumption))
            predicted_refill_date = today + timedelta(days=estimated_remaining_days)

            # Determine urgency level
            if estimated_remaining_days <= 3:
                urgency = "CRITICAL"
            elif estimated_remaining_days <= 7:
                urgency = "LOW_STOCK"
            elif estimated_remaining_days <= 14:
                urgency = "MODERATE"
            else:
                urgency = "GOOD"

            valid_count += 1
            predictions.append(
                RefillPredictionItem(
                    medicine_id=med.id,
                    medicine_name=med.name,
                    strength=med.dosage_amount,
                    unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                    dosage_form=med.medicine_form.value if hasattr(med.medicine_form, "value") else str(med.medicine_form or ""),
                    instructions=med.instructions,
                    start_date=med.start_date,
                    end_date=med.end_date,
                    is_active=med.is_active,
                    status="VALID",
                    status_message="Refill predicted dynamically from active schedule and intake history.",
                    current_stock=med.quantity,
                    daily_consumption=daily_consumption,
                    doses_per_day=doses_per_day,
                    dose_quantity_per_intake=dose_qty,
                    doses_taken_count=taken_count,
                    doses_missed_count=missed_count,
                    estimated_remaining_quantity=round(remaining_quantity, 1),
                    estimated_remaining_days=estimated_remaining_days,
                    predicted_refill_date=predicted_refill_date,
                    urgency_level=urgency,
                    prescription_id=med.prescription_id,
                    doctor_name=doctor,
                )
            )

        return RefillPredictionsResponse(
            patient_id=patient_id,
            generated_at=now_utc,
            total_medications=len(predictions),
            valid_predictions_count=valid_count,
            insufficient_data_count=insufficient_count,
            predictions=predictions,
        )
