"""User profile and account management service."""

from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.caregiver_patient import CaregiverPatientAssignment, AssignmentStatus
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileUpdateRequest, UserResponse


class UserService:
    """Service handling safe profile retrieval and updates."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def _build_user_response(self, user: User) -> Dict[str, Any]:
        """Build UserResponse dictionary with assigned caregiver details if role is PATIENT."""
        caregiver_id = None
        caregiver_name = None
        caregiver_employee_id = None
        caregiver_email = None

        if user.role == UserRole.PATIENT:
            assignment = self.db.query(CaregiverPatientAssignment).filter(
                CaregiverPatientAssignment.patient_id == user.id,
                CaregiverPatientAssignment.status == AssignmentStatus.ACTIVE
            ).first()
            if assignment:
                cg = self.db.query(User).filter(User.id == assignment.caregiver_id).first()
                if cg:
                    caregiver_id = cg.id
                    caregiver_name = cg.name
                    caregiver_employee_id = cg.employee_id or f"CG{cg.id:06d}"
                    caregiver_email = cg.email

        emp_id = user.employee_id
        if not emp_id:
            if user.role == UserRole.PATIENT:
                emp_id = f"PT{user.id:06d}"
            elif user.role == UserRole.CAREGIVER:
                emp_id = f"CG{user.id:06d}"
            elif user.role == UserRole.ADMIN:
                emp_id = f"AD{user.id:06d}"

        return {
            "id": user.id,
            "employee_id": emp_id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "approval_status": user.approval_status.value if hasattr(user.approval_status, 'value') else user.approval_status,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "assigned_caregiver_id": caregiver_id,
            "assigned_caregiver_name": caregiver_name,
            "assigned_caregiver_employee_id": caregiver_employee_id,
            "assigned_caregiver_email": caregiver_email,
            "language": getattr(user, 'language', 'en') or 'en',
        }

    def get_profile(self, user: User) -> Dict[str, Any]:
        """Retrieve user profile with assigned caregiver details."""
        return self._build_user_response(user)

    def update_profile(self, user: User, data: UserProfileUpdateRequest) -> Dict[str, Any]:
        """
        Update allowed user profile attributes.
        Allows name and language updates; preserves role, email, password_hash, and ID immutability.
        """
        if data.name is not None and data.name.strip():
            user.name = data.name.strip()
        if data.language is not None and data.language.strip():
            user.language = data.language.strip().lower()

        updated_user = self.user_repo.update(user)
        return self._build_user_response(updated_user)
