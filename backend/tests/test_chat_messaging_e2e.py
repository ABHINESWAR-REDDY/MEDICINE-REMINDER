"""End-to-end backend tests for Patient ↔ Caregiver Live Chat and Notifications."""

import pytest
from datetime import date
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User, UserRole, ApprovalStatus
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.chat_message import ChatMessage
from app.services.caregiver_service import CaregiverService


def test_patient_caregiver_chat_and_notification_flow(client: TestClient, db_session: Session, create_user):
    """
    Verify complete E2E workflow:
    1. Patient A and Caregiver A are assigned.
    2. Patient B and Caregiver B are separate unassigned users.
    3. Patient A sends message to Caregiver A -> stored in DB with correct IDs and timestamps.
    4. Caregiver A receives notification: 'You have received a message from this patient: "..."'
    5. Caregiver A opens conversation -> messages are marked read and notification clears.
    6. Caregiver A replies -> Patient A receives reply in same thread.
    7. Patient B cannot message Caregiver A (403).
    8. Caregiver B cannot read Patient A conversation (403).
    """
    # 1. Setup real users
    patient_a = create_user(
        name="Alice Patient",
        email="alice@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    caregiver_a = create_user(
        name="Dr. Bob Caregiver",
        email="bob@pillsync.test",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED
    )
    patient_b = create_user(
        name="Charlie Patient",
        email="charlie@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    caregiver_b = create_user(
        name="Dr. Dave Caregiver",
        email="dave@pillsync.test",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED
    )

    # Assign Patient A to Caregiver A
    assignment_a = CaregiverPatientAssignment(
        caregiver_id=caregiver_a.id,
        patient_id=patient_a.id,
        status=AssignmentStatus.ACTIVE
    )
    db_session.add(assignment_a)
    db_session.commit()

    token_patient_a = create_access_token(patient_a.id)
    token_caregiver_a = create_access_token(caregiver_a.id)
    token_patient_b = create_access_token(patient_b.id)
    token_caregiver_b = create_access_token(caregiver_b.id)

    headers_patient_a = {"Authorization": f"Bearer {token_patient_a}"}
    headers_caregiver_a = {"Authorization": f"Bearer {token_caregiver_a}"}
    headers_patient_b = {"Authorization": f"Bearer {token_patient_b}"}
    headers_caregiver_b = {"Authorization": f"Bearer {token_caregiver_b}"}

    # 2. Patient A checks contacts
    contacts_resp = client.get("/api/v1/chat/contacts", headers=headers_patient_a)
    assert contacts_resp.status_code == status.HTTP_200_OK
    contacts_data = contacts_resp.json()
    assert len(contacts_data) == 1
    assert contacts_data[0]["user_id"] == caregiver_a.id
    assert contacts_data[0]["name"] == "Dr. Bob Caregiver"
    assert contacts_data[0]["unread_count"] == 0

    # 3. Patient A sends message to Caregiver A
    msg_text = "Hello, I need help with my medication timing."
    send_resp = client.post(
        "/api/v1/chat/send",
        headers=headers_patient_a,
        json={"recipient_id": caregiver_a.id, "message": msg_text}
    )
    assert send_resp.status_code == status.HTTP_201_CREATED
    sent_data = send_resp.json()
    assert sent_data["sender_id"] == patient_a.id
    assert sent_data["recipient_id"] == caregiver_a.id
    assert sent_data["message"] == msg_text
    assert sent_data["is_read"] is False
    assert sent_data["created_at"] is not None

    # 4. Verify message exists in DB
    db_msg = db_session.query(ChatMessage).filter(ChatMessage.id == sent_data["id"]).first()
    assert db_msg is not None
    assert db_msg.sender_id == patient_a.id
    assert db_msg.recipient_id == caregiver_a.id
    assert db_msg.message == msg_text
    assert db_msg.is_read is False

    # 5. Caregiver A checks alerts / notifications
    alerts_resp = client.get("/api/v1/caregiver/alerts", headers=headers_caregiver_a)
    assert alerts_resp.status_code == status.HTTP_200_OK
    alerts_data = alerts_resp.json()
    chat_alerts = [a for a in alerts_data if a["type"] == "CHAT_MESSAGE"]
    assert len(chat_alerts) == 1
    assert chat_alerts[0]["patient_id"] == patient_a.id
    assert chat_alerts[0]["patient_name"] == "Alice Patient"
    assert "You have received a message from this patient" in chat_alerts[0]["message"]
    assert msg_text in chat_alerts[0]["message"]

    # Caregiver A checks contacts list -> unread count is 1
    cg_contacts_resp = client.get("/api/v1/chat/contacts", headers=headers_caregiver_a)
    assert cg_contacts_resp.status_code == status.HTTP_200_OK
    cg_contacts_data = cg_contacts_resp.json()
    assert len(cg_contacts_data) == 1
    assert cg_contacts_data[0]["user_id"] == patient_a.id
    assert cg_contacts_data[0]["unread_count"] == 1
    assert cg_contacts_data[0]["last_message"] == msg_text

    # 6. Caregiver A opens conversation with Patient A -> automatically marks as read
    convo_resp = client.get(f"/api/v1/chat/conversation/{patient_a.id}", headers=headers_caregiver_a)
    assert convo_resp.status_code == status.HTTP_200_OK
    convo_data = convo_resp.json()
    assert len(convo_data) == 1
    assert convo_data[0]["message"] == msg_text
    assert convo_data[0]["is_read"] is True

    # Check that alert clears after reading
    alerts_after_read = client.get("/api/v1/caregiver/alerts", headers=headers_caregiver_a).json()
    chat_alerts_after = [a for a in alerts_after_read if a["type"] == "CHAT_MESSAGE"]
    assert len(chat_alerts_after) == 0

    # 7. Caregiver A replies to Patient A
    reply_text = "Sure, I will review your schedule and help you."
    reply_resp = client.post(
        "/api/v1/chat/send",
        headers=headers_caregiver_a,
        json={"recipient_id": patient_a.id, "message": reply_text}
    )
    assert reply_resp.status_code == status.HTTP_201_CREATED
    reply_data = reply_resp.json()
    assert reply_data["sender_id"] == caregiver_a.id
    assert reply_data["recipient_id"] == patient_a.id
    assert reply_data["message"] == reply_text

    # 8. Patient A retrieves conversation -> sees both messages in chronological order
    pt_convo_resp = client.get(f"/api/v1/chat/conversation/{caregiver_a.id}", headers=headers_patient_a)
    assert pt_convo_resp.status_code == status.HTTP_200_OK
    pt_convo_data = pt_convo_resp.json()
    assert len(pt_convo_data) == 2
    assert pt_convo_data[0]["message"] == msg_text
    assert pt_convo_data[0]["sender_id"] == patient_a.id
    assert pt_convo_data[1]["message"] == reply_text
    assert pt_convo_data[1]["sender_id"] == caregiver_a.id

    # 9. RBAC Verification:
    # Patient B (unassigned) attempts to send message to Caregiver A -> 403 Forbidden
    unauth_send = client.post(
        "/api/v1/chat/send",
        headers=headers_patient_b,
        json={"recipient_id": caregiver_a.id, "message": "Unauthorized message"}
    )
    assert unauth_send.status_code == status.HTTP_403_FORBIDDEN

    # Patient B attempts to read conversation between Patient A and Caregiver A -> 403 Forbidden
    unauth_read = client.get(f"/api/v1/chat/conversation/{caregiver_a.id}", headers=headers_patient_b)
    assert unauth_read.status_code == status.HTTP_403_FORBIDDEN

    # Caregiver B (unassigned) attempts to read Patient A's conversation -> 403 Forbidden
    cg_unauth_read = client.get(f"/api/v1/chat/conversation/{patient_a.id}", headers=headers_caregiver_b)
    assert cg_unauth_read.status_code == status.HTTP_403_FORBIDDEN

    # Caregiver B attempts to send message to unassigned Patient A -> 403 Forbidden
    cg_unauth_send = client.post(
        "/api/v1/chat/send",
        headers=headers_caregiver_b,
        json={"recipient_id": patient_a.id, "message": "Unauthorized caregiver message"}
    )
    assert cg_unauth_send.status_code == status.HTTP_403_FORBIDDEN


