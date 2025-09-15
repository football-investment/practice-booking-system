import pytest
from fastapi import status


def test_login_success(client, admin_user):
    """Test successful login"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, admin_user):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong_password"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_nonexistent_user(client):
    """Test login with nonexistent user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "password"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token(client, admin_user):
    """Test token refresh"""
    # Get initial tokens
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    tokens = login_response.json()
    
    # Refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_invalid_token(client):
    """Test refresh with invalid token"""
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user(client, admin_token, admin_user):
    """Test getting current user info"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["name"] == "Admin User"
    assert data["role"] == "admin"


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_password(client, admin_token, admin_user):
    """Test changing password"""
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"old_password": "admin123", "new_password": "newpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Test login with new password
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "newpassword123"}
    )
    assert login_response.status_code == status.HTTP_200_OK


def test_change_password_wrong_old_password(client, admin_token):
    """Test changing password with wrong old password"""
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"old_password": "wrong_password", "new_password": "newpassword123"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_logout(client, admin_token):
    """Test logout"""
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK