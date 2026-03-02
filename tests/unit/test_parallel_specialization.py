"""
Unit tests for ParallelSpecializationService — Round 2 coverage

Scope (DB-free / DB-mockable paths only):
  - calculate_age: pure calculation, date.today() patched for determinism
  - get_specialization_combinations_by_semester: pure static return
  - check_age_requirement: single User DB query (MagicMock)
  - check_payment_requirement: User query + get_user_active_specializations patched
  - get_user_semester_count: User query + UserLicense.count() (MagicMock)

Deferred to Round 3 (integration-heavy):
  - get_available_specializations_for_semester  (LicenseService + complex self-calls)
  - start_new_specialization                    (db.commit / db.refresh)
  - get_user_specialization_dashboard           (full pipeline)
  - validate_specialization_addition            (delegates to above)

Mock isolation:
  Each test builds a *fresh* MagicMock db via _service(), so there is no
  shared state between tests. patch.object() calls are scoped to the
  individual 'with' block and are never applied at the class or module level.
"""
import pytest
from datetime import date as real_date, datetime
from unittest.mock import MagicMock, patch, patch as _patch

from app.services.parallel_specialization_service import ParallelSpecializationService


# ─── Shared helpers ────────────────────────────────────────────────────────────

_DATE_PATH = "app.services.parallel_specialization_service.date"
_TODAY = real_date(2026, 3, 2)  # pinned "today" for all age-related tests


def _service():
    """Return (service, db_mock) with a fresh MagicMock DB per call."""
    db = MagicMock()
    return ParallelSpecializationService(db=db), db


def _user_mock(
    *,
    role_value: str = "student",
    date_of_birth=None,
    payment_verified: bool = True,
    payment_verified_at=None,
    payment_verified_by=None,
    payment_status_display: str = "✅ Verified",
):
    """Build a minimal MagicMock User with controlled attributes.

    Uses explicit assignment (u.attr = value) rather than spec= so that
    attributes not present on the real model can still be set freely in tests.
    role.value is set via the MagicMock attribute chain: u.role.value = role_value,
    which matches how the service reads user.role.value in production code.
    """
    u = MagicMock()
    u.role.value = role_value
    u.date_of_birth = date_of_birth        # datetime | None
    u.payment_verified = payment_verified
    u.payment_verified_at = payment_verified_at
    u.payment_verified_by = payment_verified_by
    u.payment_status_display = payment_status_display
    return u


# ============================================================================
# Class 1 — calculate_age
# ============================================================================

@pytest.mark.unit
class TestCalculateAge:
    """
    Pure age calculation — no DB interaction.

    Algorithm: today.year - birth.year - (1 if birthday not yet this year else 0)
    where "not yet" = (today.month, today.day) < (birth.month, birth.day)

    date.today() is patched to _TODAY = 2026-03-02 in every helper call
    to prevent flakiness from the passage of real time.
    """

    def _age(self, birth: real_date, today: real_date = _TODAY) -> int:
        svc, _ = _service()
        with patch(_DATE_PATH) as mock_date:
            mock_date.today.return_value = today
            return svc.calculate_age(birth)

    def test_birthday_already_passed_this_year(self):
        """Born 2000-01-15; birthday passed (Jan < Mar) → 26."""
        assert self._age(real_date(2000, 1, 15)) == 26

    def test_birthday_not_yet_this_year(self):
        """Born 2000-12-25; birthday not yet (Dec > Mar) → 25."""
        assert self._age(real_date(2000, 12, 25)) == 25

    def test_birthday_exactly_today(self):
        """Born 2000-03-02; today is birthday → 26, NOT 25.
        Boundary: (3,2) < (3,2) is False → no subtraction → full year counted."""
        assert self._age(real_date(2000, 3, 2)) == 26

    def test_infant_born_today(self):
        """Born today → age 0."""
        assert self._age(real_date(2026, 3, 2)) == 0

    def test_elder_90_plus(self):
        """Born 1930-06-15 → birthday not yet (Jun > Mar) → 95."""
        assert self._age(real_date(1930, 6, 15)) == 95

    def test_leap_year_birthday_feb29(self):
        """Born 2000-02-29 (leap year); today 2026-03-02.
        Comparison: (3, 2) < (2, 29) → False (month 3 > 2) → birthday 'passed' → 26."""
        assert self._age(real_date(2000, 2, 29)) == 26

    def test_invariant_age_is_non_negative(self):
        """INVARIANT: age must be ≥ 0 for any valid birth date ≤ today."""
        for birth in [real_date(2026, 3, 2), real_date(2025, 4, 1), real_date(1990, 1, 1)]:
            assert self._age(birth) >= 0

    def test_age_exactly_at_player_minimum_boundary(self):
        """Born 2021-03-02; today 2026-03-02 → exactly 5 → meets PLAYER minimum."""
        assert self._age(real_date(2021, 3, 2)) == 5

    def test_one_day_before_player_minimum_boundary(self):
        """Born 2021-03-03; today 2026-03-02 → birthday not yet → 4 → below PLAYER."""
        assert self._age(real_date(2021, 3, 3)) == 4


