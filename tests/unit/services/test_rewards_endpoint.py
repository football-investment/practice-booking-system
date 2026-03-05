"""
Sprint P7 — tournaments/rewards.py
====================================
Target: ≥85% statement, ≥75% branch

Covers:
  submit_tournament_rankings  — 404 / 403 / 400 validation / 200 happy
  complete_tournament         — 404 / 403 / 400 session checks / 200 (H2H + IR)
  distribute_tournament_rewards — 403 / 404 / status guards / idempotency /
                                   reward-tier logic / exception rollback
  get_distributed_rewards     — 404 / auth / not-distributed / distributed
  get_tournament_rankings     — 404 / empty / with participations

Mock strategy
-------------
* ``_q(...)``       — fluent query-chain mock (filter/order_by/... return self)
* ``_seq_db(*qs)``  — db where each db.query() call returns next q in sequence
* ``_tourn(...)``   — lightweight Semester-like namespace
* ``_user(...)``    — lightweight User-like namespace with .role, .id
* ``_ranking(...)`` — lightweight TournamentRanking-like namespace
"""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

from fastapi import HTTPException
from app.models.user import UserRole
from app.api.api_v1.endpoints.tournaments.rewards import (
    submit_tournament_rankings,
    complete_tournament,
    distribute_tournament_rewards,
    get_distributed_rewards,
    get_tournament_rankings,
    RankingSubmissionRequest,
    RankingSubmissionItem,
    RewardDistributionRequest,
    DEFAULT_REWARD_POLICY,
)

# ── Patch paths ────────────────────────────────────────────────────────────────

_BASE = "app.api.api_v1.endpoints.tournaments.rewards"
_LIFECYCLE = "app.api.api_v1.endpoints.tournaments.lifecycle.record_status_change"


# ── Fluent query mock ──────────────────────────────────────────────────────────

def _q(*, first=None, all_=None, count=0, delete=0, scalar=None):
    """
    Return a fluent query mock. Every chaining method returns self so any
    chain depth (filter/order_by/options/offset/limit/group_by/join/subquery)
    is handled transparently.
    """
    q = MagicMock()
    for m in ("filter", "options", "order_by", "offset", "limit",
              "group_by", "join", "with_for_update", "distinct"):
        getattr(q, m).return_value = q
    q.subquery.return_value = MagicMock()
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count
    q.delete.return_value = delete
    q.scalar.return_value = scalar
    return q


def _seq_db(*qs):
    """db mock: the n-th call to db.query() returns qs[n]."""
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        if idx < len(qs):
            return qs[idx]
        return _q()  # safe fallback

    db = MagicMock()
    db.query.side_effect = _side
    return db


# ── Model helpers ──────────────────────────────────────────────────────────────

def _tourn(
    tid=1,
    status="COMPLETED",
    fmt="INDIVIDUAL_RANKING",
    master_id=99,
    name="Cup",
    reward_policy=None,
    winner_count=None,
):
    t = MagicMock()
    t.id = tid
    t.name = name
    t.tournament_status = status
    t.format = fmt
    t.master_instructor_id = master_id
    t.reward_policy_snapshot = reward_policy
    t.winner_count = winner_count
    return t


def _user(uid=42, role=UserRole.ADMIN, credit_balance=100, xp_balance=500,
          name="Alice", email="alice@test.com"):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.credit_balance = credit_balance
    u.xp_balance = xp_balance
    u.name = name
    u.email = email
    return u


def _ranking(uid=42, rank=1, points=0.0):
    r = MagicMock()
    r.user_id = uid
    r.rank = rank
    r.points = points
    return r


def _enrollment(uid=42):
    e = MagicMock()
    e.user_id = uid
    return e


def _session(sid=1, game_results=None, auto_generated=True):
    s = MagicMock()
    s.id = sid
    s.game_results = game_results
    s.auto_generated = auto_generated
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# submit_tournament_rankings
# ═══════════════════════════════════════════════════════════════════════════════

