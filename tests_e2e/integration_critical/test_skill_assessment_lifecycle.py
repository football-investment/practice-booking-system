"""
🎯 Skill Assessment Lifecycle E2E Tests — Production-Grade

Tests skill assessment state machine with same rigor as Priority 4 (Reward Distribution):
- Full lifecycle (NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED)
- Invalid transition rejection
- Idempotency (create, validate, archive)
- Concurrency protection (3-thread stress tests)
- Row-level locking validation
- Business rule validation (validation requirement)

Test Strategy:
- Direct service layer testing (no API layer yet)
- Row-level locking via SQLAlchemy
- Concurrent execution via threading
- Deterministic validation (no flake tolerance)

Performance Targets:
- Test 1: Full lifecycle (~2s)
- Test 2: Invalid transitions (~1.5s)
- Test 3: Idempotency (~1.5s)
- Test 4: Concurrent creation (~2s)
- Test 5: Concurrent validation (~2s)
- Test 6: Concurrent archive+create (~2.5s)
- TOTAL: <12s (hard cap: <30s)

Stability Target: 0 flake in 20 runs
"""
import sys
import os

# Add project root to Python path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

from app.database import get_db
from app.services.football_skill_service import FootballSkillService
from app.services.skill_state_machine import (
    SkillAssessmentState,
    determine_validation_requirement,
    get_skill_category
)
from app.models.football_skill_assessment import FootballSkillAssessment
from app.models.license import UserLicense
from app.models.user import User, UserRole
from sqlalchemy.orm import Session


# ============================================================================
# TEST MARKERS
# ============================================================================

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration_critical,
    pytest.mark.skill_lifecycle,
    pytest.mark.priority_k1
]


# ============================================================================
# HELPER FUNCTIONS — License & User Management
# ============================================================================

