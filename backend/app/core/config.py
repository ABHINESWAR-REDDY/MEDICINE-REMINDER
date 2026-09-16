from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus
from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CONFIG_DIR.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_BACKEND_DIR / ".env"),
            str(_ROOT_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    PROJECT_NAME: str = "PillSync API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Server binding
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database parameters
    DB_HOST: str = Field(
        default="localhost",
        validation_alias=AliasChoices("DB_HOST", "POSTGRES_SERVER", "POSTGRES_HOST"),
    )
    DB_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices("DB_PORT", "POSTGRES_PORT"),
    )
    DB_USER: str = Field(
        default="postgres",
        validation_alias=AliasChoices("DB_USER", "POSTGRES_USER"),
    )
    DB_PASSWORD: str = Field(
        default="",
        validation_alias=AliasChoices("DB_PASSWORD", "POSTGRES_PASSWORD"),
    )
    DB_NAME: str = Field(
        default="myproject",
        validation_alias=AliasChoices("DB_NAME", "POSTGRES_DB"),
    )

    # Backward compatibility properties
    @property
    def POSTGRES_SERVER(self) -> str:
        return self.DB_HOST

    @property
    def POSTGRES_PORT(self) -> int:
        return self.DB_PORT

    @property
    def POSTGRES_USER(self) -> str:
        return self.DB_USER

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return self.DB_PASSWORD

    @property
    def POSTGRES_DB(self) -> str:
        return self.DB_NAME
    
    # Explicit DATABASE_URL (optional override)
    DATABASE_URL: Optional[str] = None

    # JWT Security Configuration (Strictly required from environment - NO default secret)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Google SMTP Email Configuration (App Passwords: https://myaccount.google.com/apppasswords)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "PillSync"
    SMTP_TLS: bool = True
    EMAIL_OTP_EXPIRE_MINUTES: int = 10

    # Google Gemini AI Assistant & Medical Verification Configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JWT_SECRET_KEY environment variable is required and must not be empty.")
        return v.strip()

    @computed_field
    @property
    def sync_database_url(self) -> str:
        """Return the effective SQLAlchemy connection string."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = quote_plus(self.DB_USER) if self.DB_USER else ""
        password = quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
        credentials = f"{user}:{password}@" if user or password else ""
        return (
            f"postgresql://{credentials}"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
