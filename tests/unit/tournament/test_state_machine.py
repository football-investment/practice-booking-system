"""
Tournament State Machine Unit Tests
====================================

Covers every edge of the VALID_TRANSITIONS graph plus all guard conditions
in validate_status_transition().  All tests are DB-free (SimpleNamespace).

Transition graph (11 states, 22 allowed edges):

    NULL  ──────────────────────────────────────► DRAFT
    DRAFT ──────────────────────────────────────► SEEKING_INSTRUCTOR
          └─────────────────────────────────────► CANCELLED
    SEEKING_INSTRUCTOR ──────────────────────────► PENDING_INSTRUCTOR_ACCEPTANCE
                       └─────────────────────────► CANCELLED
    PENDING_INSTRUCTOR_ACCEPTANCE ───────────────► INSTRUCTOR_CONFIRMED
                                  ├──────────────► SEEKING_INSTRUCTOR
                                  └──────────────► CANCELLED
    INSTRUCTOR_CONFIRMED ────────────────────────► ENROLLMENT_OPEN
                         └───────────────────────► CANCELLED
    ENROLLMENT_OPEN ─────────────────────────────► ENROLLMENT_CLOSED
                    └────────────────────────────► CANCELLED
    ENROLLMENT_CLOSED ───────────────────────────► IN_PROGRESS
                      └──────────────────────────► CANCELLED
    IN_PROGRESS ─────────────────────────────────► COMPLETED
                ├────────────────────────────────► CANCELLED
                └────────────────────────────────► ENROLLMENT_CLOSED  ← rollback
    COMPLETED ───────────────────────────────────► REWARDS_DISTRIBUTED
              └──────────────────────────────────► ARCHIVED
    REWARDS_DISTRIBUTED ─────────────────────────► ARCHIVED
    CANCELLED ───────────────────────────────────► ARCHIVED
    ARCHIVED  (terminal — no outgoing edges)

Guards:
  SEEKING_INSTRUCTOR:      sessions non-empty, name/start_date/end_date set
  PENDING_INSTRUCTOR_ACCEPTANCE: master_instructor_id set
  ENROLLMENT_OPEN:         master_instructor_id, max_players, campus_id all set
  ENROLLMENT_CLOSED:       active enrollments >= min_players (2 if no type)
  IN_PROGRESS:             master_instructor_id, active enrollments >= min_players
  COMPLETED:               sessions non-empty
  REWARDS_DISTRIBUTED:     (no guard — pass-through)
  CANCELLED / ARCHIVED:    (no guard)

Special edge:
  IN_PROGRESS → ENROLLMENT_CLOSED  (admin rollback for stuck tournaments)
  Guard: same as plain ENROLLMENT_CLOSED guard (player count check).
  Potential issue: if enrollments were purged while IN_PROGRESS, rollback
  may be impossible — documented as SM-BUG-01.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.tournament.status_validator import (
    validate_status_transition,
    get_next_allowed_statuses,
    is_terminal_status,
    VALID_TRANSITIONS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tournament(**kwargs) -> SimpleNamespace:
    """
    Build a minimal tournament SimpleNamespace for testing.

    Defaults to a fully-configured tournament that would satisfy
    most guards.  Override via kwargs to introduce failures.
    """
    mock_session_obj = SimpleNamespace(
        match_format="HEAD_TO_HEAD",
        game_results=None,
    )
    defaults = {
        "id": 1,
        "name": "Test Tournament",
        "start_date": "2026-03-01",
        "end_date": "2026-03-02",
        "master_instructor_id": 42,
        "max_players": 16,
        "campus_id": 7,
        "tournament_type_id": None,   # skip DB query path
        "sessions": [mock_session_obj],
        "enrollments": [],
        "tournament_status": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _active_enrollments(n: int):
    """Return n fake active enrollment objects."""
    return [SimpleNamespace(is_active=True) for _ in range(n)]


def _inactive_enrollments(n: int):
    """Return n fake inactive enrollment objects."""
    return [SimpleNamespace(is_active=False) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# SM-01: NULL → DRAFT  (new tournament creation)
# ─────────────────────────────────────────────────────────────────────────────

class TestNullToDraftTransition:
    """NULL (current_status=None) must only allow → DRAFT."""

    def test_null_to_draft_ok(self):
        ok, err = validate_status_transition(None, "DRAFT", _tournament())
        assert ok is True
        assert err is None

    @pytest.mark.parametrize("target", [
        "SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE",
        "INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED",
        "IN_PROGRESS", "COMPLETED", "CANCELLED", "ARCHIVED",
    ])
    def test_null_to_non_draft_forbidden(self, target):
        ok, err = validate_status_transition(None, target, _tournament())
        assert ok is False
        assert "DRAFT" in err


# ─────────────────────────────────────────────────────────────────────────────
# SM-02: VALID_TRANSITIONS graph — allowed edges happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestAllowedEdgesHappyPath:
    """
    For every (source, target) in VALID_TRANSITIONS, verify the validator
    returns (True, None) when all guards are satisfied.

    Edges that require specific guard conditions use a custom tournament fixture.
    """

    def _tournament_for(self, source: str, target: str) -> SimpleNamespace:
        """Return a tournament pre-configured to satisfy the guard for (source→target)."""
        # For ENROLLMENT_CLOSED and IN_PROGRESS guards we need player count >= 2
        base = _tournament()
        if target in ("ENROLLMENT_CLOSED", "IN_PROGRESS"):
            base = _tournament(enrollments=_active_enrollments(4))
        if target == "SEEKING_INSTRUCTOR":
            # sessions + name/dates required
            base = _tournament(
                sessions=[SimpleNamespace()],
                name="Test",
                start_date="2026-03-01",
                end_date="2026-03-02",
            )
        if target == "COMPLETED":
            base = _tournament(sessions=[SimpleNamespace()])
        return base

    @pytest.mark.parametrize("source,targets", VALID_TRANSITIONS.items())
    def test_allowed_edge(self, source, targets):
        for target in targets:
            t = self._tournament_for(source, target)
            ok, err = validate_status_transition(source, target, t)
            assert ok is True, (
                f"Expected ({source} → {target}) to be allowed, got error: {err}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# SM-03: Forbidden cross-state jumps (parametrized)
# ─────────────────────────────────────────────────────────────────────────────

# Build the set of ALL (source, target) edges that are NOT in VALID_TRANSITIONS
_ALL_STATES = list(VALID_TRANSITIONS.keys())
_FORBIDDEN_EDGES = [
    (src, tgt)
    for src in _ALL_STATES
    for tgt in _ALL_STATES
    if tgt not in VALID_TRANSITIONS.get(src, [])
]


class TestForbiddenEdges:
    """Every (source → target) pair NOT in VALID_TRANSITIONS must be rejected."""

    @pytest.mark.parametrize("source,target", _FORBIDDEN_EDGES)
    def test_forbidden_edge_rejected(self, source, target):
        # Use a tournament that would satisfy ALL guards (to isolate graph rejection)
        t = _tournament(enrollments=_active_enrollments(4))
        ok, err = validate_status_transition(source, target, t)
        assert ok is False, (
            f"Expected ({source} → {target}) to be FORBIDDEN, but validator returned ok=True"
        )
        assert err is not None


# ─────────────────────────────────────────────────────────────────────────────
# SM-04: SEEKING_INSTRUCTOR guards
# ─────────────────────────────────────────────────────────────────────────────

class TestSeekingInstructorGuards:
    """DRAFT → SEEKING_INSTRUCTOR guard: sessions, name, start_date, end_date."""

    def test_all_guards_satisfied(self):
        t = _tournament(sessions=[SimpleNamespace()], name="T", start_date="2026-01-01", end_date="2026-01-02")
        ok, err = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)
        assert ok is True

    def test_no_sessions_blocked(self):
        t = _tournament(sessions=[])
        ok, err = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)
        assert ok is False
        assert "session" in err.lower()

    def test_sessions_none_blocked(self):
        t = _tournament(sessions=None)
        ok, err = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)
        assert ok is False

    def test_missing_name_blocked(self):
        t = _tournament(sessions=[SimpleNamespace()], name=None)
        ok, err = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)
        assert ok is False
        assert "name" in err.lower() or "information" in err.lower()

    def test_missing_start_date_blocked(self):
        t = _tournament(sessions=[SimpleNamespace()], name="T", start_date=None)
        ok, err = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)
        assert ok is False

    def test_missing_end_date_blocked(self):
        t = _tournament(sessions=[SimpleNamespace()], name="T", end_date=None)
        ok, err = validate_status_transition("DRAFT", "SEEKING_INSTRUCTOR", t)
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# SM-05: PENDING_INSTRUCTOR_ACCEPTANCE guards
# ─────────────────────────────────────────────────────────────────────────────

class TestPendingInstructorAcceptanceGuards:
    """SEEKING_INSTRUCTOR → PENDING_INSTRUCTOR_ACCEPTANCE guard: instructor assigned."""

    def test_instructor_assigned_ok(self):
        t = _tournament(master_instructor_id=99)
        ok, err = validate_status_transition("SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE", t)
        assert ok is True

    def test_no_instructor_blocked(self):
        t = _tournament(master_instructor_id=None)
        ok, err = validate_status_transition("SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE", t)
        assert ok is False
        assert "instructor" in err.lower()


# ─────────────────────────────────────────────────────────────────────────────
# SM-06: ENROLLMENT_OPEN guards (campus precondition isolated)
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrollmentOpenGuards:
    """INSTRUCTOR_CONFIRMED → ENROLLMENT_OPEN guards: instructor, max_players, campus_id."""

    def test_all_guards_satisfied(self):
        t = _tournament(master_instructor_id=1, max_players=16, campus_id=7)
        ok, err = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
        assert ok is True

    def test_no_instructor_blocked(self):
        t = _tournament(master_instructor_id=None, max_players=16, campus_id=7)
        ok, err = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
        assert ok is False
        assert "instructor" in err.lower()

    def test_no_max_players_blocked(self):
        t = _tournament(master_instructor_id=1, max_players=None, campus_id=7)
        ok, err = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
        assert ok is False
        assert "participant" in err.lower() or "max" in err.lower()

    # ── Campus precondition (isolated) ────────────────────────────────────────

    def test_campus_id_none_blocked(self):
        """CAMPUS PRECONDITION: campus_id=None must block ENROLLMENT_OPEN."""
        t = _tournament(master_instructor_id=1, max_players=16, campus_id=None)
        ok, err = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
        assert ok is False
        assert "campus" in err.lower()

    def test_campus_id_zero_blocked(self):
        """campus_id=0 is falsy — must be blocked (getattr returns 0 which is falsy)."""
        t = _tournament(master_instructor_id=1, max_players=16, campus_id=0)
        ok, err = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
        assert ok is False
        assert "campus" in err.lower()

    def test_campus_id_positive_passes(self):
        """Any positive campus_id must pass the campus guard."""
        for cid in [1, 7, 100, 9999]:
            t = _tournament(master_instructor_id=1, max_players=16, campus_id=cid)
            ok, _ = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
            assert ok is True, f"campus_id={cid} should pass"

    def test_campus_id_missing_attribute_blocked(self):
        """Tournament with no campus_id attribute at all must be blocked."""
        t = SimpleNamespace(
            id=1, name="T", start_date="2026-01-01", end_date="2026-01-02",
            master_instructor_id=1, max_players=16,
            tournament_type_id=None, sessions=[SimpleNamespace()], enrollments=[],
            # NO campus_id attribute
        )
        ok, err = validate_status_transition("INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", t)
        assert ok is False
        assert "campus" in err.lower()


# ─────────────────────────────────────────────────────────────────────────────
# SM-07: ENROLLMENT_CLOSED guards
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrollmentClosedGuards:
    """ENROLLMENT_OPEN → ENROLLMENT_CLOSED guard: active_enrollments >= min_players."""

    def test_enough_players_ok(self):
        t = _tournament(enrollments=_active_enrollments(4))
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is True

    def test_exactly_minimum_players_ok(self):
        """Exactly 2 players (default min) must pass."""
        t = _tournament(enrollments=_active_enrollments(2))
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is True

    def test_one_player_blocked(self):
        t = _tournament(enrollments=_active_enrollments(1))
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is False
        assert "minimum" in err.lower() or "participant" in err.lower()

    def test_zero_players_blocked(self):
        t = _tournament(enrollments=[])
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is False

    def test_inactive_enrollments_not_counted(self):
        """Only active enrollments count toward the minimum."""
        # 5 inactive + 1 active = 1 effective → below minimum of 2
        t = _tournament(enrollments=_inactive_enrollments(5) + _active_enrollments(1))
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is False

    def test_mixed_enrollments_with_enough_active_ok(self):
        # 3 inactive + 3 active = 3 effective ≥ 2
        t = _tournament(enrollments=_inactive_enrollments(3) + _active_enrollments(3))
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is True

    def test_no_enrollments_attribute_fallback(self):
        """If enrollments attribute missing, getattr returns [], count=0 → blocked."""
        t = SimpleNamespace(
            id=1, name="T", start_date="2026-01-01", end_date="2026-01-02",
            master_instructor_id=1, max_players=16, campus_id=7,
            tournament_type_id=None, sessions=[SimpleNamespace()],
            # NO enrollments attribute
        )
        ok, err = validate_status_transition("ENROLLMENT_OPEN", "ENROLLMENT_CLOSED", t)
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# SM-08: IN_PROGRESS guards
# ─────────────────────────────────────────────────────────────────────────────

class TestInProgressGuards:
    """ENROLLMENT_CLOSED → IN_PROGRESS guards: instructor + player count."""

    def test_all_guards_satisfied(self):
        t = _tournament(master_instructor_id=1, enrollments=_active_enrollments(4))
        ok, err = validate_status_transition("ENROLLMENT_CLOSED", "IN_PROGRESS", t)
        assert ok is True

    def test_no_instructor_blocked(self):
        t = _tournament(master_instructor_id=None, enrollments=_active_enrollments(4))
        ok, err = validate_status_transition("ENROLLMENT_CLOSED", "IN_PROGRESS", t)
        assert ok is False
        assert "instructor" in err.lower()

    def test_insufficient_players_blocked(self):
        t = _tournament(master_instructor_id=1, enrollments=_active_enrollments(1))
        ok, err = validate_status_transition("ENROLLMENT_CLOSED", "IN_PROGRESS", t)
        assert ok is False
        assert "minimum" in err.lower() or "participant" in err.lower()

    def test_exactly_minimum_ok(self):
        t = _tournament(master_instructor_id=1, enrollments=_active_enrollments(2))
        ok, err = validate_status_transition("ENROLLMENT_CLOSED", "IN_PROGRESS", t)
        assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# SM-09: COMPLETED guards
# ─────────────────────────────────────────────────────────────────────────────

class TestCompletedGuards:
    """IN_PROGRESS → COMPLETED guard: sessions non-empty."""

    def test_sessions_exist_ok(self):
        t = _tournament(sessions=[SimpleNamespace(), SimpleNamespace()])
        ok, err = validate_status_transition("IN_PROGRESS", "COMPLETED", t)
        assert ok is True

    def test_no_sessions_blocked(self):
        t = _tournament(sessions=[])
        ok, err = validate_status_transition("IN_PROGRESS", "COMPLETED", t)
        assert ok is False
        assert "session" in err.lower()

    def test_sessions_none_blocked(self):
        t = _tournament(sessions=None)
        ok, err = validate_status_transition("IN_PROGRESS", "COMPLETED", t)
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# SM-10: REWARDS_DISTRIBUTED guard (pass-through)
# ─────────────────────────────────────────────────────────────────────────────

class TestRewardsDistributedGuard:
    """COMPLETED → REWARDS_DISTRIBUTED has no active guard (pass-through)."""

    def test_pass_through_ok(self):
        t = _tournament()
        ok, err = validate_status_transition("COMPLETED", "REWARDS_DISTRIBUTED", t)
        assert ok is True

    def test_pass_through_even_without_sessions(self):
        """No sessions shouldn't block REWARDS_DISTRIBUTED (guard is a pass)."""
        t = _tournament(sessions=[])
        ok, err = validate_status_transition("COMPLETED", "REWARDS_DISTRIBUTED", t)
        assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# SM-11: Terminal states
