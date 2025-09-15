import pytest
from datetime import datetime, timedelta

from ..core.auth import create_access_token, create_refresh_token, verify_token
from ..core.security import get_password_hash, verify_password


def test_password_hashing():
    """Test password hashing and verification"""
    password = "test_password_123"
    hashed = get_password_hash(password)
    
    # Verify correct password
    assert verify_password(password, hashed)
    
    # Verify incorrect password
    assert not verify_password("wrong_password", hashed)
    
    # Ensure different hashes for same password
    hashed2 = get_password_hash(password)
    assert hashed != hashed2
    assert verify_password(password, hashed2)


def test_access_token_creation():
    """Test JWT access token creation and verification"""
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    
    # Verify token
    username = verify_token(token, "access")
    assert username == "test@example.com"


def test_refresh_token_creation():
    """Test JWT refresh token creation and verification"""
    data = {"sub": "test@example.com"}
    token = create_refresh_token(data)
    
    # Verify token
    username = verify_token(token, "refresh")
    assert username == "test@example.com"


def test_token_expiration():
    """Test token expiration"""
    data = {"sub": "test@example.com"}
    
    # Create token with short expiration
    short_expiry = timedelta(seconds=-1)  # Already expired
    token = create_access_token(data, short_expiry)
    
    # Verify expired token returns None
    username = verify_token(token, "access")
    assert username is None


def test_invalid_token():
    """Test invalid token verification"""
    # Test with invalid token
    username = verify_token("invalid_token", "access")
    assert username is None
    
    # Test with empty token
    username = verify_token("", "access")
    assert username is None


def test_wrong_token_type():
    """Test using wrong token type"""
    data = {"sub": "test@example.com"}
    access_token = create_access_token(data)
    
    # Try to verify access token as refresh token
    username = verify_token(access_token, "refresh")
    assert username is None