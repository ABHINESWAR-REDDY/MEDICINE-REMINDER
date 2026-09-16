"""Chat message database model for patient-caregiver direct communication."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ChatMessage(Base, TimestampMixin):
    """Chat message record exchanged between assigned patient and caregiver."""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_sender_recipient", "sender_id", "recipient_id"),
        Index("ix_chat_recipient_read", "recipient_id", "is_read"),
        Index("ix_chat_deleted", "is_deleted"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    # Soft deletion & per-user conversation clearing
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cleared_by_sender = Column(Boolean, default=False, nullable=False)
    cleared_by_recipient = Column(Boolean, default=False, nullable=False)

    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    deleted_by_user = relationship("User", foreign_keys=[deleted_by])

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} from={self.sender_id} to={self.recipient_id} read={self.is_read} deleted={self.is_deleted}>"

