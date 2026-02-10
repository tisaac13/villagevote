"""
Application configuration settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the directory containing this file
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file (override=True to ensure .env values are used)
load_dotenv(BASE_DIR / ".env", override=True)


class Settings(BaseSettings):
    """Application settings"""
    
    # Project info
    PROJECT_NAME: str = "RepCheck API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_PREFIX: str = "/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:19006",  # Expo
        "http://localhost:8081",   # React Native
    ]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://civicswipe:password@localhost:5432/civicswipe"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1  # Short-lived refresh tokens — rotated on each use
    
    # Encryption key for address encryption
    ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"
    
    # External APIs
    CONGRESS_API_KEY: str = ""
    OPENSTATES_API_KEY: str = ""
    LEGISCAN_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    
    # AI Services
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Admin
    ADMIN_EMAILS: str = ""  # Comma-separated list of admin email addresses

    # Monitoring
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    # Geocoding
    CENSUS_GEOCODER_URL: str = "https://geocoding.geo.census.gov/geocoder"
    
    # Phoenix Legistar
    PHOENIX_LEGISTAR_BASE_URL: str = "https://phoenix.legistar.com"
    
    # Background jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Create settings instance
settings = Settings()

# Startup safety check: reject insecure defaults outside development
_INSECURE_DEFAULTS = {
    "your-secret-key-change-in-production",
    "your-encryption-key-change-in-production",
}

if settings.ENVIRONMENT != "development":
    if settings.SECRET_KEY in _INSECURE_DEFAULTS:
        raise RuntimeError(
            "SECRET_KEY is set to the insecure default. "
            "Set a strong random SECRET_KEY environment variable before running in production."
        )
    if settings.ENCRYPTION_KEY in _INSECURE_DEFAULTS:
        raise RuntimeError(
            "ENCRYPTION_KEY is set to the insecure default. "
            "Set a strong random ENCRYPTION_KEY environment variable before running in production."
        )
