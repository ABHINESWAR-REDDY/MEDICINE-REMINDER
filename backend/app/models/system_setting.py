"""System settings and notification configuration model."""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.models.base import Base


class SystemSetting(Base):
    """Persistent platform configuration and notification settings."""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, default="GENERAL", index=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemSetting key={self.key} category={self.category}>"


# Default notification settings schema and values
DEFAULT_NOTIFICATION_SETTINGS: Dict[str, Any] = {
    # Patient Notifications
    "patient_medication_reminders_enabled": True,
    "patient_missed_dose_alerts_enabled": True,
    "patient_refill_alerts_enabled": True,
    "patient_polling_interval_seconds": 30,

    # Caregiver Notifications
    "caregiver_missed_dose_alerts_enabled": True,
    "caregiver_refill_alerts_enabled": True,
    "caregiver_adherence_risk_alerts_enabled": True,
    "caregiver_patient_chat_alerts_enabled": True,

    # System Notifications
    "system_security_alerts_enabled": True,
    "system_operational_alerts_enabled": True,
}


def get_notification_settings_from_db(db) -> Dict[str, Any]:
    """Retrieve persisted notification settings or seed and return defaults if not yet present."""
    setting_row = db.query(SystemSetting).filter(SystemSetting.key == "notification_settings").first()
    if not setting_row:
        # Seed default row
        setting_row = SystemSetting(
            key="notification_settings",
            value=dict(DEFAULT_NOTIFICATION_SETTINGS),
            description="Platform-wide notification dispatch and alert rules",
            category="NOTIFICATIONS",
            updated_by="SYSTEM_DEFAULT"
        )
        db.add(setting_row)
        try:
            db.commit()
            db.refresh(setting_row)
        except Exception:
            db.rollback()
            return dict(DEFAULT_NOTIFICATION_SETTINGS)

    # Merge with defaults in case new fields were added
    current_val = dict(DEFAULT_NOTIFICATION_SETTINGS)
    if isinstance(setting_row.value, dict):
        current_val.update(setting_row.value)
    return current_val


def set_notification_settings_in_db(db, new_settings: Dict[str, Any], updated_by: str = "ADMIN") -> Dict[str, Any]:
    """Validate, persist and return updated notification settings."""
    setting_row = db.query(SystemSetting).filter(SystemSetting.key == "notification_settings").first()
    
    current_settings = get_notification_settings_from_db(db)
    # Only update allowed keys
    for k, v in new_settings.items():
        if k in DEFAULT_NOTIFICATION_SETTINGS:
            if isinstance(DEFAULT_NOTIFICATION_SETTINGS[k], bool):
                current_settings[k] = bool(v)
            elif isinstance(DEFAULT_NOTIFICATION_SETTINGS[k], int):
                try:
                    val_int = int(v)
                    if k == "patient_polling_interval_seconds":
                        val_int = max(5, min(300, val_int))
                    current_settings[k] = val_int
                except (ValueError, TypeError):
                    pass

    if not setting_row:
        setting_row = SystemSetting(
            key="notification_settings",
            value=current_settings,
            description="Platform-wide notification dispatch and alert rules",
            category="NOTIFICATIONS",
            updated_by=updated_by
        )
        db.add(setting_row)
    else:
        setting_row.value = current_settings
        setting_row.updated_at = datetime.now(timezone.utc)
        setting_row.updated_by = updated_by

    db.commit()
    db.refresh(setting_row)
    return current_settings
