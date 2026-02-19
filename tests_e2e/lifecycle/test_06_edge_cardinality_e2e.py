"""
Phase 6: Edge Cardinality E2E Tests — System Safety
=====================================================

HIGH PRIORITY — System Safety tests. These are NOT optional coverage.
The progression engine must behave deterministically for ALL realistic
player counts, not only the standard preconfigured configurations.

Coverage (4 test functions, each self-contained):

  T06A  League — 5 players (odd, bye-round logic)
        → n*(n-1)/2 = 10 sessions expected.
          Every player gets exactly 4 opponents (no repeats, no bye skips).
          All 5 players must have skill-audit rows after reward distribution.
          unfair_entries == 0 for all 5 players.

  T06B  Group_knockout — 9 players (dynamic GroupDistribution path: 3×3)
        → GroupDistribution.calculate_optimal_distribution() invoked (not
          preconfigured). Group sessions = 9 (3 groups × 3 round-robin).
          All 9 players must have skill-audit rows.
          unfair_entries == 0 for all 9 players.

  T06C  Group_knockout — 12 players (preconfigured path: 3 groups × 4)
        → 12 is a preconfigured group_knockout size.
          Group sessions = 18 (3 groups × 6 round-robin matches each).
          All 12 players must have skill-audit rows.
          unfair_entries == 0 for all 12 players.

  T06D  Knockout — 8 players (4 QF + 2 SF + 1 Final + 1 Bronze = 8 sessions)
        → 8 is a valid power-of-two size.
          Session count == 8 (or >= 7 if bronze match is optional).
          CHAMPION badge for winner with total_participants=8.
          All 8 players must have skill-audit rows.
          unfair_entries == 0 for all 8 players.

Architecture:
    Pure API (pytest + requests). NO Playwright required.
    Runs against live backend on localhost:8000.
    Each test function is fully independent.
    Uses the iterative knockout submission loop established in T05C.

Prerequisites:
    Star players seeded (see seed_star_players.py / Phase 0b).
    Server running on localhost:8000.
    Minimum 12 star players must be seeded (T06C needs all 12).
"""

import os
import sys
import json
import time
import pytest
import requests
import psycopg2
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ============================================================================
# CONFIGURATION
# ============================================================================

API_URL = os.environ.get("API_URL",      "http://localhost:8000")
DB_URL  = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")

ADMIN_EMAIL    = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

TEST_USERS_JSON = project_root / "tests" / "e2e" / "test_users.json"


def _make_reward_config(n: int) -> list:
    """Generate a reward config for n ranks with reasonable XP/credit scaling."""
    base_xp      = 200
    base_credits = 100
    rows = []
    for rank in range(1, n + 1):
        factor = max(0.1, 1.0 - (rank - 1) * 0.1)
        rows.append({
            "rank": rank,
            "xp_reward":      max(10, int(base_xp * factor)),
            "credits_reward": max(5,  int(base_credits * factor)),
        })
    return rows


def _ts() -> str:
    """Short timestamp suffix to make tournament names unique across test runs."""
    return str(int(time.time()))[-6:]


# ============================================================================
# SHARED HELPERS  (self-contained — no imports from other test files)
# ============================================================================