class TestSubmitRankings:
    """submit_tournament_rankings — all guard branches + happy path."""

    def _req(self, items):
        return RankingSubmissionRequest(
            rankings=[RankingSubmissionItem(user_id=uid, rank=rk)
                      for uid, rk in items]
        )

    # ── Auth / existence guards ───────────────────────────────────────────────

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, self._req([(42, 1)]),
                                       db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_student_role(self):
        db = _seq_db(_q(first=_tourn()))
        current_user = _user(uid=10, role=UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, self._req([(42, 1)]),
                                       db=db, current_user=current_user)
        assert exc.value.status_code == 403

    def test_403_unassigned_instructor(self):
        tourn = _tourn(master_id=99)
        db = _seq_db(_q(first=tourn))
        current_user = _user(uid=10, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, self._req([(42, 1)]),
                                       db=db, current_user=current_user)
        assert exc.value.status_code == 403

    def test_assigned_instructor_passes_auth(self):
        """Assigned instructor must NOT get a 403 — reaches next validation."""
        tourn = _tourn(master_id=10, status="IN_PROGRESS")  # Wrong status → 400
        db = _seq_db(_q(first=tourn))
        current_user = _user(uid=10, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, self._req([(42, 1)]),
                                       db=db, current_user=current_user)
        assert exc.value.status_code == 400  # status guard, not 403

    # ── Status guards ─────────────────────────────────────────────────────────

    def test_400_tournament_not_completed(self):
        tourn = _tourn(status="IN_PROGRESS")
        db = _seq_db(_q(first=tourn))
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, self._req([(42, 1)]),
                                       db=db, current_user=_user())
        assert exc.value.status_code == 400

    def test_400_rewards_already_distributed(self):
        tourn = _tourn(status="REWARDS_DISTRIBUTED")
        db = _seq_db(_q(first=tourn))
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, self._req([(42, 1)]),
                                       db=db, current_user=_user())
        assert exc.value.status_code == 400

    # ── Player-set validation ─────────────────────────────────────────────────

    def test_400_missing_enrolled_players(self):
        tourn = _tourn()
        # Enrollment has uid=42 and uid=43; request only has uid=42
        e1, e2 = _enrollment(42), _enrollment(43)
        db = _seq_db(_q(first=tourn), _q(all_=[e1, e2]))
        req = self._req([(42, 1)])  # Missing uid=43
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, req, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "Missing" in exc.value.detail

    def test_400_extra_players_not_enrolled(self):
        tourn = _tourn()
        e1 = _enrollment(42)
        db = _seq_db(_q(first=tourn), _q(all_=[e1]))
        req = self._req([(42, 1), (99, 2)])  # 99 is not enrolled
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, req, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "Extra" in exc.value.detail

    # ── Rank sequence validation ──────────────────────────────────────────────

    def test_400_rank_does_not_start_at_1(self):
        tourn = _tourn()
        e1 = _enrollment(42)
        db = _seq_db(_q(first=tourn), _q(all_=[e1]))
        req = self._req([(42, 2)])  # Rank starts at 2
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, req, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "start from 1" in exc.value.detail

    def test_400_invalid_rank_sequence_gap(self):
        """1, 2, 2, 5 is invalid — after two 2nds, next should be 4 not 5."""
        tourn = _tourn()
        enrollments = [_enrollment(i) for i in [42, 43, 44, 45]]
        db = _seq_db(_q(first=tourn), _q(all_=enrollments))
        # ranks 1, 2, 2, 5 — gap at 5 (should be 4)
        req = self._req([(42, 1), (43, 2), (44, 2), (45, 5)])
        with pytest.raises(HTTPException) as exc:
            submit_tournament_rankings(1, req, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "Invalid rank sequence" in exc.value.detail

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_200_valid_single_player_submission(self):
        tourn = _tourn(name="Cup")
        e1 = _enrollment(42)
        db = _seq_db(
            _q(first=tourn),   # tournament
            _q(all_=[e1]),     # enrollments
            _q(delete=0),      # delete existing rankings
        )
        req = self._req([(42, 1)])
        result = submit_tournament_rankings(1, req, db=db, current_user=_user())
        assert result.tournament_id == 1
        assert result.rankings_submitted == 1
        db.commit.assert_called_once()

    def test_200_valid_tied_ranks(self):
        """Tied ranks 1, 2, 2, 4 are valid."""
        tourn = _tourn()
        enrollments = [_enrollment(i) for i in [42, 43, 44, 45]]
        db = _seq_db(
            _q(first=tourn),
            _q(all_=enrollments),
            _q(delete=0),
        )
        req = self._req([(42, 1), (43, 2), (44, 2), (45, 4)])
        result = submit_tournament_rankings(1, req, db=db, current_user=_user())
        assert result.rankings_submitted == 4


# ═══════════════════════════════════════════════════════════════════════════════
# complete_tournament
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompleteTournament:
    """complete_tournament — all guards + H2H/IR status transitions."""

    # ── Auth / existence guards ───────────────────────────────────────────────

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_admin_or_master_instructor(self):
        tourn = _tourn(master_id=99)
        db = _seq_db(_q(first=tourn))
        student = _user(uid=10, role=UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=student)
        assert exc.value.status_code == 403

    def test_400_tournament_not_in_progress(self):
        tourn = _tourn(status="COMPLETED")
        db = _seq_db(_q(first=tourn))
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=_user())
        assert exc.value.status_code == 400

    def test_400_no_sessions(self):
        tourn = _tourn(status="IN_PROGRESS")
        db = _seq_db(
            _q(first=tourn),   # tournament
            _q(all_=[]),       # no sessions
        )
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "No sessions" in exc.value.detail

    def test_400_ir_unfinalized_sessions(self):
        """INDIVIDUAL_RANKING: sessions with no game_results → 400."""
        tourn = _tourn(status="IN_PROGRESS", fmt="INDIVIDUAL_RANKING")
        sessions = [_session(1, game_results=None), _session(2, game_results={"x": 1})]
        db = _seq_db(
            _q(first=tourn),
            _q(all_=sessions),
        )
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "not finalized" in exc.value.detail

    def test_400_h2h_sessions_missing_results(self):
        """HEAD_TO_HEAD: sessions with no game_results → 400."""
        tourn = _tourn(status="IN_PROGRESS", fmt="HEAD_TO_HEAD")
        sessions = [_session(1, game_results=None)]
        db = _seq_db(
            _q(first=tourn),
            _q(all_=sessions),
        )
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "missing results" in exc.value.detail

    def test_400_ir_no_rankings_exist(self):
        """INDIVIDUAL_RANKING with existing_rankings=0 → error (not H2H)."""
        tourn = _tourn(status="IN_PROGRESS", fmt="INDIVIDUAL_RANKING")
        sessions = [_session(1, game_results={"done": True})]
        db = _seq_db(
            _q(first=tourn),
            _q(all_=sessions),
            _q(count=0),      # existing_rankings = 0
        )
        with pytest.raises(HTTPException) as exc:
            complete_tournament(1, db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "No rankings found" in exc.value.detail

    @patch(_LIFECYCLE)
    def test_200_with_existing_rankings(self, mock_lifecycle):
        """Existing rankings present → status transitions directly to COMPLETED."""
        tourn = _tourn(status="IN_PROGRESS", fmt="INDIVIDUAL_RANKING")
        sessions = [_session(1, game_results={"done": True})]
        db = _seq_db(
            _q(first=tourn),
            _q(all_=sessions),
            _q(count=3),      # existing rankings exist
        )
        result = complete_tournament(1, db=db, current_user=_user())
        assert result["new_status"] == "COMPLETED"
        db.commit.assert_called_once()

    @patch(_LIFECYCLE)
    def test_200_h2h_no_existing_rankings_creates_sequential(self, mock_lifecycle):
        """H2H, no rankings → creates sequential ranks from enrollments."""
        tourn = _tourn(status="IN_PROGRESS", fmt="HEAD_TO_HEAD")
        sessions = [_session(1, game_results={"done": True})]
        enrollments = [_enrollment(42), _enrollment(43)]
        db = _seq_db(
            _q(first=tourn),
            _q(all_=sessions),
            _q(count=0),          # existing_rankings = 0
            _q(all_=enrollments), # enrollments for H2H ranking creation
        )
        result = complete_tournament(1, db=db, current_user=_user())
        assert result["new_status"] == "COMPLETED"
        assert db.add.called


# ═══════════════════════════════════════════════════════════════════════════════
# distribute_tournament_rewards
# ═══════════════════════════════════════════════════════════════════════════════

class TestDistributeRewards:
    """distribute_tournament_rewards — auth, idempotency, tier logic, rollback."""

    def _req(self, reason=None, winner_count=None):
        return RewardDistributionRequest(reason=reason, winner_count=winner_count)

    # ── Auth / existence guards ───────────────────────────────────────────────

    def test_403_non_admin(self):
        db = _seq_db()
        instructor = _user(uid=5, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=instructor)
        assert exc.value.status_code == 403

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=_user())
        assert exc.value.status_code == 404

    def test_400_wrong_tournament_status(self):
        tourn = _tourn(status="IN_PROGRESS")
        db = _seq_db(_q(first=tourn))
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=_user())
        assert exc.value.status_code == 400
        assert "must be COMPLETED" in exc.value.detail

    # ── Idempotency guards ────────────────────────────────────────────────────

    @patch(_LIFECYCLE)
    def test_200_existing_rewards_wrong_status_auto_corrects(self, mock_lifecycle):
        """Rewards exist but status is not REWARDS_DISTRIBUTED → auto-fix."""
        tourn = _tourn(status="COMPLETED")
        db = _seq_db(
            _q(first=tourn),   # tournament
            _q(count=3),       # existing_rewards = 3 (> 0)
        )
        result = distribute_tournament_rewards(1, self._req(), db=db,
                                               current_user=_user())
        assert result.status == "REWARDS_DISTRIBUTED"
        assert "already distributed" in result.message

    def test_400_rewards_already_distributed_locked(self):
        """Rewards exist AND status already REWARDS_DISTRIBUTED → locked."""
        tourn = _tourn(status="REWARDS_DISTRIBUTED")
        db = _seq_db(
            _q(first=tourn),
            _q(count=5),  # existing_rewards > 0
        )
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=_user())
        assert exc.value.status_code == 400
        assert "locked" in exc.value.detail

    def test_400_no_rankings_found(self):
        tourn = _tourn(status="COMPLETED")
        subq_mock = _q()
        rankings_q = _q(all_=[])  # No rankings returned
        db = _seq_db(
            _q(first=tourn),   # tournament
            _q(count=0),       # no existing rewards
            subq_mock,         # subquery build
            rankings_q,        # rankings.all() → []
        )
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=_user())
        assert exc.value.status_code == 400
        assert "No rankings" in exc.value.detail

    def test_500_duplicate_rankings_detected(self):
        """Two rankings with same user_id → 500 (defensive assertion)."""
        tourn = _tourn(status="COMPLETED")
        r1 = _ranking(uid=42, rank=1)
        r2 = _ranking(uid=42, rank=1)  # same user
        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),           # subquery
            _q(all_=[r1, r2]),  # two rankings, same user → duplicate
        )
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=_user())
        assert exc.value.status_code == 500

    # ── Happy path / reward tier logic ────────────────────────────────────────

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.FootballSkillService")
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_200_1st_place_default_policy(self, mock_credit_svc, mock_xp_svc,
                                          mock_skill_svc, mock_lifecycle):
        """1st-place ranking uses DEFAULT_REWARD_POLICY (500 credits, 100 XP)."""
        tourn = _tourn(status="COMPLETED", reward_policy=None)
        rank1 = _ranking(uid=42, rank=1)
        user42 = _user(uid=42)

        mock_credit_svc.return_value.generate_idempotency_key.return_value = "k1"
        mock_credit_svc.return_value.create_transaction.return_value = (MagicMock(), True)
        mock_xp_svc.return_value.award_xp.return_value = (MagicMock(), True)

        db = _seq_db(
            _q(first=tourn),           # tournament
            _q(count=0),               # existing rewards = 0
            _q(),                      # subquery
            _q(all_=[rank1]),          # one ranking
            _q(first=user42),          # user in loop
            _q(count=2),               # total_players (rank 1 → skill path; no license)
            _q(first=None),            # UserLicense → None (skip skill)
        )
        result = distribute_tournament_rewards(1, self._req(), db=db,
                                               current_user=_user())
        assert result.status == "REWARDS_DISTRIBUTED"
        assert result.rewards_distributed == 1
        assert result.total_credits_awarded == 500
        assert result.total_xp_awarded == 100

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_200_participant_tier_rank_4(self, mock_credit_svc, mock_xp_svc,
                                         mock_lifecycle):
        """Rank 4 falls back to 'participant' tier (50 credits, 25 XP)."""
        tourn = _tourn(status="COMPLETED", reward_policy=None)
        rank4 = _ranking(uid=42, rank=4)
        user42 = _user(uid=42)

        mock_credit_svc.return_value.generate_idempotency_key.return_value = "k4"
        mock_credit_svc.return_value.create_transaction.return_value = (MagicMock(), True)
        mock_xp_svc.return_value.award_xp.return_value = (MagicMock(), True)

        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),
            _q(all_=[rank4]),
            _q(first=user42),
            _q(count=4),   # total_players=4; rank 4 → last → skill path (no license)
            _q(first=None),
        )
        result = distribute_tournament_rewards(1, self._req(), db=db,
                                               current_user=_user())
        assert result.total_credits_awarded == 50
        assert result.total_xp_awarded == 25

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_200_new_placement_rewards_format(self, mock_credit_svc, mock_xp_svc,
                                              mock_lifecycle):
        """New placement_rewards format is converted to old format correctly."""
        placement_policy = {
            "placement_rewards": {
                "1ST": {"credits": 1000, "xp": 200},
                "2ND": {"credits": 600, "xp": 150},
                "3RD": {"credits": 400, "xp": 100},
                "PARTICIPANT": {"credits": 100, "xp": 50},
            }
        }
        tourn = _tourn(status="COMPLETED", reward_policy=placement_policy)
        rank1 = _ranking(uid=42, rank=1)
        user42 = _user(uid=42)

        mock_credit_svc.return_value.generate_idempotency_key.return_value = "k"
        mock_credit_svc.return_value.create_transaction.return_value = (MagicMock(), True)
        mock_xp_svc.return_value.award_xp.return_value = (MagicMock(), True)

        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),
            _q(all_=[rank1]),
            _q(first=user42),
            _q(count=2),
            _q(first=None),
        )
        result = distribute_tournament_rewards(1, self._req(), db=db,
                                               current_user=_user())
        assert result.total_credits_awarded == 1000

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_200_invalid_policy_falls_back_to_default(self, mock_credit_svc,
                                                       mock_xp_svc,
                                                       mock_lifecycle):
        """reward_policy_snapshot without 'rewards' or 'placement_rewards' → DEFAULT."""
        tourn = _tourn(status="COMPLETED",
                       reward_policy={"unknown_key": "bad_format"})
        rank1 = _ranking(uid=42, rank=1)
        user42 = _user(uid=42)

        mock_credit_svc.return_value.generate_idempotency_key.return_value = "k"
        mock_credit_svc.return_value.create_transaction.return_value = (MagicMock(), True)
        mock_xp_svc.return_value.award_xp.return_value = (MagicMock(), True)

        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),
            _q(all_=[rank1]),
            _q(first=user42),
            _q(count=2),
            _q(first=None),
        )
        result = distribute_tournament_rewards(1, self._req(), db=db,
                                               current_user=_user())
        # DEFAULT_REWARD_POLICY: rank 1 → 500 credits
        assert result.total_credits_awarded == 500

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_200_winner_count_stored(self, mock_credit_svc, mock_xp_svc,
                                     mock_lifecycle):
        """winner_count in request is stored on tournament and committed."""
        tourn = _tourn(status="COMPLETED")
        rank1 = _ranking(uid=42, rank=1)
        user42 = _user(uid=42)

        mock_credit_svc.return_value.generate_idempotency_key.return_value = "k"
        mock_credit_svc.return_value.create_transaction.return_value = (MagicMock(), True)
        mock_xp_svc.return_value.award_xp.return_value = (MagicMock(), True)

        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),
            _q(all_=[rank1]),
            _q(first=user42),
            _q(count=2),
            _q(first=None),
        )
        distribute_tournament_rewards(1, self._req(winner_count=3),
                                      db=db, current_user=_user())
        assert tourn.winner_count == 3

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_500_exception_triggers_rollback(self, mock_credit_svc, mock_xp_svc,
                                             mock_lifecycle):
        """Any exception inside the try block → db.rollback() + 500."""
        tourn = _tourn(status="COMPLETED")
        rank1 = _ranking(uid=42, rank=1)

        # CreditService.create_transaction raises → triggers rollback path
        mock_credit_svc.return_value.generate_idempotency_key.return_value = "k"
        mock_credit_svc.return_value.create_transaction.side_effect = RuntimeError("DB error")

        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),
            _q(all_=[rank1]),
            _q(first=_user(uid=42)),
            _q(count=2),
            _q(first=None),
        )
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards(1, self._req(), db=db,
                                          current_user=_user())
        assert exc.value.status_code == 500
        db.rollback.assert_called_once()

    @patch(_LIFECYCLE)
    @patch(f"{_BASE}.XPTransactionService")
    @patch(f"{_BASE}.CreditService")
    def test_200_user_not_found_in_loop_is_skipped(self, mock_credit_svc,
                                                    mock_xp_svc, mock_lifecycle):
        """If user not found for a ranking entry, that entry is skipped gracefully."""
        tourn = _tourn(status="COMPLETED")
        rank1 = _ranking(uid=999, rank=1)  # user 999 will return None

        db = _seq_db(
            _q(first=tourn),
            _q(count=0),
            _q(),
            _q(all_=[rank1]),
            _q(first=None),    # user 999 not found → skip
        )
        result = distribute_tournament_rewards(1, self._req(), db=db,
                                               current_user=_user())
        # No user → no rewards distributed
        assert result.rewards_distributed == 0


