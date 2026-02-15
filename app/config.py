import os
import sys
import secrets
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


def is_testing() -> bool:
    """Detect if we're running in test environment"""
    return (
        "pytest" in sys.modules or
        os.getenv("TESTING", "").lower() in ("1", "true", "yes") or
        "test" in sys.argv[0].lower()
    )


def get_secret_key() -> str:
    """Get SECRET_KEY from environment or generate for testing"""
    if is_testing():
        # Use deterministic key for tests (so tokens are reproducible)
        return "test-secret-key-for-testing-only-do-not-use-in-production"

    # Try loading .env if SECRET_KEY not yet in environment
    # (needed when config is imported before pydantic-settings resolves env_file)
    secret = os.getenv("SECRET_KEY")
    if not secret:
        try:
            from dotenv import load_dotenv as _load_dotenv
            _load_dotenv()
            secret = os.getenv("SECRET_KEY")
        except ImportError:
            pass

    if not secret:
        raise ValueError(
            "SECRET_KEY environment variable must be set in production! "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # Prevent accidental use of default/weak keys
    if secret in ["super-secret-jwt-key-change-this", "changeme", "secret", "admin123"]:
        raise ValueError(
            "SECRET_KEY appears to be a default/weak value. "
            "Generate a strong key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    return secret


def get_cors_origins() -> list[str]:
    """Get CORS origins - localhost for testing/development, explicit allowlist for production"""
    # Check ENVIRONMENT variable directly (not is_testing() to avoid import issues)
    env = os.getenv("ENVIRONMENT", "development")

    # Development or test mode: allow localhost
    if env in ("development", "test", "testing"):
        return [
            "http://localhost:8501",
            "http://localhost:8000",
            "http://127.0.0.1:8501",
            "http://127.0.0.1:8000",
        ]

    # Production: explicit allowlist from environment
    origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not origins_str:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS environment variable must be set in production! "
            "Example: CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com"
        )

    origins = [origin.strip() for origin in origins_str.split(",")]

    # Prevent localhost in production
    for origin in origins:
        if "localhost" in origin or "127.0.0.1" in origin:
            raise ValueError(
                f"Localhost origin '{origin}' not allowed in production CORS! "
                "Use production domain names only."
            )

    return origins


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "test" if is_testing() else "development"
    TESTING: bool = is_testing()

    # Database
    DATABASE_URL: str = "postgresql://lovas.zoltan@localhost:5432/gancuju_education_center_prod"

    # Task queue (Celery + Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # JWT - SECURE: Uses environment variable in production
    SECRET_KEY: str = get_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "GānCuju™© Education Center"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Initial Admin - SECURE: Must use environment variables in production
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@company.com" if is_testing() else "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123" if is_testing() else "")
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

    # CORS Configuration - SECURE: Explicit allowlist (localhost only in tests)
    CORS_ALLOWED_ORIGINS: list[str] = get_cors_origins()

    # Cookie Security Configuration - SECURE: HTTPS enforced in production
    COOKIE_SECURE: bool = not is_testing()  # True in production (requires HTTPS)
    COOKIE_SAMESITE: str = "strict"  # Options: "strict", "lax", "none"
    COOKIE_HTTPONLY: bool = True
    COOKIE_MAX_AGE: int = 3600  # 1 hour (matches ACCESS_TOKEN_EXPIRE_MINUTES)

    model_config = ConfigDict(env_file=".env")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Production-only security validation (skipped in development and testing)
        _is_production = not is_testing() and self.ENVIRONMENT == "production"
        if _is_production:
            # Validate admin credentials are set
            if not self.ADMIN_EMAIL or not self.ADMIN_PASSWORD:
                raise ValueError(
                    "ADMIN_EMAIL and ADMIN_PASSWORD must be set via environment variables in production!"
                )

            # Prevent weak admin passwords
            if self.ADMIN_PASSWORD in ["admin123", "password", "changeme", "admin", "123456"]:
                raise ValueError(
                    "Admin password appears to be weak or default. "
                    "Set a strong password via ADMIN_PASSWORD environment variable."
                )

            # Validate HTTPS is configured
            if not self.COOKIE_SECURE:
                raise ValueError(
                    "COOKIE_SECURE must be True in production (HTTPS required)"
                )


settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings