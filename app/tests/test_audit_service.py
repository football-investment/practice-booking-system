"""
Test Audit Service

Comprehensive tests for audit logging functionality.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User, UserRole


def test_log_audit_event(db_session):
    """Test logging an audit event"""
    service = AuditService(db_session)

    # Create test user first
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.commit()

    log = service.log(
        action=AuditAction.LOGIN,
        user_id=user.id,
        details={"email": "test@example.com"}
    )

    assert log.id is not None
    assert log.action == AuditAction.LOGIN
    assert log.user_id == user.id
    assert log.details["email"] == "test@example.com"


def test_get_user_logs(db_session):
    """Test getting logs for specific user"""
    service = AuditService(db_session)

    # Create test user
    user = User(
        name="Test User",
        email="testuser@example.com",
        password_hash="hashed",
        role=UserRole.STUDENT
    )
    db_session.add(user)
    db_session.commit()

    # Create 3 logs for user
    service.log(action=AuditAction.LOGIN, user_id=user.id)
    service.log(action=AuditAction.LICENSE_VIEWED, user_id=user.id)
    service.log(action=AuditAction.LOGOUT, user_id=user.id)

    logs = service.get_user_logs(user.id, limit=10)
    assert len(logs) == 3
    assert all(log.user_id == user.id for log in logs)


def test_get_logs_by_action(db_session):
    """Test filtering logs by action"""
    service = AuditService(db_session)

    # Create test users
    user1 = User(name="User 1", email="user1@test.com", password_hash="h", role=UserRole.STUDENT)
    user2 = User(name="User 2", email="user2@test.com", password_hash="h", role=UserRole.STUDENT)
    db_session.add_all([user1, user2])
    db_session.commit()

    service.log(action=AuditAction.LOGIN, user_id=user1.id)
    service.log(action=AuditAction.LOGIN, user_id=user2.id)
    service.log(action=AuditAction.LOGOUT, user_id=user1.id)

    login_logs = service.get_logs_by_action(AuditAction.LOGIN)
    assert len(login_logs) == 2
    assert all(log.action == AuditAction.LOGIN for log in login_logs)


def test_get_resource_logs(db_session):
    """Test getting logs for specific resource"""
    service = AuditService(db_session)

    service.log(
        action=AuditAction.LICENSE_ISSUED,
        resource_type="license",
        resource_id=123
    )
    service.log(
        action=AuditAction.LICENSE_VIEWED,
        resource_type="license",
        resource_id=123
    )
    service.log(
        action=AuditAction.LICENSE_VIEWED,
        resource_type="license",
        resource_id=456  # Different license
    )

    logs = service.get_resource_logs("license", 123)
    assert len(logs) == 2
    assert all(log.resource_type == "license" and log.resource_id == 123 for log in logs)


def test_get_failed_logins(db_session):
    """Test getting failed login attempts"""
    service = AuditService(db_session)

    # Create test user
    user = User(name="Test", email="test@test.com", password_hash="h", role=UserRole.STUDENT)
    db_session.add(user)
    db_session.commit()

    service.log(action=AuditAction.LOGIN_FAILED, details={"email": "bad@test.com"})
    service.log(action=AuditAction.LOGIN_FAILED, details={"email": "bad2@test.com"})
    service.log(action=AuditAction.LOGIN, user_id=user.id)

    failed = service.get_failed_logins(hours=24)
    assert len(failed) == 2
    assert all(log.action == AuditAction.LOGIN_FAILED for log in failed)


def test_get_security_events(db_session):
    """Test getting security-related events"""
    service = AuditService(db_session)

    # Create test user
    user = User(name="Test", email="test@test.com", password_hash="h", role=UserRole.STUDENT)
    db_session.add(user)
    db_session.commit()

    service.log(action=AuditAction.LOGIN_FAILED)
    service.log(action=AuditAction.PASSWORD_CHANGE, user_id=user.id)
    service.log(action=AuditAction.LOGIN, user_id=user.id)

    security_logs = service.get_security_events(hours=24)
    assert len(security_logs) == 2  # LOGIN_FAILED + PASSWORD_CHANGE
    assert AuditAction.LOGIN_FAILED in [log.action for log in security_logs]
    assert AuditAction.PASSWORD_CHANGE in [log.action for log in security_logs]


def test_get_statistics(db_session):
    """Test audit log statistics"""
    service = AuditService(db_session)

    # Create test user
    user = User(name="Test", email="test@test.com", password_hash="h", role=UserRole.STUDENT)
    db_session.add(user)
    db_session.commit()

    # Create various logs
    service.log(action=AuditAction.LOGIN, user_id=user.id)
    service.log(action=AuditAction.LOGIN_FAILED)
    service.log(action=AuditAction.LICENSE_VIEWED, user_id=user.id)

    stats = service.get_statistics()

    assert stats["total_logs"] == 3
    assert stats["unique_users"] == 1
    assert stats["failed_logins"] == 1
    assert AuditAction.LOGIN in stats["action_counts"]
    assert stats["action_counts"][AuditAction.LOGIN] == 1


def test_search_logs_with_multiple_filters(db_session):
    """Test searching with multiple filters"""
    service = AuditService(db_session)

    # Create test user
    user = User(name="Test", email="test@test.com", password_hash="h", role=UserRole.STUDENT)
    db_session.add(user)
    db_session.commit()

    service.log(
        action=AuditAction.LICENSE_ISSUED,
        user_id=user.id,
        resource_type="license",
        resource_id=1
    )
    service.log(
        action=AuditAction.PROJECT_CREATED,
        user_id=user.id,
        resource_type="project",
        resource_id=1
    )
    service.log(
        action=AuditAction.LICENSE_ISSUED,
        user_id=user.id,
        resource_type="license",
        resource_id=2
    )

    # Search for license actions only
    results = service.search_logs(
        user_id=user.id,
        action=AuditAction.LICENSE_ISSUED,
        resource_type="license"
    )

    assert len(results) == 2
    assert all(log.action == AuditAction.LICENSE_ISSUED for log in results)
    assert all(log.resource_type == "license" for log in results)


def test_date_range_filtering(db_session):
    """Test filtering logs by date range"""
    from datetime import timezone
    service = AuditService(db_session)

    # Create test user
    user = User(name="Test", email="test@test.com", password_hash="h", role=UserRole.STUDENT)
    db_session.add(user)
    db_session.commit()

    service.log(action=AuditAction.LOGIN, user_id=user.id)

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

    logs = service.get_user_logs(
        user_id=user.id,
        start_date=yesterday,
        end_date=tomorrow
    )

    assert len(logs) == 1
    assert logs[0].timestamp >= yesterday
    assert logs[0].timestamp <= tomorrow


def test_audit_action_constants_exist():
    """Test that all critical audit actions are defined"""
    assert hasattr(AuditAction, 'LOGIN')
    assert hasattr(AuditAction, 'LOGIN_FAILED')
    assert hasattr(AuditAction, 'LICENSE_ISSUED')
    assert hasattr(AuditAction, 'SPECIALIZATION_SELECTED')
    assert hasattr(AuditAction, 'PROJECT_ENROLLED')
    assert hasattr(AuditAction, 'QUIZ_STARTED')
    assert hasattr(AuditAction, 'CERTIFICATE_ISSUED')

    # Verify they're strings
    assert isinstance(AuditAction.LOGIN, str)
    assert isinstance(AuditAction.LICENSE_ISSUED, str)

    # Verify expected values
    assert AuditAction.LOGIN == "LOGIN"
    assert AuditAction.LOGIN_FAILED == "LOGIN_FAILED"
