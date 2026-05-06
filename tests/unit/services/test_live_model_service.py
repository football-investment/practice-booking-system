"""Unit tests for live_model_service — PR Live-2.

LM-01  build_live_model returns expected top-level keys
LM-02  format_type == 'group_knockout' when both phases present
LM-03  format_type == 'knockout' when only KNOCKOUT sessions
LM-04  format_type == 'league' fallback when no known phases
LM-05  group standings sorted Pts DESC → GD DESC → GF DESC → user_id ASC
LM-06  KO bracket pending match produces pending=True, matchup from structure_config
LM-07  KO bracket completed match produces result_label with player names
LM-08  sponsor_context is None when no organizer_sponsor / organizer_campaign
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_session(
    id=1,
    tournament_phase=None,
    group_identifier=None,
    game_type=None,
    session_status="planned",
    participant_user_ids=None,
    game_results=None,
    structure_config=None,
    tournament_match_number=1,
    round_number=1,
):
    from app.models.tournament_enums import TournamentPhase
    return SimpleNamespace(
        id=id,
        semester_id=99,
        tournament_phase=tournament_phase,
        group_identifier=group_identifier,
        game_type=game_type,
        session_status=session_status,
        participant_user_ids=participant_user_ids or [],
        game_results=game_results,
        structure_config=structure_config,
        tournament_match_number=tournament_match_number,
        round_number=round_number,
    )


def _make_user(id, first_name="Player", last_name=None):
    return SimpleNamespace(id=id, first_name=first_name, last_name=last_name or str(id))


def _make_tournament(id=99, name="Test", status="IN_PROGRESS", sponsor=None, campaign=None, type_code=None):
    tc = None
    if type_code:
        tt = SimpleNamespace(code=type_code, format="HEAD_TO_HEAD")
        tc = SimpleNamespace(tournament_type=tt, tournament_type_id=1, scoring_type="HEAD_TO_HEAD")
    return SimpleNamespace(
        id=id,
        name=name,
        tournament_status=status,
        organizer_sponsor=sponsor,
        organizer_campaign=campaign,
        tournament_config_obj=tc,
        game_config_obj=None,
    )


def _make_db(sessions, enrollments=None, users=None):
    db = MagicMock()

    def _query_side_effect(model):
        from app.models.session import Session as SessionModel
        from app.models.semester_enrollment import SemesterEnrollment
        from app.models.user import User
        q = MagicMock()
        if model is SessionModel:
            q.filter.return_value.order_by.return_value.all.return_value = sessions
        elif model is SemesterEnrollment:
            q.filter.return_value.filter.return_value.filter.return_value.all.return_value = (
                enrollments or []
            )
        elif model is User:
            ulist = users or []
            q.filter.return_value.all.return_value = ulist
        return q

    db.query.side_effect = _query_side_effect
    return db


# ── LM-01 ─────────────────────────────────────────────────────────────────────

def test_lm_01_build_live_model_top_level_keys():
    from app.services.tournament.live_model_service import build_live_model
    t = _make_tournament()
    db = _make_db(sessions=[])
    result = build_live_model(db, t)
    for key in ("format_type", "tournament_status", "summary", "instructor_roster",
                "sponsor_context", "group_stage", "knockout_bracket", "league_rounds",
                "league_standings"):
        assert key in result, f"Missing key: {key}"


# ── LM-02 ─────────────────────────────────────────────────────────────────────

def test_lm_02_format_type_group_knockout():
    from app.models.tournament_enums import TournamentPhase
    from app.services.tournament.live_model_service import build_live_model
    sessions = [
        _make_session(id=1, tournament_phase=TournamentPhase.GROUP_STAGE, group_identifier="A"),
        _make_session(id=2, tournament_phase=TournamentPhase.KNOCKOUT, game_type="Final"),
    ]
    t = _make_tournament()
    db = _make_db(sessions=sessions)
    result = build_live_model(db, t)
    assert result["format_type"] == "group_knockout"
    assert result["group_stage"] is not None
    assert result["knockout_bracket"] is not None


# ── LM-03 ─────────────────────────────────────────────────────────────────────

def test_lm_03_format_type_knockout():
    from app.models.tournament_enums import TournamentPhase
    from app.services.tournament.live_model_service import build_live_model
    sessions = [
        _make_session(id=1, tournament_phase=TournamentPhase.KNOCKOUT, game_type="Semi-finals"),
        _make_session(id=2, tournament_phase=TournamentPhase.KNOCKOUT, game_type="Final"),
    ]
    t = _make_tournament()
    db = _make_db(sessions=sessions)
    result = build_live_model(db, t)
    assert result["format_type"] == "knockout"
    assert result["group_stage"] is None
    assert result["knockout_bracket"] is not None


# ── LM-04 ─────────────────────────────────────────────────────────────────────

def test_lm_04_format_type_league_fallback():
    from app.services.tournament.live_model_service import build_live_model
    sessions = [_make_session(id=1, tournament_phase=None)]
    t = _make_tournament()
    db = _make_db(sessions=sessions)
    result = build_live_model(db, t)
    assert result["format_type"] == "league"


# ── LM-05 ─────────────────────────────────────────────────────────────────────

def test_lm_05_group_standings_tiebreaker():
    from app.services.tournament.live_model_service import _compute_group_standings

    # uid=1: 3pts, GD=+1, GF=2
    # uid=2: 3pts, GD=+1, GF=2  → tie-break by user_id → uid=1 first
    # uid=3: 0pts
    sessions = [
        _make_session(
            id=1,
            session_status="completed",
            game_results={
                "participants": [
                    {"user_id": 1, "score": 2, "result": "win"},
                    {"user_id": 3, "score": 1, "result": "loss"},
                ]
            },
        ),
        _make_session(
            id=2,
            session_status="completed",
            game_results={
                "participants": [
                    {"user_id": 2, "score": 2, "result": "win"},
                    {"user_id": 3, "score": 1, "result": "loss"},
                ]
            },
        ),
        _make_session(
            id=3,
            session_status="planned",
            game_results=None,
            participant_user_ids=[1, 2],
        ),
    ]
    users = {u.id: u for u in [_make_user(1), _make_user(2), _make_user(3)]}
    rows = _compute_group_standings(sessions, users)

    assert rows[0]["user_id"] == 1
    assert rows[1]["user_id"] == 2
    assert rows[2]["user_id"] == 3
    assert rows[0]["pts"] == 3
    assert rows[2]["pts"] == 0


# ── LM-06 ─────────────────────────────────────────────────────────────────────

def test_lm_06_ko_pending_match_uses_structure_config():
    from app.models.tournament_enums import TournamentPhase
    from app.services.tournament.live_model_service import _build_ko_match_row

    session = _make_session(
        id=10,
        tournament_phase=TournamentPhase.KNOCKOUT,
        game_type="Semi-finals",
        session_status="planned",
        participant_user_ids=[],
        structure_config={"matchup": "A1 vs BR", "round_name": "Semi-finals"},
    )
    row = _build_ko_match_row(session, {})
    assert row["pending"] is True
    assert "A1 vs BR" in row["matchup_label"] or "TBD" in row["matchup_label"]
    assert row["result_label"] is None


# ── LM-07 ─────────────────────────────────────────────────────────────────────

def test_lm_07_ko_completed_match_result_label():
    from app.models.tournament_enums import TournamentPhase
    from app.services.tournament.live_model_service import _build_ko_match_row

    u1 = _make_user(1, "Alice", "Smith")
    u2 = _make_user(2, "Bob", "Jones")
    users = {1: u1, 2: u2}

    session = _make_session(
        id=11,
        tournament_phase=TournamentPhase.KNOCKOUT,
        game_type="Final",
        session_status="completed",
        participant_user_ids=[1, 2],
        game_results={
            "participants": [
                {"user_id": 1, "score": 3, "result": "win"},
                {"user_id": 2, "score": 1, "result": "loss"},
            ],
            "winner_user_id": 1,
        },
    )
    row = _build_ko_match_row(session, users)
    assert row["pending"] is False
    assert "Alice Smith" in row["result_label"]
    assert "Bob Jones" in row["result_label"]


# ── LM-08 ─────────────────────────────────────────────────────────────────────

def test_lm_08_sponsor_context_none_when_no_sponsor():
    from app.services.tournament.live_model_service import _build_sponsor_context
    t = _make_tournament(sponsor=None, campaign=None)
    ctx = _build_sponsor_context(t, enrollment_count=5, checkin_count=3)
    assert ctx is None