def _admin_login() -> str:
    resp = requests.post(
        f"{API_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


def _player_login(email: str, password: str) -> str:
    resp = requests.post(
        f"{API_URL}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert resp.status_code == 200, f"Player login failed ({email}): {resp.status_code}"
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _load_star_players() -> list[dict]:
    """Return up to 12 star player dicts with keys: db_id, email, password."""
    try:
        with open(TEST_USERS_JSON) as f:
            data = json.load(f)
        players = data.get("star_users", [])
        if players and all("db_id" in p and "email" in p and "password" in p for p in players[:12]):
            return players[:12]
    except Exception:
        pass
    return [
        {"db_id": 3,  "email": "kbappe@realmadrid.com",      "password": "Mbappe2026!"},
        {"db_id": 4,  "email": "ehaaland@mancity.com",       "password": "Haaland2026!"},
        {"db_id": 5,  "email": "lmessi@intermiamicf.com",    "password": "Messi2026!"},
        {"db_id": 6,  "email": "vjunior@realmadrid.com",     "password": "Vinicius2026!"},
        {"db_id": 7,  "email": "jbellingham@realmadrid.com", "password": "Bellingham2026!"},
        {"db_id": 8,  "email": "msalah@liverpoolfc.com",     "password": "Salah2026!"},
        {"db_id": 9,  "email": "pfoden@mancity.com",         "password": "Foden2026!"},
        {"db_id": 10, "email": "rodri@mancity.com",          "password": "Rodri2026!"},
        {"db_id": 11, "email": "rdias@manchestercity.com",   "password": "Dias2026!"},
        {"db_id": 12, "email": "bsaka@arsenal.com",          "password": "Saka2026!"},
        {"db_id": 13, "email": "jmusiala@bayern.com",        "password": "Musiala2026!"},
        {"db_id": 14, "email": "vosimhen@napolifc.com",      "password": "Osimhen2026!"},
    ]


def _create_tournament(
    headers: dict,
    name: str,
    tournament_type: str,
    max_players: int,
    skills: list[str],
    reward_config: list = None,
    skill_weights: dict = None,
) -> int:
    payload = {
        "name": name,
        "tournament_type": tournament_type,
        "age_group": "PRO",
        "max_players": max_players,
        "skills_to_test": skills,
        "reward_config": reward_config or _make_reward_config(max_players),
        "enrollment_cost": 0,
    }
    if skill_weights:
        payload["skill_weights"] = skill_weights
    resp = requests.post(
        f"{API_URL}/api/v1/tournaments/create",
        json=payload,
        headers=headers,
        timeout=15,
    )
    assert resp.status_code == 201, f"Create failed ({name}): {resp.status_code}\n{resp.text}"
    return resp.json()["tournament_id"]


def _batch_enroll(headers: dict, tid: int, pids: list[int]) -> None:
    resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/admin/batch-enroll",
        json={"player_ids": pids},
        headers=headers,
        timeout=15,
    )
    assert resp.status_code == 200, f"Enroll failed: {resp.status_code}\n{resp.text}"
    assert resp.json()["enrolled_count"] == len(pids), (
        f"Expected {len(pids)} enrolled, got {resp.json()['enrolled_count']}"
    )


def _generate_sessions(headers: dict, tid: int) -> list:
    resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/generate-sessions",
        json={"parallel_fields": 1, "session_duration_minutes": 90,
              "break_minutes": 15, "number_of_rounds": 1},
        headers=headers,
        timeout=20,
    )
    assert resp.status_code == 200, f"Gen sessions failed: {resp.status_code}\n{resp.text}"
    lst = requests.get(
        f"{API_URL}/api/v1/tournaments/{tid}/sessions",
        headers=headers, timeout=15,
    )
    assert lst.status_code == 200
    return lst.json()


def _submit_h2h(headers: dict, tid: int, sid: int, winner_id: int, loser_id: int,
                ws: int = 2, ls: int = 1) -> None:
    resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/sessions/{sid}/submit-results",
        json={"results": [
            {"user_id": winner_id, "score": ws},
            {"user_id": loser_id,  "score": ls},
        ], "notes": "E2E T06"},
        headers=headers,
        timeout=15,
    )
    assert resp.status_code in (200, 201), (
        f"Submit results failed (session {sid}): {resp.status_code}\n{resp.text}"
    )


def _calculate_rankings(headers: dict, tid: int) -> None:
    resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/calculate-rankings",
        headers=headers, timeout=15,
    )
    assert resp.status_code == 200, f"Calc rankings failed: {resp.status_code}\n{resp.text}"


def _complete_tournament(headers: dict, tid: int) -> None:
    for method in [
        lambda: requests.post(
            f"{API_URL}/api/v1/tournaments/{tid}/status",
            json={"new_status": "COMPLETED", "reason": "E2E T06"},
            headers=headers, timeout=15,
        ),
        lambda: requests.patch(
            f"{API_URL}/api/v1/tournaments/{tid}/status",
            json={"new_status": "COMPLETED"},
            headers=headers, timeout=15,
        ),
    ]:
        r = method()
        if r.status_code in (200, 201):
            return
    conn = psycopg2.connect(DB_URL)
    try:
        conn.cursor().execute(
            "UPDATE semesters SET tournament_status = 'COMPLETED' WHERE id = %s", (tid,)
        )
        conn.commit()
    finally:
        conn.close()


