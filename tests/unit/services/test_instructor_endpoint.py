"""
Sprint P7 — tournaments/instructor.py
======================================
Target: ≥85% statement, ≥75% branch

Covers:
  get_active_match            — 404 / 403 / INDIVIDUAL_RANKING / legacy path /
                                no-session / null participant_user_ids /
                                match+enrollment participants / rounds_data
  get_tournament_leaderboard  — 404 / 403 / auth branches / empty leaderboard /
                                group standings WIN/DRAW/LOSS / JSON-string results /
                                "participants" key format / knockout final standings /
                                pure knockout bracket / IR finalized / IR live rounds
  get_tournament_sessions_debug — 404 / 403 (instructor + student) / ADMIN /
                                   sessions with participants / JSON game_results /
                                   exception → 500

Mock strategy
-------------
* ``_q(...)``       — fluent query-chain mock (returns self for all chain methods)
* ``_seq_db(*qs)``  — db where each db.query() call returns the n-th q in sequence
* ``_tourn(...)``   — lightweight Semester-like SimpleNamespace
* ``_user(...)``    — lightweight User-like SimpleNamespace with .role, .id, .email
"""
import asyncio
import json as _json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from app.models.user import UserRole
from app.api.api_v1.endpoints.tournaments.instructor import (
    get_active_match,
    get_tournament_leaderboard,
    get_tournament_sessions_debug,
)

# ── Fluent query mock ──────────────────────────────────────────────────────────

def _q(*, first=None, all_=None, count=0, delete=0):
    q = MagicMock()
    for m in ("filter", "options", "order_by", "offset", "limit",
              "group_by", "join", "with_for_update", "distinct"):
        getattr(q, m).return_value = q
    q.subquery.return_value = MagicMock()
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count
    q.delete.return_value = delete
    return q


def _seq_db(*qs):
    """Each call to db.query() returns the next item from qs."""
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

def _tourn(tid=1, status="IN_PROGRESS", fmt="HEAD_TO_HEAD", master_id=42,
           name="Cup", measurement_unit="points", ranking_direction="DESC",
           scoring_type="PLACEMENT", winner_count=None):
    t = MagicMock()
    t.id = tid
    t.name = name
    t.tournament_status = status
    t.format = fmt
    t.master_instructor_id = master_id
    t.measurement_unit = measurement_unit
    t.ranking_direction = ranking_direction
    t.scoring_type = scoring_type
    t.winner_count = winner_count
    return t


def _user(uid=42, role=UserRole.ADMIN, name="Alice", email="alice@test.com"):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.name = name
    u.email = email
    u.nickname = None  # get_tournament_sessions_debug uses "user.nickname or user.name"
    return u


def _session(sid=1, title="Match 1", fmt="HEAD_TO_HEAD", game_results=None,
             participant_user_ids=None, phase=None, round_num=1,
             rounds_data=None, ranking_mode=None, group_identifier=None,
             match_number=0, scoring_type=None, date_start=None, date_end=None):
    s = MagicMock()
    s.id = sid
    s.title = title
    s.description = "desc"
    s.match_format = fmt
    s.game_results = game_results
    s.participant_user_ids = participant_user_ids
    s.tournament_phase = phase
    s.tournament_round = round_num
    s.tournament_match_number = match_number
    s.rounds_data = rounds_data
    s.ranking_mode = ranking_mode
    s.group_identifier = group_identifier
    s.scoring_type = scoring_type
    s.date_start = date_start
    s.date_end = date_end
    s.location = "Arena"
    s.expected_participants = 2
    s.participant_filter = None
    s.pod_tier = None
    s.structure_config = None
    s.game_type = "Round 1"
    return s


def _enrollment(uid=42, active=True):
    e = MagicMock()
    e.user_id = uid
    e.is_active = active
    e.user = _user(uid=uid)
    return e


def _attendance(status_value="present"):
    a = MagicMock()
    a.status = MagicMock()
    a.status.value = status_value
    return a


# ── Async helpers ──────────────────────────────────────────────────────────────

def _run(coro):
    """Run a coroutine synchronously (for testing async endpoint functions)."""
    return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════════════════
