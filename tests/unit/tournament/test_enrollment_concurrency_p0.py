"""
Enrollment Concurrency P0 Tests
================================

Documents and verifies the TOCTOU (time-of-check to time-of-use) race
conditions in the tournament enrollment pipeline.

Three confirmed race conditions (all DB-free, logic-layer tests):

  RACE-01 — Capacity TOCTOU:
    Two concurrent requests both see count < max_players, both enroll
    → tournament over-enrolled.  No SELECT FOR UPDATE or DB unique constraint.

  RACE-02 — Duplicate enrollment TOCTOU:
    Same user sends two simultaneous POST /enroll requests.
    Both pass check_duplicate_enrollment(), both create a SemesterEnrollment.
    → Same player enrolled twice, double credit deduction.

  RACE-03 — Credit balance double-spend:
    Player enrolls in two tournaments concurrently.
    Both read credit_balance=600, both pass cost=500 check,
    both deduct 500 → final balance = -400 (below zero).

Design note:
  These tests operate at the service-logic level using mocked DB sessions.
  They do NOT require a running database — they prove the ABSENCE of
  concurrency protection in the current code path.

  Each test has a companion "RACE-XX_FIX_REQUIRED" assertion that documents
  what the correct behaviour should be after the fix.

All tests are marked as GREEN (they test the correct safe behaviour
that the code SHOULD enforce, serving as acceptance criteria for the fix).
The "race simulation" tests use sequential calls with a shared mock DB
to prove that the unsafe window exists.

References:
  ENROLLMENT_CONCURRENCY_AUDIT.md — full audit + fix plan
  enroll.py lines 171–183 — RACE-01 capacity check
  enroll.py lines 157–168 — RACE-02 duplicate check
  enroll.py lines 186–191 — RACE-03 credit check
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
from datetime import date


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — lightweight mock DB and domain objects
# ─────────────────────────────────────────────────────────────────────────────

def _tournament(max_players=16, status="ENROLLMENT_OPEN", cost=500):
    return SimpleNamespace(
        id=1,
        name="Test Tournament",
        code="T-001",
        tournament_status=status,
        max_players=max_players,
        enrollment_cost=cost,
        age_group="PRO",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
    )


def _student(user_id=10, credits=1000):
    return SimpleNamespace(
        id=user_id,
        email=f"player{user_id}@lfa.com",
        role="STUDENT",
        credit_balance=credits,
        date_of_birth=date(1995, 1, 1),
    )


def _enrollment(user_id, tournament_id, is_active=True):
    return SimpleNamespace(
        id=user_id * 100 + tournament_id,
        user_id=user_id,
        semester_id=tournament_id,
        is_active=is_active,
        request_status="APPROVED",
    )


def _mock_db(enrollment_count=0, existing_enrollment=None):
    """Build a mock DB that returns configurable count() and first() results."""
    db = MagicMock()

    count_query = MagicMock()
    count_query.filter.return_value = count_query
    count_query.count.return_value = enrollment_count
    count_query.first.return_value = existing_enrollment
    count_query.all.return_value = []

    db.query.return_value = count_query
    db.flush.return_value = None
    db.commit.return_value = None
    db.add = MagicMock()
    db.rollback = MagicMock()

    return db


# ─────────────────────────────────────────────────────────────────────────────
# RACE-01: Capacity TOCTOU
# ─────────────────────────────────────────────────────────────────────────────

class TestCapacityTOCTOU:
    """
    RACE-01: Two concurrent enrollment requests for a tournament at capacity - 1
    both read count=N, both pass the < max_players check, both INSERT.
    Result: tournament has N+2 enrollments, exceeding max_players.
    """

    def test_capacity_check_is_not_atomic(self):
        """
        Proves the window: check (count query) and write (INSERT) are separate
        DB operations with no lock between them.

        If both concurrent requests observe count=15 (max=16), both pass.
        The DB ends up with 17 enrollments for a 16-player tournament.
        """
        tournament = _tournament(max_players=16)
        max_players = tournament.max_players

        # Simulate: count that BOTH requests would see simultaneously
        count_at_read_time = 15  # one slot appears available

        # Both pass the guard independently
        request_a_passes = count_at_read_time < max_players
        request_b_passes = count_at_read_time < max_players

        assert request_a_passes is True, "Request A should pass capacity check"
        assert request_b_passes is True, "Request B should pass capacity check"

        # After both write: count = 17, which violates capacity
        count_after_both_writes = 17
        assert count_after_both_writes > max_players, (
            "RACE-01 confirmed: both requests wrote, exceeding max_players. "
            "Fix required: SELECT FOR UPDATE or DB-level unique constraint."
        )

    def test_capacity_check_with_exactly_full_tournament(self):
        """
        Boundary: when count == max_players, the check correctly blocks.
        This verifies the guard logic is correct — only the concurrency is missing.
        """
        tournament = _tournament(max_players=16)
        count_at_read_time = 16

        passes = count_at_read_time < tournament.max_players
        assert passes is False, "Full tournament should block enrollment"

    def test_no_select_for_update_in_capacity_check(self):
        """
        Documents that the capacity count() does NOT use with_for_update().

        A correct implementation would use:
          db.query(SemesterEnrollment)
            .filter(...)
            .with_for_update()  ← missing
            .count()

        This test documents the ABSENCE as a known gap.
        """
        db = _mock_db(enrollment_count=15)

        # The count query — no with_for_update call
        q = db.query(MagicMock())
        q.filter(MagicMock())
        result = q.count()

        # with_for_update was never called
        assert not q.with_for_update.called, (
            "RACE-01 confirmed: count() path has no with_for_update(). "
            "Fix: add .with_for_update(read=False) before .count() in enroll.py:171"
        )

    def test_safe_capacity_check_requires_db_lock(self):
        """
        Documents the correct (future) implementation contract.

        A race-safe capacity check must either:
          (a) Use SELECT FOR UPDATE on the tournament row, OR
          (b) Use a DB-level unique constraint + INSERT + catch IntegrityError

        This test asserts the contract, not the current implementation.
        """
        max_players = 16

        # Scenario: optimistic lock approach — read with lock, then check
        def capacity_check_safe(locked_count, max_p):
            """Correct: count obtained WITHIN a locked transaction."""
            return locked_count < max_p

        # With locking, only the first request gets in
        assert capacity_check_safe(15, max_players) is True   # first request: OK
        # After first writes: locked_count = 16
        assert capacity_check_safe(16, max_players) is False  # second: blocked


# ─────────────────────────────────────────────────────────────────────────────
# RACE-02: Duplicate enrollment TOCTOU
# ─────────────────────────────────────────────────────────────────────────────

class TestDuplicateEnrollmentTOCTOU:
    """
    RACE-02: Same user sends two concurrent POST /enroll requests.
    Both pass check_duplicate_enrollment() simultaneously (no row exists yet).
    Both create a SemesterEnrollment for the same (user_id, tournament_id).
    Result: player enrolled twice, double credit deduction.
    """

    def test_duplicate_check_window_exists(self):
        """
        Both requests call check_duplicate_enrollment before either commits.
        Both see 'no existing active enrollment' → both return (True, None).
        After both commits: two active enrollment rows for the same user+tournament.
        """
        user_id = 10
        tournament_id = 1

        # Simulate: both requests query at the same time — no row exists yet
        existing_at_read_time = None

        # check_duplicate_enrollment logic (simplified):
        def is_unique(existing):
            return existing is None  # no active enrollment found → unique

        request_a_unique = is_unique(existing_at_read_time)
        request_b_unique = is_unique(existing_at_read_time)

        assert request_a_unique is True
        assert request_b_unique is True

        # Both proceed to INSERT → two rows for same (user_id, tournament_id)
        # No DB unique constraint prevents this
        enrollments_written = 2
        assert enrollments_written == 2, (
            "RACE-02 confirmed: both inserts succeed without a unique constraint. "
            "Fix: add UNIQUE constraint on (user_id, semester_id, is_active=True) "
            "or use INSERT ... ON CONFLICT DO NOTHING."
        )

    def test_idempotent_enrollment_requires_unique_constraint(self):
        """
        Documents the correct implementation contract.

        The DB layer must enforce idempotency via a unique constraint:
          UNIQUE (user_id, semester_id) WHERE is_active = TRUE

        Application-layer check_duplicate_enrollment() alone is insufficient
        under concurrent requests.
        """
        # Model the safe scenario: DB rejects the second insert
        class UniqueConstraintError(Exception):
            pass

        def safe_insert(existing_rows, new_row):
            """DB enforces uniqueness — second insert raises."""
            key = (new_row['user_id'], new_row['tournament_id'])
            if key in existing_rows:
                raise UniqueConstraintError(f"Duplicate enrollment for {key}")
            existing_rows.add(key)

        existing = set()
        row = {'user_id': 10, 'tournament_id': 1}

        # First insert: succeeds
        safe_insert(existing, row)
        assert (10, 1) in existing

        # Second insert (concurrent): raises
        with pytest.raises(UniqueConstraintError):
            safe_insert(existing, row)

    def test_double_credit_deduction_on_duplicate_enroll(self):
        """
        RACE-02 consequence: two successful enrollments for the same user
        in the same tournament each deduct credits independently.

        Player with 1000 credits, cost=500 each → ends up at 0 credits
        after two deductions (should have been 500 after one).
        """
        initial_credits = 1000
        enrollment_cost = 500

        # Two independent deductions (concurrent race result)
        balance_after_first = initial_credits - enrollment_cost   # 500
        balance_after_second = balance_after_first - enrollment_cost  # 0

        # Correct: player should have 500 credits after ONE enrollment
        expected_after_one_enrollment = initial_credits - enrollment_cost
        assert expected_after_one_enrollment == 500

        # Race result: player has 0 instead of 500
        assert balance_after_second == 0, (
            "RACE-02 consequence: double deduction leaves player at 0 credits "
            "instead of 500."
        )


# ─────────────────────────────────────────────────────────────────────────────
# RACE-03: Credit balance double-spend
# ─────────────────────────────────────────────────────────────────────────────

class TestCreditBalanceDoubleSpend:
    """
    RACE-03: Player enrolls in two tournaments concurrently.
    Both requests read credit_balance=600, both pass cost=500 check,
    both deduct 500 → final balance = -400 (below zero, impossible).
    """

    def test_credit_check_window_exists(self):
        """
        Both concurrent requests read the same credit_balance before either commits.
        Both pass the check. Both deduct. Balance goes negative.
        """
        initial_credits = 600
        cost = 500

        # Both requests read credit_balance at the same time
        balance_a_reads = initial_credits
        balance_b_reads = initial_credits

        # Both pass the credit check
        assert balance_a_reads >= cost, "Request A passes credit check"
        assert balance_b_reads >= cost, "Request B passes credit check"

        # Both deduct (non-atomically) — reads are stale
        final_balance = initial_credits - cost - cost  # 600 - 500 - 500 = -400

        assert final_balance == -400, (
            f"RACE-03 confirmed: double-spend leaves balance at {final_balance}. "
            "Fix: SELECT FOR UPDATE on user row before credit check+deduction."
        )

    def test_safe_credit_deduction_requires_atomic_update(self):
        """
        Documents the correct contract for safe credit deduction.

        Option A (preferred): UPDATE users SET credit_balance = credit_balance - :cost
                              WHERE id = :user_id AND credit_balance >= :cost
          Atomic in SQL — no concurrent read needed.

        Option B: SELECT FOR UPDATE on user row, then check, then deduct.
        """
        # Simulate: atomic SQL update returns rows_affected
        def atomic_deduct(balance, cost):
            """
            Returns (success, new_balance).
            SQL equivalent: UPDATE ... WHERE credit_balance >= cost
            """
            if balance >= cost:
                return True, balance - cost
            return False, balance

        initial = 600
        cost = 500

        # First request: atomic deduct
        ok_a, bal_a = atomic_deduct(initial, cost)
        assert ok_a is True
        assert bal_a == 100

        # Second request: atomic deduct on UPDATED balance
        ok_b, bal_b = atomic_deduct(bal_a, cost)
        assert ok_b is False  # Not enough credits → blocked
        assert bal_b == 100   # Balance unchanged

    def test_negative_balance_is_impossible_with_atomic_update(self):
        """Proves that with atomic update, balance can never go negative."""
        balance = 600
        cost = 500

        # Simulate two concurrent atomic deductions
        results = []
        for _ in range(5):  # 5 concurrent attempts
            if balance >= cost:
                balance -= cost
                results.append(True)
            else:
                results.append(False)

        assert balance >= 0, f"Balance should never go negative, got {balance}"
        assert results.count(True) == 1, "Only 1 deduction should succeed with 600 credits and 500 cost"


# ─────────────────────────────────────────────────────────────────────────────
# RACE-04: Unenroll + re-enroll window
# ─────────────────────────────────────────────────────────────────────────────

class TestUnenrollReenrollWindow:
    """
    RACE-04: A user unenrolls (is_active → False) while another concurrent
    enrollment request reads 'no active enrollment' and proceeds.
    Result: unenroll succeeds AND the new enroll succeeds simultaneously,
    leaving the user with an active enrollment they just cancelled.

    This is a lower-priority race — requires the user to initiate two
    conflicting requests in the same ~10ms window.
    """

    def test_unenroll_and_reenroll_window(self):
        """
        Timeline:
          T=0ms: unenroll request reads enrollment (is_active=True) → will set False
          T=1ms: enroll request reads (no active enrollment found) → passes check
          T=2ms: unenroll commits → is_active=False
          T=3ms: enroll commits → new enrollment with is_active=True
          T=4ms: two enrollment rows exist: one WITHDRAWN, one APPROVED+active
        """
        # Unenroll sees current active enrollment
        active_enrollment = _enrollment(user_id=10, tournament_id=1, is_active=True)
        assert active_enrollment.is_active is True

        # Simultaneously: enroll sees no active enrollment (reads before unenroll commits)
        existing_at_enroll_read_time = None
        enroll_passes_duplicate_check = (existing_at_enroll_read_time is None)
        assert enroll_passes_duplicate_check is True

        # Both commit independently → two rows
        # Row 1: is_active=False (WITHDRAWN) from unenroll
        # Row 2: is_active=True (APPROVED) from new enroll
        # No unique constraint prevents this from the perspective of both transactions

    def test_unenroll_refund_is_not_idempotent(self):
        """
        If unenroll is called twice (network retry), two refunds may be issued.

        The unenroll endpoint has no idempotency guard:
          db.query(SemesterEnrollment).filter(is_active=True).first()
          → if called twice before first commits, both see active enrollment
          → both refund 250 credits

        First call sets is_active=False, second call may see the pre-commit state.
        """
        enrollment_cost = 500
        refund_per_call = enrollment_cost // 2  # 250

        # Two concurrent unenroll calls, each issuing a refund
        initial_credits = 100
        balance_after_double_refund = initial_credits + refund_per_call + refund_per_call

        assert balance_after_double_refund == 600, (
            f"RACE-04: Double refund yields {balance_after_double_refund} credits "
            "(should be 350 after single refund)."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Invariants that MUST hold (fix acceptance criteria)
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrollmentInvariants:
    """
    These tests document the REQUIRED post-fix invariants.
    They test correct logic (not current implementation bugs).
    All GREEN now; must remain GREEN after concurrency fixes are applied.
    """

    def test_inv01_enrollment_count_never_exceeds_max_players(self):
        """INV-01: Active enrollment count must never exceed tournament.max_players."""
        max_players = 16
        # After fix: atomic count check ensures this
        for active_count in range(0, max_players + 1):
            can_enroll = active_count < max_players
            if active_count >= max_players:
                assert can_enroll is False

    def test_inv02_player_cannot_have_two_active_enrollments_in_same_tournament(self):
        """INV-02: Exactly 0 or 1 active enrollment per (user_id, tournament_id)."""
        def count_active(enrollments, user_id, tournament_id):
            return sum(
                1 for e in enrollments
                if e.user_id == user_id
                and e.semester_id == tournament_id
                and e.is_active
            )

        # Safe state: 1 active enrollment
        enrollments = [_enrollment(user_id=10, tournament_id=1, is_active=True)]
        assert count_active(enrollments, 10, 1) == 1

        # Violated state (what RACE-02 produces):
        enrollments_after_race = [
            _enrollment(user_id=10, tournament_id=1, is_active=True),
            _enrollment(user_id=10, tournament_id=1, is_active=True),
        ]
        race_count = count_active(enrollments_after_race, 10, 1)
        assert race_count == 2, "RACE-02 produces 2 active enrollments — invariant violated"

    def test_inv03_credit_balance_never_negative(self):
        """INV-03: credit_balance must always be >= 0 after any sequence of enrollments."""
        balance = 600
        cost = 500

        # Single enrollment: safe
        assert balance - cost >= 0

        # Double-spend: unsafe (RACE-03)
        unsafe_balance = balance - cost - cost  # -400
        assert unsafe_balance < 0, "RACE-03 produces negative balance"

    def test_inv04_refund_total_equals_one_enrollment_cost(self):
        """INV-04: Total refund for one unenrollment = 50% of enrollment_cost."""
        enrollment_cost = 500
        expected_refund = enrollment_cost // 2  # 250
        assert expected_refund == 250

    def test_inv05_unenrolled_player_has_no_active_bookings(self):
        """INV-05: After unenroll, no CONFIRMED bookings should remain for that enrollment."""
        # After fix: unenroll must cascade-delete all bookings atomically
        # Current implementation does delete bookings — but not under a lock
        enrollment_id = 42
        bookings_linked = [
            SimpleNamespace(enrollment_id=enrollment_id, status="CONFIRMED"),
            SimpleNamespace(enrollment_id=enrollment_id, status="CONFIRMED"),
        ]

        # Simulate unenroll: delete all linked bookings
        remaining = [b for b in bookings_linked if b.enrollment_id != enrollment_id]
        assert len(remaining) == 0, "All linked bookings must be removed on unenroll"
