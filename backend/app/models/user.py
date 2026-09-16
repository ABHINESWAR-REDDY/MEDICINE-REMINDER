"""User database model, role, and approval enumerations."""

import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum, Index, text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """Strongly validated user roles."""
    PATIENT = "PATIENT"
    CAREGIVER = "CAREGIVER"
    ADMIN = "ADMIN"


class ApprovalStatus(str, enum.Enum):
    """Account approval status enumeration."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class User(Base, TimestampMixin):
    """User account model for authentication, RBAC, and caregiver approval workflows."""
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_single_admin_role",
            "role",
            unique=True,
            postgresql_where=text("role = 'ADMIN'"),
            sqlite_where=text("role = 'ADMIN'")
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, name="user_role_enum", native_enum=False),
        nullable=False,
        default=UserRole.PATIENT,
        server_default="PATIENT"
    )
    approval_status = Column(
        Enum(ApprovalStatus, name="approval_status_enum", native_enum=False),
        nullable=False,
        default=ApprovalStatus.APPROVED,
        server_default="APPROVED"
    )
    is_active = Column(Boolean, default=True, nullable=False)
    language = Column(String(10), default="en", server_default="en", nullable=False)

    # Relationships
    conditions = relationship("Condition", back_populates="user", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="user", cascade="all, delete-orphan")
    medicines = relationship("Medicine", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role} status={self.approval_status}>"
