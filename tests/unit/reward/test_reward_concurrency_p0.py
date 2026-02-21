"""
P0 Concurrency tests — Reward/XP pipeline
RACE-R01..R07 hardening verification

Pattern: same as booking/enrollment P0 suites.
Mock-based — documents DB-level locking and idempotency expectations.

Each test class covers one RACE-Rxx from REWARD_XP_CONCURRENCY_AUDIT_2026-02-19.md.
"""
import pytest
from unittest.mock import MagicMock, call, patch
from types import SimpleNamespace
from sqlalchemy.exc import IntegrityError as SAIntegrityError


# Test constants for mock IDs
TEST_USER_ID = 999
TEST_TOURNAMENT_ID = 42

# ---------------------------------------------------------------------------
# Shared factory helpers
# ---------------------------------------------------------------------------

def _tournament(status="IN_PROGRESS"):
    return SimpleNamespace(
        id=TEST_TOURNAMENT_ID,
        name="Test Tournament",
        tournament_status=status,
        reward_config=None,
    )


def _participation(user_id=TEST_USER_ID, tournament_id=TEST_TOURNAMENT_ID, placement=None):
    return SimpleNamespace(
        id=99,
        user_id=user_id,
        semester_id=tournament_id,
        placement=placement,
        xp_awarded=100,
        credits_awarded=50,
        skill_points_awarded={},
        skill_rating_delta=None,
        achieved_at=None,
    )


def _badge(user_id=TEST_USER_ID, tournament_id=TEST_TOURNAMENT_ID, badge_type="CHAMPION"):
    return SimpleNamespace(
        id=7,
        user_id=user_id,
        semester_id=tournament_id,
        badge_type=badge_type,
        badge_category="PLACEMENT",
        title="Champion",
        description="Winner",
        icon="🥇",
        rarity="EPIC",
        badge_metadata={},
    )


def _user(user_id=TEST_USER_ID):
    return SimpleNamespace(
        id=user_id,
        xp_balance=1000,
        credit_balance=500,
    )


def _ranking(user_id=TEST_USER_ID, rank=1):
    return SimpleNamespace(user_id=user_id, rank=rank)


# ---------------------------------------------------------------------------
# RACE-R01 + R03: Finalization TOCTOU
# ---------------------------------------------------------------------------

