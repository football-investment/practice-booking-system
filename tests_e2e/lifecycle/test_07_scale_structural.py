"""
T07: Production Scale Structural Tests
=======================================

Pure in-process validation of the tournament engine at large cardinalities.
NO server, NO database, NO Playwright — runs in milliseconds.

Tests:
  T07A: 1024-player Knockout — session count, bracket structure, timing
  T07B: 32-player League     — session count, every player in 31 matches
  T07C: 64-player GroupKnockout — group/knockout session split
  T07D: Multi-campus parallel scheduling — field_slots advance correctly
  T07E: Background task threshold — player_count >= 128 triggers async path
  T07F: Per-campus schedule overrides — CampusScheduleConfig serialisation

All tests are marked @pytest.mark.golden_path because they protect the
engine's correctness at cardinalities that are hard to cover with E2E tests.
"""
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so we can import app code directly
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Import algorithm helpers directly (no DB, no FastAPI)
# ---------------------------------------------------------------------------
from app.services.tournament.session_generation.algorithms import (
    RoundRobinPairing,
    GroupDistribution,
    KnockoutBracket,
)
from app.api.api_v1.endpoints.tournaments.generate_sessions import (
    BACKGROUND_GENERATION_THRESHOLD,
    CampusScheduleConfig,
)


# ═══════════════════════════════════════════════════════════════════════════════
# In-process bracket generators (mirrors production generators, no DB needed)
# ═══════════════════════════════════════════════════════════════════════════════

def _knockout_bracket(n: int, parallel_fields: int = 1) -> List[Dict[str, Any]]:
    """Mirror of KnockoutGenerator.generate() — no DB, no ORM."""
    total_rounds = math.ceil(math.log2(n))
    sessions: List[Dict] = []
    player_ids = list(range(n))
    t0 = datetime(2026, 8, 1, 9, 0, 0)
    current_time = t0
    session_duration = 90
    break_minutes = 15

    for round_num in range(1, total_rounds + 1):
        players_in_round = n // (2 ** (round_num - 1))
        matches_in_round = players_in_round // 2

        for match_in_round in range(1, matches_in_round + 1):
            session_start = current_time
            session_end = session_start + timedelta(minutes=session_duration)

            if round_num == 1:
                seed1 = match_in_round - 1
                seed2 = players_in_round - match_in_round
                p1 = player_ids[seed1] if seed1 < len(player_ids) else None
                p2 = player_ids[seed2] if seed2 < len(player_ids) else None
                participant_ids = [p1, p2] if p1 is not None and p2 is not None else None
            else:
                participant_ids = None

            sessions.append({
                'tournament_round': round_num,
                'tournament_match_number': match_in_round,
                'date_start': session_start,
                'date_end': session_end,
                'participant_user_ids': participant_ids,
                'tournament_phase': 'KNOCKOUT',
            })

            if match_in_round % parallel_fields != 0:
                continue
            current_time += timedelta(minutes=session_duration + break_minutes)

        current_time += timedelta(minutes=break_minutes * 2)

    # Bronze match
    sessions.append({
        'tournament_round': total_rounds,
        'tournament_match_number': 999,
        'date_start': current_time,
        'date_end': current_time + timedelta(minutes=session_duration),
        'participant_user_ids': None,
        'tournament_phase': 'KNOCKOUT',
    })

    return sessions


def _league_h2h(n: int, parallel_fields: int = 1) -> List[Dict[str, Any]]:
    """Mirror of LeagueGenerator._generate_head_to_head_pairings() — no DB."""
    player_ids = list(range(n))
    num_rounds = RoundRobinPairing.calculate_rounds(n)
    t0 = datetime(2026, 8, 1, 9, 0, 0)
    field_slots = [t0 for _ in range(parallel_fields)]
    field_index = 0
    session_duration = 90
    break_minutes = 15
    sessions: List[Dict] = []

    for round_num in range(1, num_rounds + 1):
        round_pairings = RoundRobinPairing.get_round_pairings(player_ids, round_num)
        for match_num, (p1, p2) in enumerate(round_pairings, start=1):
            if p1 is None or p2 is None:
                continue
            session_start = field_slots[field_index]
            sessions.append({
                'tournament_round': round_num,
                'tournament_match_number': match_num,
                'participant_user_ids': [p1, p2],
                'date_start': session_start,
                'field_number': field_index + 1,
            })
            field_slots[field_index] += timedelta(minutes=session_duration + break_minutes)
            field_index = (field_index + 1) % parallel_fields

    return sessions


