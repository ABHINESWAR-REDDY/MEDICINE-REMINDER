"""Patient Notification & Medication Alert Service handling real-time reminders, missed doses, and state management."""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.models.user import User, UserRole
from app.models.medicine import Medicine
from app.models.schedule import MedicationSchedule
from app.models.dose import MedicationDose, DoseStatus
from app.models.notification import Notification
from app.models.system_setting import get_notification_settings_from_db
from app.services.dose_service import DoseService


def _format_time_str(dt: datetime) -> str:
    """Format scheduled time into clean string (e.g. '08:00')."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%H:%M")


class NotificationService:
    """Service managing database-driven medication reminders, missed dose alerts, and unread counters."""

    def __init__(self, db: Session):
        self.db = db
        self.dose_service = DoseService(db)

    def _ensure_utc_dt(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure naive UTC datetime carries explicit timezone for JSON serialization."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def generate_patient_notifications(self, patient_user: User) -> None:
        """
        Scan patient's real medication schedules and doses to generate reminders, missed dose alerts, and refill warnings.
        Guarantees strict deduplication using (user_id, type, related_dose_id) and (user_id, type, related_medicine_id).
        """
        settings = get_notification_settings_from_db(self.db)
        now_utc = datetime.now(timezone.utc)
        today_date = now_utc.date()

        # 1. Ensure doses for today are generated and overdue doses reconciled
        self.dose_service.generate_doses_for_patient(patient_user.id, target_date=today_date)
        self.dose_service.reconcile_missed_doses(patient_id=patient_user.id)

        # 2. Fetch doses for the patient from the past 30 days to upcoming 2 days
        start_scan = now_utc - timedelta(days=30)
        end_scan = now_utc + timedelta(days=2)

        doses = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id == patient_user.id,
            MedicationDose.scheduled_time >= start_scan,
            MedicationDose.scheduled_time <= end_scan
        ).order_by(MedicationDose.scheduled_time.asc()).all()

        med_ids = {d.medicine_id for d in doses}
        meds = self.db.query(Medicine).filter(Medicine.id.in_(med_ids)).all() if med_ids else []
        med_map = {m.id: m for m in meds}

        for d in doses:
            med = med_map.get(d.medicine_id)
            med_name = med.name if med else "Medication"
            t_str = _format_time_str(d.scheduled_time)

            if d.status == DoseStatus.MISSED and settings.get("patient_missed_dose_alerts_enabled", True):
                # Check for existing MISSED_DOSE notification
                existing = self.db.query(Notification).filter(
                    Notification.user_id == patient_user.id,
                    Notification.type == "MISSED_DOSE",
                    Notification.related_dose_id == d.id
                ).first()

                if not existing:
                    notif = Notification(
                        user_id=patient_user.id,
                        type="MISSED_DOSE",
                        title=f"Missed Dose: {med_name}",
                        message=f"You missed your scheduled {t_str} dose of {med_name}.",
                        severity="WARNING",
                        related_dose_id=d.id,
                        related_medicine_id=d.medicine_id,
                        is_read=False,
                        created_at=d.scheduled_time
                    )
                    self.db.add(notif)
                    try:
                        self.db.commit()
                    except Exception:
                        self.db.rollback()

                # If there was an earlier reminder for this dose, mark it as read so it doesn't clutter
                self.db.query(Notification).filter(
                    Notification.user_id == patient_user.id,
                    Notification.type == "MEDICATION_REMINDER",
                    Notification.related_dose_id == d.id
                ).update({"is_read": True}, synchronize_session=False)
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()

            elif d.status == DoseStatus.SCHEDULED and settings.get("patient_medication_reminders_enabled", True):
                # Upcoming or due dose -> create MEDICATION_REMINDER
                existing = self.db.query(Notification).filter(
                    Notification.user_id == patient_user.id,
                    Notification.type == "MEDICATION_REMINDER",
                    Notification.related_dose_id == d.id
                ).first()

                if not existing:
                    notif = Notification(
                        user_id=patient_user.id,
                        type="MEDICATION_REMINDER",
                        title=f"Medication Reminder: {med_name}",
                        message=f"Your scheduled dose of {med_name} is due at {t_str}.",
                        severity="INFO",
                        related_dose_id=d.id,
                        related_medicine_id=d.medicine_id,
                        is_read=False,
                        created_at=d.scheduled_time
                    )
                    self.db.add(notif)
                    try:
                        self.db.commit()
                    except Exception:
                        self.db.rollback()

            elif d.status in (DoseStatus.TAKEN, DoseStatus.SKIPPED):
                # When taken or skipped, mark any reminders for this dose as read
                self.db.query(Notification).filter(
                    Notification.user_id == patient_user.id,
                    Notification.related_dose_id == d.id,
                    Notification.type.in_(["MEDICATION_REMINDER", "MISSED_DOSE"])
                ).update({"is_read": True}, synchronize_session=False)
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()

        # 3. Dynamic Refill Predictions for Patient
        if settings.get("patient_refill_alerts_enabled", True):
            try:
                from app.services.patient_service import PatientService
                patient_service = PatientService(self.db)
                refill_res = patient_service.get_refill_predictions(patient_user.id)
                for pred in refill_res.predictions:
                    if pred.status == "VALID" and pred.urgency_level in ("CRITICAL", "LOW_STOCK"):
                        is_crit = pred.urgency_level == "CRITICAL"
                        sev = "CRITICAL" if is_crit else "WARNING"
                        title = f"{'Critical Refill Alert' if is_crit else 'Refill Needed'}: {pred.medicine_name}"
                        rem_days = pred.estimated_remaining_days
                        rem_qty = pred.estimated_remaining_quantity
                        unit_str = f" {pred.unit}" if pred.unit else ""
                        msg = (
                            f"Refill needed: {pred.medicine_name} — approximately {rem_days} days "
                            f"({rem_qty}{unit_str}) of medication remaining."
                        )

                        existing = self.db.query(Notification).filter(
                            Notification.user_id == patient_user.id,
                            Notification.type == "REFILL_NEEDED",
                            Notification.related_medicine_id == pred.medicine_id
                        ).first()

                        if not existing:
                            notif = Notification(
                                user_id=patient_user.id,
                                type="REFILL_NEEDED",
                                title=title,
                                message=msg,
                                severity=sev,
                                related_medicine_id=pred.medicine_id,
                                is_read=False,
                                created_at=now_utc
                            )
                            self.db.add(notif)
                            try:
                                self.db.commit()
                            except Exception:
                                self.db.rollback()
                        else:
                            existing.title = title
                            existing.message = msg
                            existing.severity = sev
                            existing.updated_at = now_utc
                            try:
                                self.db.commit()
                            except Exception:
                                self.db.rollback()

                    elif pred.urgency_level in ("GOOD", "MODERATE") or pred.status == "ENDED":
                        self.db.query(Notification).filter(
                            Notification.user_id == patient_user.id,
                            Notification.type == "REFILL_NEEDED",
                            Notification.related_medicine_id == pred.medicine_id,
                            Notification.is_read == False
                        ).update({"is_read": True}, synchronize_session=False)
                        try:
                            self.db.commit()
                        except Exception:
                            self.db.rollback()
            except Exception:
                pass

    def get_patient_notifications(
        self,
        patient_user: User,
        filter_type: Optional[str] = None,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve full notification history for currently authenticated patient with filtering."""
        # Refresh real alerts first
        self.generate_patient_notifications(patient_user)

        query = self.db.query(Notification).filter(
            Notification.user_id == patient_user.id
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        if filter_type:
            clean_type = filter_type.upper().strip()
            if clean_type in ("MEDICATION_REMINDER", "REMINDER", "MEDICATION REMINDERS"):
                query = query.filter(Notification.type == "MEDICATION_REMINDER")
            elif clean_type in ("MISSED_DOSE", "MISSED", "MISSED DOSES"):
                query = query.filter(Notification.type == "MISSED_DOSE")
            elif clean_type in ("REFILL_NEEDED", "REFILL", "REFILL ALERTS"):
                query = query.filter(Notification.type == "REFILL_NEEDED")
            elif clean_type in ("UNREAD",):
                query = query.filter(Notification.is_read == False)

        notifications = query.order_by(desc(Notification.created_at)).all()
        results: List[Dict[str, Any]] = []

        for n in notifications:
            med_name = None
            med_id = n.related_medicine_id
            sched_time = None
            strength = None
            unit = None
            dosage_form = None

            med = None
            if n.related_dose_id:
                dose = self.db.query(MedicationDose).filter(MedicationDose.id == n.related_dose_id).first()
                if dose:
                    sched_time = self._ensure_utc_dt(dose.scheduled_time)
                    if dose.medicine_id:
                        med_id = dose.medicine_id
                        med = self.db.query(Medicine).filter(Medicine.id == dose.medicine_id).first()
            elif n.related_medicine_id:
                med = self.db.query(Medicine).filter(Medicine.id == n.related_medicine_id).first()

            if med:
                med_name = med.name
                strength = med.dosage_amount
                unit = med.dosage_unit.value if hasattr(med.dosage_unit, 'value') else str(med.dosage_unit) if med.dosage_unit else None
                dosage_form = med.medicine_form.value if hasattr(med.medicine_form, 'value') else str(med.medicine_form) if med.medicine_form else None

            if sched_time is None:
                sched_time = self._ensure_utc_dt(n.created_at)

            results.append({
                "id": n.id,
                "user_id": n.user_id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "severity": n.severity,
                "related_dose_id": n.related_dose_id,
                "related_medicine_id": med_id,
                "medicine_id": med_id,
                "medicine_name": med_name,
                "strength": strength,
                "unit": unit,
                "dosage_form": dosage_form,
                "scheduled_time": sched_time,
                "is_read": n.is_read,
                "created_at": self._ensure_utc_dt(n.created_at),
            })

        return results


    def get_unread_count(self, patient_user: User) -> int:
        """Calculate active unread notification count for patient."""
        self.generate_patient_notifications(patient_user)
        return self.db.query(Notification).filter(
            Notification.user_id == patient_user.id,
            Notification.is_read == False
        ).count()

    def mark_as_read(self, patient_user: User, notification_id: int) -> Dict[str, Any]:
        """Mark a single notification as read, enforcing patient isolation."""
        notif = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == patient_user.id
        ).first()

        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found or access denied."}
            )

        notif.is_read = True
        self.db.commit()
        return {"success": True, "message": "Notification marked as read."}

    def mark_all_as_read(self, patient_user: User) -> Dict[str, Any]:
        """Mark all unread notifications for patient as read."""
        self.db.query(Notification).filter(
            Notification.user_id == patient_user.id,
            Notification.is_read == False
        ).update({"is_read": True}, synchronize_session=False)
        self.db.commit()
        return {"success": True, "message": "All notifications marked as read."}