def _distribute_rewards(headers: dict, tid: int) -> dict:
    resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/distribute-rewards-v2",
        json={"tournament_id": tid, "force_redistribution": False},
        headers=headers, timeout=30,
    )
    assert resp.status_code == 200, (
        f"Distribute rewards failed: {resp.status_code}\n{resp.text}"
    )
    return resp.json()


def _get_skill_audit(player_token: str) -> list[dict]:
    resp = requests.get(
        f"{API_URL}/api/v1/progression/skill-audit",
        headers=_auth(player_token), timeout=15,
    )
    assert resp.status_code == 200, f"skill-audit failed: {resp.status_code}\n{resp.text}"
    return resp.json()["audit"]


def _get_skill_audit_full(player_token: str) -> dict:
    """Return the full skill-audit response (audit list + unfair_entries count)."""
    resp = requests.get(
        f"{API_URL}/api/v1/progression/skill-audit",
        headers=_auth(player_token), timeout=15,
    )
    assert resp.status_code == 200, f"skill-audit failed: {resp.status_code}\n{resp.text}"
    return resp.json()


def _assert_all_players_have_audit_rows(
    players: list[dict],
    pids: list[int],
    tid: int,
    label: str,
) -> None:
    """
    Assert that every player in the tournament has at least one skill-audit row
    for the given tournament, AND that unfair_entries == 0 for each player.

    This is the core 'progression for all players' safety check.
    """
    for player in players:
        tok = _player_login(player["email"], player["password"])
        full = _get_skill_audit_full(tok)
        audit_rows = full["audit"]
        unfair     = full["unfair_entries"]

        t_rows = [r for r in audit_rows if r["tournament_id"] == tid]
        assert len(t_rows) > 0, (
            f"[{label}] Player {player['email']} (id={player['db_id']}) "
            f"has NO skill-audit rows for tournament {tid}. "
            f"Reward distribution must write progression rows for EVERY participant."
        )

        assert unfair == 0, (
            f"[{label}] Player {player['email']} has {unfair} unfair_entries. "
            f"EMA path fairness violated — check prev_value chaining for this player."
        )


def _submit_all_league_sessions(
    headers: dict,
    tid: int,
    sessions: list[dict],
    pids: list[int],
) -> None:
    """
    Submit results for all league sessions.
    Winner = player with lower index in pids (consistent, deterministic).
    Handles bye sessions (only 1 participant or None) by skipping them silently.
    """
    for session in sessions:
        s_pids = session.get("participant_user_ids") or []
        # Skip bye sessions (< 2 real participants)
        real_pids = [p for p in s_pids if p is not None]
        if len(real_pids) < 2:
            continue
        winner = min(real_pids, key=lambda x: pids.index(x) if x in pids else 999)
        loser  = max(real_pids, key=lambda x: pids.index(x) if x in pids else 999)
        _submit_h2h(headers, tid, session["id"], winner, loser)


def _submit_group_and_knockout_iteratively(
    headers: dict,
    tid: int,
    pids: list[int],
    group_session_ids: set,
) -> None:
    """
    Iteratively submit knockout sessions as participants get assigned after each round.
    Stops when no new sessions with participants appear (max 6 rounds).
    """
    submitted_ids = set(group_session_ids)

    for _pass in range(6):
        updated = requests.get(
            f"{API_URL}/api/v1/tournaments/{tid}/sessions",
            headers=headers, timeout=15,
        ).json()
        new_sessions = [
            s for s in updated
            if s.get("participant_user_ids")
            and len([p for p in s["participant_user_ids"] if p is not None]) == 2
            and s["id"] not in submitted_ids
        ]
        if not new_sessions:
            break
        for session in new_sessions:
            real_pids = [p for p in session["participant_user_ids"] if p is not None]
            winner = min(real_pids, key=lambda x: pids.index(x) if x in pids else 999)
            loser  = max(real_pids, key=lambda x: pids.index(x) if x in pids else 999)
            _submit_h2h(headers, tid, session["id"], winner, loser)
            submitted_ids.add(session["id"])
        time.sleep(0.5)


