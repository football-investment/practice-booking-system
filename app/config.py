import os
import sys
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


def is_testing() -> bool:
    """Detect if we're running in test environment"""
    return (
        "pytest" in sys.modules or
        os.getenv("TESTING", "").lower() in ("1", "true", "yes") or
        "test" in sys.argv[0].lower()
    )


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "test" if is_testing() else "development"
    TESTING: bool = is_testing()
    
    # Database
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/gancuju_education_center"
    
    # JWT
    SECRET_KEY: str = "super-secret-jwt-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # App
    APP_NAME: str = "GānCuju™© Education Center"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Initial Admin (use environment variables for security)
    ADMIN_EMAIL: str = "admin@company.com"  # Override with ADMIN_EMAIL env var
    ADMIN_PASSWORD: str = "admin123"        # Override with ADMIN_PASSWORD env var  
    ADMIN_NAME: str = "System Administrator"
    
    # Booking Rules
    MAX_BOOKINGS_PER_SEMESTER: int = 10
    BOOKING_DEADLINE_HOURS: int = 24
    
    # Production Security Settings
    ENABLE_RATE_LIMITING: bool = not is_testing()
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_REQUEST_SIZE_LIMIT: bool = True
    ENABLE_STRUCTURED_LOGGING: bool = True
    
    # Rate Limiting Configuration
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOGIN_RATE_LIMIT_CALLS: int = 10  # More permissive for testing
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = ConfigDict(env_file=".env")


settings = Settings()