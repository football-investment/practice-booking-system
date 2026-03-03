"""
Unit tests for skill_state_machine module

Covers all pure functions:
- SkillAssessmentState classmethods (all_states, active_states, terminal_states)
- validate_state_transition: all valid transitions, all invalid transitions,
  idempotent allow/deny modes, unknown state handling
- is_terminal_state
- get_valid_transitions (idempotent transitions excluded from result)
- determine_validation_requirement: all 4 business rules
- create_state_transition_audit: dict structure
- log_state_transition: idempotent and real transition branches

DB-free: zero DB calls in this module.
"""
import pytest
from datetime import datetime
from unittest.mock import patch

from app.services.skill_state_machine import (
    SkillAssessmentState,
    VALID_TRANSITIONS,
    INVALID_TRANSITIONS,
    validate_state_transition,
    is_terminal_state,
    get_valid_transitions,
    determine_validation_requirement,
    create_state_transition_audit,
    log_state_transition,
)

S = SkillAssessmentState  # shorthand


# ─── SkillAssessmentState classmethods ────────────────────────────────────────

@pytest.mark.unit
class TestSkillAssessmentStateClassmethods:

    def test_all_states_contains_four_states(self):
        states = S.all_states()
        assert len(states) == 4
        assert S.NOT_ASSESSED in states
        assert S.ASSESSED in states
        assert S.VALIDATED in states
        assert S.ARCHIVED in states

    def test_active_states_excludes_archived(self):
        active = S.active_states()
        assert S.ARCHIVED not in active
        assert S.NOT_ASSESSED not in active
        assert S.ASSESSED in active
        assert S.VALIDATED in active

    def test_terminal_states_is_archived_only(self):
        terminal = S.terminal_states()
        assert terminal == [S.ARCHIVED]


# ─── validate_state_transition — valid transitions ────────────────────────────

@pytest.mark.unit
class TestValidateStateTransitionValid:

    def test_not_assessed_to_assessed(self):
        ok, msg = validate_state_transition(S.NOT_ASSESSED, S.ASSESSED)
        assert ok is True
        assert msg == ""

    def test_assessed_to_validated(self):
        ok, msg = validate_state_transition(S.ASSESSED, S.VALIDATED)
        assert ok is True

    def test_assessed_to_archived(self):
        ok, msg = validate_state_transition(S.ASSESSED, S.ARCHIVED)
        assert ok is True

    def test_validated_to_archived(self):
        ok, msg = validate_state_transition(S.VALIDATED, S.ARCHIVED)
        assert ok is True

    def test_all_valid_transitions_from_table_pass(self):
        """Every edge in VALID_TRANSITIONS (excluding idempotent) must return True."""
        for from_s, targets in VALID_TRANSITIONS.items():
            for to_s in targets:
                if from_s == to_s:
                    continue  # idempotent tested separately
                ok, msg = validate_state_transition(from_s, to_s)
                assert ok is True, f"Expected True for {from_s!r} → {to_s!r}, got: {msg}"


# ─── validate_state_transition — invalid transitions ──────────────────────────

@pytest.mark.unit
class TestValidateStateTransitionInvalid:

    def test_not_assessed_to_validated_rejected(self):
        ok, msg = validate_state_transition(S.NOT_ASSESSED, S.VALIDATED)
        assert ok is False
        assert "assessment" in msg.lower() or "first" in msg.lower()

    def test_not_assessed_to_archived_rejected(self):
        ok, msg = validate_state_transition(S.NOT_ASSESSED, S.ARCHIVED)
        assert ok is False

    def test_assessed_to_not_assessed_rejected(self):
        ok, msg = validate_state_transition(S.ASSESSED, S.NOT_ASSESSED)
        assert ok is False
        assert msg != ""

    def test_validated_to_not_assessed_rejected(self):
        ok, msg = validate_state_transition(S.VALIDATED, S.NOT_ASSESSED)
        assert ok is False

    def test_validated_to_assessed_rejected(self):
        ok, msg = validate_state_transition(S.VALIDATED, S.ASSESSED)
        assert ok is False
        assert "un-validate" in msg.lower() or "permanent" in msg.lower()

    def test_archived_to_not_assessed_rejected(self):
        ok, msg = validate_state_transition(S.ARCHIVED, S.NOT_ASSESSED)
        assert ok is False
        assert "terminal" in msg.lower() or "archived" in msg.lower()

    def test_archived_to_assessed_rejected(self):
        ok, msg = validate_state_transition(S.ARCHIVED, S.ASSESSED)
        assert ok is False

    def test_archived_to_validated_rejected(self):
        ok, msg = validate_state_transition(S.ARCHIVED, S.VALIDATED)
        assert ok is False

    def test_all_invalid_transitions_from_table_fail(self):
        """Every edge in INVALID_TRANSITIONS must return False."""
        for from_s, targets in INVALID_TRANSITIONS.items():
            for to_s in targets:
                ok, msg = validate_state_transition(from_s, to_s)
                assert ok is False, f"Expected False for {from_s!r} → {to_s!r}"

    def test_unknown_from_state_rejected(self):
        ok, msg = validate_state_transition("GHOST", S.ASSESSED)
        assert ok is False
        assert "from_state" in msg.lower() or "Invalid" in msg

    def test_unknown_to_state_rejected(self):
        ok, msg = validate_state_transition(S.ASSESSED, "SUPER_VALIDATED")
        assert ok is False
        assert "to_state" in msg.lower() or "Invalid" in msg


# ─── validate_state_transition — idempotent mode ──────────────────────────────

