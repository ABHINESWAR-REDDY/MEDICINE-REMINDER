"""Pytest fixtures for backend test suite."""

import sys
from pathlib import Path
from typing import Generator
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in python path
import os
os.environ.setdefault("JWT_SECRET_KEY", "supersecretjwtkeyforlocaltest1234567890")
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings

from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.models import Base, User, UserRole, ApprovalStatus
from app.main import app

# Isolated in-memory SQLite engine for unit/integration testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database tables before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def mock_email_service():
    """Mock out external SMTP email delivery during unit tests."""
    with patch("app.services.email_service.email_service.send_email", return_value=True):
        yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional test database session and bind dependency override."""
    session = TestingSessionLocal()
    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient instance with test db override."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def create_user(db_session: Session):
    """Helper fixture to create test users in the test database."""
    def _create_user(
        name: str = "Test User",
        email: str = "test@example.com",
        password: str = "SecurePass123!",
        role: UserRole = UserRole.PATIENT,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        is_active: bool = True
    ) -> User:
        user = User(
            name=name,
            email=email.lower(),
            password_hash=get_password_hash(password),
            role=role,
            approval_status=approval_status,
            is_active=is_active
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user
