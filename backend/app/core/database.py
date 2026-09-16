"""Database configuration and session management using SQLAlchemy."""

from typing import Generator, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger

is_sqlite = "sqlite" in settings.sync_database_url.lower()

engine_kwargs = {"pool_pre_ping": True}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    if "postgresql" in settings.sync_database_url.lower():
        engine_kwargs["connect_args"] = {"connect_timeout": 3}

engine = create_engine(settings.sync_database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> Tuple[bool, str]:
    """
    Check if the database is reachable and responding.
    Returns a tuple of (is_connected: bool, message: str).
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", str(exc))
        return False, f"unreachable: {type(exc).__name__}"