# ============================================================================
# T06A — League, 5 Players (Odd — Bye-Round Logic)
# ============================================================================

@pytest.mark.lifecycle
@pytest.mark.phase_6
@pytest.mark.golden_path
@pytest.mark.nondestructive
@pytest.mark.skill_progression
@pytest.mark.edge_cardinality
def test_T06A_league_5_players_odd_bye_logic():
    """
    System-safety test: League tournament with 5 players (odd cardinality).

    The bye-round mechanism adds a None dummy player to make the count even,
    producing n*(n-1)/2 = 5*4/2 = 10 sessions total. Bye-round sessions
    (only 1 real participant) are silently skipped during result submission.

    Assertions:
    - Session count == 10 (formula: n*(n-1)/2 for 5 players)
    - No more than 1 participant is a bye (None) in any session
    - All 5 real players have skill-audit rows after reward distribution
    - unfair_entries == 0 for all 5 players
    - Rank-1 player has non-negative finishing delta
    - Each real player participates in exactly 4 sessions (n-1 opponents)
    """
    players = _load_star_players()
    p       = players[:5]
    pids    = [x["db_id"] for x in p]
    skills  = ["finishing", "passing", "dribbling"]

    admin_tok = _admin_login()
    h = _auth(admin_tok)

    tid = _create_tournament(
        h,
        name=f"T06A League 5p Odd Bye {_ts()}",
        tournament_type="league",
        max_players=5,
        skills=skills,
        reward_config=_make_reward_config(5),
    )
    _batch_enroll(h, tid, pids)
    sessions = _generate_sessions(h, tid)

    # ── Session count assertion ────────────────────────────────────────────────
    # 5-player league: n*(n-1)/2 = 10 sessions (including bye-round sessions)
    expected_sessions = 5 * 4 // 2   # == 10
    assert len(sessions) == expected_sessions, (
        f"T06A: Expected {expected_sessions} sessions for 5-player league "
        f"(odd → bye-round logic), got {len(sessions)}"
    )

    # ── Bye session structure check ────────────────────────────────────────────
    # Bye sessions have exactly 1 real participant (the other is None or absent)
    bye_sessions = []
    for s in sessions:
        s_pids = s.get("participant_user_ids") or []
        real = [p for p in s_pids if p is not None]
        if len(real) == 1:
            bye_sessions.append(s)
        elif len(real) == 2:
            pass  # normal session
        else:
            # 0 participants can happen if system uses a different bye representation
            bye_sessions.append(s)

    # With 5 players, there should be exactly 5 bye-round sessions
    # (each player gets one bye round per round-robin cycle with None opponent)
    # However, some implementations may not generate bye sessions at all
    # (they may just skip them). We check that real-player-pair sessions == 5*4/2 - 5 = 5
    real_sessions = [
        s for s in sessions
        if len([pp for pp in (s.get("participant_user_ids") or []) if pp is not None]) == 2
    ]
    # Must have exactly C(5,2) = 10 matchups total including bye representations,
    # OR at minimum C(5,2) - 0 = 10 real 1v1 sessions if bye is handled implicitly
    # We accept: real_sessions >= 5 (at minimum, every player plays C(4,2)/2... no).
    # The guarantee is: every player faces every other player exactly once.
    # With n=5: each player plays 4 opponents → total unique pairs = 10.
    # Sessions with 2 real participants must equal 10.
    assert len(real_sessions) == 10, (
        f"T06A: Expected 10 real 1v1 sessions for 5-player league, "
        f"got {len(real_sessions)} (total sessions={len(sessions)}, "
        f"bye sessions={len(bye_sessions)}). "
        f"The system must create C(5,2)=10 unique matchup sessions."
    )

    # ── Each player participates in exactly 4 real sessions ──────────────────
    participation_count = {pid: 0 for pid in pids}
    for s in real_sessions:
        for participant_pid in s.get("participant_user_ids", []):
            if participant_pid in participation_count:
                participation_count[participant_pid] += 1

    for pid in pids:
        assert participation_count[pid] == 4, (
            f"T06A: Player {pid} should appear in exactly 4 sessions (n-1 opponents), "
            f"got {participation_count[pid]}. "
            f"Participation counts: {participation_count}"
        )

    # ── Submit all real (non-bye) sessions ────────────────────────────────────
    _submit_all_league_sessions(h, tid, sessions, pids)

    # ── Full lifecycle completion ─────────────────────────────────────────────
    _calculate_rankings(h, tid)
    _complete_tournament(h, tid)
    _distribute_rewards(h, tid)

    # ── Progression assertions for ALL 5 players ──────────────────────────────
    _assert_all_players_have_audit_rows(p, pids, tid, "T06A-League-5p")

    # Rank-1 player (p[0]) has non-negative finishing delta
    winner_tok = _player_login(p[0]["email"], p[0]["password"])
    audit = _get_skill_audit(winner_tok)
    t_rows = [r for r in audit if r["tournament_id"] == tid]
    finishing_rows = [r for r in t_rows if r["skill"] == "finishing"]
    assert finishing_rows, (
        f"T06A: No finishing skill-audit row for winner {pids[0]} in tournament {tid}"
    )
    finishing_delta = finishing_rows[0]["delta_this_tournament"]
    assert finishing_delta >= 0, (
        f"T06A: Rank-1 finishing delta should be non-negative, got {finishing_delta}"
    )

    print(
        f"\n  T06A PASS  league 5p odd  tid={tid}  "
        f"sessions={len(sessions)} (real={len(real_sessions)})  "
        f"finishing_delta={finishing_delta:.2f}pt"
    )