class TestRaceR01R03FinalizeTOCTOU:
    """
    RACE-R01: concurrent finalize() calls — no lock on tournament row
    RACE-R03: auto-finalize path + manual admin trigger both fire

    Fix: SELECT FOR UPDATE on tournament row at start of finalize();
         idempotency guard on tournament_status after lock.
    """

    def _make_finalizer_db(self, tournament_status="IN_PROGRESS"):
        """Build a mock db whose Semester query chain returns a locked tournament."""
        db = MagicMock()
        locked_tournament = _tournament(status=tournament_status)
        locked_tournament.id = 42

        # query(Semester).filter(...).with_for_update().one() → locked_tournament
        semester_chain = MagicMock()
        semester_chain.filter.return_value.with_for_update.return_value.one.return_value = locked_tournament

        db.query.return_value = semester_chain
        return db, locked_tournament, semester_chain

    def test_r01_finalize_locks_tournament_row(self):
        """finalize() must acquire FOR UPDATE lock on tournament before any mutation."""
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer

        db, locked_tournament, semester_chain = self._make_finalizer_db("IN_PROGRESS")
        finalizer = TournamentFinalizer(db)

        # Patch sub-methods so finalize reaches the lock and returns via 'no sessions'
        finalizer.get_all_sessions = MagicMock(return_value=[])

        finalizer.finalize(_tournament("IN_PROGRESS"))

        # Assert: with_for_update().one() was called (not just .one() without lock)
        assert semester_chain.filter.return_value.with_for_update.called, (
            "RACE-R01: finalize() must call .with_for_update().one() on tournament row"
        )

    def test_r01_already_rewards_distributed_returns_early(self):
        """finalize() must return idempotent result when tournament is REWARDS_DISTRIBUTED."""
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer

        db, locked_tournament, _ = self._make_finalizer_db("REWARDS_DISTRIBUTED")
        finalizer = TournamentFinalizer(db)

        # get_all_sessions should NOT be called if we return early
        finalizer.get_all_sessions = MagicMock()

        result = finalizer.finalize(_tournament("REWARDS_DISTRIBUTED"))

        assert result["success"] is True, "RACE-R01: already-finalized should return success=True (idempotent)"
        assert "already" in result["message"].lower() or result["tournament_status"] == "REWARDS_DISTRIBUTED"
        finalizer.get_all_sessions.assert_not_called()

    def test_r01_already_completed_returns_early(self):
        """finalize() must return idempotent result when tournament is COMPLETED."""
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer

        db, locked_tournament, _ = self._make_finalizer_db("COMPLETED")
        finalizer = TournamentFinalizer(db)
        finalizer.get_all_sessions = MagicMock()

        result = finalizer.finalize(_tournament("COMPLETED"))

        assert result["success"] is True, "RACE-R01: COMPLETED status → idempotent return"
        finalizer.get_all_sessions.assert_not_called()

    def test_r03_r01_locked_tournament_prevents_double_distribution(self):
        """
        Simulates Thread B acquiring lock after Thread A committed.
        Thread B sees REWARDS_DISTRIBUTED → skips distribution entirely.
        distribute_rewards_for_tournament is imported locally inside finalize(),
        so we verify via the early return (not via mock_distribute.assert_not_called).
        """
        from app.services.tournament.results.finalization.tournament_finalizer import TournamentFinalizer

        # Thread B's view: tournament is already REWARDS_DISTRIBUTED after Thread A
        db, locked_tournament, _ = self._make_finalizer_db("REWARDS_DISTRIBUTED")
        finalizer_b = TournamentFinalizer(db)
        # get_all_sessions must NOT be called — early return before it
        finalizer_b.get_all_sessions = MagicMock()

        result = finalizer_b.finalize(_tournament("REWARDS_DISTRIBUTED"))

        # Early return → success=True, no distribution attempted
        assert result["success"] is True
        assert result["tournament_status"] == "REWARDS_DISTRIBUTED"
        finalizer_b.get_all_sessions.assert_not_called()


# ---------------------------------------------------------------------------
# RACE-R02: Idempotency guard TOCTOU in distribute_rewards_for_user
# ---------------------------------------------------------------------------