# ============================================================================
# Class 2 — get_specialization_combinations_by_semester
# ============================================================================

@pytest.mark.unit
class TestGetSpecializationCombinationsBySemester:
    """
    Pure static return — no DB, no mocks needed.
    Tests verify structural correctness of the domain model constants.
    """

    def setup_method(self):
        self.svc, _ = _service()
        self.result = self.svc.get_specialization_combinations_by_semester()

    def test_returns_dict_with_semesters_1_2_3(self):
        assert set(self.result.keys()) == {1, 2, 3}

    def test_semester_1_allows_max_1_specialization(self):
        assert self.result[1]["max_specializations"] == 1

    def test_semester_2_allows_max_2_specializations(self):
        assert self.result[2]["max_specializations"] == 2

    def test_semester_3_allows_max_3_specializations(self):
        assert self.result[3]["max_specializations"] == 3

    def test_all_semesters_list_all_three_specializations_as_available(self):
        for sem in [1, 2, 3]:
            available = self.result[sem]["available"]
            for spec in ["PLAYER", "COACH", "INTERNSHIP"]:
                assert spec in available, f"Semester {sem} missing {spec}"

    def test_semester_3_combinations_contains_all_three_parallel(self):
        assert ["PLAYER", "COACH", "INTERNSHIP"] in self.result[3]["combinations"]

    def test_descriptions_are_non_empty_strings(self):
        for sem in [1, 2, 3]:
            assert isinstance(self.result[sem]["description"], str)
            assert len(self.result[sem]["description"]) > 0


# ============================================================================
# Class 3 — check_age_requirement
# ============================================================================

