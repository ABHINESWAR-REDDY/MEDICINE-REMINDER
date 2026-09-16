"""Caregiver service for supervising assigned patients, generating persistent clinical & refill alerts, and computing adherence reports."""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, ApprovalStatus
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.medicine import Medicine
from app.models.schedule import MedicationSchedule
from app.models.dose import MedicationDose, DoseStatus
from app.models.notification import Notification
from app.models.chat_message import ChatMessage
from app.services.dose_service import DoseService
from app.services.adherence_service import AdherenceService
from app.services.patient_service import PatientService
from app.schemas.caregiver import (
    CaregiverAdherencePatientItem,
    CaregiverAdherenceReportsResponse,
    MedicationAdherenceBreakdown,
    PatientAdherenceReportDetail,
    CaregiverRefillNotification,
    CaregiverRefillNotificationsResponse,
)


class CaregiverService:
    """Service handling patient supervision, persistent clinical/refill alerts, and adherence analytics for authorized caregivers."""

    def __init__(self, db: Session):
        self.db = db
        self.dose_service = DoseService(db)
        self.adherence_service = AdherenceService(db)
        self.patient_service = PatientService(db)

    def _verify_caregiver_access(self, caregiver_user: User):
        """Ensure caregiver is approved and active."""
        if caregiver_user.role != UserRole.CAREGIVER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Access restricted to Caregiver accounts."}
            )
        if caregiver_user.approval_status != ApprovalStatus.APPROVED or not caregiver_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CAREGIVER_UNAPPROVED", "message": "Caregiver account must be approved by an administrator."}
            )

    def _batch_reconcile_missed_doses(self, patient_ids: List[int]) -> int:
        """Batch transition overdue SCHEDULED doses to MISSED for given patient IDs in a single query."""
        if not patient_ids:
            return 0
        now_utc = datetime.now(timezone.utc)
        updated = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id.in_(patient_ids),
            MedicationDose.status == DoseStatus.SCHEDULED,
            MedicationDose.scheduled_time < now_utc
        ).update({"status": DoseStatus.MISSED}, synchronize_session=False)
        if updated > 0:
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
        return updated

    def get_assigned_patients(self, caregiver_user: User) -> List[Dict[str, Any]]:
        """Query and return only patients with an ACTIVE assignment to this caregiver using batched queries."""
        self._verify_caregiver_access(caregiver_user)

        assignments = self.db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver_user.id,
            CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
        ).all()

        if not assignments:
            return []

        patient_ids = [a.patient_id for a in assignments]

        # 1. Batch fetch Patient Users
        patients = self.db.query(User).filter(User.id.in_(patient_ids)).all()
        patient_map = {p.id: p for p in patients}

        # 2. Batch reconcile missed doses once
        self._batch_reconcile_missed_doses(patient_ids)

        # 3. Batch count active medicines
        med_count_rows = self.db.query(
            Medicine.user_id,
            func.count(Medicine.id)
        ).filter(
            Medicine.user_id.in_(patient_ids),
            Medicine.is_active == True
        ).group_by(Medicine.user_id).all()
        med_count_map = {row[0]: row[1] for row in med_count_rows}

        # 4. Batch compute 30-day adherence statistics
        now_utc = datetime.now(timezone.utc)
        start_30d = now_utc - timedelta(days=30)
        dose_counts_rows = self.db.query(
            MedicationDose.patient_id,
            MedicationDose.status,
            func.count(MedicationDose.id)
        ).filter(
            MedicationDose.patient_id.in_(patient_ids),
            MedicationDose.scheduled_time >= start_30d,
            MedicationDose.scheduled_time <= now_utc
        ).group_by(MedicationDose.patient_id, MedicationDose.status).all()

        adherence_stats: Dict[int, Dict[str, int]] = {pid: {"taken": 0, "missed": 0, "skipped": 0} for pid in patient_ids}
        for pid, st, cnt in dose_counts_rows:
            if pid in adherence_stats:
                st_val = st.value if hasattr(st, "value") else str(st)
                if st_val == DoseStatus.TAKEN.value:
                    adherence_stats[pid]["taken"] = cnt
                elif st_val == DoseStatus.MISSED.value:
                    adherence_stats[pid]["missed"] = cnt
                elif st_val == DoseStatus.SKIPPED.value:
                    adherence_stats[pid]["skipped"] = cnt

        results = []
        for a in assignments:
            patient = patient_map.get(a.patient_id)
            if not patient:
                continue

            # Retrieve today's doses for this patient
            doses = self.dose_service.get_patient_doses(patient_id=patient.id)
            today_taken = sum(1 for d in doses if d["status"] == DoseStatus.TAKEN.value)
            today_missed = sum(1 for d in doses if d["status"] == DoseStatus.MISSED.value)

            p_adh = adherence_stats.get(patient.id, {"taken": 0, "missed": 0, "skipped": 0})
            total_exp = p_adh["taken"] + p_adh["missed"] + p_adh["skipped"]
            if total_exp == 0:
                adh_pct = 100.0
                adh_status = "Good"
            else:
                adh_pct = round((p_adh["taken"] / total_exp) * 100.0, 1)
                if adh_pct >= 90.0:
                    adh_status = "Good"
                elif adh_pct >= 75.0:
                    adh_status = "Needs Attention"
                else:
                    adh_status = "High Risk"

            results.append({
                "id": patient.id,
                "employee_id": patient.employee_id or f"PT{patient.id:06d}",
                "name": patient.name,
                "email": patient.email,
                "created_at": patient.created_at,
                "medications_count": med_count_map.get(patient.id, 0),
                "today_doses_total": len(doses),
                "today_doses_taken": today_taken,
                "today_doses_missed": today_missed,
                "adherence_percentage": adh_pct,
                "adherence_status": adh_status,
                "_30d_taken": p_adh["taken"],
                "_30d_missed": p_adh["missed"],
                "_30d_skipped": p_adh["skipped"],
            })

        return results

    def get_dashboard(self, caregiver_user: User) -> Dict[str, Any]:
        """Compute aggregated statistics across all assigned patients with mathematically consistent adherence."""
        self._verify_caregiver_access(caregiver_user)
        patients = self.get_assigned_patients(caregiver_user)

        if not patients:
            return {
                "total_assigned_patients": 0,
                "today_doses_scheduled": 0,
                "today_doses_taken": 0,
                "today_doses_missed": 0,
                "today_doses_pending": 0,
                "overall_adherence_percentage": 100.0,
                "overall_adherence_status": "Good",
                "patients": [],
            }

        total_scheduled = sum(p["today_doses_total"] for p in patients)
        total_taken = sum(p["today_doses_taken"] for p in patients)
        total_missed = sum(p["today_doses_missed"] for p in patients)
        total_pending = total_scheduled - (total_taken + total_missed)

        # Mathematical adherence calculation across all assigned patients (30-day tracking window)
        total_30d_taken = sum(p.get("_30d_taken", 0) for p in patients)
        total_30d_missed = sum(p.get("_30d_missed", 0) for p in patients)
        total_30d_skipped = sum(p.get("_30d_skipped", 0) for p in patients)
        total_30d_expected = total_30d_taken + total_30d_missed + total_30d_skipped

        if total_30d_expected == 0:
            today_completed = total_taken + total_missed
            if today_completed == 0:
                overall_adherence = 100.0
                overall_status = "Good"
            else:
                overall_adherence = round((total_taken / today_completed) * 100.0, 1)
                overall_status = "Good" if overall_adherence >= 90.0 else ("Needs Attention" if overall_adherence >= 75.0 else "High Risk")
        else:
            overall_adherence = round((total_30d_taken / total_30d_expected) * 100.0, 1)
            overall_status = "Good" if overall_adherence >= 90.0 else ("Needs Attention" if overall_adherence >= 75.0 else "High Risk")

        # Strip internal temporary fields from patient dicts
        clean_patients = []
        for p in patients:
            clean_p = {k: v for k, v in p.items() if not k.startswith("_")}
            clean_patients.append(clean_p)

        return {
            "total_assigned_patients": len(clean_patients),
            "today_doses_scheduled": total_scheduled,
            "today_doses_taken": total_taken,
            "today_doses_missed": total_missed,
            "today_doses_pending": max(0, total_pending),
            "overall_adherence_percentage": overall_adherence,
            "overall_adherence_status": overall_status,
            "patients": clean_patients,
        }

    def get_patient_detail(self, caregiver_user: User, patient_id: int) -> Dict[str, Any]:
        """
        Retrieve comprehensive medical and adherence detail for a specific patient.
        STRICT SECURITY: Returns 403 if the patient is not actively assigned to this caregiver.
        """
        self._verify_caregiver_access(caregiver_user)

        assignment = self.db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver_user.id,
            CaregiverPatientAssignment.patient_id == patient_id,
            CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
        ).first()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You are not authorized to view this patient."}
            )

        patient = self.db.query(User).filter(User.id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "RESOURCE_NOT_FOUND", "message": "Patient record not found."}
            )

        # Retrieve medications
        meds = self.db.query(Medicine).filter(Medicine.user_id == patient_id).all()
        med_list = []
        for m in meds:
            scheds = self.db.query(MedicationSchedule).filter(
                MedicationSchedule.medicine_id == m.id,
                MedicationSchedule.is_active == True
            ).all()
            med_list.append({
                "id": m.id,
                "name": m.name,
                "dosage_amount": m.dosage_amount,
                "dosage_unit": m.dosage_unit.value if hasattr(m.dosage_unit, "value") else str(m.dosage_unit or ""),
                "medicine_form": m.medicine_form.value if hasattr(m.medicine_form, "value") else str(m.medicine_form or ""),
                "instructions": m.instructions,
                "schedules": [
                    {
                        "id": s.id,
                        "frequency_type": s.frequency_type.value if hasattr(s.frequency_type, "value") else str(s.frequency_type),
                        "scheduled_times": s.scheduled_times,
                        "dose_quantity": s.dose_quantity,
                        "start_date": s.start_date.isoformat(),
                        "end_date": s.end_date.isoformat() if s.end_date else None,
                    }
                    for s in scheds
                ]
            })

        today_doses = self.dose_service.get_patient_doses(patient_id)
        adherence_30 = self.adherence_service.calculate_adherence(patient_id, days=30)
        adherence_7 = self.adherence_service.calculate_adherence(patient_id, days=7)

        return {
            "patient": {
                "id": patient.id,
                "employee_id": patient.employee_id or f"PT{patient.id:06d}",
                "name": patient.name,
                "email": patient.email,
                "created_at": patient.created_at.isoformat() if patient.created_at else None,
            },
            "medications": med_list,
            "today_doses": today_doses,
            "adherence_30_days": adherence_30,
            "adherence_7_days": adherence_7,
        }

    def sync_caregiver_refill_notifications(self, caregiver_user: User) -> None:
        """
        Synchronize persistent database Notification records for caregiver refill warnings.
        Strict deduplication:
          - (caregiver_id, type='REFILL_NEEDED', related_medicine_id)
          - If stock is CRITICAL / LOW_STOCK -> ensures ONE unread notification exists in DB.
          - If stock is replenished -> marks existing notification as read / resolved.
          - If assignment revoked -> clears notifications for unassigned patients.
        """
        self._verify_caregiver_access(caregiver_user)
        now_utc = datetime.now(timezone.utc)

        # Get active assigned patient IDs
        active_assignments = self.db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver_user.id,
            CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
        ).all()
        active_patient_ids = {a.patient_id for a in active_assignments}

        # Clear any existing unread refill notifications for patients no longer actively assigned
        if active_patient_ids:
            medicines_of_active = self.db.query(Medicine.id).filter(Medicine.user_id.in_(active_patient_ids)).all()
            active_med_ids = {m[0] for m in medicines_of_active}
        else:
            active_med_ids = set()

        # Mark obsolete notifications as read
        if active_med_ids:
            self.db.query(Notification).filter(
                Notification.user_id == caregiver_user.id,
                Notification.type == "REFILL_NEEDED",
                Notification.is_read == False,
                ~Notification.related_medicine_id.in_(active_med_ids)
            ).update({"is_read": True}, synchronize_session=False)
        else:
            self.db.query(Notification).filter(
                Notification.user_id == caregiver_user.id,
                Notification.type == "REFILL_NEEDED",
                Notification.is_read == False
            ).update({"is_read": True}, synchronize_session=False)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        # Evaluate real refill predictions for each active assigned patient
        for patient_id in active_patient_ids:
            patient = self.db.query(User).filter(User.id == patient_id).first()
            if not patient:
                continue

            refill_res = self.patient_service.get_refill_predictions(patient.id)
            for pred in refill_res.predictions:
                if pred.status == "VALID" and pred.urgency_level in ("CRITICAL", "LOW_STOCK"):
                    is_crit = pred.urgency_level == "CRITICAL"
                    sev = "CRITICAL" if is_crit else "WARNING"
                    title = f"{'Critical Refill Alert' if is_crit else 'Refill Needed'}: {pred.medicine_name}"
                    rem_days = pred.estimated_remaining_days
                    rem_qty = pred.estimated_remaining_quantity
                    unit_str = f" {pred.unit}" if pred.unit else ""
                    msg = (
                        f"Refill needed: {pred.medicine_name} for {patient.name} — "
                        f"approximately {rem_days} days ({rem_qty}{unit_str}) of medication remaining."
                    )

                    # Check if unread notification already exists in DB for this medicine
                    existing = self.db.query(Notification).filter(
                        Notification.user_id == caregiver_user.id,
                        Notification.type == "REFILL_NEEDED",
                        Notification.related_medicine_id == pred.medicine_id
                    ).first()

                    if not existing:
                        notif = Notification(
                            user_id=caregiver_user.id,
                            type="REFILL_NEEDED",
                            title=title,
                            message=msg,
                            severity=sev,
                            related_medicine_id=pred.medicine_id,
                            is_read=False,
                            created_at=now_utc,
                        )
                        self.db.add(notif)
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
                        Notification.user_id == caregiver_user.id,
                        Notification.type == "REFILL_NEEDED",
                        Notification.related_medicine_id == pred.medicine_id,
                        Notification.is_read == False
                    ).update({"is_read": True}, synchronize_session=False)
                    try:
                        self.db.commit()
                    except Exception:
                        self.db.rollback()

    def get_refill_notifications(self, caregiver_user: User) -> CaregiverRefillNotificationsResponse:
        """
        Get dedicated list of persistent refill notifications for all patients assigned to this caregiver.
        Strictly zero records for unassigned patients and database-level deduplication.
        """
        self._verify_caregiver_access(caregiver_user)
        # Sync database records first
        self.sync_caregiver_refill_notifications(caregiver_user)

        # Retrieve active unread persistent refill notifications from DB
        db_notifs = self.db.query(Notification).filter(
            Notification.user_id == caregiver_user.id,
            Notification.type == "REFILL_NEEDED",
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).all()

        notifications: List[CaregiverRefillNotification] = []
        crit_count = 0
        low_count = 0

        med_ids = [n.related_medicine_id for n in db_notifs if n.related_medicine_id]
        meds = self.db.query(Medicine).filter(Medicine.id.in_(med_ids)).all() if med_ids else []
        med_map = {m.id: m for m in meds}

        patient_ids = {m.user_id for m in meds}
        patients = self.db.query(User).filter(User.id.in_(patient_ids)).all() if patient_ids else []
        patient_map = {p.id: p for p in patients}

        for n in db_notifs:
            med = med_map.get(n.related_medicine_id) if n.related_medicine_id else None
            patient = patient_map.get(med.user_id) if med else None
            if not med or not patient:
                continue

            r_res = self.patient_service.get_refill_predictions(patient.id)
            pred = next((p for p in r_res.predictions if p.medicine_id == med.id), None)

            is_crit = n.severity == "CRITICAL"
            if is_crit:
                crit_count += 1
            else:
                low_count += 1

            notifications.append(
                CaregiverRefillNotification(
                    id=f"notif_{n.id}",
                    patient_id=patient.id,
                    patient_employee_id=patient.employee_id or f"PT{patient.id:06d}",
                    patient_name=patient.name,
                    medicine_id=med.id,
                    medicine_name=med.name,
                    strength=med.dosage_amount,
                    unit=med.dosage_unit.value if hasattr(med.dosage_unit, "value") else str(med.dosage_unit or ""),
                    current_stock=med.quantity,
                    estimated_remaining_quantity=pred.estimated_remaining_quantity if pred else None,
                    estimated_remaining_days=pred.estimated_remaining_days if pred else None,
                    predicted_refill_date=pred.predicted_refill_date if pred else None,
                    urgency_level="CRITICAL" if is_crit else "LOW_STOCK",
                    severity=n.severity,
                    title=n.title,
                    message=n.message,
                    timestamp=n.created_at if n.created_at.tzinfo else n.created_at.replace(tzinfo=timezone.utc),
                )
            )

        return CaregiverRefillNotificationsResponse(
            caregiver_id=caregiver_user.id,
            total_notifications=len(notifications),
            critical_count=crit_count,
            low_stock_count=low_count,
            notifications=notifications,
        )

    def get_alerts(self, caregiver_user: User) -> List[Dict[str, Any]]:
        """
        Generate clinical alerts for missed doses, low adherence, unread chat messages,
        and persistent low-stock refill warnings among assigned patients ONLY without N+1 queries.
        """
        self._verify_caregiver_access(caregiver_user)

        assignments = self.db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver_user.id,
            CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
        ).all()
        patient_ids = [a.patient_id for a in assignments]

        if not patient_ids:
            return []

        # Batch load patient records
        patients = self.db.query(User).filter(User.id.in_(patient_ids)).all()
        patient_map = {p.id: p for p in patients}

        now_utc = datetime.now(timezone.utc)
        today_date = now_utc.date()

        # Reconcile doses for all assigned patients to capture newly missed/scheduled doses
        for pid in patient_ids:
            try:
                self.dose_service.generate_doses_for_patient(pid, target_date=today_date)
                self.dose_service.reconcile_missed_doses(patient_id=pid)
            except Exception:
                pass

        # Sync persistent refill notifications in database
        self.sync_caregiver_refill_notifications(caregiver_user)

        alerts = []
        start_scan = now_utc - timedelta(days=30)

        # 1. Missed dose alerts across assigned patients (batch loaded for past 30 days)
        missed_doses = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id.in_(patient_ids),
            MedicationDose.status == DoseStatus.MISSED,
            MedicationDose.scheduled_time >= start_scan,
            MedicationDose.scheduled_time <= now_utc
        ).order_by(MedicationDose.scheduled_time.desc()).all()

        missed_med_ids = {d.medicine_id for d in missed_doses}
        missed_meds = self.db.query(Medicine).filter(Medicine.id.in_(missed_med_ids)).all() if missed_med_ids else []
        missed_med_map = {m.id: m for m in missed_meds}        # Collect IDs of alerts that this caregiver has marked as read
        read_missed_ids = {
            n.related_dose_id for n in self.db.query(Notification.related_dose_id).filter(
                Notification.user_id == caregiver_user.id,
                Notification.type == "MISSED_DOSE",
                Notification.is_read == True,
                Notification.related_dose_id.isnot(None)
            ).all()
        }
        read_risk_pt_ids = {
            n.related_dose_id for n in self.db.query(Notification.related_dose_id).filter(
                Notification.user_id == caregiver_user.id,
                Notification.type == "ADHERENCE_RISK",
                Notification.is_read == True,
                Notification.related_dose_id.isnot(None)
            ).all()
        }

        for d in missed_doses:
            if d.id in read_missed_ids:
                continue
            med = missed_med_map.get(d.medicine_id)
            pt = patient_map.get(d.patient_id)
            if med and pt:
                dt_tz = d.scheduled_time if d.scheduled_time.tzinfo else d.scheduled_time.replace(tzinfo=timezone.utc)
                t_str = dt_tz.strftime("%H:%M")
                unit_val = med.dosage_unit.value if hasattr(med.dosage_unit, 'value') else str(med.dosage_unit) if med.dosage_unit else None
                form_val = med.medicine_form.value if hasattr(med.medicine_form, 'value') else str(med.medicine_form) if med.medicine_form else None

                alerts.append({
                    "id": f"missed_{d.id}",
                    "patient_id": pt.id,
                    "patient_employee_id": pt.employee_id or f"PT{pt.id:06d}",
                    "patient_name": pt.name,
                    "severity": "WARNING",
                    "type": "MISSED_DOSE",
                    "title": f"Missed Dose: {med.name}",
                    "message": f"Patient {pt.name} missed the {t_str} scheduled dose of {med.name}.",
                    "timestamp": dt_tz.isoformat(),
                    "medicine_name": med.name,
                    "strength": med.dosage_amount,
                    "unit": unit_val,
                    "dosage_form": form_val,
                })

        # 2. Low adherence alerts (< 75% in 30 days) using batched count
        start_30d = now_utc - timedelta(days=30)
        dose_counts_rows = self.db.query(
            MedicationDose.patient_id,
            MedicationDose.status,
            func.count(MedicationDose.id)
        ).filter(
            MedicationDose.patient_id.in_(patient_ids),
            MedicationDose.scheduled_time >= start_30d,
            MedicationDose.scheduled_time <= now_utc
        ).group_by(MedicationDose.patient_id, MedicationDose.status).all()

        adherence_counts: Dict[int, Dict[str, int]] = {pid: {"taken": 0, "missed": 0, "skipped": 0} for pid in patient_ids}
        for pid, st, cnt in dose_counts_rows:
            if pid in adherence_counts:
                st_val = st.value if hasattr(st, "value") else str(st)
                if st_val == DoseStatus.TAKEN.value:
                    adherence_counts[pid]["taken"] = cnt
                elif st_val == DoseStatus.MISSED.value:
                    adherence_counts[pid]["missed"] = cnt
                elif st_val == DoseStatus.SKIPPED.value:
                    adherence_counts[pid]["skipped"] = cnt

        for pid in patient_ids:
            if pid in read_risk_pt_ids:
                continue
            pt = patient_map.get(pid)
            if not pt:
                continue
            cnts = adherence_counts.get(pid, {"taken": 0, "missed": 0, "skipped": 0})
            total_exp = cnts["taken"] + cnts["missed"] + cnts["skipped"]
            if total_exp > 0:
                adh_pct = round((cnts["taken"] / total_exp) * 100.0, 1)
                if adh_pct < 75.0:
                    alerts.append({
                        "id": f"adherence_risk_{pt.id}",
                        "patient_id": pt.id,
                        "patient_employee_id": pt.employee_id or f"PT{pt.id:06d}",
                        "patient_name": pt.name,
                        "severity": "CRITICAL",
                        "type": "ADHERENCE_RISK",
                        "title": f"High Adherence Risk: {pt.name}",
                        "message": f"Adherence has dropped to {adh_pct}% over the last 30 days.",
                        "timestamp": now_utc.isoformat(),
                    })


        # 3. Persistent Refill Warnings from database (batch loaded)
        db_refill_notifs = self.db.query(Notification).filter(
            Notification.user_id == caregiver_user.id,
            Notification.type == "REFILL_NEEDED",
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).all()

        refill_med_ids = {n.related_medicine_id for n in db_refill_notifs if n.related_medicine_id}
        refill_meds = self.db.query(Medicine).filter(Medicine.id.in_(refill_med_ids)).all() if refill_med_ids else []
        refill_med_map = {m.id: m for m in refill_meds}

        for n in db_refill_notifs:
            med = refill_med_map.get(n.related_medicine_id) if n.related_medicine_id else None
            pt = patient_map.get(med.user_id) if med else None
            if med and pt and pt.id in patient_ids:
                alerts.append({
                    "id": f"notif_{n.id}",
                    "patient_id": pt.id,
                    "patient_employee_id": pt.employee_id or f"PT{pt.id:06d}",
                    "patient_name": pt.name,
                    "severity": n.severity,
                    "type": "REFILL_NEEDED",
                    "title": n.title,
                    "message": n.message,
                    "timestamp": n.created_at.isoformat() if n.created_at else now_utc.isoformat(),
                    "medicine_name": med.name,
                    "urgency_level": "CRITICAL" if n.severity == "CRITICAL" else "LOW_STOCK",
                })

        # 4. Unread Patient Chat Messages (batch loaded, excluding deleted/cleared)
        unread_msgs = self.db.query(ChatMessage).filter(
            ChatMessage.sender_id.in_(patient_ids),
            ChatMessage.recipient_id == caregiver_user.id,
            ChatMessage.is_read == False,
            ChatMessage.is_deleted == False,
            ChatMessage.cleared_by_recipient == False
        ).order_by(ChatMessage.created_at.desc()).all()

        for m in unread_msgs:
            pt = patient_map.get(m.sender_id)
            if pt:
                preview = (m.message[:80] + "...") if len(m.message) > 80 else m.message
                m_dt = m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=timezone.utc)
                alerts.append({
                    "id": f"chat_msg_{m.id}",
                    "patient_id": pt.id,
                    "patient_employee_id": pt.employee_id or f"PT{pt.id:06d}",
                    "patient_name": pt.name,
                    "severity": "INFO",
                    "type": "CHAT_MESSAGE",
                    "title": f"New Message from {pt.name}",
                    "message": f'You have received a message from this patient: "{preview}"',
                    "timestamp": m_dt.isoformat(),
                })

        return alerts

    def get_adherence_reports(self, caregiver_user: User, days: int = 30) -> CaregiverAdherenceReportsResponse:
        """
        Generate dynamic adherence reports across all assigned patients for the given date window using batched queries.
        """
        self._verify_caregiver_access(caregiver_user)

        assignments = self.db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver_user.id,
            CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
        ).all()

        if not assignments:
            return CaregiverAdherenceReportsResponse(
                caregiver_id=caregiver_user.id,
                period_days=days,
                total_assigned_patients=0,
                overall_adherence_percentage=100.0,
                overall_adherence_status="Good",
                high_risk_count=0,
                needs_attention_count=0,
                good_standing_count=0,
                reports=[],
            )

        patient_ids = [a.patient_id for a in assignments]
        patients = self.db.query(User).filter(User.id.in_(patient_ids)).all()
        patient_map = {p.id: p for p in patients}

        # Batch reconcile missed doses once
        self._batch_reconcile_missed_doses(patient_ids)

        # Batch active medicine counts
        med_count_rows = self.db.query(
            Medicine.user_id,
            func.count(Medicine.id)
        ).filter(
            Medicine.user_id.in_(patient_ids),
            Medicine.is_active == True
        ).group_by(Medicine.user_id).all()
        med_count_map = {row[0]: row[1] for row in med_count_rows}

        reports: List[CaregiverAdherencePatientItem] = []
        total_taken = 0
        total_expected = 0
        high_risk = 0
        needs_att = 0
        good_cnt = 0

        for a in assignments:
            patient = patient_map.get(a.patient_id)
            if not patient:
                continue

            # Calculate adherence for the specific requested days period
            adh = self.adherence_service.calculate_adherence(patient_id=patient.id, days=days)
            med_count = med_count_map.get(patient.id, 0)

            status_cat = adh["adherence_status"]
            if status_cat == "High Risk":
                high_risk += 1
            elif status_cat == "Needs Attention":
                needs_att += 1
            else:
                good_cnt += 1

            total_taken += adh["taken_count"]
            total_expected += adh["total_expected_doses"]

            reports.append(
                CaregiverAdherencePatientItem(
                    patient_id=patient.id,
                    employee_id=patient.employee_id or f"PT{patient.id:06d}",
                    name=patient.name,
                    email=patient.email,
                    account_created_at=patient.created_at,
                    adherence_percentage=adh["adherence_percentage"],
                    adherence_status=adh["adherence_status"],
                    total_expected_doses=adh["total_expected_doses"],
                    taken_count=adh["taken_count"],
                    missed_count=adh["missed_count"],
                    skipped_count=adh["skipped_count"],
                    active_medications_count=med_count,
                )
            )

        if total_expected == 0:
            overall_adh = 100.0
            overall_status = "Good"
        else:
            overall_adh = round((total_taken / total_expected) * 100.0, 1)
            overall_status = "Good" if overall_adh >= 90.0 else ("Needs Attention" if overall_adh >= 75.0 else "High Risk")

        return CaregiverAdherenceReportsResponse(
            caregiver_id=caregiver_user.id,
            period_days=days,
            total_assigned_patients=len(reports),
            overall_adherence_percentage=overall_adh,
            overall_adherence_status=overall_status,
            high_risk_count=high_risk,
            needs_attention_count=needs_att,
            good_standing_count=good_cnt,
            reports=reports,
        )

    def get_patient_adherence_report(
        self,
        caregiver_user: User,
        patient_id: int,
        days: int = 30
    ) -> PatientAdherenceReportDetail:
        """
        Retrieve deep-dive adherence analytics, medication-specific compliance,
        and current refill status for a single assigned patient.
        STRICT SECURITY: Returns HTTP 403 if patient is not actively assigned to caregiver.
        """
        self._verify_caregiver_access(caregiver_user)

        assignment = self.db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver_user.id,
            CaregiverPatientAssignment.patient_id == patient_id,
            CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
        ).first()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You are not authorized to view adherence reports for this patient."}
            )

        patient = self.db.query(User).filter(User.id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "RESOURCE_NOT_FOUND", "message": "Patient record not found."}
            )

        # 1. Overall adherence for period
        adherence_summary = self.adherence_service.calculate_adherence(patient_id=patient.id, days=days)

        # 2. Refill predictions for this patient
        refill_res = self.patient_service.get_refill_predictions(patient.id)
        refill_map = {p.medicine_id: p for p in refill_res.predictions}

        # 3. Medication-wise adherence breakdown in period
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=days)

        medicines = self.db.query(Medicine).filter(Medicine.user_id == patient.id).all()
        med_breakdown: List[MedicationAdherenceBreakdown] = []

        for m in medicines:
            med_doses = self.db.query(MedicationDose).filter(
                MedicationDose.patient_id == patient.id,
                MedicationDose.medicine_id == m.id,
                MedicationDose.scheduled_time >= start_utc,
                MedicationDose.scheduled_time <= now_utc
            ).all()

            taken = sum(1 for d in med_doses if d.status == DoseStatus.TAKEN)
            missed = sum(1 for d in med_doses if d.status == DoseStatus.MISSED)
            skipped = sum(1 for d in med_doses if d.status == DoseStatus.SKIPPED)
            total = taken + missed + skipped

            adh_pct = round((taken / total * 100.0), 1) if total > 0 else 100.0
            r_pred = refill_map.get(m.id)

            med_breakdown.append(
                MedicationAdherenceBreakdown(
                    medicine_id=m.id,
                    medicine_name=m.name,
                    strength=m.dosage_amount,
                    unit=m.dosage_unit.value if hasattr(m.dosage_unit, "value") else str(m.dosage_unit or ""),
                    dosage_form=m.medicine_form.value if hasattr(m.medicine_form, "value") else str(m.medicine_form or ""),
                    total_expected=total,
                    taken_count=taken,
                    missed_count=missed,
                    skipped_count=skipped,
                    adherence_percentage=adh_pct,
                    current_stock=m.quantity,
                    estimated_remaining_days=r_pred.estimated_remaining_days if r_pred else None,
                    refill_status=r_pred.status if r_pred else None,
                )
            )

        # 4. Recent dose events in window (up to 50 items)
        recent_doses = self.db.query(MedicationDose).filter(
            MedicationDose.patient_id == patient.id,
            MedicationDose.scheduled_time >= start_utc,
            MedicationDose.scheduled_time <= now_utc
        ).order_by(MedicationDose.scheduled_time.desc()).limit(50).all()

        recent_events = []
        for d in recent_doses:
            med = next((m for m in medicines if m.id == d.medicine_id), None)
            sched = d.schedule
            recent_events.append({
                "id": d.id,
                "medicine_id": d.medicine_id,
                "medicine_name": med.name if med else "Medication",
                "scheduled_time": d.scheduled_time.isoformat() if d.scheduled_time else None,
                "actual_time": d.actual_time.isoformat() if d.actual_time else None,
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "dose_quantity": sched.dose_quantity if sched else 1.0,
            })

        return PatientAdherenceReportDetail(
            patient={
                "id": patient.id,
                "employee_id": patient.employee_id or f"PT{patient.id:06d}",
                "name": patient.name,
                "email": patient.email,
                "account_created_at": patient.created_at.isoformat() if patient.created_at else None,
            },
            period_days=days,
            adherence_summary=adherence_summary,
            medication_breakdown=med_breakdown,
            recent_dose_events=recent_events,
            refill_predictions=refill_res.predictions,
        )

    def mark_alert_read(self, caregiver_user: User, alert_id: str) -> Dict[str, Any]:
        """
        Mark a specific caregiver alert as read/acknowledged.
        Supports:
        - 'missed_{dose_id}'
        - 'notif_{notif_id}' (or numeric notif_id)
        - 'chat_msg_{message_id}'
        - 'adherence_risk_{patient_id}'
        """
        self._verify_caregiver_access(caregiver_user)
        now_utc = datetime.now(timezone.utc)

        if alert_id.startswith("missed_"):
            try:
                dose_id = int(alert_id.replace("missed_", ""))
                existing = self.db.query(Notification).filter(
                    Notification.user_id == caregiver_user.id,
                    Notification.type == "MISSED_DOSE",
                    Notification.related_dose_id == dose_id
                ).first()
                if not existing:
                    notif = Notification(
                        user_id=caregiver_user.id,
                        type="MISSED_DOSE",
                        title="Missed Dose Acknowledged",
                        message=f"Acknowledged missed dose #{dose_id}",
                        severity="INFO",
                        related_dose_id=dose_id,
                        is_read=True,
                        created_at=now_utc
                    )
                    self.db.add(notif)
                else:
                    existing.is_read = True
                    existing.updated_at = now_utc
                self.db.commit()
                return {"success": True, "alert_id": alert_id}
            except Exception as e:
                self.db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

        elif alert_id.startswith("chat_msg_"):
            try:
                msg_id = int(alert_id.replace("chat_msg_", ""))
                msg = self.db.query(ChatMessage).filter(
                    ChatMessage.id == msg_id,
                    ChatMessage.recipient_id == caregiver_user.id
                ).first()
                if msg:
                    msg.is_read = True
                    self.db.commit()
                return {"success": True, "alert_id": alert_id}
            except Exception as e:
                self.db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

        elif alert_id.startswith("adherence_risk_"):
            try:
                pt_id = int(alert_id.replace("adherence_risk_", ""))
                existing = self.db.query(Notification).filter(
                    Notification.user_id == caregiver_user.id,
                    Notification.type == "ADHERENCE_RISK",
                    Notification.related_dose_id == pt_id
                ).first()
                if not existing:
                    notif = Notification(
                        user_id=caregiver_user.id,
                        type="ADHERENCE_RISK",
                        title=f"Adherence Risk Acknowledged for Patient {pt_id}",
                        message=f"Caregiver acknowledged adherence risk for patient {pt_id}",
                        severity="INFO",
                        related_dose_id=pt_id,
                        is_read=True,
                        created_at=now_utc
                    )
                    self.db.add(notif)
                else:
                    existing.is_read = True
                    existing.updated_at = now_utc
                self.db.commit()
                return {"success": True, "alert_id": alert_id}
            except Exception as e:
                self.db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

        else:
            try:
                clean_id = int(alert_id.replace("notif_", ""))
                notif = self.db.query(Notification).filter(
                    Notification.id == clean_id,
                    Notification.user_id == caregiver_user.id
                ).first()
                if notif:
                    notif.is_read = True
                    notif.updated_at = now_utc
                    self.db.commit()
                return {"success": True, "alert_id": alert_id}
            except Exception as e:
                self.db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    def mark_all_alerts_read(self, caregiver_user: User) -> Dict[str, Any]:
        """
        Mark all current clinical alerts as read/acknowledged for this caregiver.
        """
        self._verify_caregiver_access(caregiver_user)
        current_alerts = self.get_alerts(caregiver_user)
        for a in current_alerts:
            try:
                self.mark_alert_read(caregiver_user, a["id"])
            except Exception:
                pass
        return {"success": True, "count": len(current_alerts)}