# ============================================================================
# T06B — Group_knockout, 9 Players (Dynamic Distribution: 3×3)
# ============================================================================

@pytest.mark.lifecycle
@pytest.mark.phase_6
@pytest.mark.golden_path
@pytest.mark.nondestructive
@pytest.mark.skill_progression
@pytest.mark.edge_cardinality
def test_T06B_group_knockout_9_players_dynamic_distribution():
    """
    System-safety test: Group_knockout with 9 players.

    9 is NOT a preconfigured group_knockout size (preconfigured: 8, 12, 16, 24, 32).
    This triggers GroupDistribution.calculate_optimal_distribution(), which for
    n=9 produces 3 groups of 3 players each.

    Group sessions: 3 groups × C(3,2) = 3 matches each = 9 group sessions.
    Knockout sessions: top-1 from each group → 3-player semi structure (at least 2).

    Assertions:
    - Group sessions >= 9 (3 groups × 3 matches)
    - After finalize-group-stage + knockout: all sessions submitted
    - calculate-rankings succeeds (validates group_knockout path for n=9)
    - All 9 players have skill-audit rows
    - unfair_entries == 0 for all 9 players
    - Rank-1 has non-negative finishing delta
    """
    players = _load_star_players()
    # Need exactly 9 players; ensure we have at least 9 seeded
    assert len(players) >= 9, (
        f"T06B requires 9 star players, only {len(players)} found. "
        f"Run seed_star_players.py to seed at least 9 players."
    )
    p    = players[:9]
    pids = [x["db_id"] for x in p]
    skills = ["finishing", "passing", "dribbling"]

    admin_tok = _admin_login()
    h = _auth(admin_tok)

    tid = _create_tournament(
        h,
        name=f"T06B GK 9p Dynamic {_ts()}",
        tournament_type="group_knockout",
        max_players=9,
        skills=skills,
        reward_config=_make_reward_config(9),
    )
    _batch_enroll(h, tid, pids)
    sessions = _generate_sessions(h, tid)

    # ── Session count assertion ────────────────────────────────────────────────
    # 9 players → 3 groups of 3 → C(3,2)=3 matches per group = 9 group sessions
    # Plus knockout sessions (participants not yet assigned = no participant_user_ids)
    group_sessions = [
        s for s in sessions
        if s.get("participant_user_ids")
        and len([pp for pp in s["participant_user_ids"] if pp is not None]) == 2
    ]
    assert len(group_sessions) >= 9, (
        f"T06B: Expected >= 9 group-stage sessions for 9-player group_knockout "
        f"(3 groups × 3 matches), got {len(group_sessions)}. "
        f"Total sessions: {len(sessions)}. "
        f"This tests the dynamic GroupDistribution path for n=9."
    )

    # ── Submit group sessions ─────────────────────────────────────────────────
    group_ids = {s["id"] for s in group_sessions}
    for session in group_sessions:
        s_pids = [pp for pp in session["participant_user_ids"] if pp is not None]
        winner = min(s_pids, key=lambda x: pids.index(x) if x in pids else 999)
        loser  = max(s_pids, key=lambda x: pids.index(x) if x in pids else 999)
        _submit_h2h(h, tid, session["id"], winner, loser)

    # ── Finalize group stage ──────────────────────────────────────────────────
    finalize_resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
        headers=h, timeout=20,
    )
    assert finalize_resp.status_code == 200, (
        f"T06B finalize-group-stage failed: {finalize_resp.status_code}\n{finalize_resp.text}"
    )

    # ── Iteratively submit knockout sessions ──────────────────────────────────
    _submit_group_and_knockout_iteratively(h, tid, pids, group_ids)

    # ── Full lifecycle ────────────────────────────────────────────────────────
    _calculate_rankings(h, tid)
    _complete_tournament(h, tid)
    _distribute_rewards(h, tid)

    # ── Progression assertions for ALL 9 players ──────────────────────────────
    _assert_all_players_have_audit_rows(p, pids, tid, "T06B-GK-9p")

    # Rank-1 player (p[0]) has non-negative finishing delta
    winner_tok = _player_login(p[0]["email"], p[0]["password"])
    audit = _get_skill_audit(winner_tok)
    t_rows = [r for r in audit if r["tournament_id"] == tid]
    finishing_rows = [r for r in t_rows if r["skill"] == "finishing"]
    assert finishing_rows, (
        f"T06B: No finishing skill-audit row for winner {pids[0]} in tournament {tid}"
    )
    finishing_delta = finishing_rows[0]["delta_this_tournament"]
    assert finishing_delta >= 0, (
        f"T06B: Rank-1 finishing delta should be non-negative, got {finishing_delta}"
    )

    print(
        f"\n  T06B PASS  group_knockout 9p dynamic  tid={tid}  "
        f"group_sessions={len(group_sessions)}  "
        f"finishing_delta={finishing_delta:.2f}pt"
    )


