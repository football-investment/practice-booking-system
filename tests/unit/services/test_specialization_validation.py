"""
Sprint O — SpecializationValidator unit tests
==============================================
Invariants covered:
  INV-1  No short-circuit: all steps run even after first error accumulates
  INV-2  Parental consent granted → warning (not error)
  INV-3  Config load failure → early return with error (bypasses raise_exception)
  INV-4  raise_exception=True → SpecializationValidationError raised on invalid result
  INV-5  DOB=None does NOT short-circuit LFA_COACH Step 3a (uses user.age directly)
  INV-6  Error ordering is deterministic: Step1→Step3a→Step3b→Step4 = list order
         (exception message = "; ".join(errors) — API contract depends on this)

TestLFACoachConfigSync uses REAL SpecializationConfigLoader (no mock) to detect
drift between lfa_coach.json and the hardcoded constant 14 in source code.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Optional

from app.services.specialization_validation import (
    SpecializationValidator,
    SpecializationValidationError,
)
from app.services.specialization_config_loader import SpecializationConfigLoader
from app.models.specialization import SpecializationType

_PATCH_LOADER = "app.services.specialization_validation.get_config_loader"


# ── Minimal helpers ──────────────────────────────────────────────────────────

def _config(
    min_age: int = 0,
    age_groups=None,
    name: str = "Test Spec",
    spec_id: str = "TEST",
) -> dict:
    """Minimal valid config dict sufficient for validator logic."""
    cfg = {
        "id": spec_id,
        "name": name,
        "description": "test",
        "min_age": min_age,
        "levels": [{"level": 1, "xp_required": 0, "xp_max": 999}],
    }
    if age_groups is not None:
        cfg["age_groups"] = age_groups
    return cfg


def _user(
    age: Optional[int] = 20,
    dob_set: bool = True,
    is_minor: bool = False,
    consent: bool = False,
    consent_by: Optional[str] = None,
) -> MagicMock:
    """Create a User-like mock with all validation-relevant attributes set."""
    u = MagicMock()
    u.date_of_birth = MagicMock() if dob_set else None
    u.age = age
    u.is_minor = is_minor
    u.parental_consent = consent
    u.parental_consent_by = consent_by
    return u


def _make_validator(cfg_or_exc=None) -> SpecializationValidator:
    """
    Return a SpecializationValidator with a mocked config loader.
    If cfg_or_exc is an Exception instance or type, load_config will raise it.
    If cfg_or_exc is a dict, load_config returns it.
    If None, load_config returns _config() (min_age=0, no age_groups).
    """
    mock_loader = MagicMock()
    if isinstance(cfg_or_exc, type) and issubclass(cfg_or_exc, Exception):
        mock_loader.load_config.side_effect = cfg_or_exc("config error")
    elif isinstance(cfg_or_exc, Exception):
        mock_loader.load_config.side_effect = cfg_or_exc
    elif cfg_or_exc is not None:
        mock_loader.load_config.return_value = cfg_or_exc
    else:
        mock_loader.load_config.return_value = _config()

    with patch(_PATCH_LOADER, return_value=mock_loader):
        v = SpecializationValidator(MagicMock())
    return v


# ── Class 1: Config load failure ─────────────────────────────────────────────

class TestConfigLoadFailure:
    """INV-3: Config load exception → early return with error dict."""

    def _call(self, exc) -> dict:
        v = _make_validator(exc)
        return v.validate_user_for_specialization(
            _user(), SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )

    def test_filenotfound_returns_invalid(self):
        result = self._call(FileNotFoundError("missing"))
        assert result["valid"] is False

    def test_filenotfound_error_message_describes_failure(self):
        result = self._call(FileNotFoundError("missing"))
        assert len(result["errors"]) == 1
        assert "Failed to load specialization config" in result["errors"][0]

    def test_valueerror_returns_invalid(self):
        result = self._call(ValueError("bad json"))
        assert result["valid"] is False
        assert "Failed to load specialization config" in result["errors"][0]

    def test_generic_exception_returns_invalid(self):
        result = self._call(RuntimeError("oops"))
        assert result["valid"] is False

    def test_early_return_has_empty_warnings(self):
        result = self._call(FileNotFoundError("x"))
        assert result["warnings"] == []

    def test_early_return_has_empty_requirements(self):
        result = self._call(FileNotFoundError("x"))
        assert result["requirements"] == {}

    def test_config_failure_bypasses_raise_exception(self):
        """INV-3: early return happens before raise_exception check — returns dict."""
        v = _make_validator(FileNotFoundError("x"))
        result = v.validate_user_for_specialization(
            _user(), SpecializationType.GANCUJU_PLAYER, raise_exception=True
        )
        assert result["valid"] is False


# ── Class 2: Minimum age validation ──────────────────────────────────────────

class TestMinAgeValidation:
    """INV-1 (errors accumulate), INV-6 (Step 1 error is first in list)."""

    def _call(self, user, min_age: int = 10, spec=SpecializationType.GANCUJU_PLAYER) -> dict:
        v = _make_validator(_config(min_age=min_age))
        return v.validate_user_for_specialization(user, spec, raise_exception=False)

    def test_age_above_min_valid(self):
        result = self._call(_user(age=20), min_age=10)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_age_exactly_at_min_valid(self):
        result = self._call(_user(age=10), min_age=10)
        assert result["valid"] is True

    def test_age_below_min_invalid(self):
        result = self._call(_user(age=9), min_age=10)
        assert result["valid"] is False
        assert any("at least 10 years old" in e for e in result["errors"])

    def test_age_below_min_error_contains_current_age(self):
        result = self._call(_user(age=7), min_age=10)
        assert "7" in result["errors"][0]

    def test_min_age_zero_always_passes(self):
        result = self._call(_user(age=0), min_age=0)
        assert result["valid"] is True

    def test_dob_none_skips_min_age_check(self):
        """DOB=None → _validate_min_age returns True (skip), even if min_age=100."""
        u = _user(age=None, dob_set=False)
        result = self._call(u, min_age=100)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_age_none_with_dob_set_skips_min_age_check(self):
        """age=None (DOB set) → _validate_min_age returns True (skip)."""
        u = _user(age=None, dob_set=True)
        result = self._call(u, min_age=100)
        assert result["valid"] is True

    def test_requirements_contain_min_age(self):
        result = self._call(_user(age=20), min_age=10)
        assert result["requirements"]["min_age"] == 10

    def test_requirements_contain_specialization_name(self):
        v = _make_validator(_config(min_age=5, name="MySpec"))
        result = v.validate_user_for_specialization(
            _user(age=20), SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert result["requirements"]["specialization_name"] == "MySpec"


# ── Class 3: LFA_COACH specific checks ───────────────────────────────────────

class TestLFACoachSpecific:
    """INV-5 (Step 3a uses user.age directly without DOB guard), INV-6 (ordering)."""

    def _call(self, user, cfg=None) -> dict:
        if cfg is None:
            cfg = _config(min_age=14)
        v = _make_validator(cfg)
        return v.validate_user_for_specialization(
            user, SpecializationType.LFA_COACH, raise_exception=False
        )

    def test_age_14_exactly_passes_step3a(self):
        """14 is NOT < 14 — boundary must not produce Step 3a error."""
        result = self._call(_user(age=14))
        assert not any("minimum age of 14" in e for e in result["errors"])

    def test_age_13_fails_step3a(self):
        result = self._call(_user(age=13))
        assert any("LFA_COACH requires minimum age of 14" in e for e in result["errors"])

    def test_age_13_error_mentions_user_age(self):
        result = self._call(_user(age=13))
        assert any("13 years old" in e for e in result["errors"])

    def test_age_none_skips_step3a(self):
        """user.age is None → Step 3a guard fires, step skipped."""
        u = _user(age=None, dob_set=False)
        result = self._call(u)
        assert not any("minimum age of 14" in e for e in result["errors"])

    def test_non_lfa_coach_skips_step3a(self):
        """Step 3a only runs for LFA_COACH."""
        v = _make_validator(_config(min_age=0))
        result = v.validate_user_for_specialization(
            _user(age=5), SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert not any("minimum age of 14" in e for e in result["errors"])

    def test_lfa_coach_requirements_include_parental_consent_flag(self):
        result = self._call(_user(age=20))
        assert result["requirements"]["requires_parental_consent_under_18"] is True

    def test_lfa_coach_requirements_include_min_age_override(self):
        result = self._call(_user(age=20))
        assert result["requirements"]["min_age_override"] == 14

    def test_non_lfa_coach_no_parental_consent_requirement(self):
        v = _make_validator(_config(min_age=5))
        result = v.validate_user_for_specialization(
            _user(age=10), SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert "requires_parental_consent_under_18" not in result["requirements"]

    def test_inv6_step3a_error_before_age_group_error(self):
        """INV-6: Step 3a error (age < 14) must precede age_group mismatch error."""
        age_groups = [{"name": "Adult", "min_age": 18, "max_age": None}]
        cfg = _config(min_age=0, age_groups=age_groups)
        u = _user(age=13)
        result = self._call(u, cfg=cfg)
        errors = result["errors"]
        assert len(errors) >= 2
        assert "LFA_COACH requires minimum age of 14" in errors[0]

    def test_inv1_step1_and_step3a_errors_both_accumulate(self):
        """INV-1: config min_age=20 AND age=13 → Step 1 + Step 3a errors, no short-circuit."""
        cfg = _config(min_age=20)
        u = _user(age=13)
        result = self._call(u, cfg=cfg)
        assert any("at least 20 years old" in e for e in result["errors"])
        assert any("LFA_COACH requires minimum age of 14" in e for e in result["errors"])
        assert len(result["errors"]) == 2


# ── Class 4: Parental consent matrix ─────────────────────────────────────────

class TestParentalConsentMatrix:
    """INV-1 (consent error accumulates with other errors), INV-2 (consent → warning)."""

    def _call(self, user) -> dict:
        v = _make_validator(_config(min_age=14))
        return v.validate_user_for_specialization(
            user, SpecializationType.LFA_COACH, raise_exception=False
        )

    def test_adult_no_consent_needed(self):
        u = _user(age=20, is_minor=False)
        result = self._call(u)
        assert not any("parental consent" in e.lower() for e in result["errors"])

    def test_minor_without_consent_invalid(self):
        u = _user(age=16, is_minor=True, consent=False)
        result = self._call(u)
        assert result["valid"] is False
        assert any("parental consent" in e.lower() for e in result["errors"])

    def test_minor_with_consent_valid(self):
        """INV-2: consent given → no error, only warning."""
        u = _user(age=16, is_minor=True, consent=True, consent_by="John Smith")
        result = self._call(u)
        assert result["valid"] is True
        assert not any("parental consent" in e.lower() for e in result["errors"])

    def test_minor_with_consent_warning_contains_parent_name(self):
        """INV-2: warning includes the parent/guardian name."""
        u = _user(age=16, is_minor=True, consent=True, consent_by="Jane Doe")
        result = self._call(u)
        assert any("Jane Doe" in w for w in result["warnings"])

    def test_minor_without_consent_no_parent_warning(self):
        """When consent not yet given, 'Parental consent provided' warning is absent."""
        u = _user(age=16, is_minor=True, consent=False, consent_by=None)
        result = self._call(u)
        assert not any("Parental consent provided" in w for w in result["warnings"])

    def test_non_lfa_coach_minor_no_consent_check(self):
        """Parental consent check only runs for LFA_COACH."""
        v = _make_validator(_config(min_age=5))
        u = _user(age=16, is_minor=True, consent=False)
        result = v.validate_user_for_specialization(
            u, SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert not any("parental consent" in e.lower() for e in result["errors"])

    def test_inv1_step3a_and_step3b_errors_both_accumulate(self):
        """INV-1: age=13 + no consent → Step 3a + Step 3b errors, no short-circuit.
        Uses min_age=0 so Step 1 doesn't add a third error — isolates the LFA_COACH steps.
        """
        v = _make_validator(_config(min_age=0))
        u = _user(age=13, is_minor=True, consent=False)
        result = v.validate_user_for_specialization(
            u, SpecializationType.LFA_COACH, raise_exception=False
        )
        assert any("minimum age of 14" in e for e in result["errors"])
        assert any("parental consent" in e.lower() for e in result["errors"])
        assert len(result["errors"]) == 2


# ── Class 5: Age group validation ────────────────────────────────────────────

class TestAgeGroupValidation:
    """INV-1 (age_group error accumulates), INV-6 (Step 4 after Step 1)."""

    _GROUPS = [
        {"name": "Youth", "min_age": 14, "max_age": 18},
        {"name": "Adult", "min_age": 19, "max_age": None},
    ]

    def _call(self, user, age_groups, spec=SpecializationType.LFA_FOOTBALL_PLAYER) -> dict:
        cfg = _config(min_age=5, age_groups=age_groups)
        v = _make_validator(cfg)
        return v.validate_user_for_specialization(user, spec, raise_exception=False)

    def test_age_in_bounded_group_valid(self):
        result = self._call(_user(age=15), [{"name": "G", "min_age": 14, "max_age": 18}])
        assert result["valid"] is True

    def test_age_at_lower_bound_valid(self):
        result = self._call(_user(age=14), [{"name": "G", "min_age": 14, "max_age": 18}])
        assert result["valid"] is True

    def test_age_at_upper_bound_valid(self):
        result = self._call(_user(age=18), [{"name": "G", "min_age": 14, "max_age": 18}])
        assert result["valid"] is True

    def test_age_in_unbounded_group_valid(self):
        result = self._call(_user(age=50), [{"name": "Open", "min_age": 14, "max_age": None}])
        assert result["valid"] is True

    def test_age_below_all_groups_invalid(self):
        result = self._call(_user(age=5), self._GROUPS)
        assert result["valid"] is False
        assert any("does not match any age group" in e for e in result["errors"])

    def test_age_in_gap_between_groups_invalid(self):
        groups = [
            {"name": "A", "min_age": 14, "max_age": 15},
            {"name": "B", "min_age": 18, "max_age": None},
        ]
        result = self._call(_user(age=16), groups)
        assert result["valid"] is False

    def test_no_age_groups_in_config_skips_validation(self):
        """Config with no age_groups key → age_group validation skipped."""
        cfg = _config(min_age=5)  # no age_groups
        v = _make_validator(cfg)
        result = v.validate_user_for_specialization(
            _user(age=50), SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert result["valid"] is True

    def test_dob_none_skips_age_group_check(self):
        """DOB=None → _validate_age_group returns True (skip)."""
        u = _user(age=None, dob_set=False)
        result = self._call(u, self._GROUPS)
        assert result["valid"] is True

    def test_error_message_lists_bounded_and_unbounded_ranges(self):
        groups = [
            {"name": "Youth", "min_age": 14, "max_age": 18},
            {"name": "Adult", "min_age": 19, "max_age": None},
        ]
        result = self._call(_user(age=5), groups)
        error = result["errors"][-1]
        assert "14-18" in error
        assert "19+" in error

    def test_requirements_has_age_groups_flag_true(self):
        result = self._call(_user(age=15), [{"name": "G", "min_age": 14, "max_age": 18}])
        assert result["requirements"]["has_age_groups"] is True

    def test_requirements_no_age_groups_flag_false(self):
        cfg = _config(min_age=5)
        v = _make_validator(cfg)
        result = v.validate_user_for_specialization(
            _user(age=10), SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert result["requirements"]["has_age_groups"] is False
        assert result["requirements"]["age_groups"] is None

    def test_inv6_step1_error_before_step4_age_group_error(self):
        """INV-6: Step 1 (min_age) error precedes Step 4 (age_group) error."""
        age_groups = [{"name": "G", "min_age": 25, "max_age": None}]
        cfg = _config(min_age=20, age_groups=age_groups)
        v = _make_validator(cfg)
        u = _user(age=10)
        result = v.validate_user_for_specialization(
            u, SpecializationType.LFA_FOOTBALL_PLAYER, raise_exception=False
        )
        errors = result["errors"]
        assert len(errors) == 2
        assert "at least 20 years old" in errors[0]
        assert "does not match any age group" in errors[1]


# ── Class 6: Silent skip edge cases ──────────────────────────────────────────

class TestSilentSkipsExact:
    """
    INV-5: Documents exactly which steps fire and which skip based on DOB/age.

    Key asymmetry:
      _validate_min_age  → skips if user.date_of_birth is None
      _validate_age_group → skips if user.date_of_birth is None OR user.age is None
      Step 3a (LFA_COACH)→ skips only if user.age is None (NO DOB guard)

    This means: if somehow user.age is set but date_of_birth is None (mock artifact),
    Step 3a fires while Steps 1 and 4 both skip.
    """

    def test_dob_none_age_none_no_errors_only_dob_warning(self):
        """Full DOB/age=None → all age steps skip; only DOB warning fires."""
        v = _make_validator(_config(min_age=10))
        u = _user(age=None, dob_set=False)
        result = v.validate_user_for_specialization(
            u, SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert result["valid"] is True
        assert result["errors"] == []
        assert any("date of birth not set" in w.lower() for w in result["warnings"])

    def test_lfa_coach_dob_none_age_none_skips_step3a(self):
        """DOB=None AND age=None: Step 3a guard (age is not None) → skip."""
        v = _make_validator(_config(min_age=0))
        u = _user(age=None, dob_set=False, is_minor=False)
        result = v.validate_user_for_specialization(
            u, SpecializationType.LFA_COACH, raise_exception=False
        )
        assert not any("minimum age of 14" in e for e in result["errors"])
        assert result["valid"] is True

    def test_inv5_lfa_coach_dob_none_age_set_step3a_fires(self):
        """
        INV-5 core: user.date_of_birth=None but user.age=12 (possible mock artifact) →
        Step 3a fires because it uses user.age directly without a DOB guard.
        Step 1 and Step 4 still skip (they guard on date_of_birth is None).
        """
        v = _make_validator(_config(min_age=14))
        u = MagicMock()
        u.date_of_birth = None   # → _validate_min_age skips, _validate_age_group skips
        u.age = 12               # → Step 3a fires: 12 < 14
        u.is_minor = True
        u.parental_consent = False

        result = v.validate_user_for_specialization(
            u, SpecializationType.LFA_COACH, raise_exception=False
        )
        # Step 3a fires despite DOB=None
        assert any("LFA_COACH requires minimum age of 14" in e for e in result["errors"])
        # Step 1 skipped: no "at least N years old" from config min_age check
        assert not any("at least 14 years old" in e for e in result["errors"])

    def test_dob_set_age_none_skips_both_min_and_group(self):
        """DOB set but age=None: both _validate_min_age and _validate_age_group skip."""
        age_groups = [{"name": "Youth", "min_age": 14, "max_age": 18}]
        v = _make_validator(_config(min_age=10, age_groups=age_groups))
        u = _user(age=None, dob_set=True)
        result = v.validate_user_for_specialization(
            u, SpecializationType.LFA_FOOTBALL_PLAYER, raise_exception=False
        )
        assert result["valid"] is True

    def test_dob_none_triggers_dob_warning_for_lfa_coach_too(self):
        """DOB=None warning fires for LFA_COACH regardless of other steps."""
        v = _make_validator(_config(min_age=0))
        u = _user(age=None, dob_set=False, is_minor=False)
        result = v.validate_user_for_specialization(
            u, SpecializationType.LFA_COACH, raise_exception=False
        )
        assert any("date of birth not set" in w.lower() for w in result["warnings"])


# ── Class 7: raise_exception gate ────────────────────────────────────────────

class TestRaiseExceptionGate:
    """INV-4 (invalid → raises), INV-6 (exception message = '; '.join(errors))."""

    def test_raise_exception_true_on_invalid_raises(self):
        v = _make_validator(_config(min_age=20))
        u = _user(age=10)
        with pytest.raises(SpecializationValidationError):
            v.validate_user_for_specialization(
                u, SpecializationType.GANCUJU_PLAYER, raise_exception=True
            )

    def test_raise_exception_false_returns_dict_on_invalid(self):
        v = _make_validator(_config(min_age=20))
        u = _user(age=10)
        result = v.validate_user_for_specialization(
            u, SpecializationType.GANCUJU_PLAYER, raise_exception=False
        )
        assert isinstance(result, dict)
        assert result["valid"] is False

    def test_raise_exception_true_valid_does_not_raise(self):
        v = _make_validator(_config(min_age=5))
        u = _user(age=20)
        result = v.validate_user_for_specialization(
            u, SpecializationType.GANCUJU_PLAYER, raise_exception=True
        )
        assert result["valid"] is True

    def test_raise_exception_default_is_true(self):
        """Default raise_exception=True — raises without explicit kwarg."""
        v = _make_validator(_config(min_age=20))
        u = _user(age=10)
        with pytest.raises(SpecializationValidationError):
            v.validate_user_for_specialization(u, SpecializationType.GANCUJU_PLAYER)

    def test_inv6_exception_message_equals_joined_errors(self):
        """INV-6: exception message == '; '.join(errors) — API contract."""
        age_groups = [{"name": "G", "min_age": 30, "max_age": None}]
        v = _make_validator(_config(min_age=25, age_groups=age_groups))
        u = _user(age=10)
        try:
            v.validate_user_for_specialization(
                u, SpecializationType.LFA_FOOTBALL_PLAYER, raise_exception=True
            )
            pytest.fail("Expected SpecializationValidationError")
        except SpecializationValidationError as exc:
            result = v.validate_user_for_specialization(
                u, SpecializationType.LFA_FOOTBALL_PLAYER, raise_exception=False
            )
            expected_msg = "; ".join(result["errors"])
            assert str(exc) == expected_msg

    def test_inv6_lfa_coach_multi_error_message_order(self):
        """INV-6: exception message joins Step 3a then Step 3b errors in pipeline order."""
        v = _make_validator(_config(min_age=0))
        u = _user(age=13, is_minor=True, consent=False)
        try:
            v.validate_user_for_specialization(
                u, SpecializationType.LFA_COACH, raise_exception=True
            )
            pytest.fail("Expected SpecializationValidationError")
        except SpecializationValidationError as exc:
            msg = str(exc)
            idx_age = msg.find("minimum age of 14")
            idx_consent = msg.find("parental consent")
            assert idx_age != -1, "Step 3a error absent from exception message"
            assert idx_consent != -1, "Step 3b error absent from exception message"
            assert idx_age < idx_consent, (
                f"Step 3a error must precede Step 3b in exception message.\n"
                f"Message: {msg!r}"
            )


# ── Class 8: get_eligible_specializations ────────────────────────────────────

class TestGetEligibleSpecializations:
    """get_eligible_specializations: iterates all spec types, handles display_info errors."""

    def _make_for_eligible(
        self,
        min_age: int = 0,
        display_err_spec=None,
    ) -> SpecializationValidator:
        """
        Validator whose loader returns _config(min_age) for ALL spec types,
        and optionally raises for get_display_info on a specific spec.
        """
        mock_loader = MagicMock()
        mock_loader.load_config.return_value = _config(min_age=min_age)

        if display_err_spec is not None:
            def _display_side(spec):
                if spec == display_err_spec:
                    raise RuntimeError("display info error")
                return {"name": spec.value}
            mock_loader.get_display_info.side_effect = _display_side
        else:
            mock_loader.get_display_info.return_value = {"name": "Test"}

        with patch(_PATCH_LOADER, return_value=mock_loader):
            return SpecializationValidator(MagicMock())

    def test_returns_entry_for_every_spec_enum_value(self):
        """get_eligible_specializations iterates ALL SpecializationType values."""
        v = self._make_for_eligible(min_age=0)
        results = v.get_eligible_specializations(_user(age=20))
        result_specs = {r["specialization"] for r in results}
        assert result_specs == set(SpecializationType)

    def test_result_dict_has_required_keys(self):
        v = self._make_for_eligible(min_age=0)
        results = v.get_eligible_specializations(_user(age=20))
        for r in results:
            for key in ("specialization", "specialization_id", "name", "eligible",
                        "errors", "warnings", "requirements"):
                assert key in r, f"Key '{key}' missing from result"

    def test_eligible_user_all_marked_eligible(self):
        """min_age=0 → all specs eligible for user age=20."""
        v = self._make_for_eligible(min_age=0)
        results = v.get_eligible_specializations(_user(age=20))
        for r in results:
            assert r["eligible"] is True, (
                f"{r['specialization']} should be eligible but got errors: {r['errors']}"
            )

    def test_ineligible_user_all_marked_ineligible(self):
        """min_age=100 → all specs ineligible for user age=20."""
        v = self._make_for_eligible(min_age=100)
        results = v.get_eligible_specializations(_user(age=20))
        for r in results:
            assert r["eligible"] is False
            assert len(r["errors"]) > 0

    def test_display_info_error_falls_back_to_enum_value(self):
        """get_display_info failure → name falls back to spec_enum.value."""
        v = self._make_for_eligible(
            min_age=0, display_err_spec=SpecializationType.GANCUJU_PLAYER
        )
        results = v.get_eligible_specializations(_user(age=20))
        gancuju = next(
            r for r in results if r["specialization"] == SpecializationType.GANCUJU_PLAYER
        )
        assert gancuju["name"] == SpecializationType.GANCUJU_PLAYER.value

    def test_specialization_id_matches_enum_value(self):
        v = self._make_for_eligible(min_age=0)
        results = v.get_eligible_specializations(_user(age=20))
        for r in results:
            assert r["specialization_id"] == r["specialization"].value


# ── Class 9: get_matching_age_group ──────────────────────────────────────────

class TestGetMatchingAgeGroup:
    """Boundary and edge cases for get_matching_age_group."""

    def _make_with_groups(self, age_groups) -> SpecializationValidator:
        cfg = _config(min_age=0, age_groups=age_groups)
        return _make_validator(cfg)

    def test_age_none_returns_none(self):
        v = self._make_with_groups([{"name": "G", "min_age": 14, "max_age": None}])
        result = v.get_matching_age_group(_user(age=None), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is None

    def test_age_in_bounded_group_returns_group(self):
        groups = [{"name": "Youth", "min_age": 14, "max_age": 18, "levels": [3, 4]}]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=16), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is not None
        assert result["name"] == "Youth"

    def test_age_in_unbounded_group_returns_group(self):
        groups = [{"name": "Open", "min_age": 14, "max_age": None}]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=50), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is not None
        assert result["name"] == "Open"

    def test_age_below_all_groups_returns_none(self):
        groups = [{"name": "Youth", "min_age": 14, "max_age": 18}]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=5), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is None

    def test_age_above_bounded_returns_none(self):
        groups = [{"name": "G", "min_age": 14, "max_age": 18}]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=19), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is None

    def test_first_matching_group_returned(self):
        """With multiple matching groups, the first (lowest-indexed) is returned."""
        groups = [
            {"name": "Youth", "min_age": 14, "max_age": 18},
            {"name": "Amateur", "min_age": 14, "max_age": None},
        ]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=16), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result["name"] == "Youth"

    def test_no_age_groups_in_config_returns_none(self):
        """Config with no age_groups → for-loop doesn't execute → None."""
        v = _make_validator(_config(min_age=5))
        result = v.get_matching_age_group(_user(age=20), SpecializationType.GANCUJU_PLAYER)
        assert result is None

    def test_age_exactly_at_lower_bound_matches(self):
        groups = [{"name": "G", "min_age": 14, "max_age": 18}]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=14), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is not None

    def test_age_exactly_at_upper_bound_matches(self):
        groups = [{"name": "G", "min_age": 14, "max_age": 18}]
        v = self._make_with_groups(groups)
        result = v.get_matching_age_group(_user(age=18), SpecializationType.LFA_FOOTBALL_PLAYER)
        assert result is not None


