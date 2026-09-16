"""Medication dose instance management, idempotent generation, and intake tracking."""

from datetime import datetime, date, time as dtime, timezone, timedelta
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.medicine import Medicine
from app.models.schedule import MedicationSchedule
from app.models.dose import MedicationDose, DoseStatus
from app.models.notification import Notification
from app.services.audit_service import AuditService


def _format_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Ensure datetime is serialized as standard RFC 3339 / ISO 8601 with Z UTC indicator."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class DoseService:
    """Service handling dose generation, status transitions, and overdue reconciliation."""

    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def reconcile_missed_doses(self, patient_id: Optional[int] = None) -> int:
        """
        Scan and transition any past SCHEDULED dose to MISSED if its scheduled_time is in the past.
        Executes idempotently and returns the count of updated doses.
        """
        now_utc = datetime.now(timezone.utc)
        query = self.db.query(MedicationDose).filter(
            MedicationDose.status == DoseStatus.SCHEDULED,
            MedicationDose.scheduled_time < now_utc
        )
        if patient_id:
            query = query.filter(MedicationDose.patient_id == patient_id)

        overdue_doses = query.all()
        updated_count = len(overdue_doses)

        if updated_count > 0:
            for dose in overdue_doses:
                dose.status = DoseStatus.MISSED
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
        return updated_count

    def generate_doses_for_patient(
        self,
        patient_id: int,
        target_date: Optional[date] = None
    ) -> List[MedicationDose]:
        """
        Deterministically generate MedicationDose records for all active schedules of a patient on target_date.
        Database unique constraint on (schedule_id, scheduled_time) guarantees idempotency without duplicates.
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # Find all active schedules valid for target_date
        schedules = self.db.query(MedicationSchedule).join(Medicine).filter(
            Medicine.user_id == patient_id,
            MedicationSchedule.is_active == True,
            MedicationSchedule.start_date <= target_date,
            or_(
                MedicationSchedule.end_date == None,
                MedicationSchedule.end_date >= target_date
            )
        ).all()

        generated_doses = []

        for sched in schedules:
            time_list = sched.scheduled_times if isinstance(sched.scheduled_times, list) else []
            for t_str in time_list:
                try:
                    parts = t_str.split(":")
                    h, m = int(parts[0]), int(parts[1])
                    dose_dt = datetime(
                        target_date.year, target_date.month, target_date.day,
                        h, m, 0, tzinfo=timezone.utc
                    )
                except Exception:
                    continue

                # Check if dose already exists
                existing = self.db.query(MedicationDose).filter(
                    MedicationDose.schedule_id == sched.id,
                    MedicationDose.scheduled_time == dose_dt
                ).first()

                if existing:
                    generated_doses.append(existing)
                    continue

                # Create new dose instance
                new_dose = MedicationDose(
                    schedule_id=sched.id,
                    medicine_id=sched.medicine_id,
                    patient_id=patient_id,
                    scheduled_time=dose_dt,
                    status=DoseStatus.SCHEDULED
                )
                self.db.add(new_dose)
                try:
                    self.db.commit()
                    self.db.refresh(new_dose)
                    generated_doses.append(new_dose)
                except IntegrityError:
                    self.db.rollback()
                    # Concurrent request already inserted this dose
                    existing = self.db.query(MedicationDose).filter(
                        MedicationDose.schedule_id == sched.id,
                        MedicationDose.scheduled_time == dose_dt
                    ).first()
                    if existing:
                        generated_doses.append(existing)

        # After generation, reconcile any overdue doses
        self.reconcile_missed_doses(patient_id=patient_id)
        return generated_doses

    def mark_dose_taken(self, dose_id: int, actor_user: User) -> Dict[str, Any]:
        """
        Transition a dose to TAKEN status.
        Only allowed for the dose owner (Patient) or an assigned Caregiver/Admin.
        Records exact current UTC timestamp in actual_time.
        """
        dose = self.db.query(MedicationDose).filter(MedicationDose.id == dose_id).first()
        if not dose:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "RESOURCE_NOT_FOUND", "message": "Medication dose not found."}
            )

        # Authorization: Patient can only mark their own dose
        if actor_user.role == UserRole.PATIENT and dose.patient_id != actor_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You cannot mark doses for another patient."}
            )

        # Terminal state validation
        if dose.status == DoseStatus.TAKEN:
            return {
                "success": True,
                "message": "Dose is already marked as taken.",
                "dose": {
                    "id": dose.id,
                    "status": dose.status.value,
                    "scheduled_time": _format_utc_iso(dose.scheduled_time),
                    "actual_time": _format_utc_iso(dose.actual_time)
                }
            }

        if dose.status in (DoseStatus.SKIPPED, DoseStatus.MISSED) and actor_user.role == UserRole.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_TRANSITION", "message": f"Cannot mark a {dose.status.value} dose as Taken."}
            )

        dose.status = DoseStatus.TAKEN
        dose.actual_time = datetime.now(timezone.utc)
        dose.recorded_by = actor_user.id
        self.db.commit()
        self.db.refresh(dose)

        # Clear active unread notifications for this dose
        try:
            self.db.query(Notification).filter(
                Notification.user_id == dose.patient_id,
                Notification.related_dose_id == dose.id
            ).update({"is_read": True})
            self.db.commit()
        except Exception:
            self.db.rollback()

        self.audit.log(
            action="DOSE_TAKEN",
            target_type="MedicationDose",
            actor_user_id=actor_user.id,
            target_id=dose.id,
            details={"patient_id": dose.patient_id, "medicine_id": dose.medicine_id}
        )

        return {
            "success": True,
            "message": "Dose marked as taken successfully.",
            "dose": {
                "id": dose.id,
                "status": dose.status.value,
                "scheduled_time": _format_utc_iso(dose.scheduled_time),
                "actual_time": _format_utc_iso(dose.actual_time)
            }
        }

    def mark_dose_skipped(self, dose_id: int, actor_user: User) -> Dict[str, Any]:
        """Transition a scheduled dose to SKIPPED status."""
        dose = self.db.query(MedicationDose).filter(MedicationDose.id == dose_id).first()
        if not dose:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "RESOURCE_NOT_FOUND", "message": "Medication dose not found."}
            )

        if actor_user.role == UserRole.PATIENT and dose.patient_id != actor_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You cannot modify doses for another patient."}
            )

        if dose.status != DoseStatus.SCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_TRANSITION", "message": f"Only SCHEDULED doses can be skipped. Current status: {dose.status.value}"}
            )

        dose.status = DoseStatus.SKIPPED
        dose.actual_time = None
        dose.recorded_by = actor_user.id
        self.db.commit()
        self.db.refresh(dose)

        # Clear active unread notifications for this dose
        try:
            self.db.query(Notification).filter(
                Notification.user_id == dose.patient_id,
                Notification.related_dose_id == dose.id
            ).update({"is_read": True})
            self.db.commit()
        except Exception:
            self.db.rollback()

        self.audit.log(
            action="DOSE_SKIPPED",
            target_type="MedicationDose",
            actor_user_id=actor_user.id,
            target_id=dose.id,
            details={"patient_id": dose.patient_id, "medicine_id": dose.medicine_id}
        )

        return {
            "success": True,
            "message": "Dose marked as skipped.",
            "dose": {
                "id": dose.id,
                "status": dose.status.value,
                "scheduled_time": _format_utc_iso(dose.scheduled_time)
            }
        }

    def get_patient_doses(
        self,
        patient_id: int,
        target_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve today's and upcoming doses for a patient with medicine details."""
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # Ensure doses are generated and reconciled
        self.generate_doses_for_patient(patient_id, target_date=target_date)

        start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

        doses = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id == patient_id,
            MedicationDose.scheduled_time >= start_dt,
            MedicationDose.scheduled_time <= end_dt
        ).order_by(MedicationDose.scheduled_time.asc()).all()

        results = []
        for d in doses:
            med = self.db.query(Medicine).filter(Medicine.id == d.medicine_id).first()
            sched = self.db.query(MedicationSchedule).filter(MedicationSchedule.id == d.schedule_id).first()
            results.append({
                "id": d.id,
                "schedule_id": d.schedule_id,
                "medicine_id": d.medicine_id,
                "medicine_name": med.name if med else "Unknown Medication",
                "dosage_amount": med.dosage_amount if med else None,
                "dosage_unit": med.dosage_unit.value if med and med.dosage_unit else None,
                "medicine_form": med.medicine_form.value if med and med.medicine_form else None,
                "instructions": med.instructions if med else None,
                "dose_quantity": sched.dose_quantity if sched else 1.0,
                "scheduled_time": _format_utc_iso(d.scheduled_time),
                "actual_time": _format_utc_iso(d.actual_time),
                "status": d.status.value,
            })
        return results