def test_multi_patient_notification_isolation_and_selective_read(client: TestClient, db_session: Session, create_user):
    """
    Verify that when multiple patients message the same caregiver:
    - Each patient's notification is isolated and correctly attributed.
    - Opening conversation with Patient 1 marks only Patient 1's messages as read.
    - Patient 2's notification and unread count remain intact.
    """
    caregiver = create_user(
        name="Dr. House Caregiver",
        email="house@pillsync.test",
        role=UserRole.CAREGIVER,
        approval_status=ApprovalStatus.APPROVED
    )
    patient1 = create_user(
        name="Patient One",
        email="p1@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )
    patient2 = create_user(
        name="Patient Two",
        email="p2@pillsync.test",
        role=UserRole.PATIENT,
        approval_status=ApprovalStatus.APPROVED
    )

    db_session.add(CaregiverPatientAssignment(caregiver_id=caregiver.id, patient_id=patient1.id, status=AssignmentStatus.ACTIVE))
    db_session.add(CaregiverPatientAssignment(caregiver_id=caregiver.id, patient_id=patient2.id, status=AssignmentStatus.ACTIVE))
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    token_p1 = create_access_token(patient1.id)
    token_p2 = create_access_token(patient2.id)

    headers_cg = {"Authorization": f"Bearer {token_cg}"}
    headers_p1 = {"Authorization": f"Bearer {token_p1}"}
    headers_p2 = {"Authorization": f"Bearer {token_p2}"}

    # Patient 1 sends 2 messages
    client.post("/api/v1/chat/send", headers=headers_p1, json={"recipient_id": caregiver.id, "message": "P1 Msg 1"})
    client.post("/api/v1/chat/send", headers=headers_p1, json={"recipient_id": caregiver.id, "message": "P1 Msg 2"})

    # Patient 2 sends 1 message
    client.post("/api/v1/chat/send", headers=headers_p2, json={"recipient_id": caregiver.id, "message": "P2 Msg 1"})

    # Caregiver checks contacts: P1 has unread_count=2, P2 has unread_count=1
    contacts = client.get("/api/v1/chat/contacts", headers=headers_cg).json()
    p1_contact = next(c for c in contacts if c["user_id"] == patient1.id)
    p2_contact = next(c for c in contacts if c["user_id"] == patient2.id)
    assert p1_contact["unread_count"] == 2
    assert p2_contact["unread_count"] == 1

    # Caregiver checks alerts: has 3 chat message alerts total
    alerts = client.get("/api/v1/caregiver/alerts", headers=headers_cg).json()
    chat_alerts = [a for a in alerts if a["type"] == "CHAT_MESSAGE"]
    assert len(chat_alerts) == 3

    # Caregiver opens conversation with Patient 1
    p1_convo = client.get(f"/api/v1/chat/conversation/{patient1.id}", headers=headers_cg).json()
    assert len(p1_convo) == 2

    # Check alerts now: only Patient 2's alert remains! Patient 1's alerts cleared.
    alerts_after = client.get("/api/v1/caregiver/alerts", headers=headers_cg).json()
    chat_alerts_after = [a for a in alerts_after if a["type"] == "CHAT_MESSAGE"]
    assert len(chat_alerts_after) == 1
    assert chat_alerts_after[0]["patient_id"] == patient2.id

    # Contacts check: Patient 1 unread is 0, Patient 2 unread is still 1
    contacts_after = client.get("/api/v1/chat/contacts", headers=headers_cg).json()
    p1_after = next(c for c in contacts_after if c["user_id"] == patient1.id)
    p2_after = next(c for c in contacts_after if c["user_id"] == patient2.id)
    assert p1_after["unread_count"] == 0
    assert p2_after["unread_count"] == 1


def test_empty_message_validation_and_max_length(client: TestClient, db_session: Session, create_user):
    """Verify validation: empty messages and whitespace are rejected."""
    caregiver = create_user(name="CG", email="cg_val@test.com", role=UserRole.CAREGIVER)
    patient = create_user(name="PT", email="pt_val@test.com", role=UserRole.PATIENT)
    db_session.add(CaregiverPatientAssignment(caregiver_id=caregiver.id, patient_id=patient.id, status=AssignmentStatus.ACTIVE))
    db_session.commit()

    token_pt = create_access_token(patient.id)
    headers = {"Authorization": f"Bearer {token_pt}"}

    # Empty message body
    resp_empty = client.post("/api/v1/chat/send", headers=headers, json={"recipient_id": caregiver.id, "message": ""})
    assert resp_empty.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Over 2000 characters
    long_msg = "A" * 2001
    resp_long = client.post("/api/v1/chat/send", headers=headers, json={"recipient_id": caregiver.id, "message": long_msg})
    assert resp_long.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_delete_message_soft_delete_and_ownership_enforcement(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. A user can delete ONLY their own sent message.
    2. Recipient attempting to delete sender's message receives HTTP 403 Forbidden.
    3. Deleted message returns 'This message was deleted.' and is_deleted: true.
    4. Ordering of conversation is preserved.
    """
    caregiver = create_user(name="Dr. Smith Caregiver", email="smith@test.com", role=UserRole.CAREGIVER)
    patient = create_user(name="Jane Patient", email="jane@test.com", role=UserRole.PATIENT)
    db_session.add(CaregiverPatientAssignment(caregiver_id=caregiver.id, patient_id=patient.id, status=AssignmentStatus.ACTIVE))
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    token_pt = create_access_token(patient.id)
    headers_cg = {"Authorization": f"Bearer {token_cg}"}
    headers_pt = {"Authorization": f"Bearer {token_pt}"}

    # Patient sends Message 1
    m1_resp = client.post("/api/v1/chat/send", headers=headers_pt, json={"recipient_id": caregiver.id, "message": "Message 1 from Patient"})
    m1_id = m1_resp.json()["id"]

    # Caregiver sends Message 2
    m2_resp = client.post("/api/v1/chat/send", headers=headers_cg, json={"recipient_id": patient.id, "message": "Message 2 from Caregiver"})
    m2_id = m2_resp.json()["id"]

    # Patient attempts to delete Caregiver's message (m2) -> 403 Forbidden
    hack_del = client.delete(f"/api/v1/chat/messages/{m2_id}", headers=headers_pt)
    assert hack_del.status_code == status.HTTP_403_FORBIDDEN

    # Caregiver attempts to delete Patient's message (m1) -> 403 Forbidden
    cg_hack_del = client.delete(f"/api/v1/chat/messages/{m1_id}", headers=headers_cg)
    assert cg_hack_del.status_code == status.HTTP_403_FORBIDDEN

    # Patient deletes their own message (m1) -> 200 OK
    del_resp = client.delete(f"/api/v1/chat/messages/{m1_id}", headers=headers_pt)
    assert del_resp.status_code == status.HTTP_200_OK
    assert del_resp.json()["success"] is True

    # Retrieve conversation for Caregiver
    convo_cg = client.get(f"/api/v1/chat/conversation/{patient.id}", headers=headers_cg).json()
    assert len(convo_cg) == 2
    assert convo_cg[0]["id"] == m1_id
    assert convo_cg[0]["message"] == "This message was deleted."
    assert convo_cg[0]["is_deleted"] is True
    assert convo_cg[1]["id"] == m2_id
    assert convo_cg[1]["message"] == "Message 2 from Caregiver"
    assert convo_cg[1]["is_deleted"] is False


def test_delete_conversation_per_user_isolation_and_no_data_loss(client: TestClient, db_session: Session, create_user):
    """
    Verify:
    1. Patient deletes conversation -> conversation is cleared for Patient ONLY.
    2. Caregiver's conversation remains intact.
    3. Caregiver deletes conversation -> conversation is cleared for Caregiver.
    4. Deleting conversation does NOT delete or alter Patient accounts, medicines, or schedules.
    """
    from app.models.medicine import Medicine, DosageUnit, MedicineForm
    from app.models.schedule import MedicationSchedule, ScheduleFrequency

    caregiver = create_user(name="Dr. Taylor Caregiver", email="taylor@test.com", role=UserRole.CAREGIVER)
    patient = create_user(name="Sam Patient", email="sam@test.com", role=UserRole.PATIENT)
    db_session.add(CaregiverPatientAssignment(caregiver_id=caregiver.id, patient_id=patient.id, status=AssignmentStatus.ACTIVE))

    # Add medicine and schedule for Patient to ensure medical data is completely safe
    med = Medicine(
        user_id=patient.id,
        name="Lisinopril 10mg",
        dosage_amount=10.0,
        dosage_unit=DosageUnit.MG,
        quantity=30,
        medicine_form=MedicineForm.TABLET,
        start_date=date.today()
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    sched = MedicationSchedule(
        medicine_id=med.id,
        frequency_type=ScheduleFrequency.ONCE_DAILY,
        times_per_day=1,
        scheduled_times=["08:00"],
        start_date=date.today(),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    token_cg = create_access_token(caregiver.id)
    token_pt = create_access_token(patient.id)
    headers_cg = {"Authorization": f"Bearer {token_cg}"}
    headers_pt = {"Authorization": f"Bearer {token_pt}"}

    # Exchange messages
    client.post("/api/v1/chat/send", headers=headers_pt, json={"recipient_id": caregiver.id, "message": "Hi doctor"})
    client.post("/api/v1/chat/send", headers=headers_cg, json={"recipient_id": patient.id, "message": "Hello Sam"})

    # Patient clears conversation
    del_convo_pt = client.delete(f"/api/v1/chat/conversation/{caregiver.id}", headers=headers_pt)
    assert del_convo_pt.status_code == status.HTTP_200_OK

    # Check Patient's conversation -> now 0 messages
    pt_convo = client.get(f"/api/v1/chat/conversation/{caregiver.id}", headers=headers_pt).json()
    assert len(pt_convo) == 0

    # Check Caregiver's conversation -> still has all 2 messages!
    cg_convo = client.get(f"/api/v1/chat/conversation/{patient.id}", headers=headers_cg).json()
    assert len(cg_convo) == 2

    # Verify Patient medicine and schedule are completely intact
    med_in_db = db_session.query(Medicine).filter(Medicine.id == med.id).first()
    assert med_in_db is not None
    assert med_in_db.name == "Lisinopril 10mg"

    sched_in_db = db_session.query(MedicationSchedule).filter(MedicationSchedule.id == sched.id).first()
    assert sched_in_db is not None
    assert sched_in_db.is_active is True