# get_active_match
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetActiveMatch:
    """get_active_match — all authorization branches + business logic paths."""

    # ── Auth / existence guards ───────────────────────────────────────────────

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            _run(get_active_match(1, current_user=_user(), db=db))
        assert exc.value.status_code == 404

    def test_403_student_role(self):
        tourn = _tourn()
        db = _seq_db(_q(first=tourn))
        with pytest.raises(HTTPException) as exc:
            _run(get_active_match(1, current_user=_user(uid=5, role=UserRole.STUDENT), db=db))
        assert exc.value.status_code == 403

    def test_403_unassigned_instructor(self):
        tourn = _tourn(master_id=99)
        db = _seq_db(_q(first=tourn))
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            _run(get_active_match(1, current_user=instructor, db=db))
        assert exc.value.status_code == 403

    def test_admin_access_no_restriction(self):
        """ADMIN bypasses instructor assignment check → reaches next logic."""
        tourn = _tourn(fmt="HEAD_TO_HEAD")  # non-IR → legacy path
        active_sess = None
        db = _seq_db(
            _q(first=tourn),         # tournament
            _q(first=active_sess),   # legacy active session → None
        )
        result = _run(get_active_match(1, current_user=_user(role=UserRole.ADMIN), db=db))
        # No active session → "All matches completed"
        assert result["active_match"] is None

    def test_individual_ranking_non_completed_uses_special_query(self):
        """INDIVIDUAL_RANKING, non-COMPLETED → special query (any session, not just nulls)."""
        tourn = _tourn(fmt="INDIVIDUAL_RANKING", status="IN_PROGRESS")
        active_sess = None  # no session → "completed" message
        db = _seq_db(
            _q(first=tourn),
            _q(first=active_sess),   # INDIVIDUAL_RANKING path (no game_results filter)
        )
        result = _run(get_active_match(1, current_user=_user(), db=db))
        assert result["active_match"] is None
        assert "completed" in result["message"].lower()

    def test_no_active_session_returns_completed_message(self):
        """Legacy format, no session → message dict with active_match=None."""
        tourn = _tourn(fmt="HEAD_TO_HEAD")
        db = _seq_db(
            _q(first=tourn),
            _q(first=None),  # no active session
        )
        result = _run(get_active_match(1, current_user=_user(), db=db))
        assert result["active_match"] is None
        assert result["tournament_id"] == 1

    def test_null_participant_user_ids_returns_prerequisite_message(self):
        """Active session with participant_user_ids=None → prerequisite not met."""
        tourn = _tourn(fmt="HEAD_TO_HEAD")
        active_sess = _session(1, participant_user_ids=None)
        db = _seq_db(
            _q(first=tourn),
            _q(first=active_sess),
        )
        result = _run(get_active_match(1, current_user=_user(), db=db))
        assert result["active_match"] is None
        assert result["prerequisite_status"]["ready"] is False

    def test_with_participants_no_attendance(self):
        """Active session with participants → builds match_participants list."""
        tourn = _tourn(fmt="HEAD_TO_HEAD")
        active_sess = _session(1, participant_user_ids=[42, 43])

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        enrollment = _enrollment(uid=42)

        db = _seq_db(
            _q(first=tourn),             # tournament
            _q(first=active_sess),       # active session (legacy path)
            _q(all_=[user42, user43]),   # users by id.in_(...)
            _q(first=None),              # attendance for user42 → None
            _q(first=None),              # attendance for user43 → None
            _q(all_=[enrollment]),       # SemesterEnrollment with joinedload
            _q(first=None),              # attendance for enrollment user
            _q(all_=[]),                 # upcoming sessions
            _q(count=3),                 # total_matches
            _q(count=1),                 # completed_matches
        )
        result = _run(get_active_match(1, current_user=_user(), db=db))
        assert result["active_match"] is not None
        match = result["active_match"]
        assert match["match_participants_count"] == 2
        assert match["pending_count"] == 2

    def test_participant_with_attendance_marks_as_present(self):
        """Participant with attendance.status='present' shows is_present=True."""
        tourn = _tourn(fmt="HEAD_TO_HEAD")
        active_sess = _session(1, participant_user_ids=[42])

        user42 = _user(uid=42, name="Alice")
        att = _attendance("present")

        db = _seq_db(
            _q(first=tourn),
            _q(first=active_sess),
            _q(all_=[user42]),
            _q(first=att),          # attendance for user42 → present
            _q(all_=[]),            # enrollments (empty)
            _q(all_=[]),            # upcoming
            _q(count=2),            # total
            _q(count=1),            # completed
        )
        result = _run(get_active_match(1, current_user=_user(), db=db))
        match = result["active_match"]
        assert match["present_count"] == 1
        assert match["match_participants"][0]["is_present"] is True

    def test_rounds_data_uses_round_count_not_session_count(self):
        """INDIVIDUAL_RANKING with rounds_data → uses total_rounds/completed_rounds."""
        tourn = _tourn(fmt="INDIVIDUAL_RANKING", status="IN_PROGRESS")
        rounds = {"total_rounds": 5, "completed_rounds": 3}
        active_sess = _session(1, participant_user_ids=[42], rounds_data=rounds)

        user42 = _user(uid=42)

        db = _seq_db(
            _q(first=tourn),
            _q(first=active_sess),   # INDIVIDUAL_RANKING path
            _q(all_=[user42]),
            _q(first=None),          # attendance
            _q(all_=[]),             # enrollments
            _q(all_=[]),             # upcoming
            # No count queries since rounds_data is present
        )
        result = _run(get_active_match(1, current_user=_user(), db=db))
        assert result["total_matches"] == 5
        assert result["completed_matches"] == 3

    def test_assigned_instructor_has_access(self):
        """Instructor assigned to tournament (master_id matches) → no 403."""
        tourn = _tourn(master_id=10, fmt="HEAD_TO_HEAD")
        db = _seq_db(
            _q(first=tourn),
            _q(first=None),  # no active session → "completed"
        )
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        result = _run(get_active_match(1, current_user=instructor, db=db))
        assert result["active_match"] is None  # not 403


