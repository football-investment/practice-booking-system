"""
Token Validation Utilities
Handles JWT token expiration checking without requiring SECRET_KEY
"""

import jwt
from datetime import datetime, timezone
from typing import Optional


def is_token_expired(token: str) -> bool:
    """
    Check if JWT token is expired
    Does NOT verify signature (no SECRET_KEY needed)

    Args:
        token: JWT token string

    Returns:
        True if token is expired or invalid, False otherwise
    """
    if not token:
        return True

    try:
        # Decode without verification to check expiration
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get('exp')

        if not exp:
            # No expiration claim = invalid token
            return True

        # Compare with current UTC time
        current_timestamp = datetime.now(timezone.utc).timestamp()
        return current_timestamp > exp

    except jwt.DecodeError:
        # Token is malformed
        return True
    except Exception:
        # Any other error = treat as expired
        return True


def get_token_expiry_time(token: str) -> Optional[datetime]:
    """
    Get token expiration datetime

    Args:
        token: JWT token string

    Returns:
        datetime object or None if invalid
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get('exp')

        if not exp:
            return None

        return datetime.fromtimestamp(exp, tz=timezone.utc)

    except:
        return None


def get_token_time_remaining(token: str) -> Optional[int]:
    """
    Get seconds remaining until token expiration

    Args:
        token: JWT token string

    Returns:
        Seconds remaining (int) or None if invalid/expired
    """
    expiry = get_token_expiry_time(token)
    if not expiry:
        return None

    now = datetime.now(timezone.utc)
    if expiry <= now:
        return 0  # Expired

    return int((expiry - now).total_seconds())