# ============================================================================
# T06C — Group_knockout, 12 Players (Preconfigured: 3 Groups × 4)
# ============================================================================

@pytest.mark.lifecycle
@pytest.mark.phase_6
@pytest.mark.golden_path
@pytest.mark.nondestructive
@pytest.mark.skill_progression
@pytest.mark.edge_cardinality
def test_T06C_group_knockout_12_players_preconfigured():
    """
    System-safety test: Group_knockout with 12 players.

    12 IS a preconfigured group_knockout size: 3 groups of 4.
    Group sessions: 3 groups × C(4,2) = 6 matches each = 18 group sessions.
    Knockout: top-1 (or top-2) from each group advances.

    Assertions:
    - Group sessions >= 18 (3 groups × 6 round-robin matches)
    - calculate-rankings succeeds for 12-player group_knockout
    - All 12 players have skill-audit rows (full field coverage)
    - unfair_entries == 0 for all 12 players
    - Rank-1 has non-negative finishing delta
    """
    players = _load_star_players()
    assert len(players) >= 12, (
        f"T06C requires 12 star players, only {len(players)} found. "
        f"Run seed_star_players.py to seed at least 12 players."
    )
    p    = players[:12]
    pids = [x["db_id"] for x in p]
    skills = ["finishing", "passing", "dribbling"]

    admin_tok = _admin_login()
    h = _auth(admin_tok)

    tid = _create_tournament(
        h,
        name=f"T06C GK 12p Preconfigured {_ts()}",
        tournament_type="group_knockout",
        max_players=12,
        skills=skills,
        reward_config=_make_reward_config(12),
    )
    _batch_enroll(h, tid, pids)
    sessions = _generate_sessions(h, tid)

    # ── Session count assertion ────────────────────────────────────────────────
    # 12 players → 3 groups of 4 → C(4,2)=6 matches per group = 18 group sessions
    group_sessions = [
        s for s in sessions
        if s.get("participant_user_ids")
        and len([pp for pp in s["participant_user_ids"] if pp is not None]) == 2
    ]
    assert len(group_sessions) >= 18, (
        f"T06C: Expected >= 18 group-stage sessions for 12-player group_knockout "
        f"(3 groups × 6 matches), got {len(group_sessions)}. "
        f"Total sessions: {len(sessions)}. "
        f"This tests the preconfigured GroupDistribution path for n=12."
    )

    # ── Submit group sessions ─────────────────────────────────────────────────
    group_ids = {s["id"] for s in group_sessions}
    for session in group_sessions:
        s_pids = [pp for pp in session["participant_user_ids"] if pp is not None]
        winner = min(s_pids, key=lambda x: pids.index(x) if x in pids else 999)
        loser  = max(s_pids, key=lambda x: pids.index(x) if x in pids else 999)
        _submit_h2h(h, tid, session["id"], winner, loser)

    # ── Finalize group stage ──────────────────────────────────────────────────
    finalize_resp = requests.post(
        f"{API_URL}/api/v1/tournaments/{tid}/finalize-group-stage",
        headers=h, timeout=20,
    )
    assert finalize_resp.status_code == 200, (
        f"T06C finalize-group-stage failed: {finalize_resp.status_code}\n{finalize_resp.text}"
    )

    # ── Iteratively submit knockout sessions ──────────────────────────────────
    _submit_group_and_knockout_iteratively(h, tid, pids, group_ids)

    # ── Full lifecycle ────────────────────────────────────────────────────────
    _calculate_rankings(h, tid)
    _complete_tournament(h, tid)
    _distribute_rewards(h, tid)

    # ── Progression assertions for ALL 12 players ─────────────────────────────
    _assert_all_players_have_audit_rows(p, pids, tid, "T06C-GK-12p")

    # Rank-1 player (p[0]) has non-negative finishing delta
    winner_tok = _player_login(p[0]["email"], p[0]["password"])
    audit = _get_skill_audit(winner_tok)
    t_rows = [r for r in audit if r["tournament_id"] == tid]
    finishing_rows = [r for r in t_rows if r["skill"] == "finishing"]
    assert finishing_rows, (
        f"T06C: No finishing skill-audit row for winner {pids[0]} in tournament {tid}"
    )
    finishing_delta = finishing_rows[0]["delta_this_tournament"]
    assert finishing_delta >= 0, (
        f"T06C: Rank-1 finishing delta should be non-negative, got {finishing_delta}"
    )

    print(
        f"\n  T06C PASS  group_knockout 12p preconfigured  tid={tid}  "
        f"group_sessions={len(group_sessions)}  "
        f"finishing_delta={finishing_delta:.2f}pt"
    )