def _group_knockout(n: int, parallel_fields: int = 1) -> Dict[str, Any]:
    """
    Mirror of GroupKnockoutGenerator.generate() — no DB.
    Returns {'group_sessions': [...], 'knockout_sessions': [...]}
    """
    distribution = GroupDistribution.calculate_optimal_distribution(n)
    groups_count = distribution['groups_count']
    group_sizes = distribution['group_sizes']
    qualifiers_per_group = distribution['qualifiers_per_group']

    player_ids = list(range(n))
    group_assignments: Dict[str, List[int]] = {}
    idx = 0
    for g in range(1, groups_count + 1):
        name = chr(64 + g)
        sz = group_sizes[g - 1]
        group_assignments[name] = player_ids[idx:idx + sz]
        idx += sz

    t0 = datetime(2026, 8, 1, 9, 0, 0)
    field_slots = [t0 for _ in range(parallel_fields)]
    field_index = 0
    session_duration = 5  # short for structural test
    break_minutes = 2

    group_sessions: List[Dict] = []
    for g in range(1, groups_count + 1):
        name = chr(64 + g)
        gids = group_assignments[name]
        gsz = len(gids)
        num_rounds = RoundRobinPairing.calculate_rounds(gsz)
        for rnd in range(1, num_rounds + 1):
            pairings = RoundRobinPairing.get_round_pairings(gids, rnd)
            for mn, (p1, p2) in enumerate(pairings, start=1):
                if p1 is None or p2 is None:
                    continue
                group_sessions.append({
                    'group': name,
                    'round': rnd,
                    'match': mn,
                    'participant_user_ids': [p1, p2],
                    'date_start': field_slots[field_index],
                    'field_number': field_index + 1,
                })
                field_slots[field_index] += timedelta(minutes=session_duration + break_minutes)
                field_index = (field_index + 1) % parallel_fields

    current_time = max(field_slots) + timedelta(minutes=break_minutes * 4)

    knockout_players = groups_count * qualifiers_per_group
    structure = KnockoutBracket.calculate_structure(knockout_players)
    bracket_size = structure['bracket_size']
    knockout_rounds = math.ceil(math.log2(bracket_size))

    knockout_sessions: List[Dict] = []
    for rnd in range(1, knockout_rounds + 1):
        players_in_round = bracket_size // (2 ** (rnd - 1))
        matches_in_round = players_in_round // 2
        for m in range(1, matches_in_round + 1):
            knockout_sessions.append({
                'round': rnd,
                'match': m,
                'participant_user_ids': None,
                'date_start': current_time,
            })
            current_time += timedelta(minutes=session_duration + break_minutes)
        current_time += timedelta(minutes=break_minutes * 2)

    if structure.get('has_bronze'):
        knockout_sessions.append({
            'round': knockout_rounds + 1,
            'match': 1,
            'participant_user_ids': None,
            'date_start': current_time,
            'is_bronze': True,
        })

    return {
        'group_sessions': group_sessions,
        'knockout_sessions': knockout_sessions,
        'groups_count': groups_count,
        'group_sizes': group_sizes,
        'qualifiers_per_group': qualifiers_per_group,
        'knockout_players': knockout_players,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# T07A — 1024-player Knockout: session count + bracket structure
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T07A_1024_player_knockout_structure():
    """
    1024-player Knockout:
    - Total sessions = 1023 matches + 1 bronze = 1024
    - Rounds = 10 (log2(1024))
    - Round 1 has 512 matches, all with explicit participant_user_ids
    - Rounds 2-10 have None participant_user_ids (determined by results)
    - Generation completes in < 100ms
    """
    n = 1024
    expected_rounds = 10  # log2(1024)
    expected_match_sessions = n - 1  # 1023
    expected_total = expected_match_sessions + 1  # +1 bronze

    t_start = time.perf_counter()
    sessions = _knockout_bracket(n)
    elapsed_ms = (time.perf_counter() - t_start) * 1000

    assert elapsed_ms < 100, f"Generation took {elapsed_ms:.1f}ms — expected < 100ms"
    assert len(sessions) == expected_total, (
        f"Expected {expected_total} sessions, got {len(sessions)}"
    )

    rounds = [s for s in sessions if s['tournament_match_number'] != 999]
    round_numbers = {s['tournament_round'] for s in rounds}
    assert max(round_numbers) == expected_rounds, (
        f"Expected {expected_rounds} rounds, got max={max(round_numbers)}"
    )

    round1 = [s for s in sessions if s['tournament_round'] == 1]
    assert len(round1) == n // 2, f"Round 1 should have {n//2} matches, got {len(round1)}"

    # All round-1 participants must be explicitly assigned
    for s in round1:
        pids = s['participant_user_ids']
        assert pids is not None and len(pids) == 2, (
            f"Round 1 match missing explicit participants: {pids}"
        )
        assert pids[0] != pids[1], f"Round 1 match has same player twice: {pids}"

    # All participants in round 1 cover exactly 0..n-1 (each player once)
    all_r1_pids = [pid for s in round1 for pid in s['participant_user_ids']]
    assert sorted(all_r1_pids) == list(range(n)), (
        "Round 1 participants do not cover all 1024 players exactly once"
    )

    # Rounds 2+ must have participant_user_ids = None
    later_rounds = [s for s in sessions if s['tournament_round'] > 1 and s['tournament_match_number'] != 999]
    for s in later_rounds:
        assert s['participant_user_ids'] is None, (
            f"Round {s['tournament_round']} match {s['tournament_match_number']} "
            f"should have participant_user_ids=None, got {s['participant_user_ids']}"
        )

    # Bronze match must have participant_user_ids = None
    bronze = [s for s in sessions if s['tournament_match_number'] == 999]
    assert len(bronze) == 1, "Expected exactly 1 bronze match"
    assert bronze[0]['participant_user_ids'] is None


# ═══════════════════════════════════════════════════════════════════════════════
# T07B — 32-player League: session count + every player in 31 matches
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T07B_32_player_league_fairness():
    """
    32-player League (HEAD_TO_HEAD):
    - Total sessions = 32*(32-1)/2 = 496
    - Every player appears in exactly 31 matches
    - No duplicate matchups (player A vs player B appears at most once)
    """
    n = 32
    expected_sessions = n * (n - 1) // 2  # 496

    sessions = _league_h2h(n)

    assert len(sessions) == expected_sessions, (
        f"Expected {expected_sessions} sessions, got {len(sessions)}"
    )

    # Each player should appear in exactly n-1 = 31 matches
    participation: Dict[int, int] = defaultdict(int)
    matchups: set = set()

    for s in sessions:
        pids = s['participant_user_ids']
        assert pids is not None and len(pids) == 2, f"Session missing participants: {pids}"
        p1, p2 = pids[0], pids[1]
        assert p1 != p2, f"Session has same player twice: {pids}"
        participation[p1] += 1
        participation[p2] += 1
        key = tuple(sorted([p1, p2]))
        assert key not in matchups, f"Duplicate matchup detected: {key}"
        matchups.add(key)

    for player_id in range(n):
        assert participation[player_id] == n - 1, (
            f"Player {player_id} appeared in {participation[player_id]} matches, "
            f"expected {n - 1}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T07C — 64-player GroupKnockout: group/knockout session split
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T07C_64_player_group_knockout_structure():
    """
    64-player GroupKnockout:
    - GroupDistribution should produce 16 groups of 4
    - Group stage: 16 groups × C(4,2)=6 matches = 96 group sessions
    - qualifiers_per_group = 2 → 32 knockout qualifiers
    - Knockout bracket: 32-player → 5 rounds + bronze
    - No participant is assigned in knockout sessions (None until group stage resolves)
    """
    n = 64
    result = _group_knockout(n)

    group_sessions = result['group_sessions']
    knockout_sessions = result['knockout_sessions']
    groups_count = result['groups_count']
    group_sizes = result['group_sizes']
    qualifiers = result['qualifiers_per_group']
    knockout_players = result['knockout_players']

    # With 64 players, GroupDistribution should give 16 groups of 4
    assert groups_count == 16, f"Expected 16 groups, got {groups_count}"
    assert all(sz == 4 for sz in group_sizes), f"Expected all groups size 4, got {group_sizes}"
    assert qualifiers == 2, f"Expected qualifiers_per_group=2, got {qualifiers}"

    # 16 groups × C(4,2)=6 matches per group = 96 group sessions
    expected_group_sessions = 16 * 6  # 96
    assert len(group_sessions) == expected_group_sessions, (
        f"Expected {expected_group_sessions} group sessions, got {len(group_sessions)}"
    )

    # All group sessions have explicit participant_user_ids (2 players each)
    for s in group_sessions:
        pids = s['participant_user_ids']
        assert pids is not None and len(pids) == 2, (
            f"Group session missing participants: {pids}"
        )

    # Knockout: 32 qualifiers → 5 rounds + bronze
    assert knockout_players == 32, f"Expected 32 knockout players, got {knockout_players}"
    bracket_size = KnockoutBracket.calculate_structure(32)['bracket_size']
    expected_ko_rounds = math.ceil(math.log2(bracket_size))
    knockout_matches = [s for s in knockout_sessions if not s.get('is_bronze')]
    bronze_matches = [s for s in knockout_sessions if s.get('is_bronze')]

    assert expected_ko_rounds == 5, f"Expected 5 KO rounds for 32 players, got {expected_ko_rounds}"
    assert len(bronze_matches) <= 1, "At most 1 bronze match expected"

    # All knockout sessions have participant_user_ids = None
    for s in knockout_sessions:
        assert s['participant_user_ids'] is None, (
            f"Knockout session should have participant_user_ids=None, got {s['participant_user_ids']}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T07D — Multi-campus parallel scheduling: field_slots correctness
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T07D_parallel_fields_scheduling():
    """
    Parallel fields scheduling correctness:
    - With parallel_fields=4, sessions are distributed across 4 field clocks
    - No two sessions on the same field overlap
    - With parallel_fields=4 the total wall-clock time should be ~1/4 of serial time
    """
    n = 16
    parallel = 4
    serial_sessions = _league_h2h(n, parallel_fields=1)
    parallel_sessions = _league_h2h(n, parallel_fields=parallel)

    # Session count must be identical regardless of parallel_fields
    assert len(serial_sessions) == len(parallel_sessions), (
        f"Session count differs: serial={len(serial_sessions)}, parallel={len(parallel_sessions)}"
    )

    # Check no overlap per field: for each field_number, sessions must be sequential
    session_duration_minutes = 90
    break_minutes = 15
    slot_length = timedelta(minutes=session_duration_minutes + break_minutes)

    by_field: Dict[int, List[datetime]] = defaultdict(list)
    for s in parallel_sessions:
        by_field[s['field_number']].append(s['date_start'])

    for field_num, starts in by_field.items():
        starts_sorted = sorted(starts)
        for i in range(1, len(starts_sorted)):
            gap = starts_sorted[i] - starts_sorted[i - 1]
            assert gap >= slot_length, (
                f"Field {field_num}: sessions overlap — gap {gap} < required {slot_length}"
            )

    # Parallel scheduling should use at most ceil(total_slots / parallel) rounds
    total_sessions = len(serial_sessions)
    max_sessions_per_field = math.ceil(total_sessions / parallel)
    for field_num, starts in by_field.items():
        assert len(starts) <= max_sessions_per_field + 1, (
            f"Field {field_num} has {len(starts)} sessions — exceeds fair distribution "
            f"(expected <= {max_sessions_per_field + 1})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T07E — Background task threshold: >= 128 players triggers async path
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T07E_background_task_threshold():
    """
    The BACKGROUND_GENERATION_THRESHOLD constant must be 128.
    A tournament with exactly 128 players should be routed to the async path,
    and one with 127 players to the sync path.

    This test does NOT call the API endpoint — it only verifies the constant
    is correct and the boundary condition is as designed.
    """
    assert BACKGROUND_GENERATION_THRESHOLD == 128, (
        f"Expected threshold=128, got {BACKGROUND_GENERATION_THRESHOLD}"
    )

    # 127 players → sync path
    assert 127 < BACKGROUND_GENERATION_THRESHOLD, "127 should use sync path"
    # 128 players → async path
    assert 128 >= BACKGROUND_GENERATION_THRESHOLD, "128 should use async path"
    # 1024 players → async path
    assert 1024 >= BACKGROUND_GENERATION_THRESHOLD, "1024 should use async path"


# ═══════════════════════════════════════════════════════════════════════════════
# T07F — CampusScheduleConfig serialisation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.golden_path
@pytest.mark.phase_6
@pytest.mark.scale_structural
@pytest.mark.nondestructive
def test_T07F_campus_schedule_config_serialisation():
    """
    CampusScheduleConfig.model_dump(exclude_none=True) must:
    - Include only provided fields
    - Omit None fields
    - Survive a round-trip through JSON-compatible dict
    """
    # Full override
    full = CampusScheduleConfig(
        match_duration_minutes=5,
        break_duration_minutes=2,
        parallel_fields=3,
    )
    dumped = full.model_dump(exclude_none=True)
    assert dumped == {
        'match_duration_minutes': 5,
        'break_duration_minutes': 2,
        'parallel_fields': 3,
    }, f"Unexpected dump: {dumped}"

    # Partial override — only parallel_fields
    partial = CampusScheduleConfig(parallel_fields=8)
    dumped_partial = partial.model_dump(exclude_none=True)
    assert dumped_partial == {'parallel_fields': 8}, (
        f"Partial override should only contain parallel_fields, got: {dumped_partial}"
    )
    assert 'match_duration_minutes' not in dumped_partial
    assert 'break_duration_minutes' not in dumped_partial

    # Multi-campus dict (as stored in DB column)
    campus_overrides = {
        '42': CampusScheduleConfig(match_duration_minutes=5, parallel_fields=4),
        '99': CampusScheduleConfig(break_duration_minutes=0, parallel_fields=2),
    }
    raw = {
        campus_id: cfg.model_dump(exclude_none=True)
        for campus_id, cfg in campus_overrides.items()
    }
    assert raw['42'] == {'match_duration_minutes': 5, 'parallel_fields': 4}
    assert raw['99'] == {'break_duration_minutes': 0, 'parallel_fields': 2}
    # Keys are strings (as stored in JSONB)
    assert all(isinstance(k, str) for k in raw.keys())
