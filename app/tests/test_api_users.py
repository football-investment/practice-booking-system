import pytest
from fastapi import status


def test_create_user_admin(client, admin_token):
    """Test creating user as admin"""
    user_data = {
        "name": "New Student",
        "email": "newstudent@test.com",
        "password": "password123",
        "role": "student"
    }
    response = client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=user_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "New Student"
    assert data["email"] == "newstudent@test.com"
    assert data["role"] == "student"


def test_create_user_non_admin(client, student_token):
    """Test creating user as non-admin (should fail)"""
    user_data = {
        "name": "New Student",
        "email": "newstudent@test.com",
        "password": "password123",
        "role": "student"
    }
    response = client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {student_token}"},
        json=user_data
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_user_duplicate_email(client, admin_token, student_user):
    """Test creating user with duplicate email"""
    user_data = {
        "name": "Another Student",
        "email": "student@test.com",  # Same as existing student
        "password": "password123",
        "role": "student"
    }
    response = client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=user_data
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_users_admin(client, admin_token, admin_user, student_user):
    """Test listing users as admin"""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 2  # At least admin and student
    assert len(data["users"]) >= 2


def test_list_users_non_admin(client, student_token):
    """Test listing users as non-admin (should fail)"""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_user_admin(client, admin_token, student_user):
    """Test getting user by ID as admin"""
    response = client.get(
        f"/api/v1/users/{student_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "student@test.com"
    assert "total_bookings" in data
    assert "completed_sessions" in data


def test_get_nonexistent_user(client, admin_token):
    """Test getting nonexistent user"""
    response = client.get(
        "/api/v1/users/9999",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_user_admin(client, admin_token, student_user):
    """Test updating user as admin"""
    update_data = {"name": "Updated Student Name"}
    response = client.patch(
        f"/api/v1/users/{student_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Student Name"


def test_update_own_profile(client, student_token, student_user):
    """Test updating own profile"""
    update_data = {"name": "Self Updated Name"}
    response = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {student_token}"},
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Self Updated Name"


def test_delete_user_admin(client, admin_token, student_user):
    """Test deactivating user as admin"""
    response = client.delete(
        f"/api/v1/users/{student_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK


def test_reset_user_password_admin(client, admin_token, student_user):
    """Test resetting user password as admin"""
    reset_data = {"new_password": "newpassword123"}
    response = client.post(
        f"/api/v1/users/{student_user.id}/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=reset_data
    )
    assert response.status_code == status.HTTP_200_OK