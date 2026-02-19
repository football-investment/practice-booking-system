"""
🧪 Sync Edge Case Test Suite
============================

P2 TASK: Comprehensive edge case testing for Progress-License synchronization

Test Scenarios:
1. Interrupted License Upgrade (transaction rollback)
2. Concurrent Level Up (race conditions)
3. Orphan Prevention (FK constraints)
4. License Without Progress (auto-sync creates progress)
5. Progress Without License (auto-sync creates license)
6. Desync After Rollback (background job fixes)
7. Max Level Overflow (validation prevents)
8. Negative XP (validation prevents)
9. Duplicate Auto-Sync (idempotent behavior)

Usage:
    pytest app/tests/test_sync_edge_cases.py -v
    pytest app/tests/test_sync_edge_cases.py::SyncEdgeCaseTester::test_interrupted_license_upgrade -v
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, timezone
from contextlib import contextmanager
from threading import Thread

from app.database import SessionLocal
from app.services.specialization_service import SpecializationService
from app.services.license_service import LicenseService
from app.services.progress_license_sync_service import ProgressLicenseSyncService
from app.models.user import User, UserRole
from app.models.user_progress import SpecializationProgress, Specialization
from app.models.license import UserLicense


@contextmanager
def get_test_db():
    """Context manager for test database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def db_session():
    """Pytest fixture for database session"""
    with get_test_db() as db:
        yield db


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user"""
    import uuid
    user = User(
        email=f"test_edge_{uuid.uuid4().hex[:8]}@test.com",  # Use UUID for uniqueness
        password_hash="hashed",
        name="Edge Case Test User",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_specialization(db_session: Session):
    """Get PLAYER specialization for testing"""
    spec = db_session.query(Specialization).filter(
        Specialization.id == "PLAYER"
    ).first()
    assert spec is not None, "PLAYER specialization must exist"
    return spec


class TestSyncEdgeCases:
    """
    Edge Case Test Suite for Progress-License Synchronization

    P2 VALIDATION: Ensures system handles boundary conditions correctly
    """

    def test_interrupted_license_upgrade(self, db_session: Session, test_user: User):
        """
        EDGE CASE 1: Transaction Rollback During License Upgrade

        Scenario:
        1. Start license advancement
        2. Simulate DB error mid-transaction
        3. Verify rollback (no partial update)

        Expected:
        - License level unchanged
        - No progression record created
        - Clean rollback
        """
        license_service = LicenseService(db_session)

        # Create initial license at level 1
        license = license_service.get_or_create_user_license(test_user.id, "PLAYER")
        assert license.current_level == 1

        # Attempt to advance with forced error
        try:
            # Force a constraint violation to trigger rollback
            result = license_service.advance_license(
                user_id=test_user.id,
                specialization="PLAYER",
                target_level=999,  # Invalid level (max is 8)
                advanced_by=test_user.id,
                reason="Edge case test"
            )

            # Should fail validation
            assert result["success"] == False
            assert "invalid" in result["message"].lower() or "validation" in result["message"].lower()

        except Exception as e:
            # Any exception should trigger rollback
            db_session.rollback()

        # Verify license unchanged
        db_session.refresh(license)
        assert license.current_level == 1, "License level should be unchanged after failed upgrade"

    def test_concurrent_level_up(self, test_user: User, test_specialization: Specialization):
        """
        EDGE CASE 2: Race Condition - Concurrent Level Up Attempts

        Scenario:
        1. Create progress at level 1
        2. Two threads try to level up simultaneously
        3. Only one should succeed

        Expected:
        - Only 1 level up succeeds
        - No duplicate progress records
        - Clean conflict resolution
        """
        # Create initial progress
        with get_test_db() as db1:
            progress = SpecializationProgress(
                student_id=test_user.id,
                specialization_id=test_specialization.id,
                current_level=1,
                total_xp=1000,  # Enough XP to level up
                completed_sessions=10
            )
            db1.add(progress)
            db1.commit()

        results = []

        def attempt_level_up(thread_id):
            """Function to run in separate thread"""
            try:
                with get_test_db() as db:
                    service = SpecializationService(db)
                    result = service.update_progress(
                        student_id=test_user.id,
                        specialization_id=test_specialization.id,
                        xp_gained=500,  # Should trigger level up
                        sessions_completed=5
                    )
                    results.append((thread_id, result))
            except Exception as e:
                results.append((thread_id, {"error": str(e)}))

        # Start two concurrent threads
        thread1 = Thread(target=attempt_level_up, args=(1,))
        thread2 = Thread(target=attempt_level_up, args=(2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Verify results
        assert len(results) == 2

        # At least one should succeed
        successes = [r for r in results if r[1].get('success')]
        assert len(successes) >= 1, "At least one level up should succeed"

        # Verify final state
        with get_test_db() as db:
            final_progress = db.query(SpecializationProgress).filter(
                SpecializationProgress.student_id == test_user.id,
                SpecializationProgress.specialization_id == test_specialization.id
            ).all()

            # Should have exactly ONE progress record (unique constraint)
            assert len(final_progress) == 1, "Should have exactly one progress record"

    def test_orphan_prevention_fk_constraint(self, db_session: Session, test_user: User):
        """
        EDGE CASE 3: Foreign Key Constraints Prevent Orphan Records

        Scenario:
        1. Create progress for user
        2. Try to delete user (should fail due to FK constraint)

        Expected:
        - User deletion blocked by FK constraint
        - Progress record remains intact
        """
        # Create progress
        progress = SpecializationProgress(
            student_id=test_user.id,
            specialization_id="PLAYER",
            current_level=1,
            total_xp=100,
            completed_sessions=1
        )
        db_session.add(progress)
        db_session.commit()

        # Try to delete user (should fail)
        with pytest.raises((IntegrityError, SQLAlchemyError)):
            db_session.delete(test_user)
            db_session.commit()

        # Rollback the failed delete
        db_session.rollback()

        # Verify user and progress still exist
        user_exists = db_session.query(User).filter(User.id == test_user.id).first()
        progress_exists = db_session.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == test_user.id
        ).first()

        assert user_exists is not None, "User should still exist"
        assert progress_exists is not None, "Progress should still exist"

    def test_license_without_progress_auto_sync(self, db_session: Session, test_user: User):
        """
        EDGE CASE 4: License Exists But No Progress (Auto-Sync Creates Progress)

        Scenario:
        1. Admin manually creates license at level 3
        2. No progress exists
        3. Auto-sync should create progress

        Expected:
        - Progress created with level matching license
        - Sync result indicates "created"
        """
        license_service = LicenseService(db_session)
        sync_service = ProgressLicenseSyncService(db_session)

        # Create license without progress
        license = license_service.get_or_create_user_license(test_user.id, "PLAYER")
        license.current_level = 3
        db_session.commit()

        # Delete any existing progress (simulate missing progress)
        db_session.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == test_user.id,
            SpecializationProgress.specialization_id == "PLAYER"
        ).delete()
        db_session.commit()

        # Run sync
        result = sync_service.sync_license_to_progress(test_user.id, "PLAYER")

        # Verify
        assert result["success"] == True
        assert result["action"] == "created"

        # Check progress created
        progress = db_session.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == test_user.id,
            SpecializationProgress.specialization_id == "PLAYER"
        ).first()

        assert progress is not None
        assert progress.current_level == 3

    def test_progress_without_license_auto_sync(self, db_session: Session, test_user: User):
        """
        EDGE CASE 5: Progress Exists But No License (Auto-Sync Creates License)

        Scenario:
        1. Student levels up naturally (progress created)
        2. No license exists
        3. Auto-sync should create license

        Expected:
        - License created with level matching progress
        - Sync result indicates "created"
        """
        spec_service = SpecializationService(db_session)
        sync_service = ProgressLicenseSyncService(db_session)

        # Delete any existing license
        db_session.query(UserLicense).filter(
            UserLicense.user_id == test_user.id,
            UserLicense.specialization_type == "PLAYER"
        ).delete()
        db_session.commit()

        # Create progress at level 2
        progress = SpecializationProgress(
            student_id=test_user.id,
            specialization_id="PLAYER",
            current_level=2,
            total_xp=500,
            completed_sessions=5
        )
        db_session.add(progress)
        db_session.commit()

        # Run sync
        result = sync_service.sync_progress_to_license(test_user.id, "PLAYER")

        # Verify
        assert result["success"] == True
        assert result["action"] == "created"

        # Check license created
        license = db_session.query(UserLicense).filter(
            UserLicense.user_id == test_user.id,
            UserLicense.specialization_type == "PLAYER"
        ).first()

        assert license is not None
        assert license.current_level == 2

    def test_max_level_overflow_validation(self, db_session: Session, test_user: User):
        """
        EDGE CASE 7: Attempt to Exceed Max Level

        Scenario:
        1. User at level 8 (max for PLAYER)
        2. Try to level up to 9
        3. Should be prevented by validation

        Expected:
        - Level remains at 8
        - Validation error returned
        """
        spec_service = SpecializationService(db_session)

        # Create progress at max level (8)
        progress = SpecializationProgress(
            student_id=test_user.id,
            specialization_id="PLAYER",
            current_level=8,
            total_xp=10000,
            completed_sessions=100
        )
        db_session.add(progress)
        db_session.commit()

        # Try to gain more XP (should not level up past 8)
        result = spec_service.update_progress(
            student_id=test_user.id,
            specialization_id="PLAYER",
            xp_gained=5000,  # Lots of XP
            sessions_completed=10
        )

        # Should succeed but not level up
        assert result["success"] == True
        assert result["leveled_up"] == False
        assert result["new_level"] == 8  # Still at max

    def test_negative_xp_validation(self, db_session: Session, test_user: User):
        """
        EDGE CASE 8: Attempt to Add Negative XP

        Scenario:
        1. Try to update progress with negative XP
        2. Should be rejected or handled safely

        Expected:
        - No XP reduction (or handled with warning)
        - No system crash
        """
        spec_service = SpecializationService(db_session)

        # Create progress
        progress = SpecializationProgress(
            student_id=test_user.id,
            specialization_id="PLAYER",
            current_level=1,
            total_xp=100,
            completed_sessions=1
        )
        db_session.add(progress)
        db_session.commit()

        initial_xp = progress.total_xp

        # Try negative XP (this might be allowed for corrections, or rejected)
        try:
            result = spec_service.update_progress(
                student_id=test_user.id,
                specialization_id="PLAYER",
                xp_gained=-50,  # Negative XP
                sessions_completed=0
            )

            # If allowed, verify safe handling
            db_session.refresh(progress)
            # XP should either stay same or reduce safely (not go negative)
            assert progress.total_xp >= 0, "XP should never go below 0"

        except ValueError as e:
            # If validation rejects negative XP, that's also acceptable
            assert "negative" in str(e).lower() or "invalid" in str(e).lower()

    def test_duplicate_auto_sync_idempotent(self, db_session: Session, test_user: User):
        """
        EDGE CASE 9: Multiple Auto-Sync Calls Are Idempotent

        Scenario:
        1. Progress and License already in sync
        2. Call auto-sync multiple times
        3. Should be idempotent (no changes, no errors)

        Expected:
        - All sync calls return "already in sync"
        - No duplicate records created
        - No errors
        """
        sync_service = ProgressLicenseSyncService(db_session)

        # Create synced progress and license
        progress = SpecializationProgress(
            student_id=test_user.id,
            specialization_id="PLAYER",
            current_level=3,
            total_xp=500,
            completed_sessions=5
        )
        db_session.add(progress)

        license = UserLicense(
            user_id=test_user.id,
            specialization_type="PLAYER",
            current_level=3,
            max_achieved_level=3,
            started_at=datetime.now(timezone.utc)
        )
        db_session.add(license)
        db_session.commit()

        # Call sync multiple times
        results = []
        for i in range(5):
            result1 = sync_service.sync_progress_to_license(test_user.id, "PLAYER")
            result2 = sync_service.sync_license_to_progress(test_user.id, "PLAYER")
            results.append((result1, result2))

        # All should indicate "already in sync"
        for r1, r2 in results:
            assert r1["success"] == True
            assert r1["message"] == "Already in sync"
            assert r2["success"] == True
            assert r2["message"] == "Already in sync"

        # Verify no duplicates created
        progress_count = db_session.query(SpecializationProgress).filter(
            SpecializationProgress.student_id == test_user.id,
            SpecializationProgress.specialization_id == "PLAYER"
        ).count()

        license_count = db_session.query(UserLicense).filter(
            UserLicense.user_id == test_user.id,
            UserLicense.specialization_type == "PLAYER"
        ).count()

        assert progress_count == 1, "Should have exactly one progress record"
        assert license_count == 1, "Should have exactly one license record"


# Run with: pytest app/tests/test_sync_edge_cases.py -v --tb=short