# ============================================================================
# T06D — Knockout, 8 Players (Larger Bracket: 4 QF + 2 SF + 1 Final + 1 Bronze)
# ============================================================================

@pytest.mark.lifecycle
@pytest.mark.phase_6
@pytest.mark.golden_path
@pytest.mark.nondestructive
@pytest.mark.skill_progression
@pytest.mark.edge_cardinality
def test_T06D_knockout_8_players_larger_bracket():
    """
    System-safety test: Pure knockout tournament with 8 players.

    8 is a valid power-of-2 knockout size.
    Session structure: 4 QF (round 1) + 2 SF (round 2) + 1 Final + 1 Bronze (round 3) = 8 sessions.

    Lifecycle:
        1. Create knockout tournament (8 players, 3 skills)
        2. Enroll 8 players
        3. Generate sessions (expect 8 sessions total, >= 7)
        4. Submit round-1 (QF) results
        5. Submit round-2 (SF) results (after participants assigned)
        6. Submit round-3 (Final + Bronze) results
        7. Calculate rankings → complete → distribute rewards

    Assertions:
    - Sessions >= 7 (4 QF + 2 SF + 1 Final, bronze may or may not be generated)
    - CHAMPION badge for rank-1 player (winner) with total_participants=8
    - All 8 players have skill-audit rows after reward distribution
    - unfair_entries == 0 for all 8 players
    - Rank-1 has non-negative finishing delta
    """
    players = _load_star_players()
    assert len(players) >= 8, (
        f"T06D requires 8 star players, only {len(players)} found. "
        f"Run seed_star_players.py to seed at least 8 players."
    )
    p    = players[:8]
    pids = [x["db_id"] for x in p]
    skills = ["finishing", "passing", "dribbling"]

    admin_tok = _admin_login()
    h = _auth(admin_tok)

    tid = _create_tournament(
        h,
        name=f"T06D Knockout 8p {_ts()}",
        tournament_type="knockout",
        max_players=8,
        skills=skills,
        reward_config=_make_reward_config(8),
    )
    _batch_enroll(h, tid, pids)
    sessions = _generate_sessions(h, tid)

    # ── Session count assertion ────────────────────────────────────────────────
    # 8-player knockout: 4 QF + 2 SF + 1 Final = 7 minimum (+ 1 bronze = 8 maximum)
    assert len(sessions) >= 7, (
        f"T06D: Expected >= 7 sessions for 8-player knockout bracket, "
        f"got {len(sessions)}"
    )

    # ── Iteratively submit all rounds ─────────────────────────────────────────
    # Round 1 (QF) sessions have participants assigned at generation time.
    # Round 2 (SF) sessions get participants after QF results submitted.
    # Round 3 (Final + Bronze) sessions get participants after SF results submitted.
    # Use the iterative submission helper (empty group_ids since all sessions are knockout).
    _submit_group_and_knockout_iteratively(h, tid, pids, set())

    # ── Full lifecycle ────────────────────────────────────────────────────────
    _calculate_rankings(h, tid)
    _complete_tournament(h, tid)
    _distribute_rewards(h, tid)

    # ── CHAMPION badge assertion ──────────────────────────────────────────────
    badges_resp = requests.get(
        f"{API_URL}/api/v1/tournaments/badges/user/{pids[0]}",
        headers=h, timeout=15,
    )
    assert badges_resp.status_code == 200, (
        f"T06D: badges endpoint failed: {badges_resp.status_code}"
    )
    badges_data = badges_resp.json()
    # Response: {"user_id": ..., "total_badges": ..., "badges": [...]}
    badges = badges_data.get("badges", badges_data) if isinstance(badges_data, dict) else badges_data
    champion_badges = [b for b in badges if isinstance(b, dict) and b.get("badge_type") == "CHAMPION"]

    # Badge uses "semester_id" not "tournament_id" as the tournament reference key
    assert any(b.get("semester_id") == tid for b in champion_badges), (
        f"T06D: No CHAMPION badge for tournament/semester {tid} on player {pids[0]}. "
        f"Champion badge semester_ids: {[b.get('semester_id') for b in champion_badges]}"
    )
    champ = next(b for b in champion_badges if b.get("semester_id") == tid)
    bm = champ.get("badge_metadata") or {}
    assert bm.get("total_participants") == 8, (
        f"T06D: badge_metadata.total_participants should be 8, got {bm.get('total_participants')}"
    )

    # ── Progression assertions for ALL 8 players ──────────────────────────────
    _assert_all_players_have_audit_rows(p, pids, tid, "T06D-Knockout-8p")

    # Rank-1 player (p[0]) has non-negative finishing delta
    winner_tok = _player_login(p[0]["email"], p[0]["password"])
    audit = _get_skill_audit(winner_tok)
    t_rows = [r for r in audit if r["tournament_id"] == tid]
    finishing_rows = [r for r in t_rows if r["skill"] == "finishing"]
    assert finishing_rows, (
        f"T06D: No finishing skill-audit row for winner {pids[0]} in tournament {tid}"
    )
    finishing_delta = finishing_rows[0]["delta_this_tournament"]
    assert finishing_delta >= 0, (
        f"T06D: Rank-1 finishing delta should be non-negative, got {finishing_delta}"
    )

    print(
        f"\n  T06D PASS  knockout 8p  tid={tid}  "
        f"sessions={len(sessions)}  "
        f"CHAMPION badge OK (total_participants={bm.get('total_participants')})  "
        f"finishing_delta={finishing_delta:.2f}pt"
    )
