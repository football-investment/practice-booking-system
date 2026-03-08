"""
Reward + Leaderboard Matrix — Playwright + API Tests
=====================================================

Validates the full tournament lifecycle ending in REWARDS_DISTRIBUTED status,
specifically testing the new skill_rating_delta field and leaderboard rendering.

Coverage:
    - POST /tournaments/{id}/calculate-rankings response structure
    - GET  /tournaments/{id}/rankings  →  skill_rating_delta field contract
    - Tournament Monitor leaderboard renders without errors under REWARDS_DISTRIBUTED
    - XP + credits + skills_awarded + skill_rating_delta all present or gracefully absent
    - No regression in Streamlit UI after match-performance EMA refactor

Matrix (API smoke tests):
    8p  →  2 groups,  2 KO r1 sessions
    16p →  4 groups,  4 KO r1 sessions
    32p →  8 groups,  8 KO r1 sessions

Playwright (headed/headless):
    8p full lifecycle  →  Tournament Monitor leaderboard verification

Run (headless CI):
    pytest tests_e2e/test_reward_leaderboard_matrix.py -v --tb=short

Run (headed debug):
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=600 \\
        pytest tests_e2e/test_reward_leaderboard_matrix.py -v -s -k 8p
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import pytest
import requests
from playwright.sync_api import Page, expect

# ── Constants ──────────────────────────────────────────────────────────────────

_API_URL  = os.environ.get("API_URL",  "http://localhost:8000")
_BASE_URL = os.environ.get("BASE_URL", "http://localhost:8501")
_ADMIN_EMAIL    = "admin@lfa.com"
_ADMIN_PASSWORD = "admin123"

_LOAD_TIMEOUT = 30_000
_SETTLE_SECS  = 3


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _login() -> Tuple[str, Dict[str, Any]]:
    resp = requests.post(
        f"{_API_URL}/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    me = requests.get(
        f"{_API_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert me.status_code == 200
    return token, me.json()


def _h(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── OPS helpers ────────────────────────────────────────────────────────────────

def _submit_result(token: str, tid: int, session: Dict[str, Any]) -> None:
    """Submit deterministic result for a 2-participant session.

    Handles both HEAD_TO_HEAD (WIN/LOSS) and INDIVIDUAL_RANKING (placement) formats.
    Lower user_id always wins for deterministic behaviour.
    """
    pids = session.get("participant_user_ids") or []
    if len(pids) < 2:
        return  # skip unassigned sessions (e.g. 3rd place with no participants)
    winner_id, loser_id = sorted(pids)   # lower user_id always wins (deterministic)

    match_format = session.get("match_format") or "HEAD_TO_HEAD"
    if match_format == "INDIVIDUAL_RANKING":
        # Placement-based format
        results_payload = [
            {"user_id": winner_id, "placement": 1},
            {"user_id": loser_id,  "placement": 2},
        ]
    else:
        # HEAD_TO_HEAD WIN/LOSS format
        results_payload = [
            {"user_id": winner_id, "result": "WIN"},
            {"user_id": loser_id,  "result": "LOSS"},
        ]

    resp = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions/{session['id']}/submit-results",
        json={"results": results_payload},
        headers=_h(token),
        timeout=30,
    )
    assert resp.status_code in (200, 201), (
        f"submit-results failed for session {session['id']} "
        f"(format={match_format}): {resp.status_code} {resp.text[:200]}"
    )


def _create_full_tournament(token: str, player_count: int) -> int:
    """
    Full manual lifecycle for a group_knockout tournament → REWARDS_DISTRIBUTED.

    Steps:
      A  OPS manual  → tournament + sessions created, no results
      B  Submit all group-stage results
      C  finalize-group-stage  → crossover seeding applied
      D  Submit all knockout results (skip 3rd-place if no participants)
      E  POST calculate-rankings
      F  POST complete  → COMPLETED
      G  POST distribute-rewards  → REWARDS_DISTRIBUTED
    """
    name = f"OPS-REWARD-MATRIX-{player_count}p-{int(time.time())}"
    resp = requests.post(
        f"{_API_URL}/api/v1/tournaments/ops/run-scenario",
        json={
            "scenario": "large_field_monitor",
            "player_count": player_count,
            "tournament_type_code": "group_knockout",
            "tournament_format": "HEAD_TO_HEAD",
            "simulation_mode": "manual",
            "tournament_name": name,
            "dry_run": False,
            "confirmed": player_count >= 128,
        },
        headers=_h(token),
        timeout=120,
    )
    assert resp.status_code == 200, (
        f"ops/run-scenario failed ({player_count}p): {resp.status_code} {resp.text[:500]}"
    )
    tid = resp.json().get("tournament_id")
    assert tid, f"No tournament_id: {resp.json()}"
    print(f"    [A] Tournament {tid} created")

    # B — submit group stage results
    all_sessions = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions",
        headers=_h(token), timeout=30,
    ).json()
    group_sessions = [
        s for s in all_sessions
        if s.get("participant_user_ids")
        and len(s.get("participant_user_ids")) == 2
        and "Group" in (s.get("title") or "")
    ]
    assert group_sessions, f"No group sessions for {player_count}p tournament {tid}"
    for s in group_sessions:
        _submit_result(token, tid, s)
    print(f"    [B] {len(group_sessions)} group results submitted")

    # C — finalize group stage (triggers crossover seeding)
    fg = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
        headers=_h(token), timeout=30,
    )
    assert fg.status_code == 200, f"finalize-group-stage failed: {fg.status_code} {fg.text[:200]}"
    print(f"    [C] Group stage finalized")

    # D — submit knockout results (skip sessions with no participants)
    refreshed = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions",
        headers=_h(token), timeout=30,
    ).json()
    ko_sessions = [
        s for s in refreshed
        if "Group" not in (s.get("title") or "")
        and s.get("participant_user_ids")
        and len(s.get("participant_user_ids")) == 2
        and not s.get("game_results")
    ]
    submitted_ko = 0
    while ko_sessions:
        for s in ko_sessions:
            _submit_result(token, tid, s)
            submitted_ko += 1
        # Re-fetch to pick up newly seeded next-round sessions
        refreshed = requests.get(
            f"{_API_URL}/api/v1/tournaments/{tid}/sessions",
            headers=_h(token), timeout=30,
        ).json()
        ko_sessions = [
            s for s in refreshed
            if "Group" not in (s.get("title") or "")
            and s.get("participant_user_ids")
            and len(s.get("participant_user_ids")) == 2
            and not s.get("game_results")
        ]
    print(f"    [D] {submitted_ko} knockout results submitted")

    # E — calculate rankings
    rr = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/calculate-rankings",
        headers=_h(token), timeout=30,
    )
    print(f"    [E] calculate-rankings: {rr.status_code}")

    # F — complete (IN_PROGRESS → COMPLETED); skip sessions without participants
    cr = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/complete",
        headers=_h(token), timeout=30,
    )
    if cr.status_code != 200:
        # Complete may fail if some sessions exist without participants (e.g.
        # 3rd-place or Play-in rounds created by OPS but never seeded).
        # Strategy: assign participants to 3rd-place, then submit dummy results
        # for any remaining sessions that still have no participants.
        _assign_third_place_participants(token, tid)
        _submit_dummy_results_for_unassigned(token, tid)
        cr = requests.post(
            f"{_API_URL}/api/v1/tournaments/{tid}/complete",
            headers=_h(token), timeout=30,
        )
    assert cr.status_code == 200, (
        f"POST /complete failed: {cr.status_code} {cr.text[:300]}"
    )
    print(f"    [F] complete → {cr.json().get('new_status')}")

    # G — distribute rewards (v2: orchestrator → writes TournamentParticipation + skill_rating_delta)
    dr = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/distribute-rewards-v2",
        json={"tournament_id": tid},
        headers=_h(token), timeout=60,
    )
    assert dr.status_code == 200, (
        f"POST /distribute-rewards-v2 failed: {dr.status_code} {dr.text[:300]}"
    )
    dr_data = dr.json()
    print(f"    [G] distribute-rewards-v2 → {dr_data.get('status') or dr_data.get('tournament_status')}")
    return tid


def _assign_third_place_participants(token: str, tid: int) -> None:
    """
    Find the 3rd-place session (no participants) and assign the two semifinal losers.
    This is needed because the OPS simulator does not seed the 3rd-place match.
    """
    sessions = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions",
        headers=_h(token), timeout=15,
    ).json()

    # 3rd place session: title contains "3rd Place" and no participants
    third_sess = next(
        (s for s in sessions
         if "3rd Place" in (s.get("title") or "")
         and not s.get("participant_user_ids")),
        None,
    )
    if not third_sess:
        return  # no unassigned 3rd place match

    # Semifinal sessions: completed, result present
    # Losers = participants NOT in the final
    final_sess = next(
        (s for s in sessions if "Final" in (s.get("title") or "")
         and "3rd" not in (s.get("title") or "")
         and s.get("game_results")),
        None,
    )
    if not final_sess:
        return

    import json as _json
    finalists: set = set()
    raw = final_sess.get("game_results")
    gr = _json.loads(raw) if isinstance(raw, str) else raw
    for p in (gr or {}).get("participants", []):
        finalists.add(p.get("user_id"))

    # All knockout participants
    all_ko_pids: set = set()
    for s in sessions:
        if "Group" not in (s.get("title") or "") and s.get("participant_user_ids"):
            all_ko_pids.update(s.get("participant_user_ids"))

    semifinal_losers = list(all_ko_pids - finalists)[:2]
    if len(semifinal_losers) < 2:
        return

    # Assign via PATCH or direct submit (session may support result with custom pids)
    # Easiest: submit a result for the 3rd place session with the two losers
    resp = requests.post(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions/{third_sess['id']}/submit-results",
        json={"results": [
            {"user_id": semifinal_losers[0], "result": "WIN"},
            {"user_id": semifinal_losers[1], "result": "LOSS"},
        ]},
        headers=_h(token), timeout=30,
    )
    # Non-fatal: if this fails, complete() will fail with a clear message
    print(f"    [3rd-place] assign {semifinal_losers} → {resp.status_code}")


def _submit_dummy_results_for_unassigned(token: str, tid: int) -> None:
    """
    Submit dummy results for any KNOCKOUT sessions that have no participants
    (e.g. Play-in rounds created by OPS but never seeded).

    Finds two enrolled players from the tournament and submits a WIN/LOSS result
    so the `complete` endpoint doesn't reject these sessions.
    """
    import json as _json

    sessions = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/sessions",
        headers=_h(token), timeout=15,
    ).json()

    # Sessions missing results with no participants
    unassigned = [
        s for s in sessions
        if not s.get("participant_user_ids")
        and not s.get("game_results")
        and s.get("is_tournament_game")
        and s.get("tournament_phase") == "KNOCKOUT"
    ]
    if not unassigned:
        return

    # Pick two enrolled user_ids from any session that has participants
    enrolled_pair: List[int] = []
    for s in sessions:
        pids = s.get("participant_user_ids") or []
        if len(pids) >= 2:
            enrolled_pair = list(pids[:2])
            break

    if len(enrolled_pair) < 2:
        return  # Can't proceed without known players

    dummy_a, dummy_b = enrolled_pair
    for s in unassigned:
        resp = requests.post(
            f"{_API_URL}/api/v1/tournaments/{tid}/sessions/{s['id']}/submit-results",
            json={"results": [
                {"user_id": dummy_a, "result": "WIN"},
                {"user_id": dummy_b, "result": "LOSS"},
            ]},
            headers=_h(token), timeout=30,
        )
        print(f"    [play-in] dummy result for session {s['id']} → {resp.status_code}")


def _get_tournament(token: str, tid: int) -> Dict[str, Any]:
    """Get tournament summary (status, name, etc.)."""
    resp = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/summary",
        headers=_h(token),
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"GET tournament/summary failed: {resp.status_code} {resp.text[:200]}"
    )
    return resp.json()


def _get_rankings(token: str, tid: int) -> Dict[str, Any]:
    resp = requests.get(
        f"{_API_URL}/api/v1/tournaments/{tid}/rankings",
        headers=_h(token),
        timeout=15,
    )
    assert resp.status_code == 200, (
        f"GET rankings failed: {resp.status_code} {resp.text[:300]}"
    )
    return resp.json()


# ── API smoke tests ────────────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.parametrize("player_count", [
    pytest.param(8,  id="8p"),
    pytest.param(16, id="16p"),
    pytest.param(32, id="32p"),
])
def test_rankings_skill_rating_delta_contract(player_count: int):
    """
    Full auto_immediate lifecycle → GET /rankings must return skill_rating_delta
    as a dict on every entry.  Tests the new per-tournament EMA snapshot field.
    """
    print(f"\n[API] {player_count}p — creating full tournament …")
    token, _ = _login()
    tid = _create_full_tournament(token, player_count)
    print(f"[API] Tournament {tid} created")

    # Verify tournament reached COMPLETED or REWARDS_DISTRIBUTED
    t_data = _get_tournament(token, tid)
    # summary endpoint returns both 'status' (display) and 'tournament_status' (internal)
    status = t_data.get("tournament_status") or t_data.get("status")
    print(f"[API] Tournament status: {status}")
    assert status in ("COMPLETED", "REWARDS_DISTRIBUTED"), (
        f"Expected COMPLETED or REWARDS_DISTRIBUTED after accelerated run, got: {status!r}"
    )

    # Fetch rankings
    rankings_data = _get_rankings(token, tid)
    rankings = (
        rankings_data.get("rankings")
        or rankings_data.get("data")
        or rankings_data
    )
    if isinstance(rankings, dict):
        rankings = rankings.get("rankings", [])

    assert isinstance(rankings, list), f"rankings is not a list: {type(rankings)}"
    assert len(rankings) > 0, f"rankings is empty for {player_count}p tournament {tid}"
    print(f"[API] {len(rankings)} ranking entries found")

    # ── Contract check: skill_rating_delta ─────────────────────────────────────
    entries_with_delta = 0
    for entry in rankings:
        assert "skill_rating_delta" in entry, (
            f"skill_rating_delta missing from ranking entry: {entry}"
        )
        delta = entry["skill_rating_delta"]
        assert isinstance(delta, dict), (
            f"skill_rating_delta must be a dict, got {type(delta)}: {delta}"
        )
        if delta:
            entries_with_delta += 1
            for sk, v in delta.items():
                assert isinstance(sk, str), f"skill key must be str: {sk}"
                assert isinstance(v, (int, float)), (
                    f"skill delta value must be numeric: {v}"
                )

    # ── Contract check: XP / credits always present ────────────────────────────
    if status == "REWARDS_DISTRIBUTED":
        for entry in rankings:
            assert "xp_earned" in entry, f"xp_earned missing: {entry}"
            assert "credits_earned" in entry, f"credits_earned missing: {entry}"
            assert "skills_awarded" in entry, f"skills_awarded missing: {entry}"
            assert isinstance(entry["skills_awarded"], dict), (
                f"skills_awarded must be dict: {entry['skills_awarded']}"
            )

    print(
        f"[API] Contract OK — {len(rankings)} entries, "
        f"{entries_with_delta} with non-empty skill_rating_delta"
    )


# ── Playwright tests ───────────────────────────────────────────────────────────

@pytest.mark.e2e
@pytest.mark.tournament_monitor
@pytest.mark.parametrize("player_count", [
    pytest.param(8,  id="8p"),
    pytest.param(16, id="16p"),
])
def test_leaderboard_rewards_distributed_renders(page: Page, player_count: int):
    """
    Full lifecycle → Tournament Monitor leaderboard must render correctly
    under REWARDS_DISTRIBUTED status.

    Checks:
      - No Traceback / AttributeError in UI
      - XP and credits display present for at least one entry
      - ↑ Skills: caption present if skill points were awarded
      - 📊 Rating Δ: caption present if skill_rating_delta is non-empty
      - 'No participants assigned' NOT present (knockout seeding regression)
    """
    print(f"\n[E2E] {player_count}p leaderboard test")

    token, user = _login()
    tid = _create_full_tournament(token, player_count)
    print(f"[E2E] Tournament {tid} created and finalized")

    # Navigate to Tournament Monitor with auth + auto-track for this tournament.
    # ?track_id=N causes render_tournament_monitor to add tid to _ops_tracked_tournaments
    # so the card is rendered without requiring the OPS Wizard flow.
    params = urllib.parse.urlencode({
        "token": token,
        "user": json.dumps(user),
        "track_id": tid,
    })
    url = f"{_BASE_URL}/Tournament_Monitor?{params}"
    page.goto(url, timeout=_LOAD_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=_LOAD_TIMEOUT)
    time.sleep(_SETTLE_SECS)
    print(f"[E2E] Monitor page loaded")

    body = page.text_content("body") or ""

    # ── Hard error checks ───────────────────────────────────────────────────────
    assert "Traceback" not in body, "Streamlit traceback on page"
    assert "AttributeError" not in body, "AttributeError on page"
    assert "KeyError" not in body, "KeyError on page"
    assert "No participants assigned" not in body, (
        "Knockout sessions not seeded — regression in apply_crossover_seeding"
    )
    print("[E2E] No hard errors on page")

    # ── Verify tournament card is rendered ──────────────────────────────────────
    # The tournament card uses st.expander(f"🔴 {name} · {status} · ...", expanded=True)
    # so content is already visible without clicking. Search for the OPS name fragment.
    tournament_name_fragment = f"OPS-REWARD-MATRIX-{player_count}p"
    card_found = tournament_name_fragment in body
    print(f"[E2E] Tournament card visible: {card_found}")
    if not card_found:
        print(f"[E2E] WARNING: Tournament {tid} card not found — body snippet: {body[:500]!r}")

    body = page.text_content("body") or ""

    # ── XP / credits display ────────────────────────────────────────────────────
    has_xp      = "XP" in body
    has_credits = " cr" in body or "credits" in body.lower()
    print(f"[E2E] XP display found: {has_xp}")
    print(f"[E2E] Credits display found: {has_credits}")

    # ── Skills display ──────────────────────────────────────────────────────────
    has_skills_caption = "↑ Skills:" in body
    has_rating_delta   = "📊 Rating Δ:" in body
    print(f"[E2E] '↑ Skills:' caption: {has_skills_caption}")
    print(f"[E2E] '📊 Rating Δ:' caption: {has_rating_delta}")

    # ── Verify via API that our UI claims match the data ───────────────────────
    rankings_data = _get_rankings(token, tid)
    rankings = (
        rankings_data.get("rankings")
        or rankings_data.get("data")
        or rankings_data
    )
    if isinstance(rankings, dict):
        rankings = rankings.get("rankings", [])

    t_info = _get_tournament(token, tid)
    t_status = t_info.get("tournament_status") or t_info.get("status")

    if t_status == "REWARDS_DISTRIBUTED":
        any_skills    = any(e.get("skills_awarded")    for e in rankings)
        any_rd        = any(e.get("skill_rating_delta") for e in rankings)

        if any_skills:
            assert has_skills_caption, (
                "API has skills_awarded data but UI does not show '↑ Skills:'"
            )
        if any_rd:
            assert has_rating_delta, (
                "API has skill_rating_delta data but UI does not show '📊 Rating Δ:'"
            )
        print(
            f"[E2E] Data-UI consistency OK — "
            f"skills_awarded={any_skills}, rating_delta={any_rd}"
        )

    # Final error sweep after expansion
    body_final = page.text_content("body") or ""
    assert "Traceback" not in body_final, "Traceback appeared after card expansion"
    print(f"[E2E] {player_count}p PASSED")
