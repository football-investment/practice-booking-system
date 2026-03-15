"""
Full-flow integration tests — Semester hierarchy, enrollment gate, reward generation
=====================================================================================

Uses SAVEPOINT-isolated ``test_db`` + shared-session ``client`` from
``tests/integration/conftest.py``.  Every test starts with a clean slate;
all data is rolled back automatically at teardown — no explicit cleanup needed.

The ``client`` fixture overrides ``get_db`` so the API endpoint uses the same
transactional session as the test itself.  This means builders only need to
``flush()`` (not ``commit()``) before the API call, and the endpoint will see
the data immediately.

Tests
-----
  FLOW-01  Standalone semester — enrollment succeeds without parent gate check
  FLOW-02  Nested semester + active parent enrollment → enrollment succeeds (200)
  FLOW-03  Nested semester + NO parent enrollment → 403
  FLOW-04  Nested semester + INACTIVE (PENDING) parent enrollment → 403
  FLOW-05  TRAINING session default XP (50) — direct service call
  FLOW-06  MATCH session default XP (100) — direct service call
  FLOW-07  session_reward_config.base_xp overrides category default
  FLOW-08  Full standalone E2E: enroll → session → EventRewardLog created in DB
  FLOW-09  Full nested hierarchy E2E: parent enroll → child enroll → session → reward
  FLOW-10  Reward idempotency: second award updates existing row, no duplicate
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.semester import SemesterCategory
from app.models.semester_enrollment import SemesterEnrollment, EnrollmentStatus
from app.models.session import EventCategory
from app.models.event_reward_log import EventRewardLog
from app.models.user import User
from app.services.reward_service import award_session_completion
from tests.fixtures.builders import build_enrollment, build_semester, build_session, build_user_license
from tests.fixtures.api_error_helpers import assert_error_contains


# ── Shared helpers ────────────────────────────────────────────────────────────

def _auth(token: str) -> dict:
    """Build Bearer auth header dict."""
    return {"Authorization": f"Bearer {token}"}


# ── FLOW-01 to FLOW-04: Enrollment hierarchy gate (API-level) ─────────────────

class TestEnrollmentHierarchyGate:
    """
    Full-flow tests for the parent_semester_id access-control gate.

    The gate is enforced inside ``create_enrollment()`` in
    ``app/api/api_v1/endpoints/semester_enrollments/crud.py``.
    """

    def test_flow01_standalone_semester_no_gate(
        self,
        client: TestClient,
        test_db: Session,
        admin_user: User,
        admin_token: str,
        student_user: User,
    ):
        """
        FLOW-01: Standalone semester (parent_semester_id=None) — gate is skipped.

        Verifies: enrollment row created with is_active=True.
        """
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        lic = build_user_license(test_db, user_id=student_user.id)

        resp = client.post(
            "/api/v1/semester-enrollments/enroll",
            json={"user_id": student_user.id, "semester_id": sem.id, "user_license_id": lic.id},
            headers=_auth(admin_token),
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

        enr = test_db.query(SemesterEnrollment).filter(
            SemesterEnrollment.user_id == student_user.id,
            SemesterEnrollment.semester_id == sem.id,
        ).first()
        assert enr is not None, "Enrollment row must exist after successful enroll"
        assert enr.is_active is True

    def test_flow02_nested_with_active_parent_enrollment_succeeds(
        self,
        client: TestClient,
        test_db: Session,
        admin_user: User,
        admin_token: str,
        student_user: User,
    ):
        """
        FLOW-02: Child semester + student enrolled in parent (is_active=True) → 200.

        Verifies: both parent and child enrollment rows exist.
        """
        parent = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        child = build_semester(
            test_db,
            semester_category=SemesterCategory.CAMP,
            parent_semester_id=parent.id,
        )
        lic = build_user_license(test_db, user_id=student_user.id)
        build_enrollment(test_db, user_id=student_user.id, semester_id=parent.id, user_license_id=lic.id)

        resp = client.post(
            "/api/v1/semester-enrollments/enroll",
            json={"user_id": student_user.id, "semester_id": child.id, "user_license_id": lic.id},
            headers=_auth(admin_token),
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

        child_enr = test_db.query(SemesterEnrollment).filter(
            SemesterEnrollment.user_id == student_user.id,
            SemesterEnrollment.semester_id == child.id,
        ).first()
        assert child_enr is not None, "Child enrollment row must be created"
        assert child_enr.is_active is True

    def test_flow03_nested_without_parent_enrollment_returns_403(
        self,
        client: TestClient,
        test_db: Session,
        admin_user: User,
        admin_token: str,
        student_user: User,
    ):
        """
        FLOW-03: Child semester + student has NO enrollment in parent → 403.

        Verifies: gate blocks enrollment and no child enrollment row is created.
        """
        parent = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        child = build_semester(
            test_db,
            semester_category=SemesterCategory.MINI_SEASON,
            parent_semester_id=parent.id,
        )
        lic = build_user_license(test_db, user_id=student_user.id)
        # Deliberately skip parent enrollment

        resp = client.post(
            "/api/v1/semester-enrollments/enroll",
            json={"user_id": student_user.id, "semester_id": child.id, "user_license_id": lic.id},
            headers=_auth(admin_token),
        )

        assert resp.status_code == 403, resp.text
        assert_error_contains(resp, "parent program")

        # Gate must prevent the row from being created
        child_enr = test_db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == child.id,
        ).first()
        assert child_enr is None, "Gate should have blocked enrollment creation"

    def test_flow04_inactive_parent_enrollment_returns_403(
        self,
        client: TestClient,
        test_db: Session,
        admin_user: User,
        admin_token: str,
        student_user: User,
    ):
        """
        FLOW-04: Parent enrollment is PENDING (is_active=False) → 403.

        The gate filters on is_active=True.  A pending enrollment does not satisfy
        the requirement, so the child enrollment is blocked.
        """
        parent = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        child = build_semester(
            test_db,
            semester_category=SemesterCategory.CAMP,
            parent_semester_id=parent.id,
        )
        lic = build_user_license(test_db, user_id=student_user.id)
        # Pending enrollment: is_active=False
        build_enrollment(
            test_db,
            user_id=student_user.id,
            semester_id=parent.id,
            user_license_id=lic.id,
            approved=False,   # → is_active=False, request_status=PENDING
        )

        resp = client.post(
            "/api/v1/semester-enrollments/enroll",
            json={"user_id": student_user.id, "semester_id": child.id, "user_license_id": lic.id},
            headers=_auth(admin_token),
        )

        assert resp.status_code == 403, resp.text
        assert_error_contains(resp, "parent program")


# ── FLOW-05 to FLOW-07: XP resolution (service-layer) ────────────────────────

class TestXPResolution:
    """
    Direct service-layer tests for ``_resolve_base_xp`` and
    ``award_session_completion``.

    These tests bypass the HTTP layer and call the service function directly
    with a real DB session (SAVEPOINT-isolated).
    """

    def test_flow05_training_session_default_xp_50(
        self,
        test_db: Session,
        student_user: User,
    ):
        """
        FLOW-05: EventCategory.TRAINING with no session_reward_config → 50 XP.
        """
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, event_category=EventCategory.TRAINING)

        log = award_session_completion(test_db, user_id=student_user.id, session=sess)

        assert log.xp_earned == 50
        assert log.points_earned == 50
        assert log.multiplier_applied == 1.0
        assert log.user_id == student_user.id
        assert log.session_id == sess.id

    def test_flow06_match_session_default_xp_100(
        self,
        test_db: Session,
        student_user: User,
    ):
        """
        FLOW-06: EventCategory.MATCH with no session_reward_config → 100 XP.
        """
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, event_category=EventCategory.MATCH)

        log = award_session_completion(test_db, user_id=student_user.id, session=sess)

        assert log.xp_earned == 100

    def test_flow07_config_base_xp_overrides_category_default(
        self,
        test_db: Session,
        student_user: User,
    ):
        """
        FLOW-07: session_reward_config.base_xp=200 takes priority over TRAINING
        category default (50).
        """
        sem = build_semester(test_db)
        sess = build_session(
            test_db,
            sem.id,
            event_category=EventCategory.TRAINING,
            session_reward_config={"v": 1, "base_xp": 200, "skill_areas": []},
        )

        log = award_session_completion(test_db, user_id=student_user.id, session=sess)

        assert log.xp_earned == 200, "Config base_xp must override category default (50)"


# ── FLOW-08 to FLOW-10: End-to-end scenarios ──────────────────────────────────

class TestEndToEndScenarios:
    """
    Academy Season → Sessions → Rewards full lifecycle.

    These tests exercise all three layers together:
      API (enrollment gate) → service (reward) → database (EventRewardLog).
    """

    def test_flow08_standalone_full_lifecycle(
        self,
        client: TestClient,
        test_db: Session,
        admin_user: User,
        admin_token: str,
        student_user: User,
    ):
        """
        FLOW-08: Standalone semester — enroll student → TRAINING session → 50 XP.

        Full path for a non-nested semester:
          - No gate check
          - Enrollment created with is_active=True
          - EventRewardLog row in DB with xp_earned=50
        """
        sem = build_semester(test_db, semester_category=SemesterCategory.TOURNAMENT)
        lic = build_user_license(test_db, user_id=student_user.id)

        # Step 1: Enroll via API
        resp = client.post(
            "/api/v1/semester-enrollments/enroll",
            json={"user_id": student_user.id, "semester_id": sem.id, "user_license_id": lic.id},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, resp.text

        # Step 2: Create TRAINING session + award reward
        sess = build_session(test_db, sem.id, event_category=EventCategory.TRAINING)
        log = award_session_completion(
            test_db,
            user_id=student_user.id,
            session=sess,
            multiplier=1.0,
            skill_areas=["dribbling", "passing"],
        )

        # Step 3: Assert EventRewardLog
        assert log.id is not None
        assert log.xp_earned == 50
        assert log.points_earned == 50
        assert log.multiplier_applied == 1.0
        assert log.skill_areas_affected == ["dribbling", "passing"]

        # Step 4: Verify row is persisted
        test_db.expire_all()
        persisted = test_db.query(EventRewardLog).filter(
            EventRewardLog.user_id == student_user.id,
            EventRewardLog.session_id == sess.id,
        ).first()
        assert persisted is not None
        assert persisted.xp_earned == 50
        assert persisted.skill_areas_affected == ["dribbling", "passing"]

    def test_flow09_nested_hierarchy_full_lifecycle(
        self,
        client: TestClient,
        test_db: Session,
        admin_user: User,
        admin_token: str,
        student_user: User,
    ):
        """
        FLOW-09: Academy Season → Camp — full nested hierarchy lifecycle.

        Steps:
          1. Create ACADEMY_SEASON parent + CAMP child (parent_semester_id link)
          2. Enroll student in parent via builder (direct DB — bypasses API)
          3. Enroll student in child via API (gate passes: parent enrollment active)
          4. Create MATCH session in child semester
          5. Award session completion → 100 XP (MATCH default)
          6. Verify EventRewardLog in DB with correct user/session/xp
        """
        # Step 1: Semester hierarchy
        parent = build_semester(test_db, semester_category=SemesterCategory.ACADEMY_SEASON)
        child = build_semester(
            test_db,
            semester_category=SemesterCategory.CAMP,
            parent_semester_id=parent.id,
        )
        lic = build_user_license(test_db, user_id=student_user.id)

        # Step 2: Parent enrollment (direct DB — hierarchy setup, not the feature under test)
        build_enrollment(test_db, user_id=student_user.id, semester_id=parent.id, user_license_id=lic.id)

        # Step 3: Child enrollment via API (gate must pass)
        resp = client.post(
            "/api/v1/semester-enrollments/enroll",
            json={"user_id": student_user.id, "semester_id": child.id, "user_license_id": lic.id},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200, f"Child enrollment failed (gate): {resp.text}"

        # Step 4: MATCH session in child semester
        sess = build_session(test_db, child.id, event_category=EventCategory.MATCH)

        # Step 5: Award
        log = award_session_completion(test_db, user_id=student_user.id, session=sess)

        # Step 6: Assert
        assert log.xp_earned == 100
        assert log.user_id == student_user.id
        assert log.session_id == sess.id

        # Confirm only one EventRewardLog row for this student
        test_db.expire_all()
        all_logs = test_db.query(EventRewardLog).filter(
            EventRewardLog.user_id == student_user.id,
        ).all()
        assert len(all_logs) == 1
        assert all_logs[0].xp_earned == 100

    def test_flow10_reward_idempotency_within_full_flow(
        self,
        test_db: Session,
        student_user: User,
    ):
        """
        FLOW-10: Idempotent reward — second ``award_session_completion`` call updates,
        does not insert a duplicate row.

        First award: multiplier=1.0 → MATCH XP = 100
        Second award: multiplier=2.0 → MATCH XP = 200 (updated, same row ID)
        count(EventRewardLog for (user, session)) must be 1 after both calls.
        """
        sem = build_semester(test_db)
        sess = build_session(test_db, sem.id, event_category=EventCategory.MATCH)

        log1 = award_session_completion(
            test_db, user_id=student_user.id, session=sess, multiplier=1.0
        )
        assert log1.xp_earned == 100   # MATCH default × 1.0

        log2 = award_session_completion(
            test_db, user_id=student_user.id, session=sess, multiplier=2.0
        )
        assert log2.xp_earned == 200   # MATCH default × 2.0
        assert log1.id == log2.id, "Second award must UPDATE the existing row, not INSERT"
        assert log2.multiplier_applied == 2.0

        count = test_db.query(EventRewardLog).filter(
            EventRewardLog.user_id == student_user.id,
            EventRewardLog.session_id == sess.id,
        ).count()
        assert count == 1, f"Expected exactly 1 EventRewardLog row, found {count}"