# ── Class 10: Config-sync guardrail (REAL loader, no mock) ───────────────────

class TestLFACoachConfigSync:
    """
    Uses the REAL SpecializationConfigLoader to detect drift between
    lfa_coach.json and the hardcoded constant 14 in specialization_validation.py.

    Fails CI immediately if:
      - lfa_coach.json min_age is changed without updating Step 3a constant
      - parental_consent_required_under_18 is removed from the JSON
      - any age group min_age deviates from 14
    """

    def test_lfa_coach_config_min_age_equals_hardcoded_14(self):
        """lfa_coach.json min_age MUST equal the hardcoded Step 3a constant 14."""
        loader = SpecializationConfigLoader()
        config = loader.load_config(SpecializationType.LFA_COACH)
        assert config["min_age"] == 14, (
            "DRIFT DETECTED: lfa_coach.json min_age changed without updating "
            "the hardcoded constant 14 in specialization_validation.py Step 3a. "
            "Either revert the JSON change or update both the constant and this test."
        )

    def test_lfa_coach_config_parental_consent_flag_set(self):
        """lfa_coach.json must declare parental_consent_required_under_18=true."""
        loader = SpecializationConfigLoader()
        config = loader.load_config(SpecializationType.LFA_COACH)
        assert config.get("parental_consent_required_under_18") is True, (
            "lfa_coach.json must declare parental_consent_required_under_18=true. "
            "This is a regulatory constraint, not a platform configuration."
        )

    def test_lfa_coach_all_age_groups_allow_entry_at_14(self):
        """All LFA_COACH age groups must have min_age=14 (consistent with entry age)."""
        loader = SpecializationConfigLoader()
        config = loader.load_config(SpecializationType.LFA_COACH)
        age_groups = config.get("age_groups", [])
        assert age_groups, "lfa_coach.json must have at least one age group"
        for ag in age_groups:
            assert ag["min_age"] == 14, (
                f"Age group '{ag['name']}' has min_age={ag['min_age']}, expected 14. "
                "All LFA_COACH age groups must allow entry at the minimum entry age 14."
            )
