"""SQLAlchemy Model for Asynchronous OCR Prescription Jobs."""

import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.base import Base


class OCRJob(Base):
    """Tracks asynchronous processing of uploaded prescription OCR jobs."""

    __tablename__ = "ocr_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Status: queued, processing, completed, failed
    status = Column(String(30), nullable=False, default="queued", index=True)
    stage = Column(String(50), nullable=False, default="uploading")
    progress_message = Column(String(255), nullable=False, default="Uploaded prescription...")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Serialized JSON result for user review
    result_json = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="ocr_jobs")
