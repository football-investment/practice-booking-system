from passlib.context import CryptContext

# Production-optimized bcrypt configuration
# rounds=10: Balance between security and performance (~100ms per hash)
# rounds=12 (default): ~400ms per hash - too slow for high concurrency
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)