"""Seed real data in pillsync.db for live browser and API verification."""

from datetime import datetime, date, timezone, timedelta
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole, ApprovalStatus
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.medicine import Medicine, MedicineForm, DosageUnit
from app.models.schedule import MedicationSchedule, ScheduleFrequency
from app.models.dose import MedicationDose, DoseStatus
from app.models.chat_message import ChatMessage
from app.models.notification import Notification
from app.services.dose_service import DoseService
from app.services.caregiver_service import CaregiverService
from app.services.notification_service import NotificationService


def setup_verification_data():
    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        # 1. Patient User
        patient = db.query(User).filter(User.email == "patient@pillsync.com").first()
        if not patient:
            patient = User(
                email="patient@pillsync.com",
                name="Alex Mercer",
                password_hash=get_password_hash("Password123!"),
                role=UserRole.PATIENT,
                approval_status=ApprovalStatus.APPROVED,
                is_active=True,
                employee_id="PT000001",
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
        else:
            patient.password_hash = get_password_hash("Password123!")
            patient.approval_status = ApprovalStatus.APPROVED
            patient.is_active = True
            db.commit()

        # 2. Caregiver User
        caregiver = db.query(User).filter(User.email == "caregiver@pillsync.com").first()
        if not caregiver:
            caregiver = User(
                email="caregiver@pillsync.com",
                name="Dr. Elena Vance",
                password_hash=get_password_hash("Password123!"),
                role=UserRole.CAREGIVER,
                approval_status=ApprovalStatus.APPROVED,
                is_active=True,
                employee_id="CG000001",
            )
            db.add(caregiver)
            db.commit()
            db.refresh(caregiver)
        else:
            caregiver.password_hash = get_password_hash("Password123!")
            caregiver.approval_status = ApprovalStatus.APPROVED
            caregiver.is_active = True
            db.commit()

        # 3. Active Assignment
        assignment = db.query(CaregiverPatientAssignment).filter(
            CaregiverPatientAssignment.caregiver_id == caregiver.id,
            CaregiverPatientAssignment.patient_id == patient.id,
        ).first()
        if not assignment:
            assignment = CaregiverPatientAssignment(
                caregiver_id=caregiver.id,
                patient_id=patient.id,
                status=AssignmentStatus.ACTIVE,
            )
            db.add(assignment)
            db.commit()
        else:
            assignment.status = AssignmentStatus.ACTIVE
            db.commit()

        # 4. Medicines for Patient Alex Mercer
        # Medicine 1: Metformin 500mg (Daily dose, missed earlier today)
        med1 = db.query(Medicine).filter(Medicine.user_id == patient.id, Medicine.name == "Metformin 500mg").first()
        if not med1:
            med1 = Medicine(
                user_id=patient.id,
                name="Metformin 500mg",
                dosage_amount=500.0,
                dosage_unit=DosageUnit.MG,
                medicine_form=MedicineForm.TABLET,
                quantity=30,
                instructions="Take with food after breakfast",
                start_date=today - timedelta(days=5),
                is_active=True,
            )
            db.add(med1)
            db.commit()
            db.refresh(med1)

        sched1 = db.query(MedicationSchedule).filter(MedicationSchedule.medicine_id == med1.id).first()
        if not sched1:
            sched1 = MedicationSchedule(
                medicine_id=med1.id,
                frequency_type=ScheduleFrequency.TWICE_DAILY,
                times_per_day=2,
                scheduled_times=["08:00", "20:00"],
                dose_quantity=1.0,
                start_date=today - timedelta(days=5),
                is_active=True,
            )
            db.add(sched1)
            db.commit()
            db.refresh(sched1)

        # Medicine 2: Atorvastatin 20mg (Low stock -> Refill Needed)
        med2 = db.query(Medicine).filter(Medicine.user_id == patient.id, Medicine.name == "Atorvastatin 20mg").first()
        if not med2:
            med2 = Medicine(
                user_id=patient.id,
                name="Atorvastatin 20mg",
                dosage_amount=20.0,
                dosage_unit=DosageUnit.MG,
                medicine_form=MedicineForm.TABLET,
                quantity=2,  # Low stock
                instructions="Take 1 tablet at night",
                start_date=today - timedelta(days=10),
                is_active=True,
            )
            db.add(med2)
            db.commit()
            db.refresh(med2)
        else:
            med2.quantity = 2
            db.commit()

        sched2 = db.query(MedicationSchedule).filter(MedicationSchedule.medicine_id == med2.id).first()
        if not sched2:
            sched2 = MedicationSchedule(
                medicine_id=med2.id,
                frequency_type=ScheduleFrequency.ONCE_DAILY,
                times_per_day=1,
                scheduled_times=["21:00"],
                dose_quantity=1.0,
                start_date=today - timedelta(days=10),
                is_active=True,
            )
            db.add(sched2)
            db.commit()
            db.refresh(sched2)

        # 5. Doses generation and missed doses reconciliation
        dose_service = DoseService(db)
        dose_service.generate_doses_for_patient(patient.id, target_date=today)
        dose_service.reconcile_missed_doses(patient_id=patient.id)

        # 6. Generate Patient and Caregiver notifications
        notif_service = NotificationService(db)
        notif_service.generate_patient_notifications(patient)

        cg_service = CaregiverService(db)
        cg_service.get_alerts(caregiver)

        # 7. Add a chat message from Patient to Caregiver
        chat_msg = db.query(ChatMessage).filter(
            ChatMessage.sender_id == patient.id,
            ChatMessage.recipient_id == caregiver.id,
            ChatMessage.is_read == False,
        ).first()
        if not chat_msg:
            chat_msg = ChatMessage(
                sender_id=patient.id,
                recipient_id=caregiver.id,
                message="Hi Dr. Vance, I experienced mild dizziness after today's morning dose.",
                is_read=False,
                is_deleted=False,
                cleared_by_sender=False,
                cleared_by_recipient=False,
            )
            db.add(chat_msg)
            db.commit()

        print("=== Real verification data successfully configured in database ===")
        print(f"Patient: {patient.name} ({patient.email}) - Password: Password123!")
        print(f"Caregiver: {caregiver.name} ({caregiver.email}) - Password: Password123!")
        print("Assignment: Active")
        print(f"Patient unread notifications: {notif_service.get_unread_count(patient)}")
        print(f"Caregiver alerts count: {len(cg_service.get_alerts(caregiver))}")

    finally:
        db.close()


if __name__ == "__main__":
    setup_verification_data()
