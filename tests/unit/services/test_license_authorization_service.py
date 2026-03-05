"""
Unit tests for LicenseAuthorizationService
(app/services/license_authorization_service.py)

Sprint N (2026-03-05) — branch hardening: authorization system

Targets:
  100% stmt coverage
  ≥85% branch coverage (aim 100%)

Branch clusters covered:
  extract_age_group_from_specialization:
    - None/empty → None
    - PRE/YOUTH/AMATEUR/PRO recognized → return
    - No match → None

  extract_base_specialization:
    - None/empty → None
    - PLAYER/COACH/INTERNSHIP/INTERN keyword → return
    - No match → None (fallthrough)

  can_be_master_instructor:
    - expiry loop: license active vs expired
    - if not active_licenses → early deny
    - semester_age_group provided vs None (extracted from spec)
    - invalid base_spec → deny
    - INTERNSHIP path: with/without INTERNSHIP license
    - PLAYER semester: PLAYER/COACH license above/below min
    - COACH semester: COACH above/below min; PLAYER denied
    - age_group unknown → default min=1
    - matching_licenses found → authorized; empty → denied
    - db.commit() always called after expiry loop

  can_teach_session:
    - is_mixed_session=True → immediate authorized (no DB)
    - session_specialization=None → immediate authorized (no DB)
    - no active licenses → deny
    - invalid base_spec → deny
    - PLAYER session: PLAYER lic with/without age_group, above/below min
    - PLAYER session: COACH lic with/without age_group, above/below min
    - PLAYER session: INTERNSHIP lic → not matching
    - COACH session: COACH lic with/without age_group, above/below min
    - COACH session: PLAYER lic → denied
    - INTERNSHIP session: INTERNSHIP lic → authorized; PLAYER lic → denied
    - db.commit() called iff not mixed session
    - reason strings include spec/license info

  get_qualified_instructors_for_semester:
    - no users → []
    - all denied → []
    - all authorized → full list
    - mixed → only authorized included
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.license_authorization_service import LicenseAuthorizationService

_PATCH_EXPIRY = (
    "app.services.license_authorization_service"
    ".LicenseRenewalService.check_license_expiration"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    return MagicMock()


def _instructor(uid=42):
    u = MagicMock()
    u.id = uid
    return u


def _license(spec_type, level):
    lic = MagicMock()
    lic.specialization_type = spec_type
    lic.current_level = level
    return lic


def _db_with_licenses(licenses):
    """Set up db.query(...).filter(...).all() → licenses list."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.all.return_value = licenses
    db.query.return_value = q
    return db


def _db_for_users(users):
    """Set up db.query(User).join(...).filter(...).distinct().all() → users."""
    db = MagicMock()
    q = MagicMock()
    q.join.return_value = q
    q.filter.return_value = q
    q.distinct.return_value = q
    q.all.return_value = users
    db.query.return_value = q
    return db


# ===========================================================================
# extract_age_group_from_specialization
# ===========================================================================