# ═══════════════════════════════════════════════════════════════════════════════
# get_distributed_rewards
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetDistributedRewards:
    """get_distributed_rewards — auth branches + distribution state logic."""

    # ── Auth / existence guards ───────────────────────────────────────────────

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_distributed_rewards(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_unassigned_instructor(self):
        tourn = _tourn(master_id=99)
        db = _seq_db(_q(first=tourn))
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            get_distributed_rewards(1, db=db, current_user=instructor)
        assert exc.value.status_code == 403

    def test_403_student_role(self):
        tourn = _tourn()
        db = _seq_db(_q(first=tourn))
        student = _user(uid=5, role=UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            get_distributed_rewards(1, db=db, current_user=student)
        assert exc.value.status_code == 403

    def test_200_rewards_not_yet_distributed(self):
        tourn = _tourn(status="COMPLETED")
        db = _seq_db(_q(first=tourn))
        result = get_distributed_rewards(1, db=db, current_user=_user())
        assert result["rewards_distributed"] is False
        assert result["rewards"] == []

    def test_200_assigned_instructor_can_view(self):
        """Assigned instructor (master_id matches) bypasses 403."""
        tourn = _tourn(status="COMPLETED", master_id=10)
        db = _seq_db(_q(first=tourn))
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        result = get_distributed_rewards(1, db=db, current_user=instructor)
        assert result["rewards_distributed"] is False  # status is COMPLETED not REWARDS_DISTRIBUTED

    def test_200_distributed_rewards_with_data(self):
        """REWARDS_DISTRIBUTED status → query credit+xp transactions and build list."""
        tourn = _tourn(status="REWARDS_DISTRIBUTED")
        user42 = _user(uid=42, name="Alice", email="alice@t.com")

        # Credit transaction
        credit_txn = SimpleNamespace(
            user_id=42, amount=500, description="Tournament 'Cup' - Rank #1 reward"
        )
        # XP transaction (same user)
        xp_txn = SimpleNamespace(
            user_id=42, amount=100, description="Tournament 'Cup' - Rank #1 reward"
        )
        # Ranking row (best_rank)
        ranking_row = SimpleNamespace(user_id=42, best_rank=1)
        # SkillReward
        skill_reward = SimpleNamespace(
            user_id=42, skill_name="dribbling", points_awarded=5
        )

        db = _seq_db(
            _q(first=tourn),            # tournament
            _q(all_=[credit_txn]),      # credit transactions
            _q(all_=[xp_txn]),          # xp transactions
            _q(all_=[user42]),          # users query
            _q(all_=[ranking_row]),     # best rank per user
            _q(all_=[skill_reward]),    # skill rewards
        )
        result = get_distributed_rewards(1, db=db, current_user=_user())
        assert result["rewards_distributed"] is True
        assert len(result["rewards"]) == 1
        assert result["rewards"][0]["rank"] == 1
        assert result["rewards"][0]["credits"] == 500
        assert result["rewards"][0]["xp"] == 100
        assert result["rewards"][0]["skill_points_awarded"] == {"dribbling": 5}


# ═══════════════════════════════════════════════════════════════════════════════
# get_tournament_rankings
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTournamentRankings:
    """get_tournament_rankings — 404, empty, with participation rewards."""

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_tournament_rankings(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_200_empty_rankings(self):
        tourn = _tourn(status="COMPLETED")
        db = _seq_db(
            _q(first=tourn),          # tournament
            _q(all_=[]),              # first rankings query (unused result, re-queried below)
            _q(all_=[]),              # joinedload rankings
            _q(all_=[]),              # participations
        )
        result = get_tournament_rankings(1, db=db, current_user=_user())
        assert result["tournament_id"] == 1
        assert result["rankings"] == []
        assert result["total_participants"] == 0

    def test_200_rankings_with_participation_data(self):
        """Rankings include credits/xp from TournamentParticipation."""
        tourn = _tourn(status="REWARDS_DISTRIBUTED", name="Cup")

        ranking_row = MagicMock()
        ranking_row.rank = 1
        ranking_row.user_id = 42
        ranking_row.user = SimpleNamespace(name="Alice", email="alice@t.com")
        ranking_row.points = 100.0
        ranking_row.updated_at = None

        participation = MagicMock()
        participation.user_id = 42
        participation.credits_awarded = 500
        participation.xp_awarded = 100
        participation.skill_points_awarded = {"dribbling": 5}

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[ranking_row]),       # first rankings (overridden by joinedload)
            _q(all_=[ranking_row]),       # joinedload rankings
            _q(all_=[participation]),     # participations
        )
        result = get_tournament_rankings(1, db=db, current_user=_user())
        assert result["total_participants"] == 1
        r = result["rankings"][0]
        assert r["rank"] == 1
        assert r["credits_awarded"] == 500
        assert r["xp_awarded"] == 100
        assert r["skill_points_awarded"] == {"dribbling": 5}