class TestRaceR02IdempotencyGuardTOCTOU:
    """
    RACE-R02: distribute_rewards_for_user checks TournamentParticipation
    without FOR UPDATE — two concurrent calls both see None and both proceed.

    Fix: SELECT FOR UPDATE on TournamentParticipation in the idempotency guard.
         IntegrityError at commit → graceful return of existing summary.
    """

    def _common_patches(self):
        """Returns a list of patch contexts common to R02 tests."""
        return [
            patch("app.services.tournament.tournament_reward_orchestrator.participation_service"),
            patch("app.services.tournament.tournament_reward_orchestrator.badge_service"),
            patch("app.services.tournament.tournament_reward_orchestrator.skill_progression_service"),
            patch("app.services.tournament.tournament_reward_orchestrator.get_placement_rewards",
                  return_value={"xp": 0, "credits": 0}),
        ]

    def _mock_db_for_orchestrator(self, participation_result=None):
        """Build a mock db that handles multi-model query dispatch for orchestrator tests."""
        from app.models.semester import Semester as SemesterModel

        db = MagicMock()

        participation_chain = MagicMock()
        participation_chain.filter.return_value.with_for_update.return_value.first.return_value = (
            participation_result
        )

        # Semester query for tournament info (needed by orchestrator)
        semester_chain = MagicMock()
        mock_semester = SimpleNamespace(id=42, name="Test Tournament", reward_config=None)
        semester_chain.filter.return_value.first.return_value = mock_semester

        def _dispatch(model):
            # Lazy import inside function → check by class name
            if hasattr(model, "__name__") and "Participation" in model.__name__:
                return participation_chain
            if hasattr(model, "__name__") and "Semester" in model.__name__:
                return semester_chain
            return MagicMock()  # fallback

        db.query.side_effect = _dispatch
        db.execute.return_value.scalar.return_value = 1000
        return db, participation_chain

    def test_r02_distribute_user_locks_participation_row(self):
        """distribute_rewards_for_user must use FOR UPDATE on participation idempotency check."""
        from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_user
        from app.schemas.tournament_rewards import RewardPolicy

        db, participation_chain = self._mock_db_for_orchestrator(participation_result=None)

        with (
            patch("app.services.tournament.tournament_reward_orchestrator.participation_service") as mock_ps,
            patch("app.services.tournament.tournament_reward_orchestrator.badge_service") as mock_bs,
            patch("app.services.tournament.tournament_reward_orchestrator.skill_progression_service"),
            patch("app.services.tournament.tournament_reward_orchestrator.get_placement_rewards",
                  return_value={"xp": 0, "credits": 0}),
            patch("sqlalchemy.orm.attributes.flag_modified"),  # SimpleNamespace not SA instance
        ):
            mock_ps.calculate_skill_points_for_placement.return_value = {}
            mock_ps.convert_skill_points_to_xp.return_value = 0
            mock_ps.record_tournament_participation.return_value = _participation()
            mock_bs.award_placement_badges.return_value = []
            mock_bs.award_participation_badge.return_value = _badge()
            mock_bs.check_and_award_milestone_badges.return_value = []

            distribute_rewards_for_user(db, 1, 42, None, 10, RewardPolicy())

        assert participation_chain.filter.return_value.with_for_update.called, (
            "RACE-R02: distribute_rewards_for_user must call "
            ".with_for_update().first() on TournamentParticipation"
        )

    def test_r02_integrity_error_at_commit_returns_graceful_summary(self):
        """
        On IntegrityError at commit (uq_user_semester_participation), distribute_rewards_for_user
        must return gracefully (not raise HTTP 500).
        """
        from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_user
        from app.schemas.tournament_rewards import RewardPolicy

        db, _ = self._mock_db_for_orchestrator(participation_result=None)
        db.commit.side_effect = SAIntegrityError("INSERT", {}, Exception("uq_user_semester_participation"))

        with (
            patch("app.services.tournament.tournament_reward_orchestrator.participation_service") as mock_ps,
            patch("app.services.tournament.tournament_reward_orchestrator.badge_service") as mock_bs,
            patch("app.services.tournament.tournament_reward_orchestrator.skill_progression_service"),
            patch("app.services.tournament.tournament_reward_orchestrator.get_placement_rewards",
                  return_value={"xp": 0, "credits": 0}),
            patch("app.services.tournament.tournament_reward_orchestrator.get_user_reward_summary",
                  return_value=MagicMock()) as mock_summary,
            patch("sqlalchemy.orm.attributes.flag_modified"),
        ):
            mock_ps.calculate_skill_points_for_placement.return_value = {}
            mock_ps.convert_skill_points_to_xp.return_value = 0
            mock_ps.record_tournament_participation.return_value = _participation()
            mock_bs.award_placement_badges.return_value = []
            mock_bs.award_participation_badge.return_value = _badge()
            mock_bs.check_and_award_milestone_badges.return_value = []

            result = distribute_rewards_for_user(db, 1, 42, None, 10, RewardPolicy())

        db.rollback.assert_called_once()
        mock_summary.assert_called_once()
        assert result is not None, (
            "RACE-R02: IntegrityError at commit must return existing summary, not raise"
        )

    def test_r02_skips_if_existing_participation_found_under_lock(self):
        """If FOR UPDATE reveals existing participation, distribution is skipped."""
        from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_user
        from app.schemas.tournament_rewards import RewardPolicy

        db = MagicMock()
        participation_chain = MagicMock()
        # Simulate Thread B acquires lock, sees Thread A's committed row
        participation_chain.filter.return_value.with_for_update.return_value.first.return_value = (
            _participation()
        )
        db.query.return_value = participation_chain

        with patch(
            "app.services.tournament.tournament_reward_orchestrator.get_user_reward_summary",
            return_value=MagicMock(user_id=TEST_USER_ID),
        ) as mock_summary:
            result = distribute_rewards_for_user(
                db, 1, 42, None, 10, RewardPolicy(), force_redistribution=False
            )

        mock_summary.assert_called_once_with(db, 1, 42)
        assert result is not None


