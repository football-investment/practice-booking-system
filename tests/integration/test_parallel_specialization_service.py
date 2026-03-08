"""
Integration tests for ParallelSpecializationService — Round 3

Uses real PostgreSQL with SAVEPOINT isolation (test_db fixture).
Tests the full pipeline methods that require actual DB objects:
  - get_user_specialization_dashboard: user not found + full output structure

Why integration (not unit mock):
  get_user_specialization_dashboard calls get_user_semester_count,
  get_user_active_specializations, and get_available_specializations_for_semester,
  which in turn call LicenseService.get_license_metadata_by_level. Mocking all
  of these would replicate the service implementation rather than test it.
  A real DB run exercises the full delegation chain with zero false positives.

Fixture dependencies (from tests/integration/conftest.py):
  - test_db:      function-scoped SAVEPOINT session (auto-rollback at teardown)
  - student_user: fresh student User inserted via test_db, UUID-suffixed email
  - admin_user:   fresh admin User inserted via test_db
"""
import pytest
from sqlalchemy.orm import Session

from app.services.parallel_specialization_service import ParallelSpecializationService


# ============================================================================
# TestGetUserSpecializationDashboard
# ============================================================================

@pytest.mark.integration
class TestGetUserSpecializationDashboard:
    """
    Full output structure validation for get_user_specialization_dashboard.

    Assertions are deliberately structural (key presence, types) rather than
    content-based, because available_specializations depends on LicenseMetadata
    rows which may or may not be seeded in the test DB.
    """

    _REQUIRED_KEYS = {
        "user",
        "current_semester",
        "active_specializations",
        "available_specializations",
        "progression_info",
        "parallel_progress",
    }
    _USER_KEYS = {"id", "name", "email"}
    _PARALLEL_PROGRESS_KEYS = {"total_active", "can_add_more", "next_available"}
    _PROGRESSION_KEYS = {"semester_1", "semester_2_plus"}

    def test_nonexistent_user_returns_error_dict(self, test_db: Session):
        """Guard: unknown user_id → {'error': 'User not found'}, no exception raised."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=999_999_999)
        assert result == {"error": "User not found"}

    def test_fresh_student_output_has_all_required_keys(self, test_db: Session, student_user):
        """Top-level response must contain exactly the documented keys."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        assert self._REQUIRED_KEYS.issubset(result.keys()), (
            f"Missing keys: {self._REQUIRED_KEYS - result.keys()}"
        )

    def test_fresh_student_user_sub_dict_matches_db_record(self, test_db: Session, student_user):
        """user sub-dict must reflect the DB record exactly."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        user_data = result["user"]
        assert self._USER_KEYS.issubset(user_data.keys())
        assert user_data["id"] == student_user.id
        assert user_data["email"] == student_user.email
        assert user_data["name"] == student_user.name

    def test_fresh_student_has_no_active_specializations(self, test_db: Session, student_user):
        """A freshly created student has zero licenses → active_specializations is empty."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        assert result["active_specializations"] == []

    def test_fresh_student_is_in_semester_1(self, test_db: Session, student_user):
        """No licenses → get_user_semester_count returns 1."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        assert result["current_semester"] == 1

    def test_parallel_progress_invariants_for_fresh_student(self, test_db: Session, student_user):
        """
        parallel_progress invariants for a user with 0 active specializations:
          - total_active == 0
          - can_add_more is bool
          - next_available is None iff available_specializations is empty
        """
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        pp = result["parallel_progress"]

        assert self._PARALLEL_PROGRESS_KEYS.issubset(pp.keys())
        assert pp["total_active"] == 0
        assert isinstance(pp["can_add_more"], bool)

        # Structural invariant: next_available ↔ available_specializations[0]
        available = result["available_specializations"]
        if available:
            assert pp["next_available"] == available[0]
        else:
            assert pp["next_available"] is None

    def test_progression_info_contains_both_semester_keys(self, test_db: Session, student_user):
        """progression_info must document both the base and advanced semester paths."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        assert self._PROGRESSION_KEYS.issubset(result["progression_info"].keys())

    def test_available_specializations_is_a_list(self, test_db: Session, student_user):
        """available_specializations is always a list (may be empty if no LicenseMetadata seeded)."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=student_user.id)
        assert isinstance(result["available_specializations"], list)

    def test_admin_user_dashboard_has_all_required_keys(self, test_db: Session, admin_user):
        """Admin users go through the payment bypass path; output shape must still be correct."""
        svc = ParallelSpecializationService(db=test_db)
        result = svc.get_user_specialization_dashboard(user_id=admin_user.id)
        assert self._REQUIRED_KEYS.issubset(result.keys())
        assert result["user"]["id"] == admin_user.id
