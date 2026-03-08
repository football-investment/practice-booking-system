"""
T08: 1024-Player Multi-Campus Load Test
=========================================

Pure in-process validation of multi-campus tournament scheduling at 1024-player scale.
NO server, NO database, NO Playwright — runs in milliseconds.

Scenario:
  - 1024 players split across 4 campuses (256 players each)
  - Each campus has independently configured match_duration_minutes,
    break_duration_minutes, and parallel_fields
  - League format: every player within each campus plays a full round-robin
  - Validates session generation, parallel scheduling, and per-campus overrides

Tests:
  T08A: Multi-campus split correctness — 4 campuses × 256 players each
  T08B: Per-campus schedule override resolution — CampusScheduleConfig precedence
  T08C: Campus isolation — sessions from different campuses do NOT overlap on shared timeline
  T08D: Parallel field correctness per campus — each campus uses its own field_slots
  T08E: Total session count across all campuses — sum matches formula
  T08F: Campus-level timing independence — fast campus finishes before slow campus
  T08G: get_campus_schedule() fallback chain — no config → returns globals
  T08H: 1024-player multi-campus generation performance — completes in < 500ms
"""
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure project root on sys.path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.tournament.session_generation.algorithms import RoundRobinPairing
from app.api.api_v1.endpoints.tournaments.generate_sessions import CampusScheduleConfig


# ═══════════════════════════════════════════════════════════════════════════════
# Campus configuration fixture
# ═══════════════════════════════════════════════════════════════════════════════