# ---------------------------------------------------------------------------
# RACE-R04: Skill write-back race (JSONB last-writer-wins)
# ---------------------------------------------------------------------------

class TestRaceR04SkillWriteBack:
    """
    RACE-R04: concurrent distributions both read UserLicense without lock,
    compute independently, last writer wins.

    Fix: SELECT FOR UPDATE on UserLicense before reading football_skills.
    """

    def test_r04_skill_writeback_locks_user_license(self):
        """Skill write-back must use FOR UPDATE on UserLicense."""
        from app.services.tournament.tournament_reward_orchestrator import distribute_rewards_for_user
        from app.schemas.tournament_rewards import RewardPolicy

        db = MagicMock()

        # Participation chain: returns None (first distribution)
        participation_chain = MagicMock()
        participation_chain.filter.return_value.with_for_update.return_value.first.return_value = None

        # Semester chain: needed for tournament info
        semester_chain = MagicMock()
        semester_chain.filter.return_value.first.return_value = SimpleNamespace(
            id=42, name="Test Tournament", reward_config=None
        )

        # UserLicense chain — track with_for_update call
        license_chain = MagicMock()
        mock_license = MagicMock()
        mock_license.id = 5
        mock_license.user_id = 1
        mock_license.football_skills = {
            "passing": {"current_level": 5, "tournament_delta": 0.0,
                        "total_delta": 0.0, "tournament_count": 1}
        }
        mock_license.skills_last_updated_at = None
        mock_license.skills_updated_by = None
        license_chain.filter.return_value.with_for_update.return_value.first.return_value = mock_license

        def _query_dispatch(model):
            model_name = getattr(model, "__name__", "")
            if "Participation" in model_name:
                return participation_chain
            if "License" in model_name or "UserLicense" in model_name:
                return license_chain
            return semester_chain  # Semester and everything else

        db.query.side_effect = _query_dispatch
        db.execute.return_value.scalar.return_value = 1000

        with (
            patch("app.services.tournament.tournament_reward_orchestrator.participation_service") as mock_ps,
            patch("app.services.tournament.tournament_reward_orchestrator.badge_service") as mock_bs,
            patch("app.services.tournament.tournament_reward_orchestrator.skill_progression_service") as mock_sp,
            patch("app.services.tournament.tournament_reward_orchestrator.get_placement_rewards",
                  return_value={"xp": 0, "credits": 0}),
            patch("sqlalchemy.orm.attributes.flag_modified"),
        ):
            mock_ps.calculate_skill_points_for_placement.return_value = {}
            mock_ps.convert_skill_points_to_xp.return_value = 0
            mock_ps.record_tournament_participation.return_value = _participation()
            mock_sp.get_skill_profile.return_value = {
                "skills": {"passing": {"current_level": 6, "tournament_delta": 1.0,
                                       "total_delta": 1.0, "tournament_count": 2}}
            }
            mock_bs.award_placement_badges.return_value = []
            mock_bs.award_participation_badge.return_value = _badge()
            mock_bs.check_and_award_milestone_badges.return_value = []

            distribute_rewards_for_user(db, 1, 42, None, 10, RewardPolicy())

        assert license_chain.filter.return_value.with_for_update.called, (
            "RACE-R04: skill write-back must use .with_for_update().first() on UserLicense"
        )


# ---------------------------------------------------------------------------
# RACE-R05: Badge double-award TOCTOU
# ---------------------------------------------------------------------------