# ═══════════════════════════════════════════════════════════════════════════════
# get_tournament_leaderboard
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTournamentLeaderboard:
    """get_tournament_leaderboard — all auth + data building branches."""

    # ── Auth guards ───────────────────────────────────────────────────────────

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert exc.value.status_code == 404

    def test_403_instructor_not_assigned(self):
        tourn = _tourn(master_id=99)
        db = _seq_db(_q(first=tourn))
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            _run(get_tournament_leaderboard(1, current_user=instructor, db=db))
        assert exc.value.status_code == 403

    def test_403_student_not_enrolled(self):
        tourn = _tourn()
        db = _seq_db(
            _q(first=tourn),     # tournament
            _q(first=None),      # SemesterEnrollment → not enrolled
        )
        student = _user(uid=5, role=UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            _run(get_tournament_leaderboard(1, current_user=student, db=db))
        assert exc.value.status_code == 403

    def test_200_student_enrolled_passes(self):
        """Enrolled student passes auth; endpoint returns leaderboard."""
        tourn = _tourn()
        enrollment = _enrollment(uid=5)

        db = _seq_db(
            _q(first=tourn),         # tournament
            _q(first=enrollment),    # enrollment found → student OK
            _q(all_=[]),             # group sessions → []
            _q(count=2),             # total_matches
            _q(count=1),             # completed_matches
            _q(all_=[]),             # knockout sessions (else branch)
            _q(first=None),          # individual_session
        )
        db.execute.return_value.fetchall.return_value = []

        student = _user(uid=5, role=UserRole.STUDENT)
        result = _run(get_tournament_leaderboard(1, current_user=student, db=db))
        assert result["tournament_id"] == 1
        assert result["leaderboard"] == []

    # ── Leaderboard data building ─────────────────────────────────────────────

    def test_200_empty_leaderboard_no_group_sessions(self):
        """No rankings, no group sessions → empty leaderboard with progress stats."""
        tourn = _tourn()
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),      # group sessions
            _q(count=3),      # total_matches
            _q(count=1),      # completed_matches
            _q(all_=[]),      # knockout (else branch)
            _q(first=None),   # individual_session
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["leaderboard"] == []
        assert result["total_matches"] == 3
        assert result["completed_matches"] == 1
        assert result["remaining_matches"] == 2

    def test_200_leaderboard_with_ranking_rows(self):
        """Raw SQL rankings are serialised correctly."""
        tourn = _tourn()
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),    # no group sessions
            _q(count=2),
            _q(count=2),
            _q(all_=[]),    # knockout
            _q(first=None), # individual
        )

        row = SimpleNamespace(
            rank=1, user_id=42, user_name="Alice", user_email="alice@t.com",
            points=100, wins=2, losses=0, draws=0, updated_at=None
        )
        db.execute.return_value.fetchall.return_value = [row]

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert len(result["leaderboard"]) == 1
        assert result["leaderboard"][0]["rank"] == 1

    def test_200_group_sessions_win_calculation(self):
        """Group session H2H result where player 1 wins (score 3 > 1)."""
        tourn = _tourn()
        game_res = {"raw_results": [{"user_id": 42, "score": 3},
                                    {"user_id": 43, "score": 1}]}
        group_sess = _session(1, game_results=game_res,
                              participant_user_ids=[42, 43],
                              group_identifier="A", phase="GROUP_STAGE")

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        db = _seq_db(
            _q(first=tourn),
            # group sessions
            _q(all_=[group_sess]),
            # users for group standings
            _q(first=user42),
            _q(first=user43),
            # knockout (if group_sessions branch)
            _q(all_=[]),
            # individual session
            _q(first=None),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["group_standings"]["A"]
        alice = next(p for p in standings if p["user_id"] == 42)
        bob = next(p for p in standings if p["user_id"] == 43)
        assert alice["wins"] == 1
        assert alice["points"] == 3
        assert bob["losses"] == 1
        assert bob["points"] == 0

    def test_200_group_sessions_draw_calculation(self):
        """Group session where scores are equal → draw."""
        tourn = _tourn()
        game_res = {"raw_results": [{"user_id": 42, "score": 2},
                                    {"user_id": 43, "score": 2}]}
        group_sess = _session(1, game_results=game_res,
                              participant_user_ids=[42, 43],
                              group_identifier="B", phase="GROUP_STAGE")

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[group_sess]),
            _q(first=user42),
            _q(first=user43),
            _q(all_=[]),    # knockout
            _q(first=None), # individual
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["group_standings"]["B"]
        for p in standings:
            assert p["draws"] == 1
            assert p["points"] == 1

    def test_200_group_sessions_json_string_results(self):
        """game_results stored as JSON string → parsed correctly."""
        tourn = _tourn()
        raw = {"raw_results": [{"user_id": 42, "score": 5},
                                {"user_id": 43, "score": 2}]}
        group_sess = _session(1, game_results=_json.dumps(raw),
                              participant_user_ids=[42, 43],
                              group_identifier="C", phase="GROUP_STAGE")

        user42 = _user(uid=42)
        user43 = _user(uid=43)

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[group_sess]),
            _q(first=user42),
            _q(first=user43),
            _q(all_=[]),
            _q(first=None),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["group_standings"]["C"]
        winner = next(p for p in standings if p["user_id"] == 42)
        assert winner["wins"] == 1

    def test_200_group_sessions_participants_key_format(self):
        """game_results using 'participants' key (vs 'raw_results')."""
        tourn = _tourn()
        game_res = {"participants": [{"user_id": 42, "score": 3},
                                     {"user_id": 43, "score": 1}]}
        group_sess = _session(1, game_results=game_res,
                              participant_user_ids=[42, 43],
                              group_identifier="D", phase="GROUP_STAGE")

        user42 = _user(uid=42)
        user43 = _user(uid=43)

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[group_sess]),
            _q(first=user42),
            _q(first=user43),
            _q(all_=[]),
            _q(first=None),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["group_standings"]["D"]
        winner = next(p for p in standings if p["user_id"] == 42)
        assert winner["wins"] == 1

    def test_200_group_session_no_game_results_skipped(self):
        """Sessions with no game_results are skipped in standings calc."""
        tourn = _tourn()
        group_sess = _session(1, game_results=None,
                              participant_user_ids=[42, 43],
                              group_identifier="E", phase="GROUP_STAGE")

        user42 = _user(uid=42)
        user43 = _user(uid=43)

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[group_sess]),
            _q(first=user42),
            _q(first=user43),
            _q(all_=[]),    # knockout
            _q(first=None),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        # Group standings exist but with 0 wins
        standings = result["group_standings"]["E"]
        for p in standings:
            assert p["wins"] == 0

    def test_200_pure_knockout_no_group_stage_finalized(self):
        """Pure knockout tournament: no group sessions, knockout_sessions → finalized=True, bracket built."""
        tourn = _tourn()

        # Knockout session with results
        game_res = {"raw_results": [{"user_id": 42, "score": 2},
                                    {"user_id": 43, "score": 1}]}
        ko_sess = _session(2, game_results=game_res,
                           participant_user_ids=[42, 43],
                           phase="KNOCKOUT", round_num=1, match_number=1)

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),            # no group sessions
            _q(count=1),            # total_matches
            _q(count=1),            # completed_matches
            _q(all_=[ko_sess]),     # knockout sessions (else branch → finalized)
            _q(first=None),         # individual_session (no IR format)
            # Pure knockout bracket (group_stage_finalized=True, knockout, not group)
            _q(first=user42),       # user in bracket participant loop (user42)
            _q(first=user43),       # user in bracket participant loop (user43)
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["group_stage_finalized"] is True
        assert result["knockout_bracket"] is not None
        assert len(result["knockout_bracket"]) == 1  # 1 round

    def test_200_knockout_all_complete_final_standings(self):
        """All knockout matches complete → final_standings with champion."""
        tourn = _tourn()

        # Final match (highest round)
        final_res = {"raw_results": [{"user_id": 42, "score": 3},
                                     {"user_id": 43, "score": 1}]}
        final_sess = _session(10, title="Grand Final",
                              game_results=final_res,
                              participant_user_ids=[42, 43],
                              phase="KNOCKOUT", round_num=2, match_number=1)

        # Group session to trigger the `if group_sessions:` branch
        group_res = {"raw_results": [{"user_id": 42, "score": 1},
                                     {"user_id": 43, "score": 0}]}
        group_sess = _session(5, game_results=group_res,
                              participant_user_ids=[42, 43],
                              group_identifier="A", phase="GROUP_STAGE")

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        db = _seq_db(
            _q(first=tourn),
            # group sessions present
            _q(all_=[group_sess]),
            # user queries for group standings
            _q(first=user42),
            _q(first=user43),
            # knockout sessions (if group_sessions branch): all complete → finalized
            _q(all_=[final_sess]),
            # final standings user lookup
            _q(all_=[user42, user43]),
            # individual_session
            _q(first=None),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["final_standings"] is not None
        champion = result["final_standings"][0]
        assert champion["rank"] == 1
        assert champion["user_id"] == 42

    def test_200_ir_finalized_game_results(self):
        """INDIVIDUAL_RANKING session with finalized game_results → performance_rankings."""
        tourn = _tourn()
        game_res = {
            "performance_rankings": [{"user_id": 42, "rank": 1, "best_score": 100}],
            "wins_rankings": [{"user_id": 42, "rank": 1, "wins": 3}],
        }
        ir_sess = _session(1, fmt="INDIVIDUAL_RANKING", game_results=game_res)

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),     # no group sessions
            _q(count=1),
            _q(count=1),
            _q(all_=[]),     # knockout
            _q(first=ir_sess),  # individual_session
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["performance_rankings"] is not None
        assert result["performance_rankings"][0]["user_id"] == 42

    def test_200_ir_finalized_with_derived_rankings_key(self):
        """IR game_results uses 'derived_rankings' (new ResultProcessor format)."""
        tourn = _tourn()
        game_res = {
            "derived_rankings": [{"user_id": 42, "rank": 1}],
        }
        ir_sess = _session(1, fmt="INDIVIDUAL_RANKING", game_results=game_res)

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=1),
            _q(all_=[]),
            _q(first=ir_sess),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["performance_rankings"] == [{"user_id": 42, "rank": 1}]

    def test_200_ir_live_rounds_data_score_based(self):
        """INDIVIDUAL_RANKING session NOT finalized: live calculation from rounds_data."""
        tourn = _tourn()
        rounds_data = {
            "round_results": {
                "1": {"42": "10", "43": "8"},   # round 1: 42 scored 10, 43 scored 8
                "2": {"42": "7", "43": "9"},    # round 2: 43 wins
            }
        }
        ir_sess = _session(1, fmt="INDIVIDUAL_RANKING", game_results=None,
                           rounds_data=rounds_data, scoring_type="SCORE_BASED")

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),      # no group sessions
            _q(count=2),
            _q(count=0),
            _q(all_=[]),      # knockout
            _q(first=ir_sess),  # individual session → IR
            # User queries inside live rankings calculation
            _q(first=user42),
            _q(first=user43),
            # Wins rankings: user queries again
            _q(first=user42),
            _q(first=user43),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        # SCORE_BASED: sum of scores → 42: 17, 43: 17 (tie)
        assert result["performance_rankings"] is not None
        assert result["wins_rankings"] is not None

    def test_200_ir_live_rounds_time_based(self):
        """INDIVIDUAL_RANKING, TIME_BASED: lower score = better → sorted ASC."""
        tourn = _tourn()
        rounds_data = {
            "round_results": {
                "1": {"42": "5.2", "43": "6.1"},  # 42 is faster
            }
        }
        ir_sess = _session(1, fmt="INDIVIDUAL_RANKING", game_results=None,
                           rounds_data=rounds_data, scoring_type="TIME_BASED")

        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
            _q(first=user42),
            _q(first=user43),
            _q(first=user42),
            _q(first=user43),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        perf = result["performance_rankings"]
        # Time-based: 42 (5.2s) should rank higher than 43 (6.1s)
        assert perf[0]["user_id"] == 42

    def test_200_assigned_instructor_has_full_access(self):
        """Assigned instructor (master_id matches) → no 403, gets leaderboard."""
        tourn = _tourn(master_id=10)
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),    # no group
            _q(count=0),
            _q(count=0),
            _q(all_=[]),    # knockout
            _q(first=None),
        )
        db.execute.return_value.fetchall.return_value = []

        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        result = _run(get_tournament_leaderboard(1, current_user=instructor, db=db))
        assert result["tournament_id"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# get_tournament_sessions_debug
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTournamentSessionsDebug:
    """get_tournament_sessions_debug — 404 / auth / sessions loop / exception."""

    def test_404_tournament_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_instructor_not_assigned(self):
        tourn = _tourn(master_id=99)
        db = _seq_db(_q(first=tourn))
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            get_tournament_sessions_debug(1, db=db, current_user=instructor)
        assert exc.value.status_code == 403

    def test_403_student_role(self):
        tourn = _tourn()
        db = _seq_db(_q(first=tourn))
        student = _user(uid=5, role=UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            get_tournament_sessions_debug(1, db=db, current_user=student)
        assert exc.value.status_code == 403

    def test_200_admin_no_sessions(self):
        """Admin, no sessions → empty list."""
        tourn = _tourn()
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),    # sessions query
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert result == []

    def test_200_session_with_participants_and_dict_results(self):
        """Sessions loop: participant name lookup + dict game_results."""
        tourn = _tourn()
        game_res = {"winner": 42, "scores": [3, 1]}
        sess = _session(1, participant_user_ids=[42], game_results=game_res,
                        phase="GROUP_STAGE")

        user42 = _user(uid=42, name="Alice")

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[sess]),     # sessions
            _q(first=user42),    # user for participant 42
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert len(result) == 1
        assert result[0]["participant_names"] == ["Alice"]
        assert result[0]["game_results"] == game_res

    def test_200_session_with_json_string_results(self):
        """game_results stored as JSON string → parsed to dict."""
        tourn = _tourn()
        game_res = {"scores": [5, 2]}
        sess = _session(1, participant_user_ids=[], game_results=_json.dumps(game_res))

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[sess]),
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert result[0]["game_results"] == game_res

    def test_200_session_matchup_display_from_structure_config(self):
        """structure_config with 'matchup' key → matchup_display set."""
        tourn = _tourn()
        sess = _session(1, participant_user_ids=[], game_results=None)
        sess.structure_config = {"matchup": "A1 vs B2"}

        db = _seq_db(
            _q(first=tourn),
            _q(all_=[sess]),
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert result[0]["matchup_display"] == "A1 vs B2"

    def test_500_unexpected_exception(self):
        """Non-HTTP exception → caught, re-raised as 500."""
        db = _seq_db(_q(first=_tourn()))
        # Second query (sessions) raises unexpected error
        calls = [0]
        def _boom(*a, **kw):
            calls[0] += 1
            if calls[0] == 1:
                return _q(first=_tourn())
            raise RuntimeError("Unexpected DB error")
        db.query.side_effect = _boom

        with pytest.raises(HTTPException) as exc:
            get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert exc.value.status_code == 500
        assert "Unexpected DB error" in exc.value.detail