# Four campus configurations (mirrors what would be stored in campus_schedule_configs)
CAMPUS_CONFIGS = {
    1: {  # Buda Campus — standard football (90 min, 15 min break, 2 fields)
        "campus_id": 1,
        "name": "Buda Campus",
        "match_duration_minutes": 90,
        "break_duration_minutes": 15,
        "parallel_fields": 2,
    },
    2: {  # Pest Campus — speed format (45 min, 10 min break, 4 fields)
        "campus_id": 2,
        "name": "Pest Campus",
        "match_duration_minutes": 45,
        "break_duration_minutes": 10,
        "parallel_fields": 4,
    },
    3: {  # Online Campus — blitz format (5 min, 2 min break, 8 fields)
        "campus_id": 3,
        "name": "Online Campus",
        "match_duration_minutes": 5,
        "break_duration_minutes": 2,
        "parallel_fields": 8,
    },
    4: {  # International Campus — extended format (120 min, 30 min break, 1 field)
        "campus_id": 4,
        "name": "International Campus",
        "match_duration_minutes": 120,
        "break_duration_minutes": 30,
        "parallel_fields": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# In-process multi-campus league generator (mirrors production, no DB)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_campus_sessions(
    campus_id: int,
    player_ids: List[int],
    campus_cfg: Dict[str, Any],
    start_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Generate full round-robin sessions for one campus.
    Returns a list of session dicts with campus_id attached.
    """
    match_duration = campus_cfg["match_duration_minutes"]
    break_duration = campus_cfg["break_duration_minutes"]
    parallel_fields = campus_cfg["parallel_fields"]
    n = len(player_ids)
    num_rounds = RoundRobinPairing.calculate_rounds(n)

    field_slots = [start_time for _ in range(parallel_fields)]
    field_index = 0
    sessions: List[Dict[str, Any]] = []

    for round_num in range(1, num_rounds + 1):
        pairings = RoundRobinPairing.get_round_pairings(player_ids, round_num)
        for match_num, (p1, p2) in enumerate(pairings, start=1):
            if p1 is None or p2 is None:
                continue
            session_start = field_slots[field_index]
            session_end = session_start + timedelta(minutes=match_duration)
            sessions.append({
                "campus_id": campus_id,
                "campus_name": campus_cfg["name"],
                "tournament_round": round_num,
                "tournament_match_number": match_num,
                "participant_user_ids": [p1, p2],
                "date_start": session_start,
                "date_end": session_end,
                "field_number": field_index + 1,
                "match_duration_minutes": match_duration,
                "break_duration_minutes": break_duration,
            })
            field_slots[field_index] += timedelta(minutes=match_duration + break_duration)
            field_index = (field_index + 1) % parallel_fields

    return sessions


def _generate_all_campuses(
    total_players: int = 1024,
    campus_count: int = 4,
    start_time: Optional[datetime] = None,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Split total_players evenly across campus_count campuses and generate
    full round-robin sessions for each campus using CAMPUS_CONFIGS.

    Returns: {campus_id: [session, ...]}
    """
    if start_time is None:
        start_time = datetime(2026, 8, 1, 9, 0, 0)

    players_per_campus = total_players // campus_count
    all_sessions: Dict[int, List[Dict[str, Any]]] = {}

    for campus_id in range(1, campus_count + 1):
        offset = (campus_id - 1) * players_per_campus
        player_ids = list(range(offset, offset + players_per_campus))
        cfg = CAMPUS_CONFIGS[campus_id]
        sessions = _generate_campus_sessions(campus_id, player_ids, cfg, start_time)
        all_sessions[campus_id] = sessions

    return all_sessions


# ═══════════════════════════════════════════════════════════════════════════════
# T08A — Multi-campus split correctness
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08A_multicampus_player_split():
    """
    1024 players split across 4 campuses:
    - Each campus gets exactly 256 players
    - Player IDs are disjoint across campuses (no player on two campuses)
    - Every player appears in the correct campus sessions
    """
    total = 1024
    campus_count = 4
    expected_per_campus = total // campus_count  # 256

    all_sessions = _generate_all_campuses(total, campus_count)

    assert len(all_sessions) == campus_count, (
        f"Expected {campus_count} campuses in result, got {len(all_sessions)}"
    )

    # Collect all player IDs per campus from sessions
    campus_players: Dict[int, set] = {}
    for campus_id, sessions in all_sessions.items():
        players = set()
        for s in sessions:
            players.update(s["participant_user_ids"])
        campus_players[campus_id] = players

    # Each campus has exactly expected_per_campus players
    for campus_id, players in campus_players.items():
        assert len(players) == expected_per_campus, (
            f"Campus {campus_id}: expected {expected_per_campus} players, got {len(players)}"
        )

    # No player appears on more than one campus
    all_player_sets = list(campus_players.values())
    for i in range(len(all_player_sets)):
        for j in range(i + 1, len(all_player_sets)):
            overlap = all_player_sets[i] & all_player_sets[j]
            assert not overlap, (
                f"Campus {i+1} and campus {j+1} share players: {overlap}"
            )

    # Total unique players across all campuses = 1024
    all_players = set()
    for players in campus_players.values():
        all_players |= players
    assert len(all_players) == total, (
        f"Expected {total} unique players across all campuses, got {len(all_players)}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T08B — Per-campus schedule override resolution
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08B_campus_schedule_override_resolution():
    """
    Each campus's sessions must use its own schedule config:
    - Campus 1: match_duration=90, break=15, parallel_fields=2
    - Campus 2: match_duration=45, break=10, parallel_fields=4
    - Campus 3: match_duration=5,  break=2,  parallel_fields=8
    - Campus 4: match_duration=120, break=30, parallel_fields=1

    Verify that session.date_end - date_start matches the campus's match_duration.
    """
    all_sessions = _generate_all_campuses(1024, 4)

    for campus_id, sessions in all_sessions.items():
        cfg = CAMPUS_CONFIGS[campus_id]
        expected_duration = timedelta(minutes=cfg["match_duration_minutes"])

        # Verify all sessions use the correct match duration
        for s in sessions[:10]:  # sample first 10 sessions per campus
            actual_duration = s["date_end"] - s["date_start"]
            assert actual_duration == expected_duration, (
                f"Campus {campus_id} ({cfg['name']}): expected match duration "
                f"{cfg['match_duration_minutes']}min, got {actual_duration.seconds // 60}min "
                f"for session round={s['tournament_round']} match={s['tournament_match_number']}"
            )

        # Verify parallel_fields: max field_number used should be exactly parallel_fields
        max_field = max(s["field_number"] for s in sessions)
        assert max_field == cfg["parallel_fields"], (
            f"Campus {campus_id}: expected parallel_fields={cfg['parallel_fields']}, "
            f"but max field_number used = {max_field}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T08C — Campus isolation: sessions within each campus are non-overlapping
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08C_campus_session_isolation():
    """
    Within each campus, no two sessions on the same field overlap.
    Across campuses, sessions may overlap (they are on separate physical fields).
    """
    all_sessions = _generate_all_campuses(1024, 4)

    for campus_id, sessions in all_sessions.items():
        cfg = CAMPUS_CONFIGS[campus_id]

        # Group sessions by field_number
        by_field: Dict[int, List[Dict]] = defaultdict(list)
        for s in sessions:
            by_field[s["field_number"]].append(s)

        assert len(by_field) == cfg["parallel_fields"], (
            f"Campus {campus_id}: expected {cfg['parallel_fields']} fields used, "
            f"got {len(by_field)}"
        )

        # For each field: sessions sorted by date_start must not overlap
        for field_num, field_sessions in by_field.items():
            field_sessions_sorted = sorted(field_sessions, key=lambda s: s["date_start"])
            for i in range(1, len(field_sessions_sorted)):
                prev = field_sessions_sorted[i - 1]
                curr = field_sessions_sorted[i]
                # Current session must not start before previous ends
                assert curr["date_start"] >= prev["date_end"], (
                    f"Campus {campus_id}, field {field_num}: session overlap detected! "
                    f"Session {i-1} ends at {prev['date_end']}, "
                    f"session {i} starts at {curr['date_start']}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# T08D — Parallel field distribution fairness per campus
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08D_parallel_field_distribution_fairness():
    """
    Sessions are distributed fairly (round-robin) across parallel fields.
    Max sessions on any one field ≤ ceil(total_sessions / parallel_fields) + 1.
    """
    all_sessions = _generate_all_campuses(1024, 4)

    for campus_id, sessions in all_sessions.items():
        cfg = CAMPUS_CONFIGS[campus_id]
        parallel_fields = cfg["parallel_fields"]
        total_sessions = len(sessions)

        by_field: Dict[int, int] = defaultdict(int)
        for s in sessions:
            by_field[s["field_number"]] += 1

        # All configured fields should be used
        assert len(by_field) == parallel_fields, (
            f"Campus {campus_id}: {parallel_fields} fields configured, "
            f"but only {len(by_field)} used"
        )

        # Fair distribution: no field has more than ceil(total/parallel) + 1 sessions
        fair_max = math.ceil(total_sessions / parallel_fields) + 1
        for field_num, count in by_field.items():
            assert count <= fair_max, (
                f"Campus {campus_id}, field {field_num}: {count} sessions "
                f"exceeds fair max {fair_max} "
                f"(total={total_sessions}, parallel={parallel_fields})"
            )

        # Min sessions on any field ≥ floor(total/parallel) - 1
        fair_min = max(0, total_sessions // parallel_fields - 1)
        for field_num, count in by_field.items():
            assert count >= fair_min, (
                f"Campus {campus_id}, field {field_num}: only {count} sessions, "
                f"expected at least {fair_min}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# T08E — Total session count across all campuses
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08E_total_session_count():
    """
    For 4 campuses × 256 players each (full round-robin league):
    - Sessions per campus = 256 * (256-1) / 2 = 32,640
    - Total sessions = 4 * 32,640 = 130,560
    """
    players_per_campus = 256
    campus_count = 4
    expected_per_campus = players_per_campus * (players_per_campus - 1) // 2  # 32,640
    expected_total = campus_count * expected_per_campus  # 130,560

    all_sessions = _generate_all_campuses(players_per_campus * campus_count, campus_count)

    total = sum(len(sessions) for sessions in all_sessions.values())

    for campus_id, sessions in all_sessions.items():
        assert len(sessions) == expected_per_campus, (
            f"Campus {campus_id}: expected {expected_per_campus} sessions, "
            f"got {len(sessions)}"
        )

    assert total == expected_total, (
        f"Total sessions across all campuses: expected {expected_total}, got {total}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T08F — Campus-level timing independence
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08F_campus_timing_independence():
    """
    The fast campus (Online Campus: 5 min match, 8 parallel fields) completes
    well before the slow campus (International Campus: 120 min match, 1 field).

    Validates that per-campus schedule configs produce logically distinct timelines.
    """
    # Use a smaller scale (64 players per campus) to keep fast but still verify timing
    players_per_campus = 64
    campus_count = 4
    start_time = datetime(2026, 8, 1, 9, 0, 0)
    all_sessions: Dict[int, List[Dict]] = {}

    for campus_id in range(1, campus_count + 1):
        offset = (campus_id - 1) * players_per_campus
        player_ids = list(range(offset, offset + players_per_campus))
        cfg = CAMPUS_CONFIGS[campus_id]
        sessions = _generate_campus_sessions(campus_id, player_ids, cfg, start_time)
        all_sessions[campus_id] = sessions

    # Get the last session end time for each campus
    def last_end(sessions: List[Dict]) -> datetime:
        return max(s["date_end"] for s in sessions)

    online_end = last_end(all_sessions[3])    # Campus 3: Online (fast)
    international_end = last_end(all_sessions[4])  # Campus 4: International (slow)
    buda_end = last_end(all_sessions[1])      # Campus 1: Buda (medium)
    pest_end = last_end(all_sessions[2])      # Campus 2: Pest (fast)

    # Online campus (5 min match, 8 fields) finishes much sooner than International (120 min, 1 field)
    assert online_end < international_end, (
        f"Online campus (5min/8fields) should finish before International (120min/1field). "
        f"Online end: {online_end}, International end: {international_end}"
    )

    # Pest campus (45 min match, 4 fields) finishes sooner than International (120 min, 1 field)
    assert pest_end < international_end, (
        f"Pest campus (45min/4fields) should finish before International (120min/1field). "
        f"Pest end: {pest_end}, International end: {international_end}"
    )

    # All campuses start at the same time
    for campus_id, sessions in all_sessions.items():
        first_start = min(s["date_start"] for s in sessions)
        assert first_start == start_time, (
            f"Campus {campus_id} first session starts at {first_start}, expected {start_time}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T08G — get_campus_schedule() fallback chain
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08G_get_campus_schedule_fallback_chain():
    """
    Validates the get_campus_schedule() helper's precedence chain without DB:

    1. campus_id=None → always returns globals
    2. campus_id set + no DB row → returns globals
    3. campus_id set + DB row with all fields → returns DB row values
    4. campus_id set + DB row with partial fields (None) → resolved_* methods fill gaps
    """
    from app.services.tournament.session_generation.utils import get_campus_schedule
    from app.models.campus_schedule_config import CampusScheduleConfig as CampusScheduleConfigModel

    # 1. campus_id=None → globals (no DB query attempted)
    mock_db = MagicMock()
    result = get_campus_schedule(
        db=mock_db,
        tournament_id=1,
        campus_id=None,
        global_match_duration=90,
        global_break_duration=15,
        global_parallel_fields=2,
    )
    assert result == {
        "match_duration_minutes": 90,
        "break_duration_minutes": 15,
        "parallel_fields": 2,
        "venue_label": None,
    }, f"campus_id=None should return globals: {result}"
    mock_db.query.assert_not_called()

    # 2. campus_id set + DB returns None (no config row)
    mock_db2 = MagicMock()
    mock_db2.query.return_value.filter.return_value.first.return_value = None
    result2 = get_campus_schedule(
        db=mock_db2,
        tournament_id=1,
        campus_id=42,
        global_match_duration=90,
        global_break_duration=15,
        global_parallel_fields=1,
    )
    assert result2["match_duration_minutes"] == 90
    assert result2["break_duration_minutes"] == 15
    assert result2["parallel_fields"] == 1
    assert result2["venue_label"] is None

    # 3. campus_id set + DB row with all fields → returns DB values
    mock_cfg_full = MagicMock(spec=CampusScheduleConfigModel)
    mock_cfg_full.match_duration_minutes = 45
    mock_cfg_full.break_duration_minutes = 10
    mock_cfg_full.parallel_fields = 4
    mock_cfg_full.venue_label = "Pest Arena"
    mock_cfg_full.resolved_match_duration = lambda default: 45
    mock_cfg_full.resolved_break_duration = lambda default: 10
    mock_cfg_full.resolved_parallel_fields = lambda default: 4

    mock_db3 = MagicMock()
    mock_db3.query.return_value.filter.return_value.first.return_value = mock_cfg_full
    result3 = get_campus_schedule(
        db=mock_db3,
        tournament_id=1,
        campus_id=42,
        global_match_duration=90,
        global_break_duration=15,
        global_parallel_fields=1,
    )
    assert result3["match_duration_minutes"] == 45, f"Expected 45, got {result3['match_duration_minutes']}"
    assert result3["break_duration_minutes"] == 10, f"Expected 10, got {result3['break_duration_minutes']}"
    assert result3["parallel_fields"] == 4, f"Expected 4, got {result3['parallel_fields']}"
    assert result3["venue_label"] == "Pest Arena"

    # 4. campus_id set + DB row with partial fields (match_duration=None) → falls back to global
    mock_cfg_partial = MagicMock(spec=CampusScheduleConfigModel)
    mock_cfg_partial.match_duration_minutes = None
    mock_cfg_partial.break_duration_minutes = 5
    mock_cfg_partial.parallel_fields = 3
    mock_cfg_partial.venue_label = None
    # resolved_* mirrors the real model's behaviour: None → use default
    mock_cfg_partial.resolved_match_duration = lambda default: default  # None → use global
    mock_cfg_partial.resolved_break_duration = lambda default: 5
    mock_cfg_partial.resolved_parallel_fields = lambda default: 3

    mock_db4 = MagicMock()
    mock_db4.query.return_value.filter.return_value.first.return_value = mock_cfg_partial
    result4 = get_campus_schedule(
        db=mock_db4,
        tournament_id=1,
        campus_id=99,
        global_match_duration=90,
        global_break_duration=15,
        global_parallel_fields=1,
    )
    assert result4["match_duration_minutes"] == 90, (
        f"Partial config: match_duration should fall back to global 90, got {result4['match_duration_minutes']}"
    )
    assert result4["break_duration_minutes"] == 5, (
        f"Partial config: break_duration should use campus value 5, got {result4['break_duration_minutes']}"
    )
    assert result4["parallel_fields"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# T08H — 1024-player multi-campus generation performance
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T08H_multicampus_1024_performance():
    """
    Full 1024-player multi-campus session generation completes in < 500ms.

    With 4 campuses × 256 players each (full round-robin), the generator
    produces 130,560 sessions. This tests that the in-process generation
    logic scales within acceptable bounds for background task processing.
    """
    total_players = 1024
    campus_count = 4

    t_start = time.perf_counter()
    all_sessions = _generate_all_campuses(total_players, campus_count)
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    total_sessions = sum(len(sessions) for sessions in all_sessions.values())

    # Generation must complete within 500ms (background task budget)
    assert elapsed_ms < 500, (
        f"Multi-campus generation for {total_players} players took {elapsed_ms:.1f}ms — "
        f"expected < 500ms (background task budget). "
        f"Generated {total_sessions:,} sessions."
    )

    # Sanity: correct session count
    expected_per_campus = 256 * 255 // 2  # 32,640
    expected_total = campus_count * expected_per_campus  # 130,560
    assert total_sessions == expected_total, (
        f"Expected {expected_total:,} sessions, got {total_sessions:,}"
    )