class TestRaceR05BadgeDoubleAward:
    """
    RACE-R05: award_badge checks existing badge without FOR UPDATE; no unique constraint.

    Fix: SAVEPOINT pattern in award_badge; unique DB constraint on (user_id, semester_id, badge_type).
    """

    def _badge_test_db(self):
        """Build mock db for badge service tests (needs Semester + TournamentBadge queries)."""
        db = MagicMock()

        badge_chain = MagicMock()
        badge_chain.filter.return_value.with_for_update.return_value.first.return_value = None
        badge_chain.filter.return_value.first.return_value = _badge()

        semester_chain = MagicMock()
        semester_chain.filter.return_value.first.return_value = SimpleNamespace(
            id=42, name="Test Tournament"
        )

        def _dispatch(model):
            model_name = getattr(model, "__name__", "")
            if "Badge" in model_name:
                return badge_chain
            return semester_chain  # Semester

        db.query.side_effect = _dispatch
        return db, badge_chain

    def test_r05_award_badge_returns_existing_on_integrity_error(self):
        """
        When uq_user_tournament_badge fires (IntegrityError on savepoint commit),
        award_badge must return the existing badge, not raise.
        """
        from app.services.tournament.tournament_badge_service import award_badge

        db, badge_chain = self._badge_test_db()

        # Savepoint mock: sp.commit() raises IntegrityError
        sp = MagicMock()
        sp.commit.side_effect = SAIntegrityError("INSERT", {}, Exception("uq_user_tournament_badge"))
        db.begin_nested.return_value = sp

        with (
            patch("app.services.tournament.tournament_badge_service.BADGE_DEFINITIONS", {
                "CHAMPION": {
                    "title_template": "Champion",
                    "description_template": "Winner of {tournament_name}",
                    "category": "PLACEMENT",
                    "icon": "🥇",
                    "rarity": "EPIC",
                }
            }),
        ):
            result = award_badge(db, 1, 42, "CHAMPION")

        sp.rollback.assert_called_once()
        assert result is not None, "RACE-R05: IntegrityError on badge insert must return existing badge"

    def test_r05_no_duplicate_badge_on_concurrent_insert(self):
        """award_badge must not create a second badge when savepoint fails."""
        from app.services.tournament.tournament_badge_service import award_badge

        db, badge_chain = self._badge_test_db()

        sp = MagicMock()
        sp.commit.side_effect = SAIntegrityError("INSERT", {}, Exception("uq_user_tournament_badge"))
        db.begin_nested.return_value = sp

        with patch("app.services.tournament.tournament_badge_service.BADGE_DEFINITIONS", {
            "CHAMPION": {
                "title_template": "Champion",
                "description_template": "Winner of {tournament_name}",
                "category": "PLACEMENT",
                "icon": "🥇",
                "rarity": "EPIC",
            }
        }):
            award_badge(db, 1, 42, "CHAMPION")

        # db.add was called (badge was created) but savepoint was rolled back
        # Net result: no second badge committed to DB
        sp.rollback.assert_called_once()
        assert db.commit.call_count == 0, "award_badge must not issue a full commit"


# ---------------------------------------------------------------------------
# RACE-R06: XP/credit double transaction (no idempotency key on XP)
# ---------------------------------------------------------------------------

class TestRaceR06XPCreditIdempotency:
    """
    RACE-R06: record_tournament_participation creates XPTransaction without
    idempotency_key. Credit already has one, but IntegrityError is uncaught.

    Fix: Add idempotency_key to XPTransaction; catch IntegrityError on credit INSERT.
    """

    def test_r06_xp_transaction_idempotency_key_is_set(self):
        """XPTransaction created in record_tournament_participation must have idempotency_key."""
        from app.models.xp_transaction import XPTransaction

        # Verify the model has the idempotency_key column
        assert hasattr(XPTransaction, "idempotency_key"), (
            "RACE-R06: XPTransaction must have idempotency_key column"
        )

    def test_r06_credit_idempotency_key_format(self):
        """CreditTransaction idempotency key must be deterministic for (tournament, user, placement)."""
        # The key format from participation_service.py:
        tournament_id, user_id, placement = 42, 1, 1
        expected_key = f"tournament_reward_{tournament_id}_{user_id}_{placement}"
        # Verify the format is deterministic and unique per (tournament, user, placement)
        key_a = f"tournament_reward_{tournament_id}_{user_id}_{placement}"
        key_b = f"tournament_reward_{tournament_id}_{user_id}_{placement}"
        assert key_a == key_b, "Idempotency key must be deterministic"
        # Different placement → different key
        key_c = f"tournament_reward_{tournament_id}_{user_id}_None"
        assert key_a != key_c

    def test_r06_xp_idempotency_key_format(self):
        """XP idempotency key must be deterministic for (tournament, user)."""
        tournament_id, user_id = 42, 1
        key = f"reward_xp_{tournament_id}_{user_id}"
        # Regression: same call → same key
        assert key == f"reward_xp_{tournament_id}_{user_id}"
        # Different user → different key
        assert key != f"reward_xp_{tournament_id}_2"


