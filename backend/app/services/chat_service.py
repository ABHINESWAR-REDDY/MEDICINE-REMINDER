"""Chat service handling direct messaging and conversation authorization between patients and caregivers."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.models.user import User, UserRole
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatContact
from app.services.audit_service import AuditService


class ChatService:
    """Business logic for patient-caregiver direct messaging."""

    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    def _verify_chat_access(self, user_a: User, user_b_id: int) -> User:
        """
        Enforce strict RBAC:
        Users can only message if:
        1. User A is PATIENT and User B is their assigned CAREGIVER.
        2. User A is CAREGIVER and User B is their assigned PATIENT.
        3. User A is ADMIN.
        """
        user_b = self.db.query(User).filter(User.id == user_b_id).first()
        if not user_b:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "Recipient user not found."}
            )

        if user_a.role == UserRole.ADMIN or user_b.role == UserRole.ADMIN:
            return user_b

        if user_a.role == UserRole.PATIENT:
            assignment = self.db.query(CaregiverPatientAssignment).filter(
                CaregiverPatientAssignment.patient_id == user_a.id,
                CaregiverPatientAssignment.caregiver_id == user_b_id,
                CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
            ).first()
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "You can only message your assigned caregiver supervisor."}
                )
        elif user_a.role == UserRole.CAREGIVER:
            assignment = self.db.query(CaregiverPatientAssignment).filter(
                CaregiverPatientAssignment.caregiver_id == user_a.id,
                CaregiverPatientAssignment.patient_id == user_b_id,
                CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
            ).first()
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "You can only message patients currently assigned to you."}
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Unauthorized to access messaging."}
            )

        return user_b

    def _format_dt(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Return naive datetime preserving exact recorded wall-clock timestamp."""
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt


    def get_contacts(self, current_user: User) -> List[Dict[str, Any]]:
        """Retrieve authorized chat contacts for current user with unread counts."""
        contacts = []

        if current_user.role == UserRole.PATIENT:
            # Patient contact: their assigned caregiver
            assignment = self.db.query(CaregiverPatientAssignment).filter(
                CaregiverPatientAssignment.patient_id == current_user.id,
                CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
            ).first()
            if assignment:
                cg = self.db.query(User).filter(User.id == assignment.caregiver_id).first()
                if cg:
                    contacts.append(self._build_contact_summary(current_user.id, cg))

        elif current_user.role == UserRole.CAREGIVER:
            # Caregiver contacts: all their assigned patients
            assignments = self.db.query(CaregiverPatientAssignment).filter(
                CaregiverPatientAssignment.caregiver_id == current_user.id,
                CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
            ).all()
            for a in assignments:
                pt = self.db.query(User).filter(User.id == a.patient_id).first()
                if pt:
                    contacts.append(self._build_contact_summary(current_user.id, pt))

        elif current_user.role == UserRole.ADMIN:
            # Admin can view all active caregivers and patients
            users = self.db.query(User).filter(User.id != current_user.id).all()
            for u in users:
                contacts.append(self._build_contact_summary(current_user.id, u))

        return contacts

    def _build_contact_summary(self, current_user_id: int, other_user: User) -> Dict[str, Any]:
        """Compute unread message count and latest message for a contact, respecting deletions and clearings."""
        unread_count = self.db.query(ChatMessage).filter(
            ChatMessage.sender_id == other_user.id,
            ChatMessage.recipient_id == current_user_id,
            ChatMessage.is_read == False,
            ChatMessage.is_deleted == False,
            ChatMessage.cleared_by_recipient == False
        ).count()

        last_msg = self.db.query(ChatMessage).filter(
            or_(
                and_(ChatMessage.sender_id == current_user_id, ChatMessage.recipient_id == other_user.id, ChatMessage.cleared_by_sender == False),
                and_(ChatMessage.sender_id == other_user.id, ChatMessage.recipient_id == current_user_id, ChatMessage.cleared_by_recipient == False),
            )
        ).order_by(desc(ChatMessage.created_at)).first()

        last_msg_text = None
        if last_msg:
            last_msg_text = "This message was deleted." if last_msg.is_deleted else last_msg.message

        emp_id = other_user.employee_id
        if not emp_id:
            if other_user.role == UserRole.PATIENT:
                emp_id = f"PT{other_user.id:06d}"
            elif other_user.role == UserRole.CAREGIVER:
                emp_id = f"CG{other_user.id:06d}"
            elif other_user.role == UserRole.ADMIN:
                emp_id = f"AD{other_user.id:06d}"

        return {
            "user_id": other_user.id,
            "employee_id": emp_id,
            "name": other_user.name,
            "email": other_user.email,
            "role": other_user.role.value if hasattr(other_user.role, 'value') else other_user.role,
            "unread_count": unread_count,
            "last_message": last_msg_text,
            "last_message_time": self._format_dt(last_msg.created_at) if last_msg else None,
        }

    def get_conversation(self, current_user: User, other_user_id: int) -> List[Dict[str, Any]]:
        """Retrieve conversation history with other user, respecting per-user clears and soft-deletes."""
        other_user = self._verify_chat_access(current_user, other_user_id)

        # Mark all unread messages sent from other_user to current_user as read
        unread_messages = self.db.query(ChatMessage).filter(
            ChatMessage.sender_id == other_user_id,
            ChatMessage.recipient_id == current_user.id,
            ChatMessage.is_read == False,
            ChatMessage.cleared_by_recipient == False
        ).all()

        if unread_messages:
            for msg in unread_messages:
                msg.is_read = True
            self.db.commit()

        # Fetch messages not cleared by current user, sorted chronologically
        messages = self.db.query(ChatMessage).filter(
            or_(
                and_(ChatMessage.sender_id == current_user.id, ChatMessage.recipient_id == other_user_id, ChatMessage.cleared_by_sender == False),
                and_(ChatMessage.sender_id == other_user_id, ChatMessage.recipient_id == current_user.id, ChatMessage.cleared_by_recipient == False),
            )
        ).order_by(ChatMessage.created_at.asc()).all()

        results = []
        for m in messages:
            sender = current_user if m.sender_id == current_user.id else other_user
            recipient = other_user if m.sender_id == current_user.id else current_user

            s_emp_id = sender.employee_id or (f"PT{sender.id:06d}" if sender.role == UserRole.PATIENT else f"CG{sender.id:06d}")
            r_emp_id = recipient.employee_id or (f"PT{recipient.id:06d}" if recipient.role == UserRole.PATIENT else f"CG{recipient.id:06d}")

            msg_content = "This message was deleted." if m.is_deleted else m.message

            results.append({
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_name": sender.name,
                "sender_role": sender.role.value if hasattr(sender.role, 'value') else sender.role,
                "sender_employee_id": s_emp_id,
                "recipient_id": m.recipient_id,
                "recipient_name": recipient.name,
                "recipient_role": recipient.role.value if hasattr(recipient.role, 'value') else recipient.role,
                "recipient_employee_id": r_emp_id,
                "message": msg_content,
                "is_read": m.is_read,
                "is_deleted": m.is_deleted,
                "deleted_at": self._format_dt(m.deleted_at),
                "created_at": self._format_dt(m.created_at),
            })

        return results

    def send_message(self, current_user: User, data: ChatMessageCreate) -> Dict[str, Any]:
        """Send a new message to an authorized recipient."""
        recipient = self._verify_chat_access(current_user, data.recipient_id)

        msg = ChatMessage(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            message=data.message.strip(),
            is_read=False,
            is_deleted=False,
            cleared_by_sender=False,
            cleared_by_recipient=False
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)

        self.audit.log(
            action="CHAT_MESSAGE_SENT",
            target_type="ChatMessage",
            actor_user_id=current_user.id,
            target_id=msg.id,
            details={"recipient_id": recipient.id, "sender_role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role}
        )

        s_emp_id = current_user.employee_id or (f"PT{current_user.id:06d}" if current_user.role == UserRole.PATIENT else f"CG{current_user.id:06d}")
        r_emp_id = recipient.employee_id or (f"PT{recipient.id:06d}" if recipient.role == UserRole.PATIENT else f"CG{recipient.id:06d}")

        return {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": current_user.name,
            "sender_role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
            "sender_employee_id": s_emp_id,
            "recipient_id": msg.recipient_id,
            "recipient_name": recipient.name,
            "recipient_role": recipient.role.value if hasattr(recipient.role, 'value') else recipient.role,
            "recipient_employee_id": r_emp_id,
            "message": msg.message,
            "is_read": msg.is_read,
            "is_deleted": False,
            "deleted_at": None,
            "created_at": self._format_dt(msg.created_at),
        }

    def mark_read(self, current_user: User, sender_id: int) -> Dict[str, Any]:
        """Mark incoming messages from sender as read."""
        self.db.query(ChatMessage).filter(
            ChatMessage.sender_id == sender_id,
            ChatMessage.recipient_id == current_user.id,
            ChatMessage.is_read == False
        ).update({"is_read": True}, synchronize_session=False)
        self.db.commit()
        return {"success": True, "message": "Messages marked as read."}

    def delete_message(self, current_user: User, message_id: int) -> Dict[str, Any]:
        """
        Soft-delete an individual chat message.
        STRICT SECURITY: A user can delete ONLY their own sent message.
        If recipient attempts to delete sender's message, raise HTTP 403 Forbidden.
        """
        msg = self.db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "MESSAGE_NOT_FOUND", "message": "Chat message not found."}
            )

        # Enforce sender ownership
        if msg.sender_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You can only delete your own sent messages."}
            )

        now_utc = datetime.now(timezone.utc)
        msg.is_deleted = True
        msg.deleted_at = now_utc
        msg.deleted_by = current_user.id
        self.db.commit()

        return {
            "success": True,
            "message": "Message deleted successfully.",
            "deleted_id": message_id
        }

    def delete_conversation(self, current_user: User, other_user_id: int) -> Dict[str, Any]:
        """
        Delete/clear conversation for the requesting user ONLY.
        The other user's conversation and history remain completely intact.
        Patient and medication records are never modified or affected.
        """
        other_user = self._verify_chat_access(current_user, other_user_id)

        # Mark all messages sent by current_user to other_user as cleared_by_sender
        self.db.query(ChatMessage).filter(
            ChatMessage.sender_id == current_user.id,
            ChatMessage.recipient_id == other_user.id
        ).update({"cleared_by_sender": True}, synchronize_session=False)

        # Mark all messages sent by other_user to current_user as cleared_by_recipient
        self.db.query(ChatMessage).filter(
            ChatMessage.sender_id == other_user.id,
            ChatMessage.recipient_id == current_user.id
        ).update({"cleared_by_recipient": True, "is_read": True}, synchronize_session=False)

        self.db.commit()

        return {
            "success": True,
            "message": "Conversation cleared successfully for your account."
        }