# ─────────────────────────────────────────────────────────────────────────────

class TestTerminalStates:
    """ARCHIVED is the only terminal state; all others have at least one exit."""

    def test_archived_is_terminal(self):
        assert is_terminal_status("ARCHIVED") is True

    @pytest.mark.parametrize("status", [
        s for s in VALID_TRANSITIONS if s != "ARCHIVED"
    ])
    def test_non_archived_is_not_terminal(self, status):
        assert is_terminal_status(status) is False

    def test_archived_allows_no_transition(self):
        for target in _ALL_STATES:
            ok, _ = validate_status_transition("ARCHIVED", target, _tournament())
            assert ok is False, f"ARCHIVED → {target} should be forbidden"

    def test_unknown_status_treated_as_terminal(self):
        """Unrecognized current_status has no transitions → all targets rejected."""
        for target in _ALL_STATES:
            ok, _ = validate_status_transition("TOTALLY_UNKNOWN_STATUS", target, _tournament())
            assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# SM-12: IN_PROGRESS → ENROLLMENT_CLOSED rollback (isolated)
# ─────────────────────────────────────────────────────────────────────────────

class TestRollbackEdgeInProgressToEnrollmentClosed:
    """
    IN_PROGRESS → ENROLLMENT_CLOSED is an admin rollback edge for tournaments
    stuck with 0 sessions generated (e.g., OPS scenario failure mid-flight).

    The same guard as ENROLLMENT_OPEN→ENROLLMENT_CLOSED applies:
    active_enrollments >= min_players.

    SM-BUG-01: If a tournament stuck IN_PROGRESS has had its enrollments
    purged (active=0), this rollback is impossible via the normal API path.
    The admin would need to bypass the validator. Documented, not fixed here.
    """

    def test_rollback_allowed_when_players_present(self):
        """Admin can roll back to ENROLLMENT_CLOSED if players are still enrolled."""
        t = _tournament(enrollments=_active_enrollments(4))
        ok, err = validate_status_transition("IN_PROGRESS", "ENROLLMENT_CLOSED", t)
        assert ok is True, f"Rollback should be allowed with 4 players, got: {err}"

    def test_rollback_allowed_when_no_players(self):
        """
        SM-BUG-01 FIX VERIFIED: rollback to ENROLLMENT_CLOSED must be allowed
        even when active_enrollments == 0.

        The player-count guard was bifurcated (SM-BUG-01 fix) so that
        IN_PROGRESS → ENROLLMENT_CLOSED skips the count check entirely.
        Admin emergency rewind must not be gated on current player count.
        """
        t = _tournament(enrollments=[])
        ok, err = validate_status_transition("IN_PROGRESS", "ENROLLMENT_CLOSED", t)
        assert ok is True, (
            f"Rollback with 0 players should be ALLOWED after SM-BUG-01 fix, got: {err}"
        )

    def test_rollback_allowed_when_one_player(self):
        """Rollback with only 1 active player (below forward-path minimum) must pass."""
        t = _tournament(enrollments=_active_enrollments(1))
        ok, err = validate_status_transition("IN_PROGRESS", "ENROLLMENT_CLOSED", t)
        assert ok is True, (
            f"Rollback with 1 player should be ALLOWED after SM-BUG-01 fix, got: {err}"
        )

    def test_rollback_with_minimum_players_ok(self):
        """Exactly 2 active players → rollback allowed."""
        t = _tournament(enrollments=_active_enrollments(2))
        ok, err = validate_status_transition("IN_PROGRESS", "ENROLLMENT_CLOSED", t)
        assert ok is True

    def test_rollback_not_confused_with_in_progress_to_completed(self):
        """Sanity: IN_PROGRESS → COMPLETED is a different (normal) forward edge."""
        t = _tournament(sessions=[SimpleNamespace()])
        ok, _ = validate_status_transition("IN_PROGRESS", "COMPLETED", t)
        assert ok is True

    def test_rollback_is_in_allowed_graph(self):
        """Verify the rollback edge is explicitly encoded in VALID_TRANSITIONS."""
        assert "ENROLLMENT_CLOSED" in VALID_TRANSITIONS["IN_PROGRESS"], (
            "IN_PROGRESS → ENROLLMENT_CLOSED must be in VALID_TRANSITIONS "
            "(admin rollback design decision)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SM-13: get_next_allowed_statuses helper
# ─────────────────────────────────────────────────────────────────────────────

class TestGetNextAllowedStatuses:
    """get_next_allowed_statuses() must mirror VALID_TRANSITIONS exactly."""

    def test_null_returns_draft(self):
        assert get_next_allowed_statuses(None) == ["DRAFT"]

    @pytest.mark.parametrize("status,expected", VALID_TRANSITIONS.items())
    def test_matches_valid_transitions(self, status, expected):
        result = get_next_allowed_statuses(status)
        assert result == expected, (
            f"get_next_allowed_statuses({status!r}) returned {result}, "
            f"expected {expected}"
        )

    def test_unknown_status_returns_empty(self):
        assert get_next_allowed_statuses("TOTALLY_UNKNOWN") == []

    def test_archived_returns_empty(self):
        assert get_next_allowed_statuses("ARCHIVED") == []


# ─────────────────────────────────────────────────────────────────────────────
# SM-14: CANCELLED → ARCHIVED (and no other target)
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelledTransitions:
    """CANCELLED can only go to ARCHIVED."""

    def test_cancelled_to_archived_ok(self):
        ok, err = validate_status_transition("CANCELLED", "ARCHIVED", _tournament())
        assert ok is True

    @pytest.mark.parametrize("target", [
        "DRAFT", "SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE",
        "INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED",
        "IN_PROGRESS", "COMPLETED", "REWARDS_DISTRIBUTED", "CANCELLED",
    ])
    def test_cancelled_to_non_archived_forbidden(self, target):
        ok, err = validate_status_transition("CANCELLED", target, _tournament())
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# SM-15: CANCELLATION is always allowed (from any non-terminal state)
# ─────────────────────────────────────────────────────────────────────────────

class TestCancellationAlwaysReachable:
    """
    Every non-terminal, non-cancelled state must have CANCELLED as a valid target.

    This is a business invariant: admin can cancel any in-progress tournament.
    Exceptions: COMPLETED, REWARDS_DISTRIBUTED, CANCELLED, ARCHIVED do NOT allow
    CANCELLED transition (tournament is past the point of cancellation).
    """

    STATES_THAT_CAN_CANCEL = [
        "DRAFT", "SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE",
        "INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED",
        "IN_PROGRESS",
    ]
    STATES_THAT_CANNOT_CANCEL = [
        "COMPLETED", "REWARDS_DISTRIBUTED", "CANCELLED", "ARCHIVED",
    ]

    @pytest.mark.parametrize("source", STATES_THAT_CAN_CANCEL)
    def test_can_cancel_from(self, source):
        assert "CANCELLED" in VALID_TRANSITIONS[source], (
            f"CANCELLED must be reachable from {source}"
        )

    @pytest.mark.parametrize("source", STATES_THAT_CANNOT_CANCEL)
    def test_cannot_cancel_from(self, source):
        assert "CANCELLED" not in VALID_TRANSITIONS[source], (
            f"CANCELLED must NOT be reachable from {source}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SM-16: Graph completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphCompleteness:
    """Structural checks on VALID_TRANSITIONS — guards against accidental graph mutations."""

    EXPECTED_STATES = {
        "DRAFT", "SEEKING_INSTRUCTOR", "PENDING_INSTRUCTOR_ACCEPTANCE",
        "INSTRUCTOR_CONFIRMED", "ENROLLMENT_OPEN", "ENROLLMENT_CLOSED",
        "IN_PROGRESS", "COMPLETED", "REWARDS_DISTRIBUTED",
        "CANCELLED", "ARCHIVED",
    }

    def test_all_expected_states_present(self):
        assert set(VALID_TRANSITIONS.keys()) == self.EXPECTED_STATES

    def test_archived_is_only_terminal(self):
        terminals = [s for s in VALID_TRANSITIONS if VALID_TRANSITIONS[s] == []]
        assert terminals == ["ARCHIVED"], (
            f"Only ARCHIVED should be terminal, found: {terminals}"
        )

    def test_all_targets_are_known_states(self):
        """Every target in the graph must itself be a key in the graph."""
        for source, targets in VALID_TRANSITIONS.items():
            for target in targets:
                assert target in VALID_TRANSITIONS, (
                    f"Target {target!r} (from {source}) is not in VALID_TRANSITIONS"
                )

    def test_total_allowed_edge_count(self):
        """Verify the exact number of allowed edges to catch accidental additions.

        Manual count:
          DRAFT(2) + SEEKING_INSTRUCTOR(2) + PENDING_INSTRUCTOR_ACCEPTANCE(3)
          + INSTRUCTOR_CONFIRMED(2) + ENROLLMENT_OPEN(2) + ENROLLMENT_CLOSED(2)
          + IN_PROGRESS(3) + COMPLETED(2) + REWARDS_DISTRIBUTED(1)
          + CANCELLED(1) + ARCHIVED(0) = 20
        """
        total = sum(len(v) for v in VALID_TRANSITIONS.values())
        assert total == 20, (
            f"Expected 20 allowed edges in VALID_TRANSITIONS, found {total}. "
            "Update this test if a new edge is intentionally added."
        )