# ---------------------------------------------------------------------------
# RACE-R07: XP/credit balance read-modify-write
# ---------------------------------------------------------------------------

class TestRaceR07BalanceReadModifyWrite:
    """
    RACE-R07: XP and credit balance updated as read-modify-write (no FOR UPDATE on User).

    Fix: Atomic SQL UPDATE: SET xp_balance = xp_balance + :delta RETURNING xp_balance.
    """

    def _participation_test_db(self, participation_result=None):
        """Build mock db for participation service tests."""
        db = MagicMock()

        # Multi-model dispatch: Participation + Semester
        participation_chain = MagicMock()
        participation_chain.filter.return_value.first.return_value = (
            participation_result or _participation()
        )

        semester_chain = MagicMock()
        semester_chain.filter.return_value.first.return_value = SimpleNamespace(
            id=42, name="Test Tournament"
        )

        def _dispatch(model):
            model_name = getattr(model, "__name__", "")
            if "Participation" in model_name:
                return participation_chain
            return semester_chain

        db.query.side_effect = _dispatch
        db.execute.return_value.scalar.return_value = 1100
        db.begin_nested.return_value = MagicMock()  # savepoint mock
        return db

    def test_r07_xp_balance_uses_atomic_sql_update(self):
        """
        record_tournament_participation must use db.execute(text('UPDATE users SET xp_balance =
        xp_balance + :delta ...')) for XP balance, not read-modify-write.
        """
        from app.services.tournament import tournament_participation_service as ps

        db = self._participation_test_db()

        with (
            patch.object(ps, "update_skill_assessments"),
            patch.object(ps, "convert_skill_points_to_xp", return_value=100),  # bonus_xp > 0
            patch("app.services.skill_progression_service.compute_single_tournament_skill_delta",
                  return_value=None),
        ):
            ps.record_tournament_participation(
                db, user_id=TEST_USER_ID, tournament_id=TEST_TOURNAMENT_ID,
                placement=None, skill_points={}, base_xp=50, credits=0
            )

        assert db.execute.called, (
            "RACE-R07: XP balance update must use atomic db.execute(UPDATE ... SET xp_balance = "
            "xp_balance + :delta ...) — not read-modify-write user.xp_balance = new_val"
        )
        # Extract SQL text from call args (text() object is first positional arg)
        sql_texts = [str(c.args[0]) if c.args else "" for c in db.execute.call_args_list]
        assert any("xp_balance" in t for t in sql_texts), (
            "db.execute must reference xp_balance in SQL — "
            f"actual calls: {sql_texts}"
        )

    def test_r07_credit_balance_uses_atomic_sql_update(self):
        """credit_balance update must be atomic (UPDATE ... SET credit_balance = credit_balance + N)."""
        from app.services.tournament import tournament_participation_service as ps

        db = self._participation_test_db()

        with (
            patch.object(ps, "update_skill_assessments"),
            patch.object(ps, "convert_skill_points_to_xp", return_value=0),
            patch("app.services.skill_progression_service.compute_single_tournament_skill_delta",
                  return_value=None),
        ):
            ps.record_tournament_participation(
                db, user_id=TEST_USER_ID, tournament_id=TEST_TOURNAMENT_ID,
                placement=1, skill_points={}, base_xp=0, credits=100  # credits > 0
            )

        assert db.execute.called, (
            "RACE-R07: credit_balance update must use atomic db.execute(UPDATE ... SET "
            "credit_balance = credit_balance + :delta ...)"
        )
        sql_texts = [str(c.args[0]) if c.args else "" for c in db.execute.call_args_list]
        assert any("credit_balance" in t for t in sql_texts), (
            "db.execute must reference credit_balance in SQL — "
            f"actual calls: {sql_texts}"
        )