@pytest.mark.unit
class TestCheckAgeRequirement:
    """
    DB mock: db.query(User).filter().first() → user_mock or None.
    date.today() patched to _TODAY for determinism.

    AGE_REQUIREMENTS (from service): PLAYER=5, COACH=14, INTERNSHIP=18.
    """

    def _check(self, user_mock, specialization: str, today: real_date = _TODAY):
        svc, db = _service()
        db.query.return_value.filter.return_value.first.return_value = user_mock
        with patch(_DATE_PATH) as mock_date:
            mock_date.today.return_value = today
            return svc.check_age_requirement(user_id=1, specialization=specialization)

    def test_user_not_found_returns_false(self):
        result = self._check(None, "PLAYER")
        assert result["meets_requirement"] is False
        assert result["reason"] == "User not found"

    def test_user_no_date_of_birth_returns_false(self):
        u = _user_mock(date_of_birth=None)
        result = self._check(u, "PLAYER")
        assert result["meets_requirement"] is False
        assert "hiányzik" in result["reason"]   # service uses Hungarian: "Születési dátum hiányzik"

    def test_player_age_below_minimum(self):
        """Age 3 (born 2023-01-01) — below PLAYER minimum of 5."""
        u = _user_mock(date_of_birth=datetime(2023, 1, 1))
        result = self._check(u, "PLAYER")
        assert result["meets_requirement"] is False
        assert result["required_age"] == 5
        assert result["user_age"] == 3

    def test_player_age_exactly_at_minimum(self):
        """Born 2021-03-02; today 2026-03-02 → exactly 5 → meets requirement."""
        u = _user_mock(date_of_birth=datetime(2021, 3, 2))
        result = self._check(u, "PLAYER")
        assert result["meets_requirement"] is True
        assert result["user_age"] == 5

    def test_player_age_above_minimum(self):
        u = _user_mock(date_of_birth=datetime(2000, 1, 1))
        result = self._check(u, "PLAYER")
        assert result["meets_requirement"] is True

    def test_coach_age_below_minimum(self):
        """Born 2013-03-03; today 2026-03-02 → birthday not yet → age 12 < 14."""
        u = _user_mock(date_of_birth=datetime(2013, 3, 3))
        result = self._check(u, "COACH")
        assert result["meets_requirement"] is False
        assert result["required_age"] == 14
        assert result["user_age"] == 12

    def test_coach_age_exactly_at_minimum(self):
        """Born 2012-03-02; today 2026-03-02 → exactly 14."""
        u = _user_mock(date_of_birth=datetime(2012, 3, 2))
        result = self._check(u, "COACH")
        assert result["meets_requirement"] is True
        assert result["user_age"] == 14

    def test_internship_age_exactly_at_minimum(self):
        """Born 2008-03-02; today 2026-03-02 → exactly 18."""
        u = _user_mock(date_of_birth=datetime(2008, 3, 2))
        result = self._check(u, "INTERNSHIP")
        assert result["meets_requirement"] is True
        assert result["user_age"] == 18

    def test_unknown_specialization_defaults_to_zero_required_age(self):
        """AGE_REQUIREMENTS.get(unknown, 0) → required_age=0 → any age meets it."""
        u = _user_mock(date_of_birth=datetime(2020, 1, 1))   # age ~6
        result = self._check(u, "UNKNOWN_SPEC")
        assert result["meets_requirement"] is True
        assert result["required_age"] == 0

    def test_reason_message_includes_both_ages_on_failure(self):
        """Failure reason must embed required_age and user_age for UI display."""
        u = _user_mock(date_of_birth=datetime(2023, 6, 15))   # age ~2
        result = self._check(u, "PLAYER")
        assert not result["meets_requirement"]
        assert str(result["required_age"]) in result["reason"]
        assert str(result["user_age"]) in result["reason"]


# ============================================================================
# Class 4 — check_payment_requirement
# ============================================================================