@pytest.mark.unit
class TestExtractAgeGroup:

    def test_none_input_returns_none(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization(None) is None

    def test_empty_string_returns_none(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization("") is None

    def test_lfa_player_pre(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization("LFA_PLAYER_PRE") == "PRE"

    def test_lfa_player_youth(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization("LFA_PLAYER_YOUTH") == "YOUTH"

    def test_lfa_player_amateur(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization("LFA_PLAYER_AMATEUR") == "AMATEUR"

    def test_lfa_player_pro(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization("LFA_PLAYER_PRO") == "PRO"

    def test_gancuju_player_pre(self):
        """Cross-brand spec: age group still extracted correctly."""
        assert LicenseAuthorizationService.extract_age_group_from_specialization("GANCUJU_PLAYER_PRE") == "PRE"

    def test_lfa_coach_without_age_group_returns_none(self):
        """LFA_COACH has no PRE/YOUTH/AMATEUR/PRO part → None."""
        assert LicenseAuthorizationService.extract_age_group_from_specialization("LFA_COACH") is None

    def test_completely_unknown_spec_returns_none(self):
        assert LicenseAuthorizationService.extract_age_group_from_specialization("SOMETHING_ELSE") is None


# ===========================================================================
# extract_base_specialization
# ===========================================================================

@pytest.mark.unit
class TestExtractBaseSpec:

    def test_none_input_returns_none(self):
        assert LicenseAuthorizationService.extract_base_specialization(None) is None

    def test_empty_string_returns_none(self):
        assert LicenseAuthorizationService.extract_base_specialization("") is None

    def test_player_keyword_returns_player(self):
        assert LicenseAuthorizationService.extract_base_specialization("LFA_PLAYER_PRE") == "PLAYER"

    def test_gancuju_player_returns_player(self):
        assert LicenseAuthorizationService.extract_base_specialization("GANCUJU_PLAYER_YOUTH") == "PLAYER"

    def test_coach_keyword_returns_coach(self):
        assert LicenseAuthorizationService.extract_base_specialization("LFA_COACH") == "COACH"

    def test_coach_with_age_group_returns_coach(self):
        assert LicenseAuthorizationService.extract_base_specialization("LFA_COACH_PRE") == "COACH"

    def test_internship_keyword_returns_internship(self):
        assert LicenseAuthorizationService.extract_base_specialization("LFA_INTERNSHIP") == "INTERNSHIP"

    def test_intern_substring_returns_internship(self):
        """'INTERN' substring (without 'SHIP') also maps to INTERNSHIP."""
        assert LicenseAuthorizationService.extract_base_specialization("LFA_INTERN_TRACK") == "INTERNSHIP"

    def test_no_match_returns_none(self):
        assert LicenseAuthorizationService.extract_base_specialization("SOMETHING_COMPLETELY_ELSE") is None


# ===========================================================================
# can_be_master_instructor
# ===========================================================================

@pytest.mark.unit
class TestCanBeMasterInstructor:
    """Covers all deny/allow paths and branch states in can_be_master_instructor."""

    def _call(self, instructor, semester_spec, semester_age_group, db,
              expiry_returns=True):
        """Patch check_license_expiration and call the method."""
        if isinstance(expiry_returns, list):
            cm = patch(_PATCH_EXPIRY, side_effect=expiry_returns)
        else:
            cm = patch(_PATCH_EXPIRY, return_value=expiry_returns)
        with cm:
            return LicenseAuthorizationService.can_be_master_instructor(
                instructor=instructor,
                semester_specialization=semester_spec,
                semester_age_group=semester_age_group,
                db=db,
            )

    # --- No active licenses ---

    def test_no_licenses_in_db_denied(self):
        db = _db_with_licenses([])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", "PRE", db)
        assert result["authorized"] is False
        assert "No active licenses" in result["reason"]
        assert result["matching_licenses"] == []

    def test_all_licenses_expired_denied(self):
        lic = _license("PLAYER", 5)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", "PRE", db,
                            expiry_returns=False)
        assert result["authorized"] is False
        assert "No active licenses" in result["reason"]

    def test_partial_expiration_only_active_used(self):
        """First license expires (False), second stays active (True)."""
        lic_expired = _license("PLAYER", 1)
        lic_active = _license("PLAYER", 5)
        db = _db_with_licenses([lic_expired, lic_active])
        # lic_active level=5 >= AMATEUR min=5 → authorized
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", "AMATEUR", db,
                            expiry_returns=[False, True])
        assert result["authorized"] is True

    def test_db_commit_always_called(self):
        """db.commit() is called even when no active licenses remain."""
        db = _db_with_licenses([])
        self._call(_instructor(), "LFA_PLAYER_PRE", "PRE", db)
        db.commit.assert_called_once()

    def test_db_commit_called_when_authorized(self):
        lic = _license("PLAYER", 1)
        db = _db_with_licenses([lic])
        self._call(_instructor(), "LFA_PLAYER_PRE", "PRE", db)
        db.commit.assert_called_once()

    # --- Invalid specialization ---

    def test_invalid_specialization_denied(self):
        lic = _license("PLAYER", 5)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "UNKNOWN_XYZ_ABC", None, db)
        assert result["authorized"] is False
        assert "Invalid semester specialization" in result["reason"]
        assert "UNKNOWN_XYZ_ABC" in result["reason"]

    # --- semester_age_group: provided vs extracted ---

    def test_age_group_provided_directly(self):
        """semester_age_group='PRE' is used; extraction skipped."""
        lic = _license("PLAYER", 1)  # PRE min=1
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", "PRE", db)
        assert result["authorized"] is True

    def test_age_group_none_extracted_from_spec(self):
        """semester_age_group=None → age group extracted from spec string."""
        lic = _license("PLAYER", 3)  # YOUTH min=3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_YOUTH", None, db)
        assert result["authorized"] is True

    def test_age_group_none_spec_has_no_age_group_default_min(self):
        """semester_age_group=None AND spec has no age group → None → default min=1."""
        lic = _license("PLAYER", 1)
        db = _db_with_licenses([lic])
        # "LFA_PLAYER" → no PRE/YOUTH/AMATEUR/PRO → age_group=None → get(None, 1)=1
        result = self._call(_instructor(), "LFA_PLAYER", None, db)
        assert result["authorized"] is True

    # --- INTERNSHIP semester ---

    def test_internship_semester_with_internship_license_authorized(self):
        lic = _license("INTERNSHIP", 2)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERNSHIP", None, db)
        assert result["authorized"] is True
        assert "INTERNSHIP license" in result["reason"]
        assert lic in result["matching_licenses"]

    def test_internship_semester_without_internship_license_denied(self):
        """PLAYER license does not qualify for INTERNSHIP semester."""
        lic = _license("PLAYER", 8)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERNSHIP", None, db)
        assert result["authorized"] is False
        assert "No INTERNSHIP license" in result["reason"]

    def test_internship_semester_intern_keyword_in_spec(self):
        """'INTERN' substring triggers INTERNSHIP path."""
        lic = _license("INTERNSHIP", 1)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERN_TRACK", None, db)
        assert result["authorized"] is True

    # --- PLAYER semester (all four age groups) ---

    def test_player_semester_pre_age_group_min_level_1(self):
        lic = _license("PLAYER", 1)  # PRE min=1
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", "PRE", db)
        assert result["authorized"] is True

    def test_player_semester_youth_age_group_min_level_3(self):
        lic = _license("PLAYER", 3)  # YOUTH min=3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_YOUTH", "YOUTH", db)
        assert result["authorized"] is True

    def test_player_semester_amateur_meets_minimum(self):
        lic = _license("PLAYER", 5)  # AMATEUR min=5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", "AMATEUR", db)
        assert result["authorized"] is True
        assert lic in result["matching_licenses"]

    def test_player_semester_amateur_below_minimum(self):
        lic = _license("PLAYER", 4)  # AMATEUR needs 5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", "AMATEUR", db)
        assert result["authorized"] is False

    def test_player_semester_pro_exact_level(self):
        lic = _license("PLAYER", 8)  # PRO min=8
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRO", "PRO", db)
        assert result["authorized"] is True

    def test_player_semester_pro_insufficient_level(self):
        lic = _license("PLAYER", 7)  # PRO needs 8
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRO", "PRO", db)
        assert result["authorized"] is False

    def test_player_semester_coach_license_authorized(self):
        """Business rule 1: COACH license CAN teach PLAYER sessions."""
        lic = _license("COACH", 5)  # AMATEUR coach min=5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", "AMATEUR", db)
        assert result["authorized"] is True
        assert lic in result["matching_licenses"]

    def test_player_semester_coach_license_below_minimum(self):
        lic = _license("COACH", 4)  # AMATEUR coach needs 5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", "AMATEUR", db)
        assert result["authorized"] is False

    def test_player_semester_both_licenses_qualify(self):
        """Both PLAYER and COACH licenses qualify → both in matching_licenses."""
        lic_player = _license("PLAYER", 5)
        lic_coach = _license("COACH", 5)
        db = _db_with_licenses([lic_player, lic_coach])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", "AMATEUR", db)
        assert result["authorized"] is True
        assert len(result["matching_licenses"]) == 2

    def test_player_semester_coach_min_levels_unknown_age_group_uses_default(self):
        """COACH license in PLAYER semester, age_group unknown → COACH_MIN_LEVELS.get(None, 1)=1."""
        lic = _license("COACH", 1)
        db = _db_with_licenses([lic])
        # "LFA_PLAYER" → no age group → None → get(None, 1) = 1
        result = self._call(_instructor(), "LFA_PLAYER", None, db)
        assert result["authorized"] is True

    def test_player_semester_reason_includes_license_desc(self):
        lic = _license("PLAYER", 3)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_YOUTH", "YOUTH", db)
        assert result["authorized"] is True
        assert "PLAYER Level 3" in result["reason"]

    # --- COACH semester (business rule 2: PLAYER cannot teach COACH) ---

    def test_coach_semester_pre_coach_license_authorized(self):
        lic = _license("COACH", 1)  # PRE coach min=1
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRE", "PRE", db)
        assert result["authorized"] is True

    def test_coach_semester_youth_coach_license_authorized(self):
        lic = _license("COACH", 3)  # YOUTH coach min=3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_YOUTH", "YOUTH", db)
        assert result["authorized"] is True

    def test_coach_semester_amateur_coach_license_authorized(self):
        lic = _license("COACH", 5)  # AMATEUR coach min=5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_AMATEUR", "AMATEUR", db)
        assert result["authorized"] is True

    def test_coach_semester_pro_coach_license_authorized(self):
        lic = _license("COACH", 7)  # PRO coach min=7
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRO", "PRO", db)
        assert result["authorized"] is True

    def test_coach_semester_coach_license_below_minimum(self):
        lic = _license("COACH", 6)  # PRO needs 7
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRO", "PRO", db)
        assert result["authorized"] is False

    def test_coach_semester_player_license_any_level_denied(self):
        """Business rule 2: PLAYER license CANNOT teach COACH semester — any level.

        Fixed in Sprint N: PLAYER license check is now explicitly gated to
        base_spec == 'PLAYER' only. A PLAYER level 8 is correctly denied for
        COACH_PRO (previously it was incorrectly authorized).
        """
        lic = _license("PLAYER", 8)  # max PLAYER level — correctly denied for COACH semester
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRO", "PRO", db)
        assert result["authorized"] is False
        assert "No license meets minimum requirement" in result["reason"]

    def test_coach_semester_player_license_low_level_also_denied(self):
        """PLAYER license at any level is denied for COACH semester."""
        lic = _license("PLAYER", 1)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRE", "PRE", db)
        assert result["authorized"] is False

    def test_coach_semester_unknown_age_group_uses_default(self):
        """COACH semester, no age_group → COACH_MIN_LEVELS.get(None, 1) = 1."""
        lic = _license("COACH", 1)
        db = _db_with_licenses([lic])
        # "LFA_COACH" → no age group → None → get(None, 1) = 1
        result = self._call(_instructor(), "LFA_COACH", None, db)
        assert result["authorized"] is True


# ===========================================================================
# can_teach_session
# ===========================================================================

@pytest.mark.unit
class TestCanTeachSession:
    """Covers all deny/allow paths in can_teach_session."""

    def _call(self, instructor, session_spec, is_mixed, db,
              expiry_returns=True):
        if isinstance(expiry_returns, list):
            cm = patch(_PATCH_EXPIRY, side_effect=expiry_returns)
        else:
            cm = patch(_PATCH_EXPIRY, return_value=expiry_returns)
        with cm:
            return LicenseAuthorizationService.can_teach_session(
                instructor=instructor,
                session_specialization=session_spec,
                is_mixed_session=is_mixed,
                db=db,
            )

    # --- Mixed / no spec → immediate authorize (no DB access) ---

    def test_is_mixed_session_authorized_without_db(self):
        db = _db()
        result = self._call(_instructor(), "LFA_PLAYER_PRE", True, db)
        assert result["authorized"] is True
        assert "Mixed session" in result["reason"]
        db.query.assert_not_called()

    def test_no_session_spec_authorized_without_db(self):
        db = _db()
        result = self._call(_instructor(), None, False, db)
        assert result["authorized"] is True
        assert "Mixed session" in result["reason"]
        db.query.assert_not_called()

    def test_mixed_and_no_spec_both_true(self):
        """Both conditions True → early authorized."""
        db = _db()
        result = self._call(_instructor(), None, True, db)
        assert result["authorized"] is True
        db.query.assert_not_called()

    def test_db_commit_not_called_for_mixed_session(self):
        db = _db()
        self._call(_instructor(), "LFA_PLAYER_PRE", True, db)
        db.commit.assert_not_called()

    # --- No active licenses ---

    def test_no_licenses_denied(self):
        db = _db_with_licenses([])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", False, db)
        assert result["authorized"] is False
        assert "No active licenses" in result["reason"]

    def test_all_licenses_expired_denied(self):
        lic = _license("PLAYER", 5)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", False, db,
                            expiry_returns=False)
        assert result["authorized"] is False

    def test_partial_expiration_only_active_used(self):
        lic_expired = _license("PLAYER", 1)
        lic_active = _license("PLAYER", 3)
        db = _db_with_licenses([lic_expired, lic_active])
        result = self._call(_instructor(), "LFA_PLAYER_YOUTH", False, db,
                            expiry_returns=[False, True])
        # lic_active level=3 >= YOUTH min=3 → authorized
        assert result["authorized"] is True

    def test_db_commit_called_when_non_mixed(self):
        db = _db_with_licenses([])
        self._call(_instructor(), "LFA_PLAYER_PRE", False, db)
        db.commit.assert_called_once()

    # --- Invalid specialization ---

    def test_invalid_specialization_denied(self):
        lic = _license("PLAYER", 5)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "UNKNOWN_XYZ", False, db)
        assert result["authorized"] is False
        assert "Invalid session specialization" in result["reason"]
        assert "UNKNOWN_XYZ" in result["reason"]

    # --- PLAYER sessions ---

    def test_player_session_player_license_with_age_group(self):
        """PLAYER license + recognized age group → uses PLAYER_MIN_LEVELS.get(age_group)."""
        lic = _license("PLAYER", 3)  # YOUTH min=3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_YOUTH", False, db)
        assert result["authorized"] is True
        assert lic in result["matching_licenses"]

    def test_player_session_player_license_below_min_with_age_group(self):
        lic = _license("PLAYER", 2)  # YOUTH needs 3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_YOUTH", False, db)
        assert result["authorized"] is False

    def test_player_session_player_license_no_age_group(self):
        """No age group in spec → else branch → min_level=1."""
        lic = _license("PLAYER", 1)
        db = _db_with_licenses([lic])
        # "LFA_PLAYER" → age_group=None → if age_group else 1 → min=1
        result = self._call(_instructor(), "LFA_PLAYER", False, db)
        assert result["authorized"] is True

    def test_player_session_player_license_pro_age_group(self):
        lic = _license("PLAYER", 8)  # PRO min=8
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRO", False, db)
        assert result["authorized"] is True

    def test_player_session_coach_license_with_age_group(self):
        """COACH license can teach PLAYER session (business rule 1)."""
        lic = _license("COACH", 5)  # AMATEUR coach min=5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", False, db)
        assert result["authorized"] is True
        assert lic in result["matching_licenses"]

    def test_player_session_coach_license_below_min(self):
        lic = _license("COACH", 4)  # AMATEUR needs 5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", False, db)
        assert result["authorized"] is False

    def test_player_session_coach_license_no_age_group(self):
        """COACH license, no age group → else branch → min=1."""
        lic = _license("COACH", 1)
        db = _db_with_licenses([lic])
        # "LFA_PLAYER" → age_group=None → if age_group else 1 → min=1
        result = self._call(_instructor(), "LFA_PLAYER", False, db)
        assert result["authorized"] is True

    def test_player_session_internship_license_denied(self):
        """INTERNSHIP license cannot teach PLAYER session."""
        lic = _license("INTERNSHIP", 5)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_PRE", False, db)
        assert result["authorized"] is False

    def test_player_session_reason_includes_license_info(self):
        lic = _license("PLAYER", 5)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", False, db)
        assert "PLAYER Level 5" in result["reason"]

    def test_player_session_denied_reason_includes_spec(self):
        """Final deny message includes session_specialization."""
        lic = _license("INTERNSHIP", 1)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_PLAYER_AMATEUR", False, db)
        assert result["authorized"] is False
        assert "LFA_PLAYER_AMATEUR" in result["reason"]

    # --- COACH sessions ---

    def test_coach_session_coach_license_with_age_group(self):
        lic = _license("COACH", 3)  # YOUTH coach min=3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_YOUTH", False, db)
        assert result["authorized"] is True

    def test_coach_session_coach_license_no_age_group(self):
        """COACH session, no age group → else branch → min=1."""
        lic = _license("COACH", 1)
        db = _db_with_licenses([lic])
        # "LFA_COACH" → age_group=None → if age_group else 1 → min=1
        result = self._call(_instructor(), "LFA_COACH", False, db)
        assert result["authorized"] is True

    def test_coach_session_coach_below_min(self):
        lic = _license("COACH", 2)  # YOUTH needs 3
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_YOUTH", False, db)
        assert result["authorized"] is False

    def test_coach_session_player_license_denied(self):
        """Business rule 2: PLAYER license cannot teach COACH session."""
        lic = _license("PLAYER", 8)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRE", False, db)
        assert result["authorized"] is False
        assert "No license meets requirement" in result["reason"]

    def test_coach_session_pro_age_group(self):
        lic = _license("COACH", 7)  # PRO coach min=7
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_PRO", False, db)
        assert result["authorized"] is True

    def test_coach_session_amateur_age_group(self):
        lic = _license("COACH", 5)  # AMATEUR coach min=5
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_COACH_AMATEUR", False, db)
        assert result["authorized"] is True

    # --- INTERNSHIP sessions ---

    def test_internship_session_internship_license_authorized(self):
        lic = _license("INTERNSHIP", 2)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERNSHIP", False, db)
        assert result["authorized"] is True
        assert lic in result["matching_licenses"]

    def test_internship_session_player_license_denied(self):
        lic = _license("PLAYER", 8)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERNSHIP", False, db)
        assert result["authorized"] is False

    def test_internship_session_coach_license_denied(self):
        lic = _license("COACH", 8)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERNSHIP", False, db)
        assert result["authorized"] is False

    def test_internship_session_via_intern_keyword(self):
        """INTERN substring → INTERNSHIP base spec → INTERNSHIP license works."""
        lic = _license("INTERNSHIP", 1)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERN_PROGRAM", False, db)
        assert result["authorized"] is True

    def test_internship_session_reason_includes_license_desc(self):
        lic = _license("INTERNSHIP", 3)
        db = _db_with_licenses([lic])
        result = self._call(_instructor(), "LFA_INTERNSHIP", False, db)
        assert "INTERNSHIP Level 3" in result["reason"]


# ===========================================================================
# get_qualified_instructors_for_semester
# ===========================================================================

@pytest.mark.unit
class TestGetQualifiedInstructors:

    def test_no_users_with_licenses_returns_empty(self):
        db = _db_for_users([])
        result = LicenseAuthorizationService.get_qualified_instructors_for_semester(
            "LFA_PLAYER_PRE", "PRE", db
        )
        assert result == []

    def test_authorized_user_included_in_result(self):
        user = _instructor(uid=42)
        db = _db_for_users([user])
        auth = {
            "authorized": True,
            "reason": "Qualified with: PLAYER Level 5",
            "matching_licenses": [_license("PLAYER", 5)],
        }
        with patch.object(LicenseAuthorizationService, "can_be_master_instructor",
                          return_value=auth):
            result = LicenseAuthorizationService.get_qualified_instructors_for_semester(
                "LFA_PLAYER_PRE", "PRE", db
            )
        assert len(result) == 1
        assert result[0]["instructor"] is user
        assert result[0]["authorization_reason"] == auth["reason"]
        assert result[0]["matching_licenses"] == auth["matching_licenses"]

    def test_unauthorized_user_excluded(self):
        user = _instructor(uid=42)
        db = _db_for_users([user])
        auth = {"authorized": False, "reason": "No license", "matching_licenses": []}
        with patch.object(LicenseAuthorizationService, "can_be_master_instructor",
                          return_value=auth):
            result = LicenseAuthorizationService.get_qualified_instructors_for_semester(
                "LFA_PLAYER_PRE", "PRE", db
            )
        assert result == []

    def test_mixed_authorized_and_unauthorized(self):
        """Only authorized users appear in result."""
        user1 = _instructor(uid=42)
        user2 = _instructor(uid=43)
        db = _db_for_users([user1, user2])
        auth_yes = {
            "authorized": True,
            "reason": "OK",
            "matching_licenses": [_license("PLAYER", 5)],
        }
        auth_no = {"authorized": False, "reason": "No", "matching_licenses": []}
        with patch.object(LicenseAuthorizationService, "can_be_master_instructor",
                          side_effect=[auth_yes, auth_no]):
            result = LicenseAuthorizationService.get_qualified_instructors_for_semester(
                "LFA_PLAYER_PRE", "PRE", db
            )
        assert len(result) == 1
        assert result[0]["instructor"] is user1

    def test_multiple_authorized_users(self):
        user1 = _instructor(uid=42)
        user2 = _instructor(uid=43)
        db = _db_for_users([user1, user2])
        auth = {
            "authorized": True,
            "reason": "OK",
            "matching_licenses": [_license("PLAYER", 5)],
        }
        with patch.object(LicenseAuthorizationService, "can_be_master_instructor",
                          return_value=auth):
            result = LicenseAuthorizationService.get_qualified_instructors_for_semester(
                "LFA_PLAYER_PRE", "PRE", db
            )
        assert len(result) == 2
        assert result[0]["instructor"] is user1
        assert result[1]["instructor"] is user2