@pytest.mark.unit
class TestValidateStateTransitionIdempotent:

    def test_idempotent_allowed_by_default(self):
        ok, msg = validate_state_transition(S.ASSESSED, S.ASSESSED)
        assert ok is True
        assert msg == ""

    def test_idempotent_allowed_explicitly(self):
        ok, msg = validate_state_transition(S.VALIDATED, S.VALIDATED, allow_idempotent=True)
        assert ok is True

    def test_idempotent_denied_when_flag_false(self):
        ok, msg = validate_state_transition(S.ASSESSED, S.ASSESSED, allow_idempotent=False)
        assert ok is False
        assert "Idempotent" in msg

    def test_idempotent_denied_for_archived_when_flag_false(self):
        ok, msg = validate_state_transition(S.ARCHIVED, S.ARCHIVED, allow_idempotent=False)
        assert ok is False


# ─── is_terminal_state ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsTerminalState:

    def test_archived_is_terminal(self):
        assert is_terminal_state(S.ARCHIVED) is True

    def test_assessed_is_not_terminal(self):
        assert is_terminal_state(S.ASSESSED) is False

    def test_validated_is_not_terminal(self):
        assert is_terminal_state(S.VALIDATED) is False

    def test_not_assessed_is_not_terminal(self):
        assert is_terminal_state(S.NOT_ASSESSED) is False


# ─── get_valid_transitions ────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetValidTransitions:

    def test_not_assessed_can_only_go_to_assessed(self):
        result = get_valid_transitions(S.NOT_ASSESSED)
        assert result == [S.ASSESSED]

    def test_assessed_can_go_to_validated_and_archived(self):
        result = get_valid_transitions(S.ASSESSED)
        assert S.VALIDATED in result
        assert S.ARCHIVED in result
        assert S.ASSESSED not in result  # idempotent excluded

    def test_validated_can_only_go_to_archived(self):
        result = get_valid_transitions(S.VALIDATED)
        assert result == [S.ARCHIVED]

    def test_archived_has_no_valid_transitions(self):
        result = get_valid_transitions(S.ARCHIVED)
        assert result == []

    def test_unknown_state_returns_empty(self):
        assert get_valid_transitions("NONEXISTENT") == []


# ─── determine_validation_requirement ────────────────────────────────────────

@pytest.mark.unit
class TestDetermineValidationRequirement:

    def test_rule1_high_stake_level_5_requires_validation(self):
        assert determine_validation_requirement(5, 200, "outfield") is True

    def test_rule1_high_stake_level_6_requires_validation(self):
        assert determine_validation_requirement(6, 200, "outfield") is True

    def test_rule1_level_8_requires_validation(self):
        assert determine_validation_requirement(8, 300, "physical") is True

    def test_rule2_new_instructor_below_180_days_requires_validation(self):
        # Level 4, tenure 100 days, non-critical skill
        assert determine_validation_requirement(4, 100, "outfield") is True

    def test_rule2_exactly_at_probation_boundary_179_days_requires(self):
        assert determine_validation_requirement(3, 179, "physical") is True

    def test_rule2_exactly_180_days_no_longer_new(self):
        # 180 days = not new; level 3, non-critical category → auto-accept
        assert determine_validation_requirement(3, 180, "outfield") is False

    def test_rule3_mental_category_requires_validation(self):
        assert determine_validation_requirement(3, 200, "mental") is True

    def test_rule3_set_pieces_category_requires_validation(self):
        assert determine_validation_requirement(3, 200, "set_pieces") is True

    def test_rule4_default_auto_accepted(self):
        # Level 3, senior instructor (200 days), non-critical skill
        assert determine_validation_requirement(3, 200, "outfield") is False

    def test_rule4_physical_category_auto_accepted(self):
        assert determine_validation_requirement(3, 200, "physical") is False

    def test_rule1_takes_priority_over_rule2(self):
        """Level 5+ requires validation regardless of tenure."""
        assert determine_validation_requirement(5, 999, "outfield") is True

    def test_combined_level_4_senior_instructor_non_critical_auto(self):
        assert determine_validation_requirement(4, 365, "outfield") is False


# ─── create_state_transition_audit ───────────────────────────────────────────

@pytest.mark.unit
class TestCreateStateTransitionAudit:

    def test_returns_dict_with_required_keys(self):
        result = create_state_transition_audit(S.ASSESSED, S.VALIDATED, 42)
        assert "previous_status" in result
        assert "status" in result
        assert "status_changed_at" in result
        assert "status_changed_by" in result

    def test_status_values_correct(self):
        result = create_state_transition_audit(S.ASSESSED, S.VALIDATED, 99)
        assert result["previous_status"] == S.ASSESSED
        assert result["status"] == S.VALIDATED
        assert result["status_changed_by"] == 99

    def test_status_changed_at_is_datetime(self):
        result = create_state_transition_audit(S.ASSESSED, S.VALIDATED, 1)
        assert isinstance(result["status_changed_at"], datetime)

    def test_with_reason_not_in_result(self):
        """Reason is accepted but not yet in schema (Phase 2)."""
        result = create_state_transition_audit(S.ASSESSED, S.VALIDATED, 1, reason="audit")
        # Should not raise; result may or may not include reason
        assert "status" in result


# ─── log_state_transition ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestLogStateTransition:

    def test_idempotent_log_does_not_raise(self):
        log_state_transition(1, S.ASSESSED, S.ASSESSED, changed_by=10)

    def test_real_transition_log_does_not_raise(self):
        log_state_transition(2, S.ASSESSED, S.VALIDATED, changed_by=5, reason="Admin check")

    def test_log_without_reason_does_not_raise(self):
        log_state_transition(3, S.NOT_ASSESSED, S.ASSESSED, changed_by=1)