@pytest.mark.unit
class TestCheckPaymentRequirement:
    """
    DB mock: db.query(User).filter().first() → user_mock or None.

    get_user_active_specializations is patched via patch.object to isolate
    this method from UserLicense DB queries and LicenseService calls.

    semester is passed explicitly to short-circuit
    `semester or self.get_user_semester_count(user_id)`, avoiding a second
    DB mock chain for UserLicense.count().
    """

    def _check(
        self,
        user_mock,
        *,
        specialization_type=None,
        semester: int = 1,
        active_specs=None,
    ):
        svc, db = _service()
        db.query.return_value.filter.return_value.first.return_value = user_mock
        with _patch.object(svc, "get_user_active_specializations", return_value=active_specs or []):
            return svc.check_payment_requirement(
                user_id=1,
                specialization_type=specialization_type,
                semester=semester,
            )

    # ── Not found / role bypass ─────────────────────────────────────────────

    def test_user_not_found_returns_false(self):
        result = self._check(None)
        assert result["payment_verified"] is False
        assert result["reason"] == "User not found"

    def test_admin_role_bypasses_payment_unconditionally(self):
        """Admin with payment_verified=False still gets payment_verified=True."""
        u = _user_mock(role_value="admin", payment_verified=False)
        result = self._check(u)
        assert result["payment_verified"] is True
        assert "Admin" in result["reason"]

    def test_instructor_role_bypasses_payment_unconditionally(self):
        """Instructor with payment_verified=False still gets payment_verified=True."""
        u = _user_mock(role_value="instructor", payment_verified=False)
        result = self._check(u)
        assert result["payment_verified"] is True
        assert "Instructor" in result["reason"]

    # ── Semester 1 (baseline) ────────────────────────────────────────────────

    def test_student_semester1_payment_verified_true(self):
        u = _user_mock(role_value="student", payment_verified=True)
        result = self._check(u, semester=1)
        assert result["payment_verified"] is True

    def test_student_semester1_payment_verified_false(self):
        u = _user_mock(role_value="student", payment_verified=False)
        result = self._check(u, semester=1)
        assert result["payment_verified"] is False

    # ── Semester 2+ branching ────────────────────────────────────────────────

    def test_student_semester2_no_existing_specs_payment_true(self):
        """No active specs yet (first enrollment); semester 2; payment verified → True."""
        u = _user_mock(role_value="student", payment_verified=True)
        result = self._check(u, specialization_type="PLAYER", semester=2, active_specs=[])
        assert result["payment_verified"] is True

    def test_student_semester2_adding_new_spec_type_payment_verified_true(self):
        """Has PLAYER, adding COACH (new type); payment verified → True."""
        u = _user_mock(role_value="student", payment_verified=True)
        active_specs = [{"specialization_type": "PLAYER"}]
        result = self._check(u, specialization_type="COACH", semester=2, active_specs=active_specs)
        assert result["payment_verified"] is True

    def test_student_semester2_adding_new_spec_type_payment_not_verified(self):
        """Has PLAYER, adding COACH; payment NOT verified → False."""
        u = _user_mock(role_value="student", payment_verified=False)
        active_specs = [{"specialization_type": "PLAYER"}]
        result = self._check(u, specialization_type="COACH", semester=2, active_specs=active_specs)
        assert result["payment_verified"] is False

    def test_student_semester2_requesting_already_enrolled_spec_falls_to_else(self):
        """Has PLAYER, requesting PLAYER again → existing-spec branch (else) → payment as-is."""
        u = _user_mock(role_value="student", payment_verified=True)
        active_specs = [{"specialization_type": "PLAYER"}]
        result = self._check(u, specialization_type="PLAYER", semester=2, active_specs=active_specs)
        assert result["payment_verified"] is True

    # ── Output shape ─────────────────────────────────────────────────────────

    def test_output_semester_context_reflects_passed_semester(self):
        """semester_context in output must match the semester argument."""
        u = _user_mock(role_value="student", payment_verified=True)
        result = self._check(u, semester=3)
        assert result["semester_context"] == 3

    def test_admin_output_contains_verified_at_and_by_as_none(self):
        """Admin bypass returns verified_at=None and verified_by=None (no real verification)."""
        u = _user_mock(role_value="admin")
        result = self._check(u)
        assert result["verified_at"] is None
        assert result["verified_by"] is None


# ============================================================================
# Class 5 — get_user_semester_count
# ============================================================================

@pytest.mark.unit
class TestGetUserSemesterCount:
    """
    DB mock:
      - db.query(User).filter().first()          → user or None
      - db.query(UserLicense).filter().count()   → int

    Both queries share the same MagicMock chain (db.query.return_value.filter.return_value),
    but terminate on different methods (.first() vs .count()), so they can be
    configured independently on the same mock object without interference.
    """

    def _count(self, user_mock, license_count: int = 0) -> int:
        svc, db = _service()
        db.query.return_value.filter.return_value.first.return_value = user_mock
        db.query.return_value.filter.return_value.count.return_value = license_count
        return svc.get_user_semester_count(user_id=1)

    def test_user_not_found_returns_semester_1(self):
        """Guard: unknown user defaults to semester 1 (safe minimum)."""
        assert self._count(None) == 1

    def test_user_with_zero_licenses_is_semester_1(self):
        u = _user_mock()
        assert self._count(u, license_count=0) == 1

    def test_user_with_one_license_is_semester_2(self):
        u = _user_mock()
        assert self._count(u, license_count=1) == 2

    def test_user_with_multiple_licenses_is_still_semester_2(self):
        """Function returns binary: 1 (no licenses) or 2 (any licenses > 0)."""
        u = _user_mock()
        assert self._count(u, license_count=5) == 2
