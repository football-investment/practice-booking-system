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


# ═══════════════════════════════════════════════════════════════════════════════
# get_tournament_leaderboard — gap tests (Sprint 22)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTournamentLeaderboardGaps:
    """
    Gap-fill tests targeting remaining uncovered branches in get_tournament_leaderboard.

    Targets (instructor.py):
      lines 450-451   — group session: invalid JSON string → JSONDecodeError → continue
      lines 456-457   — group session: list-format results (old format)
      line  459       — group session: non-dict/str/list → else: continue
      line  570 FALSE — knockout not all complete → final_standings=None
      lines 606-608   — final: p2 wins
      lines 609-612   — final: tie → first player champion
      lines 619-642   — bronze match determines 3rd/4th place
      lines 673-689   — 3rd / 4th place final_standings entries
      line  726       — rounds_data stored as JSON string → parsed
      line  730 FALSE — empty round_results → skip live calculation
      lines 748-749   — invalid value string → ValueError → 0.0
      line  770       — ROUNDS_BASED scoring
      line  774       — else/default scoring
      line  837 FALSE — empty round_scores → skip winner determination
      lines 929-930   — knockout bracket: p2 wins
    """

    # ── Group session result format edge cases ─────────────────────────────────

    def test_group_session_invalid_json_string_skipped(self):
        """game_results is a non-parseable JSON string → JSONDecodeError → continue."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        group_sess = _session(
            1, game_results="not-json{bad",
            participant_user_ids=[42, 43],
            group_identifier="A", phase="GROUP_STAGE",
        )
        db = _seq_db(
            _q(first=tourn),        # q0: tournament
            _q(all_=[group_sess]),  # q1: group sessions
            _q(first=user42),       # q2: user42 for standings
            _q(first=user43),       # q3: user43 for standings
            _q(all_=[]),            # q4: knockout sessions (group branch)
            _q(first=None),         # q5: individual session
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["group_standings"]["A"]
        for player in standings:
            assert player["wins"] == 0
            assert player["losses"] == 0

    def test_group_session_list_format_results(self):
        """game_results is a Python list (old format) → elif isinstance(results, list) branch."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        game_res = [{"user_id": 42, "score": 3}, {"user_id": 43, "score": 1}]
        group_sess = _session(
            1, game_results=game_res,
            participant_user_ids=[42, 43],
            group_identifier="F", phase="GROUP_STAGE",
        )
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
        standings = result["group_standings"]["F"]
        alice = next(p for p in standings if p["user_id"] == 42)
        assert alice["wins"] == 1

    def test_group_session_non_dict_str_list_results_skipped(self):
        """game_results is an integer (unexpected type) → else: continue."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        group_sess = _session(
            1, game_results=12345,
            participant_user_ids=[42, 43],
            group_identifier="G", phase="GROUP_STAGE",
        )
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
        standings = result["group_standings"]["G"]
        for player in standings:
            assert player["wins"] == 0

    # ── Knockout: not all complete ──────────────────────────────────────────────

    def test_knockout_not_all_complete_no_final_standings(self):
        """
        Pure knockout, one match not complete → all_knockout_complete=False
        → final_standings stays None.  Also builds bracket with no winner.
        """
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        ko_sess = _session(
            2, title="Semifinal", game_results=None,
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=1, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),      # q0
            _q(all_=[]),          # q1: no group sessions
            _q(count=1),          # q2: total_matches
            _q(count=0),          # q3: completed_matches
            _q(all_=[ko_sess]),   # q4: knockout → group_stage_finalized=True
            _q(first=None),       # q5: individual session
            _q(first=user42),     # q6: bracket participant 42
            _q(first=user43),     # q7: bracket participant 43
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["final_standings"] is None
        assert result["knockout_bracket"] is not None

    # ── Final standings: p2 wins and tie ───────────────────────────────────────

    def test_final_standings_p2_wins_and_bracket_p2_winner(self):
        """
        Final match p2 score > p1 → champion=p2.
        Also exercises knockout bracket p2-wins path (lines 929-930).
        """
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        final_res = {"raw_results": [{"user_id": 42, "score": 1},
                                     {"user_id": 43, "score": 3}]}
        final_sess = _session(
            10, title="Grand Final", game_results=final_res,
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=1, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),           # q0
            _q(all_=[]),               # q1: no group
            _q(count=1),               # q2
            _q(count=1),               # q3
            _q(all_=[final_sess]),     # q4: knockout
            _q(all_=[user42, user43]), # q5: users for final_standings
            _q(first=None),            # q6: individual session
            _q(first=user42),          # q7: bracket participant 42
            _q(first=user43),          # q8: bracket participant 43
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["final_standings"] is not None
        champion = result["final_standings"][0]
        assert champion["rank"] == 1
        assert champion["user_id"] == 43  # p2 wins
        runner_up = result["final_standings"][1]
        assert runner_up["user_id"] == 42
        bracket_match = result["knockout_bracket"][0]["matches"][0]
        assert bracket_match["winner"] == 43

    def test_final_standings_tie_first_player_is_champion(self):
        """Final match tie (equal scores) → champion = first player (p1)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        final_res = {"raw_results": [{"user_id": 42, "score": 2},
                                     {"user_id": 43, "score": 2}]}
        final_sess = _session(
            10, title="Grand Final", game_results=final_res,
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=1, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=1),
            _q(all_=[final_sess]),
            _q(all_=[user42, user43]),
            _q(first=None),
            _q(first=user42),
            _q(first=user43),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["final_standings"] is not None
        champion = result["final_standings"][0]
        assert champion["user_id"] == 42  # tie → first player

    # ── Bronze match (3rd / 4th place) ─────────────────────────────────────────

    def test_final_standings_with_bronze_match_full_podium(self):
        """
        Bronze match exists → 3rd and 4th place in final_standings.
        Covers lines 619-642 (bronze parsing) and 673-689 (3rd/4th entries).
        """
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        user44 = _user(uid=44, name="Charlie")
        user45 = _user(uid=45, name="Dave")
        bronze_res = {"raw_results": [{"user_id": 44, "score": 3},
                                      {"user_id": 45, "score": 1}]}
        bronze_sess = _session(
            9, title="3rd Place Match", game_results=bronze_res,
            participant_user_ids=[44, 45],
            phase="KNOCKOUT", round_num=1, match_number=2,
        )
        final_res = {"raw_results": [{"user_id": 42, "score": 3},
                                     {"user_id": 43, "score": 1}]}
        final_sess = _session(
            10, title="Grand Final", game_results=final_res,
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=2, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),                              # q0
            _q(all_=[]),                                  # q1: no group
            _q(count=2),                                  # q2
            _q(count=2),                                  # q3
            _q(all_=[bronze_sess, final_sess]),           # q4: knockout
            _q(all_=[user42, user43, user44, user45]),    # q5: users for final_standings
            _q(first=None),                               # q6: individual
            # bracket (sorted by round: round1=bronze, round2=final)
            _q(first=user44),  # q7: bronze participant 44
            _q(first=user45),  # q8: bronze participant 45
            _q(first=user42),  # q9: final participant 42
            _q(first=user43),  # q10: final participant 43
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["final_standings"]
        assert standings is not None
        assert len(standings) == 4
        assert standings[0]["user_id"] == 42  # champion
        assert standings[1]["user_id"] == 43  # runner-up
        assert standings[2]["user_id"] == 44  # 3rd place
        assert standings[3]["user_id"] == 45  # 4th place
        assert standings[2]["rank"] == 3
        assert standings[3]["rank"] == 4

    # ── IR live rounds_data edge cases ─────────────────────────────────────────

    def test_live_rounds_string_rounds_data_is_parsed(self):
        """rounds_data stored as JSON string → parsed before processing (line 726)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        rounds_data_dict = {"round_results": {"1": {"42": "10", "43": "8"}}}
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING", game_results=None,
            rounds_data=_json.dumps(rounds_data_dict),
            scoring_type="SCORE_BASED",
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
            _q(first=user42),  # perf user 42
            _q(first=user43),  # perf user 43
            _q(first=user42),  # wins user 42
            _q(first=user43),  # wins user 43
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["performance_rankings"] is not None
        assert len(result["performance_rankings"]) == 2

    def test_live_rounds_empty_round_results_skips_calculation(self):
        """rounds_data has empty round_results → live ranking not computed (line 730 FALSE)."""
        tourn = _tourn()
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING", game_results=None,
            rounds_data={"round_results": {}},
            scoring_type="SCORE_BASED",
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=0),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["performance_rankings"] is None

    def test_live_rounds_invalid_value_string_falls_back_to_zero(self):
        """
        Round value "abc" cannot be parsed → ValueError → numeric_value = 0.0.
        Covers lines 748-749 (perf loop) and 832-833 (wins loop).
        """
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING", game_results=None,
            rounds_data={"round_results": {"1": {"42": "abc", "43": "7"}}},
            scoring_type="SCORE_BASED",
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
            _q(first=user42),  # perf user42 (score=0.0)
            _q(first=user43),  # perf user43 (score=7.0)
            _q(first=user42),  # wins user42
            _q(first=user43),  # wins user43
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        perf = result["performance_rankings"]
        assert perf is not None
        alice = next(p for p in perf if p["user_id"] == 42)
        bob = next(p for p in perf if p["user_id"] == 43)
        assert alice["best_score"] == 0.0  # "abc" → fallback 0.0
        assert bob["best_score"] == 7.0

    def test_live_rounds_rounds_based_scoring_uses_max(self):
        """ROUNDS_BASED: best_score = max(scores) per user (line 770)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING", game_results=None,
            rounds_data={"round_results": {"1": {"42": "5"}, "2": {"42": "8"}}},
            scoring_type="ROUNDS_BASED",
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=2),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
            _q(first=user42),  # perf
            _q(first=user42),  # wins
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        perf = result["performance_rankings"]
        assert perf is not None
        assert perf[0]["best_score"] == 8.0  # max(5, 8) = 8

    def test_live_rounds_default_scoring_type_uses_max(self):
        """Unknown scoring_type → else branch: best_score = max(scores) (line 774)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING", game_results=None,
            rounds_data={"round_results": {"1": {"42": "9"}}},
            scoring_type="DISTANCE_BASED",
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
            _q(first=user42),
            _q(first=user42),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["performance_rankings"][0]["best_score"] == 9.0

    def test_live_rounds_wins_ranking_empty_round_scores_skips_winner(self):
        """
        Round with no user scores → round_scores={} → if round_scores: False (line 837 FALSE).
        Round 1 is normal; round 2 is empty → only round 1 winner counted.
        """
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING", game_results=None,
            rounds_data={"round_results": {"1": {"42": "5"}, "2": {}}},
            scoring_type="SCORE_BASED",
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=2),
            _q(count=0),
            _q(all_=[]),
            _q(first=ir_sess),
            _q(first=user42),  # perf
            _q(first=user42),  # wins
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        wins = result["wins_rankings"]
        assert wins is not None
        assert wins[0]["user_id"] == 42
        assert wins[0]["wins"] == 1  # only round 1 winner counted


# ═══════════════════════════════════════════════════════════════════════════════
# get_tournament_sessions_debug — gap tests (Sprint 22)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetTournamentSessionsDebugGaps:
    """
    Gap-fill tests for get_tournament_sessions_debug.

    Targets (instructor.py):
      line  1006      — assigned instructor passes auth check (print path)
      line  1034      — participant user not found → fallback "User {id}"
      lines 1047-1048 — invalid JSON game_results → except → raw string fallback
    """

    def test_assigned_instructor_gets_access(self):
        """Assigned instructor (master_id matches) → line 1006 print, no 403."""
        tourn = _tourn(master_id=10)
        instructor = _user(uid=10, role=UserRole.INSTRUCTOR)
        db = _seq_db(
            _q(first=tourn),  # q0: tournament
            _q(all_=[]),      # q1: sessions → empty
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=instructor)
        assert result == []

    def test_participant_user_not_found_uses_fallback_name(self):
        """Participant user_id with no DB record → appends 'User {id}' (line 1034)."""
        sess = _session(1, participant_user_ids=[999], game_results=None)
        db = _seq_db(
            _q(first=_tourn()),  # q0: tournament
            _q(all_=[sess]),     # q1: sessions
            _q(first=None),      # q2: user 999 → not found
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert result[0]["participant_names"] == ["User 999"]

    def test_invalid_json_game_results_falls_back_to_raw_string(self):
        """
        game_results is a non-parseable JSON string → bare except → raw string returned
        (lines 1047-1048).
        """
        sess = _session(1, participant_user_ids=[], game_results='{"broken": }')
        db = _seq_db(
            _q(first=_tourn()),  # q0
            _q(all_=[sess]),     # q1: sessions
        )
        result = get_tournament_sessions_debug(1, db=db, current_user=_user())
        assert result[0]["game_results"] == '{"broken": }'


# ═══════════════════════════════════════════════════════════════════════════════
# Additional targeted gap tests (Sprint 22 — push to ≥95%)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLeaderboardAdditionalGaps:
    """
    Covers remaining uncovered statements for get_tournament_leaderboard:
      lines 486-488   — group stage: p2 wins (score2 > score1)
      line  588       — final match game_results stored as JSON string
      line  713       — IR finalized game_results stored as JSON string
      lines 917-918   — bracket: session game_results stored as JSON string
      lines 636-638   — bronze match: p2 wins (third_place = p2)
    """

    def test_group_session_p2_wins_updates_stats(self):
        """Group stage: p2 score(3) > p1 score(1) → p2 wins, p1 loses (lines 486-488)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        game_res = {"raw_results": [{"user_id": 42, "score": 1},
                                    {"user_id": 43, "score": 3}]}
        group_sess = _session(
            1, game_results=game_res,
            participant_user_ids=[42, 43],
            group_identifier="H", phase="GROUP_STAGE",
        )
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
        standings = result["group_standings"]["H"]
        bob = next(p for p in standings if p["user_id"] == 43)
        alice = next(p for p in standings if p["user_id"] == 42)
        assert bob["wins"] == 1
        assert alice["losses"] == 1

    def test_final_standings_json_string_game_results(self):
        """final_match.game_results stored as JSON string → json.loads (line 588)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        final_res = {"raw_results": [{"user_id": 42, "score": 2},
                                     {"user_id": 43, "score": 1}]}
        final_sess = _session(
            10, title="Grand Final",
            game_results=_json.dumps(final_res),
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=1, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=1),
            _q(all_=[final_sess]),
            _q(all_=[user42, user43]),
            _q(first=None),
            _q(first=user42),
            _q(first=user43),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        assert result["final_standings"] is not None
        assert result["final_standings"][0]["user_id"] == 42

    def test_ir_finalized_game_results_as_json_string(self):
        """IR finalized: game_results stored as JSON string → json.loads (line 713)."""
        tourn = _tourn()
        game_res = {"performance_rankings": [{"user_id": 42, "rank": 1}],
                    "wins_rankings": [{"user_id": 42, "rank": 1, "wins": 3}]}
        ir_sess = _session(
            1, fmt="INDIVIDUAL_RANKING",
            game_results=_json.dumps(game_res),
        )
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

    def test_knockout_bracket_json_string_game_results(self):
        """Bracket session game_results stored as JSON string → lines 917-918."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        game_res = {"raw_results": [{"user_id": 42, "score": 3},
                                    {"user_id": 43, "score": 1}]}
        ko_sess = _session(
            2, title="Final",
            game_results=_json.dumps(game_res),
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=1, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=1),
            _q(count=1),
            _q(all_=[ko_sess]),
            _q(all_=[user42, user43]),
            _q(first=None),
            _q(first=user42),
            _q(first=user43),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        bracket_match = result["knockout_bracket"][0]["matches"][0]
        assert bracket_match["winner"] == 42

    def test_bronze_match_p2_wins_gets_third_place(self):
        """Bronze match p2 score > p1 → third_place=p2, fourth_place=p1 (lines 636-638)."""
        tourn = _tourn()
        user42 = _user(uid=42, name="Alice")
        user43 = _user(uid=43, name="Bob")
        user44 = _user(uid=44, name="Charlie")
        user45 = _user(uid=45, name="Dave")
        bronze_res = {"raw_results": [{"user_id": 44, "score": 1},
                                      {"user_id": 45, "score": 3}]}
        bronze_sess = _session(
            9, title="3rd Place Match", game_results=bronze_res,
            participant_user_ids=[44, 45],
            phase="KNOCKOUT", round_num=1, match_number=2,
        )
        final_res = {"raw_results": [{"user_id": 42, "score": 3},
                                     {"user_id": 43, "score": 1}]}
        final_sess = _session(
            10, title="Grand Final", game_results=final_res,
            participant_user_ids=[42, 43],
            phase="KNOCKOUT", round_num=2, match_number=1,
        )
        db = _seq_db(
            _q(first=tourn),
            _q(all_=[]),
            _q(count=2),
            _q(count=2),
            _q(all_=[bronze_sess, final_sess]),
            _q(all_=[user42, user43, user44, user45]),
            _q(first=None),
            _q(first=user44), _q(first=user45),
            _q(first=user42), _q(first=user43),
        )
        db.execute.return_value.fetchall.return_value = []

        result = _run(get_tournament_leaderboard(1, current_user=_user(), db=db))
        standings = result["final_standings"]
        third = next(p for p in standings if p["rank"] == 3)
        fourth = next(p for p in standings if p["rank"] == 4)
        assert third["user_id"] == 45
        assert fourth["user_id"] == 44
