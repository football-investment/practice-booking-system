"""
Test Audit API Endpoints

Tests for audit log API access control and functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import timedelta

from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.services.audit_service import AuditService
from app.core.auth import create_access_token

def test_get_my_logs_as_user(client: TestClient, db_session: Session):
    """Test user can get their own audit logs"""
    # Create test user
    user = User(
        name="Test Student",
        email="student@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",  # Dummy hash
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Create audit logs for user
    audit_service = AuditService(db_session)
    audit_service.log(action=AuditAction.LOGIN, user_id=user.id)
    audit_service.log(action=AuditAction.LICENSE_VIEWED, user_id=user.id)

    # Login and get token
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/my-logs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data
    assert data["total"] >= 2  # At least the 2 logs we created


def test_get_my_logs_with_filters(client: TestClient, db_session: Session):
    """Test filtering my logs"""
    # Create test user
    user = User(
        name="Test Student",
        email="student@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Create audit logs
    audit_service = AuditService(db_session)
    audit_service.log(action=AuditAction.LOGIN, user_id=user.id)
    audit_service.log(action=AuditAction.LOGOUT, user_id=user.id)

    # Login
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/my-logs?action=LOGIN&limit=5",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5


def test_get_all_logs_as_admin(client: TestClient, db_session: Session):
    """Test admin can get all logs"""
    # Create admin user
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    # Create some audit logs
    audit_service = AuditService(db_session)
    audit_service.log(action=AuditAction.LOGIN, user_id=admin.id)

    # Login as admin
    token = create_access_token(data={"sub": admin.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data


def test_get_all_logs_forbidden_for_student(client: TestClient, db_session: Session):
    """Test student cannot access all logs"""
    # Create student user
    student = User(
        name="Student",
        email="student@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(student)
    db_session.commit()

    # Login as student
    token = create_access_token(data={"sub": student.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_get_statistics_as_admin(client: TestClient, db_session: Session):
    """Test admin can get statistics"""
    # Create admin user
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    # Create audit logs
    audit_service = AuditService(db_session)
    audit_service.log(action=AuditAction.LOGIN, user_id=admin.id)
    audit_service.log(action=AuditAction.LOGIN_FAILED)

    # Login as admin
    token = create_access_token(data={"sub": admin.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/statistics",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_logs" in data
    assert "unique_users" in data
    assert "failed_logins" in data
    assert data["total_logs"] >= 2


def test_get_security_events(client: TestClient, db_session: Session):
    """Test admin can get security events"""
    # Create admin user
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    # Create security events
    audit_service = AuditService(db_session)
    audit_service.log(action=AuditAction.LOGIN_FAILED)
    audit_service.log(action=AuditAction.PASSWORD_CHANGE, user_id=admin.id)

    # Login as admin
    token = create_access_token(data={"sub": admin.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/security-events",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data


def test_get_resource_history(client: TestClient, db_session: Session):
    """Test admin can get resource audit history"""
    # Create admin user
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    # Create resource logs
    audit_service = AuditService(db_session)
    audit_service.log(
        action=AuditAction.LICENSE_ISSUED,
        resource_type="license",
        resource_id=1
    )

    # Login as admin
    token = create_access_token(data={"sub": admin.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/resource/license/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data


def test_pagination_works(client: TestClient, db_session: Session):
    """Test pagination parameters work"""
    # Create admin user
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    # Create multiple logs
    audit_service = AuditService(db_session)
    for i in range(10):
        audit_service.log(action=AuditAction.LOGIN, user_id=admin.id)

    # Login as admin
    token = create_access_token(data={"sub": admin.email}, expires_delta=timedelta(hours=1))

    response = client.get(
        "/api/v1/audit/logs?limit=5&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["logs"]) <= 5


def test_tournament_enrollment_audit(client: TestClient, db_session: Session):
    """Test that tournament enrollment/unenrollment actions are audited"""
    # Create test user
    user = User(
        name="Test Player",
        email="player@test.com",
        password_hash="$2b$10$abcdefghijklmnopqrstuv",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Create audit logs for tournament actions
    audit_service = AuditService(db_session)
    audit_service.log(
        action=AuditAction.TOURNAMENT_ENROLLED,
        user_id=user.id,
        resource_type="tournament",
        resource_id=1,
        details={"tournament_name": "Test Tournament"}
    )
    audit_service.log(
        action=AuditAction.TOURNAMENT_UNENROLLED,
        user_id=user.id,
        resource_type="tournament",
        resource_id=1,
        details={"tournament_name": "Test Tournament"}
    )

    # Login as user
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))

    # Query user's logs
    response = client.get(
        "/api/v1/audit/my-logs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2

    # Verify tournament actions are present
    actions = [log["action"] for log in data["logs"]]
    assert AuditAction.TOURNAMENT_ENROLLED in actions
    assert AuditAction.TOURNAMENT_UNENROLLED in actions
