"""Audit logging service for tracking administrative, clinical, and security operations."""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

logger = logging.getLogger("pillsync.audit")


class AuditService:
    """Service for creating safe technical audit logs."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        target_type: str,
        actor_user_id: Optional[int] = None,
        target_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create and persist an audit record.
        Sanitizes details to ensure no passwords or auth tokens are saved.
        """
        safe_details = None
        if details:
            # Filter out sensitive credentials if present
            safe_details = {
                k: v for k, v in details.items()
                if k.lower() not in ("password", "password_hash", "token", "access_token", "otp_code", "secret")
            }

        audit_entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=safe_details,
        )
        self.db.add(audit_entry)
        try:
            self.db.commit()
            self.db.refresh(audit_entry)
        except Exception as exc:
            self.db.rollback()
            logger.error("Failed to commit audit log entry: %s", exc)

        return audit_entry