def create_test_license(
    db: Session,
    user: User,
    specialization_type: str = "LFA_FOOTBALL_PLAYER",
    current_level: int = 3
) -> UserLicense:
    """
    Create test license for skill assessment testing.

    Args:
        db: Database session
        user: User to create license for
        specialization_type: License specialization
        current_level: Current license level

    Returns:
        Created UserLicense
    """
    license = UserLicense(
        user_id=user.id,
        specialization_type=specialization_type,
        current_level=current_level,
        max_achieved_level=current_level,
        started_at=datetime.now(timezone.utc),
        is_active=True,
        payment_verified=True,
        payment_verified_at=datetime.now(timezone.utc),
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(timezone.utc),
        football_skills={}  # Empty initially
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    return license


def create_test_instructor(
    db: Session,
    email_suffix: str,
    tenure_days: int = 365
) -> User:
    """
    Create test instructor with specific tenure.

    Args:
        db: Database session
        email_suffix: Unique email suffix
        tenure_days: Instructor tenure in days (affects validation requirement)

    Returns:
        Created instructor User
    """
    timestamp = int(time.time() * 1000)
    instructor = User(
        email=f"instructor_{email_suffix}_{timestamp}@test.lfa",
        name=f"Test Instructor {email_suffix}",
        role=UserRole.INSTRUCTOR,
        is_active=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=tenure_days),
        password_hash="dummy_hash_for_service_tests"  # Service-layer tests don't need real password
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return instructor


def create_test_admin(db: Session, email_suffix: str) -> User:
    """Create test admin user"""
    timestamp = int(time.time() * 1000)
    admin = User(
        email=f"admin_{email_suffix}_{timestamp}@test.lfa",
        name=f"Test Admin {email_suffix}",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        password_hash="dummy_hash_for_service_tests"  # Service-layer tests don't need real password
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


# ============================================================================
# HELPER FUNCTIONS — Verification & Assertions
# ============================================================================

def verify_assessment_state(
    assessment: FootballSkillAssessment,
    expected_status: str,
    expected_validated_by: int = None,
    expected_archived_by: int = None
) -> None:
    """
    Verify assessment state matches expectations.

    Args:
        assessment: Assessment to verify
        expected_status: Expected status
        expected_validated_by: Expected validator user ID (if validated)
        expected_archived_by: Expected archiver user ID (if archived)

    Raises:
        AssertionError: If state doesn't match expectations
    """
    assert assessment.status == expected_status, \
        f"Expected status={expected_status}, got {assessment.status}"

    if expected_status == SkillAssessmentState.VALIDATED:
        assert assessment.validated_by == expected_validated_by, \
            f"Expected validated_by={expected_validated_by}, got {assessment.validated_by}"
        assert assessment.validated_at is not None, \
            "Expected validated_at to be set"

    if expected_status == SkillAssessmentState.ARCHIVED:
        assert assessment.archived_by == expected_archived_by, \
            f"Expected archived_by={expected_archived_by}, got {assessment.archived_by}"
        assert assessment.archived_at is not None, \
            "Expected archived_at to be set"
        assert assessment.archived_reason is not None, \
            "Expected archived_reason to be set"


def verify_state_transition_audit(
    assessment: FootballSkillAssessment,
    expected_previous_status: str,
    expected_current_status: str,
    expected_changed_by: int
) -> None:
    """
    Verify state transition audit trail.

    Args:
        assessment: Assessment to verify
        expected_previous_status: Expected previous status
        expected_current_status: Expected current status
        expected_changed_by: Expected user who changed status

    Raises:
        AssertionError: If audit trail doesn't match expectations
    """
    assert assessment.previous_status == expected_previous_status, \
        f"Expected previous_status={expected_previous_status}, got {assessment.previous_status}"
    assert assessment.status == expected_current_status, \
        f"Expected status={expected_current_status}, got {assessment.status}"
    assert assessment.status_changed_by == expected_changed_by, \
        f"Expected status_changed_by={expected_changed_by}, got {assessment.status_changed_by}"
    assert assessment.status_changed_at is not None, \
        "Expected status_changed_at to be set"


# ============================================================================
# TEST 1: Full Lifecycle
# ============================================================================

@pytest.mark.full_lifecycle
def test_skill_assessment_full_lifecycle():
    """
    Test full skill assessment lifecycle.

    Flow:
    1. Create instructor + student with license
    2. Instructor creates assessment (NOT_ASSESSED → ASSESSED)
    3. Verify status = ASSESSED, requires_validation determined
    4. Admin validates assessment (ASSESSED → VALIDATED)
    5. Verify status = VALIDATED, validated_by = admin_id
    6. Instructor creates new assessment → old auto-archived (VALIDATED → ARCHIVED)
    7. Verify old status = ARCHIVED, new status = ASSESSED

    Validations:
    - State transitions follow state machine
    - Timestamps populated correctly
    - Auto-archiving works (old → ARCHIVED when new created)
    - Audit trail complete (previous_status, status_changed_*)

    Runtime Target: ~2s
    """
    db = next(get_db())
    service = FootballSkillService(db)

    try:
        # ==================================================================
        # Setup: Create instructor + student + license
        # ==================================================================
        instructor = create_test_instructor(db, "lifecycle", tenure_days=365)
        admin = create_test_admin(db, "lifecycle")

        student = User(
            email=f"student_lifecycle_{int(time.time()*1000)}@test.lfa",
            name="Test Student Lifecycle",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        license = create_test_license(db, student, current_level=3)

        # ==================================================================
        # Step 1: Create assessment (NOT_ASSESSED → ASSESSED)
        # ==================================================================
        assessment1, created1 = service.create_assessment(
            user_license_id=license.id,
            skill_name='ball_control',
            points_earned=7,
            points_total=10,
            assessed_by=instructor.id,
            notes="First assessment"
        )

        assert created1 == True, "Expected assessment to be created"
        assert assessment1.status == SkillAssessmentState.ASSESSED, \
            f"Expected status=ASSESSED, got {assessment1.status}"
        assert assessment1.requires_validation == False, \
            "Expected requires_validation=False (level 3, tenure 365, physical category)"
        assert assessment1.previous_status == SkillAssessmentState.NOT_ASSESSED, \
            "Expected previous_status=NOT_ASSESSED"

        assessment1_id = assessment1.id
        db.commit()

        # ==================================================================
        # Step 2: Validate assessment (ASSESSED → VALIDATED)
        # ==================================================================
        validated = service.validate_assessment(
            assessment_id=assessment1_id,
            validated_by=admin.id
        )
        db.commit()

        verify_assessment_state(
            validated,
            expected_status=SkillAssessmentState.VALIDATED,
            expected_validated_by=admin.id
        )
        verify_state_transition_audit(
            validated,
            expected_previous_status=SkillAssessmentState.ASSESSED,
            expected_current_status=SkillAssessmentState.VALIDATED,
            expected_changed_by=admin.id
        )

        # ==================================================================
        # Step 3: Create new assessment → old auto-archived
        # ==================================================================
        assessment2, created2 = service.create_assessment(
            user_license_id=license.id,
            skill_name='ball_control',
            points_earned=8,
            points_total=10,
            assessed_by=instructor.id,
            notes="Second assessment (replaces first)"
        )
        db.commit()

        assert created2 == True, "Expected new assessment to be created"
        assert assessment2.status == SkillAssessmentState.ASSESSED, \
            f"Expected new status=ASSESSED, got {assessment2.status}"

        # Verify old assessment archived
        db.refresh(validated)
        verify_assessment_state(
            validated,
            expected_status=SkillAssessmentState.ARCHIVED,
            expected_archived_by=instructor.id
        )
        assert validated.archived_reason == "Replaced by new assessment", \
            f"Expected archived_reason='Replaced by new assessment', got {validated.archived_reason}"

        print(f"✅ Full lifecycle test PASSED")
        print(f"   Assessment 1: NOT_ASSESSED → ASSESSED → VALIDATED → ARCHIVED")
        print(f"   Assessment 2: NOT_ASSESSED → ASSESSED")

    finally:
        # Cleanup
        db.rollback()
        db.close()


# ============================================================================
# TEST 2: Invalid Transitions
# ============================================================================

@pytest.mark.invalid_transitions
def test_skill_assessment_invalid_transitions():
    """
    Test invalid state transition rejection.

    Test Cases:
    1. Cannot validate non-existent assessment → ValueError
    2. Cannot validate ARCHIVED assessment → ValueError
    3. Cannot archive NOT_ASSESSED (no assessment exists) → ValueError
    4. Cannot un-validate (VALIDATED → ASSESSED) → ValueError (attempted via direct status change)

    Validations:
    - All invalid transitions rejected with clear error messages
    - State machine enforces business rules
    - No state corruption

    Runtime Target: ~1.5s
    """
    db = next(get_db())
    service = FootballSkillService(db)

    try:
        # ==================================================================
        # Setup
        # ==================================================================
        instructor = create_test_instructor(db, "invalid", tenure_days=365)
        student = User(
            email=f"student_invalid_{int(time.time()*1000)}@test.lfa",
            name="Test Student Invalid",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        license = create_test_license(db, student, current_level=3)

        # ==================================================================
        # Test 1: Cannot validate non-existent assessment
        # ==================================================================
        with pytest.raises(ValueError, match="Assessment 99999 not found"):
            service.validate_assessment(
                assessment_id=99999,
                validated_by=instructor.id
            )

        # ==================================================================
        # Test 2: Cannot validate ARCHIVED assessment
        # ==================================================================
        # Create + archive assessment
        assessment, _ = service.create_assessment(
            user_license_id=license.id,
            skill_name='dribbling',
            points_earned=6,
            points_total=10,
            assessed_by=instructor.id
        )
        db.commit()

        archived = service.archive_assessment(
            assessment_id=assessment.id,
            archived_by=instructor.id,
            reason="Test archive"
        )
        db.commit()

        # Try to validate archived
        with pytest.raises(ValueError, match="Invalid state transition.*ARCHIVED.*VALIDATED"):
            service.validate_assessment(
                assessment_id=archived.id,
                validated_by=instructor.id
            )

        # ==================================================================
        # Test 3: Cannot archive non-existent assessment
        # ==================================================================
        with pytest.raises(ValueError, match="Assessment 99998 not found"):
            service.archive_assessment(
                assessment_id=99998,
                archived_by=instructor.id,
                reason="Test"
            )

        print(f"✅ Invalid transitions test PASSED")
        print(f"   All invalid transitions correctly rejected")

    finally:
        db.rollback()
        db.close()


# ============================================================================
# TEST 3: Idempotency
# ============================================================================

@pytest.mark.idempotency
def test_skill_assessment_idempotency():
    """
    Test idempotency of state transitions.

    Test Cases:
    1. Create same assessment twice → returns existing (created=False)
    2. Validate same assessment twice → returns existing (idempotent)
    3. Archive same assessment twice → returns existing (idempotent)

    Validations:
    - Idempotent operations return existing object
    - No duplicate records created
    - State unchanged on idempotent call

    Runtime Target: ~1.5s
    """
    db = next(get_db())
    service = FootballSkillService(db)

    try:
        # ==================================================================
        # Setup
        # ==================================================================
        instructor = create_test_instructor(db, "idempotent", tenure_days=365)
        admin = create_test_admin(db, "idempotent")
        student = User(
            email=f"student_idempotent_{int(time.time()*1000)}@test.lfa",
            name="Test Student Idempotent",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        license = create_test_license(db, student, current_level=3)

        # ==================================================================
        # Test 1: Idempotent creation
        # ==================================================================
        assessment1, created1 = service.create_assessment(
            user_license_id=license.id,
            skill_name='passing',
            points_earned=8,
            points_total=10,
            assessed_by=instructor.id
        )
        db.commit()

        assert created1 == True, "Expected first creation to return created=True"

        # Create same assessment again (idempotent)
        assessment2, created2 = service.create_assessment(
            user_license_id=license.id,
            skill_name='passing',
            points_earned=8,
            points_total=10,
            assessed_by=instructor.id
        )
        db.commit()

        assert created2 == False, "Expected second creation to return created=False (idempotent)"
        assert assessment1.id == assessment2.id, \
            f"Expected same assessment ID (idempotent), got {assessment1.id} vs {assessment2.id}"

        # ==================================================================
        # Test 2: Idempotent validation
        # ==================================================================
        validated1 = service.validate_assessment(
            assessment_id=assessment1.id,
            validated_by=admin.id
        )
        db.commit()
        validated1_at = validated1.validated_at

        # Validate again (idempotent)
        validated2 = service.validate_assessment(
            assessment_id=assessment1.id,
            validated_by=admin.id
        )
        db.commit()

        assert validated2.id == validated1.id, "Expected same assessment ID (idempotent)"
        assert validated2.validated_at == validated1_at, \
            "Expected validated_at unchanged (idempotent)"

        # ==================================================================
        # Test 3: Idempotent archive
        # ==================================================================
        archived1 = service.archive_assessment(
            assessment_id=assessment1.id,
            archived_by=admin.id,
            reason="Test archive"
        )
        db.commit()
        archived1_at = archived1.archived_at

        # Archive again (idempotent)
        archived2 = service.archive_assessment(
            assessment_id=assessment1.id,
            archived_by=admin.id,
            reason="Test archive again"
        )
        db.commit()

        assert archived2.id == archived1.id, "Expected same assessment ID (idempotent)"
        assert archived2.archived_at == archived1_at, \
            "Expected archived_at unchanged (idempotent)"

        print(f"✅ Idempotency test PASSED")
        print(f"   All idempotent operations returned existing objects")

    finally:
        db.rollback()
        db.close()


# ============================================================================
# TEST 4: Concurrent Assessment Creation
# ============================================================================

@pytest.mark.concurrency
def test_concurrent_skill_assessment_creation():
    """
    Test concurrent assessment creation protection.

    Scenario:
    - 3 threads create assessment for same skill simultaneously
    - Simulates high-concurrency production environment

    Expected Behavior:
    - Thread 1: Creates assessment (created=True)
    - Thread 2, 3: Return existing (created=False, idempotent)

    Validations:
    - Only 1 FootballSkillAssessment with status=ASSESSED
    - All threads succeed (no exceptions)
    - No duplicate ASSESSED assessments

    Runtime Target: ~2s
    """
    db_main = next(get_db())

    try:
        # ==================================================================
        # Setup (main thread)
        # ==================================================================
        instructor = create_test_instructor(db_main, "concurrent_create", tenure_days=365)
        student = User(
            email=f"student_concurrent_{int(time.time()*1000)}@test.lfa",
            name="Test Student Concurrent",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db_main.add(student)
        db_main.commit()
        db_main.refresh(student)

        license = create_test_license(db_main, student, current_level=3)
        db_main.commit()

        license_id = license.id
        instructor_id = instructor.id

        # ==================================================================
        # Concurrent creation (3 threads)
        # ==================================================================
        results = []
        errors = []

        def create_assessment_thread(thread_id):
            """Thread function to create assessment"""
            db_thread = next(get_db())
            try:
                service = FootballSkillService(db_thread)
                assessment, created = service.create_assessment(
                    user_license_id=license_id,
                    skill_name='finishing',
                    points_earned=7,
                    points_total=10,
                    assessed_by=instructor_id,
                    notes=f"Thread {thread_id}"
                )
                db_thread.commit()
                results.append({
                    'thread_id': thread_id,
                    'assessment_id': assessment.id,
                    'created': created,
                    'status': assessment.status
                })
            except Exception as e:
                errors.append({'thread_id': thread_id, 'error': str(e)})
                db_thread.rollback()
            finally:
                db_thread.close()

        # Launch 3 threads simultaneously
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_assessment_thread, args=(i,))
            threads.append(thread)

        # Start all threads (concurrent execution)
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # ==================================================================
        # Verification
        # ==================================================================
        assert len(errors) == 0, f"Expected no errors, got {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Count created vs idempotent
        created_count = sum(1 for r in results if r['created'])
        idempotent_count = sum(1 for r in results if not r['created'])

        assert created_count == 1, \
            f"Expected exactly 1 thread to create assessment, got {created_count}"
        assert idempotent_count == 2, \
            f"Expected exactly 2 threads to return existing (idempotent), got {idempotent_count}"

        # Verify only 1 ASSESSED assessment exists
        db_main.expire_all()  # Refresh from DB
        active_assessments = db_main.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == license_id,
            FootballSkillAssessment.skill_name == 'finishing',
            FootballSkillAssessment.status == SkillAssessmentState.ASSESSED
        ).all()

        assert len(active_assessments) == 1, \
            f"Expected 1 active assessment, got {len(active_assessments)}"

        print(f"✅ Concurrent creation test PASSED")
        print(f"   Created: {created_count}, Idempotent: {idempotent_count}")
        print(f"   Race condition protection verified")

    finally:
        db_main.rollback()
        db_main.close()


# ============================================================================
# TEST 5: Concurrent Validation
# ============================================================================

@pytest.mark.concurrency
def test_concurrent_skill_validation():
    """
    Test concurrent validation protection.

    Scenario:
    - Create 1 ASSESSED assessment
    - 3 threads validate same assessment simultaneously

    Expected Behavior:
    - Thread 1: Validates (status=VALIDATED)
    - Thread 2, 3: Return existing (idempotent)

    Validations:
    - validated_at timestamp set exactly once
    - validated_by = first thread's user_id
    - No race condition artifacts

    Runtime Target: ~2s
    """
    db_main = next(get_db())

    try:
        # ==================================================================
        # Setup (main thread)
        # ==================================================================
        instructor = create_test_instructor(db_main, "concurrent_validate", tenure_days=365)
        admin = create_test_admin(db_main, "concurrent_validate")
        student = User(
            email=f"student_concurrent_val_{int(time.time()*1000)}@test.lfa",
            name="Test Student Concurrent Val",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db_main.add(student)
        db_main.commit()
        db_main.refresh(student)

        license = create_test_license(db_main, student, current_level=3)

        # Create initial assessment
        service = FootballSkillService(db_main)
        assessment, _ = service.create_assessment(
            user_license_id=license.id,
            skill_name='shot_power',
            points_earned=8,
            points_total=10,
            assessed_by=instructor.id
        )
        db_main.commit()

        assessment_id = assessment.id
        admin_id = admin.id

        # ==================================================================
        # Concurrent validation (3 threads)
        # ==================================================================
        results = []
        errors = []

        def validate_assessment_thread(thread_id):
            """Thread function to validate assessment"""
            db_thread = next(get_db())
            try:
                service = FootballSkillService(db_thread)
                validated = service.validate_assessment(
                    assessment_id=assessment_id,
                    validated_by=admin_id
                )
                db_thread.commit()
                results.append({
                    'thread_id': thread_id,
                    'assessment_id': validated.id,
                    'status': validated.status,
                    'validated_at': validated.validated_at
                })
            except Exception as e:
                errors.append({'thread_id': thread_id, 'error': str(e)})
                db_thread.rollback()
            finally:
                db_thread.close()

        # Launch 3 threads simultaneously
        threads = []
        for i in range(3):
            thread = threading.Thread(target=validate_assessment_thread, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # ==================================================================
        # Verification
        # ==================================================================
        assert len(errors) == 0, f"Expected no errors, got {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # All threads should return same assessment
        assessment_ids = [r['assessment_id'] for r in results]
        assert len(set(assessment_ids)) == 1, \
            f"Expected all threads to return same assessment, got {assessment_ids}"

        # All should have status=VALIDATED
        statuses = [r['status'] for r in results]
        assert all(s == SkillAssessmentState.VALIDATED for s in statuses), \
            f"Expected all status=VALIDATED, got {statuses}"

        # validated_at should be same (set exactly once)
        validated_ats = [r['validated_at'] for r in results]
        assert len(set(validated_ats)) == 1, \
            f"Expected validated_at set exactly once, got {validated_ats}"

        print(f"✅ Concurrent validation test PASSED")
        print(f"   All threads succeeded, validated_at set exactly once")

    finally:
        db_main.rollback()
        db_main.close()


# ============================================================================
# TEST 6: Concurrent Archive + Create
# ============================================================================

@pytest.mark.concurrency
def test_concurrent_archive_and_create():
    """
    Test concurrent archive + create new assessment.

    Scenario:
    - Create 1 VALIDATED assessment (id=1)
    - 3 threads simultaneously create new assessment (should archive id=1)

    Expected Behavior:
    - Thread 1: Archives old (id=1) + creates new (id=2)
    - Thread 2, 3: Return new (id=2, idempotent)

    Validations:
    - Old assessment (id=1) archived exactly once
    - Only 1 new ASSESSED assessment created
    - No duplicate ASSESSED assessments

    Runtime Target: ~2.5s
    """
    db_main = next(get_db())

    try:
        # ==================================================================
        # Setup (main thread)
        # ==================================================================
        instructor = create_test_instructor(db_main, "concurrent_archive", tenure_days=365)
        admin = create_test_admin(db_main, "concurrent_archive")
        student = User(
            email=f"student_concurrent_arch_{int(time.time()*1000)}@test.lfa",
            name="Test Student Concurrent Archive",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db_main.add(student)
        db_main.commit()
        db_main.refresh(student)

        license = create_test_license(db_main, student, current_level=3)

        # Create + validate initial assessment
        service = FootballSkillService(db_main)
        old_assessment, _ = service.create_assessment(
            user_license_id=license.id,
            skill_name='long_shots',
            points_earned=6,
            points_total=10,
            assessed_by=instructor.id,
            notes="Old assessment"
        )
        validated_old = service.validate_assessment(
            assessment_id=old_assessment.id,
            validated_by=admin.id
        )
        db_main.commit()

        old_assessment_id = validated_old.id
        license_id = license.id
        instructor_id = instructor.id

        # ==================================================================
        # Concurrent create new (archives old)
        # ==================================================================
        results = []
        errors = []

        def create_new_assessment_thread(thread_id):
            """Thread function to create new assessment (archives old)"""
            db_thread = next(get_db())
            try:
                service = FootballSkillService(db_thread)
                new_assessment, created = service.create_assessment(
                    user_license_id=license_id,
                    skill_name='long_shots',
                    points_earned=9,
                    points_total=10,
                    assessed_by=instructor_id,
                    notes=f"New assessment (thread {thread_id})"
                )
                db_thread.commit()
                results.append({
                    'thread_id': thread_id,
                    'assessment_id': new_assessment.id,
                    'created': created,
                    'status': new_assessment.status
                })
            except Exception as e:
                errors.append({'thread_id': thread_id, 'error': str(e)})
                db_thread.rollback()
            finally:
                db_thread.close()

        # Launch 3 threads simultaneously
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_new_assessment_thread, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # ==================================================================
        # Verification
        # ==================================================================
        assert len(errors) == 0, f"Expected no errors, got {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Count created vs idempotent
        created_count = sum(1 for r in results if r['created'])
        idempotent_count = sum(1 for r in results if not r['created'])

        assert created_count == 1, \
            f"Expected exactly 1 thread to create new assessment, got {created_count}"
        assert idempotent_count == 2, \
            f"Expected exactly 2 threads to return existing (idempotent), got {idempotent_count}"

        # Verify old assessment archived exactly once
        db_main.expire_all()
        old = db_main.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.id == old_assessment_id
        ).first()

        assert old.status == SkillAssessmentState.ARCHIVED, \
            f"Expected old status=ARCHIVED, got {old.status}"
        assert old.archived_reason == "Replaced by new assessment", \
            f"Expected archived_reason='Replaced by new assessment', got {old.archived_reason}"

        # Verify only 1 new ASSESSED assessment
        active_assessments = db_main.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == license_id,
            FootballSkillAssessment.skill_name == 'long_shots',
            FootballSkillAssessment.status == SkillAssessmentState.ASSESSED
        ).all()

        assert len(active_assessments) == 1, \
            f"Expected 1 active assessment, got {len(active_assessments)}"

        print(f"✅ Concurrent archive+create test PASSED")
        print(f"   Old archived exactly once, new created exactly once")

    finally:
        db_main.rollback()
        db_main.close()


# ============================================================================
# TEST 7: Comprehensive Invalid Transitions (Edge Cases)
# ============================================================================

@pytest.mark.invalid_transitions
@pytest.mark.edge_cases
def test_skill_assessment_invalid_transitions_comprehensive():
    """
    Test comprehensive invalid state transition rejection (all edge cases).

    Additional Test Cases (beyond test 2):
    1. VALIDATED → ASSESSED (cannot un-validate)
    2. VALIDATED → NOT_ASSESSED (cannot un-create validated)
    3. ARCHIVED → ASSESSED (terminal state)
    4. ARCHIVED → VALIDATED (terminal state)
    5. ARCHIVED → NOT_ASSESSED (terminal state)
    6. NOT_ASSESSED → VALIDATED (must create first)

    Validations:
    - All invalid transitions explicitly rejected
    - Error messages are descriptive
    - State machine integrity maintained

    Runtime Target: ~2s
    """
    db = next(get_db())
    service = FootballSkillService(db)

    try:
        # ==================================================================
        # Setup
        # ==================================================================
        instructor = create_test_instructor(db, "invalid_comprehensive", tenure_days=365)
        admin = create_test_admin(db, "invalid_comprehensive")
        student = User(
            email=f"student_invalid_comp_{int(time.time()*1000)}@test.lfa",
            name="Test Student Invalid Comprehensive",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        license = create_test_license(db, student, current_level=3)

        # ==================================================================
        # Edge Case 1: VALIDATED → ASSESSED (cannot un-validate)
        # ==================================================================
        # Create + validate assessment
        assessment1, _ = service.create_assessment(
            user_license_id=license.id,
            skill_name='crossing',
            points_earned=7,
            points_total=10,
            assessed_by=instructor.id
        )
        validated = service.validate_assessment(
            assessment_id=assessment1.id,
            validated_by=admin.id
        )
        db.commit()

        # Try to manually change VALIDATED → ASSESSED (simulate invalid transition)
        # Note: Service layer doesn't expose this, but we test state machine validation
        from app.services.skill_state_machine import validate_state_transition
        is_valid, error = validate_state_transition(
            SkillAssessmentState.VALIDATED,
            SkillAssessmentState.ASSESSED,
            allow_idempotent=False
        )
        assert is_valid == False, "Expected VALIDATED → ASSESSED to be invalid"
        assert "un-validate" in error.lower(), \
            f"Expected 'un-validate' in error message, got: {error}"

        # ==================================================================
        # Edge Case 2: VALIDATED → NOT_ASSESSED (cannot un-create)
        # ==================================================================
        is_valid, error = validate_state_transition(
            SkillAssessmentState.VALIDATED,
            SkillAssessmentState.NOT_ASSESSED,
            allow_idempotent=False
        )
        assert is_valid == False, "Expected VALIDATED → NOT_ASSESSED to be invalid"
        assert "un-create" in error.lower() or "validated" in error.lower(), \
            f"Expected 'un-create' or 'validated' in error message, got: {error}"

        # ==================================================================
        # Edge Case 3-5: ARCHIVED → * (all transitions from terminal state)
        # ==================================================================
        # Archive the validated assessment
        archived = service.archive_assessment(
            assessment_id=validated.id,
            archived_by=admin.id,
            reason="Test comprehensive invalid transitions"
        )
        db.commit()

        # Test ARCHIVED → ASSESSED
        is_valid, error = validate_state_transition(
            SkillAssessmentState.ARCHIVED,
            SkillAssessmentState.ASSESSED,
            allow_idempotent=False
        )
        assert is_valid == False, "Expected ARCHIVED → ASSESSED to be invalid"
        assert "terminal" in error.lower() or "archived" in error.lower(), \
            f"Expected 'terminal' or 'archived' in error message, got: {error}"

        # Test ARCHIVED → VALIDATED
        is_valid, error = validate_state_transition(
            SkillAssessmentState.ARCHIVED,
            SkillAssessmentState.VALIDATED,
            allow_idempotent=False
        )
        assert is_valid == False, "Expected ARCHIVED → VALIDATED to be invalid"
        assert "terminal" in error.lower() or "archived" in error.lower(), \
            f"Expected 'terminal' or 'archived' in error message, got: {error}"

        # Test ARCHIVED → NOT_ASSESSED
        is_valid, error = validate_state_transition(
            SkillAssessmentState.ARCHIVED,
            SkillAssessmentState.NOT_ASSESSED,
            allow_idempotent=False
        )
        assert is_valid == False, "Expected ARCHIVED → NOT_ASSESSED to be invalid"
        assert "terminal" in error.lower() or "archived" in error.lower(), \
            f"Expected 'terminal' or 'archived' in error message, got: {error}"

        # ==================================================================
        # Edge Case 6: NOT_ASSESSED → VALIDATED (must create first)
        # ==================================================================
        is_valid, error = validate_state_transition(
            SkillAssessmentState.NOT_ASSESSED,
            SkillAssessmentState.VALIDATED,
            allow_idempotent=False
        )
        assert is_valid == False, "Expected NOT_ASSESSED → VALIDATED to be invalid"
        assert "create" in error.lower() or "non-existent" in error.lower(), \
            f"Expected 'create' or 'non-existent' in error message, got: {error}"

        print(f"✅ Comprehensive invalid transitions test PASSED")
        print(f"   All 6 edge case invalid transitions correctly rejected")

    finally:
        db.rollback()
        db.close()


# ============================================================================
# TEST 8: Validation Requirement Business Rules
# ============================================================================

@pytest.mark.business_rules
@pytest.mark.edge_cases
def test_skill_assessment_validation_requirements():
    """
    Test validation requirement determination (business rules).

    Business Rules:
    1. High-stakes: License level 5+ requires validation
    2. New instructor: Tenure < 180 days requires validation
    3. Critical skills: mental, set_pieces categories require validation
    4. Default: Auto-accepted (no validation)

    Test Cases:
    - Level 5+ with experienced instructor, physical skill → requires validation
    - Level 3 with new instructor (< 180 days), physical skill → requires validation
    - Level 3 with experienced instructor, mental skill → requires validation
    - Level 3 with experienced instructor, set_pieces skill → requires validation
    - Level 3 with experienced instructor, physical skill → NO validation (auto-accepted)
    - Combination: Level 5+ + new instructor + critical skill → requires validation

    Runtime Target: ~2s
    """
    db = next(get_db())
    service = FootballSkillService(db)

    try:
        # ==================================================================
        # Setup: Multiple instructors with different tenures
        # ==================================================================
        experienced_instructor = create_test_instructor(db, "experienced", tenure_days=365)
        new_instructor = create_test_instructor(db, "new", tenure_days=100)

        # Students with different license levels
        student_level3 = User(
            email=f"student_level3_{int(time.time()*1000)}@test.lfa",
            name="Student Level 3",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        student_level5 = User(
            email=f"student_level5_{int(time.time()*1000)}@test.lfa",
            name="Student Level 5",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db.add_all([student_level3, student_level5])
        db.commit()
        db.refresh(student_level3)
        db.refresh(student_level5)

        license_level3 = create_test_license(db, student_level3, current_level=3)
        license_level5 = create_test_license(db, student_level5, current_level=5)

        # ==================================================================
        # Test Case 1: High-stakes (level 5+) requires validation
        # ==================================================================
        assessment_level5, _ = service.create_assessment(
            user_license_id=license_level5.id,
            skill_name='ball_control',  # Physical category
            points_earned=8,
            points_total=10,
            assessed_by=experienced_instructor.id,
            notes="High-stakes test"
        )
        db.commit()

        assert assessment_level5.requires_validation == True, \
            "Expected requires_validation=True for license level 5+"

        # ==================================================================
        # Test Case 2: New instructor (< 180 days) requires validation
        # ==================================================================
        assessment_new_instructor, _ = service.create_assessment(
            user_license_id=license_level3.id,
            skill_name='dribbling',  # Physical category
            points_earned=7,
            points_total=10,
            assessed_by=new_instructor.id,
            notes="New instructor test"
        )
        db.commit()

        assert assessment_new_instructor.requires_validation == True, \
            "Expected requires_validation=True for new instructor (< 180 days)"

        # ==================================================================
        # Test Case 3: Critical skill category (mental) requires validation
        # ==================================================================
        assessment_mental, _ = service.create_assessment(
            user_license_id=license_level3.id,
            skill_name='composure',  # Mental category
            points_earned=8,
            points_total=10,
            assessed_by=experienced_instructor.id,
            notes="Mental skill test"
        )
        db.commit()

        assert assessment_mental.requires_validation == True, \
            "Expected requires_validation=True for mental skill category"

        # ==================================================================
        # Test Case 4: Critical skill category (set_pieces) requires validation
        # ==================================================================
        assessment_set_pieces, _ = service.create_assessment(
            user_license_id=license_level3.id,
            skill_name='free_kicks',  # Set pieces category
            points_earned=9,
            points_total=10,
            assessed_by=experienced_instructor.id,
            notes="Set pieces test"
        )
        db.commit()

        assert assessment_set_pieces.requires_validation == True, \
            "Expected requires_validation=True for set_pieces skill category"

        # ==================================================================
        # Test Case 5: Auto-accepted (no validation required)
        # ==================================================================
        assessment_auto_accepted, _ = service.create_assessment(
            user_license_id=license_level3.id,
            skill_name='passing',  # Physical category
            points_earned=8,
            points_total=10,
            assessed_by=experienced_instructor.id,
            notes="Auto-accepted test"
        )
        db.commit()

        assert assessment_auto_accepted.requires_validation == False, \
            "Expected requires_validation=False for auto-accepted (level 3, experienced instructor, physical skill)"

        # ==================================================================
        # Test Case 6: Multiple rules triggering (level 5+ + new instructor)
        # ==================================================================
        # Even though level 5+ already requires validation, verify multiple rules work together
        assessment_multi_rule, _ = service.create_assessment(
            user_license_id=license_level5.id,
            skill_name='composure',  # Mental category (also requires validation)
            points_earned=7,
            points_total=10,
            assessed_by=new_instructor.id,  # New instructor (also requires validation)
            notes="Multiple rules test"
        )
        db.commit()

        assert assessment_multi_rule.requires_validation == True, \
            "Expected requires_validation=True when multiple rules trigger"

        print(f"✅ Validation requirement business rules test PASSED")
        print(f"   All 6 business rule scenarios validated correctly")
        print(f"   - High-stakes (level 5+): ✅")
        print(f"   - New instructor (< 180 days): ✅")
        print(f"   - Mental skill category: ✅")
        print(f"   - Set pieces skill category: ✅")
        print(f"   - Auto-accepted: ✅")
        print(f"   - Multiple rules: ✅")

    finally:
        db.rollback()
        db.close()


# ============================================================================
# TEST 9: Auto-Archive Edge Cases
# ============================================================================

@pytest.mark.auto_archive
@pytest.mark.edge_cases
def test_skill_assessment_auto_archive_edge_cases():
    """
    Test auto-archive logic in edge case scenarios.

    Test Cases:
    1. Auto-archive when creating new assessment (already VALIDATED)
    2. Auto-archive when creating new assessment (already ASSESSED)
    3. No auto-archive when no active assessment exists
    4. Auto-archive preserves audit trail (archived_by = new assessor)
    5. Multiple consecutive auto-archives (assessment 1→2→3)

    Validations:
    - Old assessment always archived before new created
    - archived_reason = "Replaced by new assessment"
    - Only 1 active assessment per (license, skill) pair
    - Audit trail complete

    Runtime Target: ~2.5s
    """
    db = next(get_db())
    service = FootballSkillService(db)

    try:
        # ==================================================================
        # Setup
        # ==================================================================
        instructor = create_test_instructor(db, "auto_archive_edge", tenure_days=365)
        admin = create_test_admin(db, "auto_archive_edge")
        student = User(
            email=f"student_auto_archive_{int(time.time()*1000)}@test.lfa",
            name="Test Student Auto Archive",
            role=UserRole.STUDENT, password_hash="dummy_hash_for_service_tests",
            is_active=True
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        license = create_test_license(db, student, current_level=3)

        # ==================================================================
        # Test Case 1: Auto-archive VALIDATED assessment
        # ==================================================================
        assessment1, _ = service.create_assessment(
            user_license_id=license.id,
            skill_name='heading',
            points_earned=6,
            points_total=10,
            assessed_by=instructor.id,
            notes="Assessment 1"
        )
        validated1 = service.validate_assessment(
            assessment_id=assessment1.id,
            validated_by=admin.id
        )
        db.commit()

        # Create new (should auto-archive validated1)
        assessment2, created2 = service.create_assessment(
            user_license_id=license.id,
            skill_name='heading',
            points_earned=7,
            points_total=10,
            assessed_by=instructor.id,
            notes="Assessment 2 (replaces validated)"
        )
        db.commit()

        assert created2 == True, "Expected new assessment created"
        db.refresh(validated1)
        assert validated1.status == SkillAssessmentState.ARCHIVED, \
            "Expected old VALIDATED assessment auto-archived"
        assert validated1.archived_reason == "Replaced by new assessment", \
            f"Expected archived_reason='Replaced by new assessment', got {validated1.archived_reason}"
        assert validated1.archived_by == instructor.id, \
            f"Expected archived_by={instructor.id} (new assessor), got {validated1.archived_by}"

        # ==================================================================
        # Test Case 2: Auto-archive ASSESSED assessment (not validated)
        # ==================================================================
        # assessment2 is currently ASSESSED (not validated)
        assessment3, created3 = service.create_assessment(
            user_license_id=license.id,
            skill_name='heading',
            points_earned=8,
            points_total=10,
            assessed_by=instructor.id,
            notes="Assessment 3 (replaces assessed)"
        )
        db.commit()

        assert created3 == True, "Expected new assessment created"
        db.refresh(assessment2)
        assert assessment2.status == SkillAssessmentState.ARCHIVED, \
            "Expected old ASSESSED assessment auto-archived"

        # ==================================================================
        # Test Case 3: No auto-archive when no active assessment
        # ==================================================================
        # Archive assessment3 manually
        archived3 = service.archive_assessment(
            assessment_id=assessment3.id,
            archived_by=admin.id,
            reason="Manual archive"
        )
        db.commit()

        # Create new (no active assessment to archive)
        assessment4, created4 = service.create_assessment(
            user_license_id=license.id,
            skill_name='heading',
            points_earned=9,
            points_total=10,
            assessed_by=instructor.id,
            notes="Assessment 4 (no auto-archive)"
        )
        db.commit()

        assert created4 == True, "Expected new assessment created"
        # Verify only 1 active assessment (assessment4)
        active_assessments = db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == license.id,
            FootballSkillAssessment.skill_name == 'heading',
            FootballSkillAssessment.status.in_([
                SkillAssessmentState.ASSESSED,
                SkillAssessmentState.VALIDATED
            ])
        ).all()

        assert len(active_assessments) == 1, \
            f"Expected 1 active assessment, got {len(active_assessments)}"
        assert active_assessments[0].id == assessment4.id, \
            "Expected assessment4 to be the only active assessment"

        # ==================================================================
        # Test Case 4: Multiple consecutive auto-archives (1→2→3)
        # ==================================================================
        # Already tested above: assessment1→2, assessment2→3, no active→4
        # Verify archived count
        archived_assessments = db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id == license.id,
            FootballSkillAssessment.skill_name == 'heading',
            FootballSkillAssessment.status == SkillAssessmentState.ARCHIVED
        ).all()

        assert len(archived_assessments) == 3, \
            f"Expected 3 archived assessments (1, 2, 3), got {len(archived_assessments)}"

        print(f"✅ Auto-archive edge cases test PASSED")
        print(f"   - Auto-archive VALIDATED: ✅")
        print(f"   - Auto-archive ASSESSED: ✅")
        print(f"   - No auto-archive when no active: ✅")
        print(f"   - Multiple consecutive auto-archives: ✅")
        print(f"   Total archived: {len(archived_assessments)}, Active: {len(active_assessments)}")

    finally:
        db.rollback()
        db.close()
