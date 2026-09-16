"""User repository for database persistence operations."""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, UserRole, ApprovalStatus


class UserRepository:
    """Repository handling database operations for User model."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by primary key ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by unique email address (case-insensitive comparison)."""
        return self.db.query(User).filter(User.email.ilike(email.strip())).first()

    def get_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Fetch user by unique employee ID (case-insensitive comparison)."""
        if not employee_id:
            return None
        return self.db.query(User).filter(User.employee_id.ilike(employee_id.strip())).first()

    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.PATIENT,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        is_active: bool = True,
        employee_id: Optional[str] = None
    ) -> User:
        """Create and persist a new user record."""
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            approval_status=approval_status,
            is_active=is_active,
            employee_id=employee_id.strip().upper() if employee_id else None
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        if not user.employee_id:
            role_enum = role if isinstance(role, UserRole) else UserRole(str(role).upper())
            prefix = "PT" if role_enum == UserRole.PATIENT else ("CG" if role_enum == UserRole.CAREGIVER else "AD")
            user.employee_id = f"{prefix}{user.id:06d}"
            self.db.commit()
            self.db.refresh(user)

        return user

    def update(self, user: User) -> User:
        """Commit updates to an existing user record."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def count(self) -> int:
        """Return total count of registered users."""
        return self.db.query(User).count()

    def count_admins(self) -> int:
        """Return total count of registered ADMIN accounts."""
        return self.db.query(User).filter(User.role == UserRole.ADMIN).count()

    def has_admin(self) -> bool:
        """Return True if at least one ADMIN account exists."""
        return self.db.query(User.id).filter(User.role == UserRole.ADMIN).first() is not None

