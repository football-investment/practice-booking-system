"""
Shared tournament payload factory for smoke and E2E tests.

Pure functions — no fixtures, no imports from conftest.
Usage:
    from tests.integration.api_smoke.tournament_payloads import (
        create_tournament_payload,
        ops_scenario_payload,
        ...
    )
"""

from __future__ import annotations

from typing import List, Optional


def create_tournament_payload(
    campus_ids: List[int],
    *,
    suffix: Optional[str] = None,
    enrollment_cost: int = 0,
    player_count: int = 4,
    game_preset_id: int = 1,
) -> dict:
    """
    Minimal-valid payload for POST /api/v1/tournaments/create.

    Args:
        campus_ids: List of campus IDs to include in the tournament.
        suffix: Optional string appended to name/code for uniqueness.
        enrollment_cost: Credit cost for enrollment (default 0 — free).
        player_count: Number of players (min 4 for knockout).
        game_preset_id: Game preset identifier (default 1).
    """
    name_suffix = f"_{suffix}" if suffix else ""
    return {
        "name": f"Smoke Tournament{name_suffix}",
        "code": f"SMKT{name_suffix}",
        "age_group": "PRO",
        "enrollment_cost": enrollment_cost,
        "player_count": player_count,
        "campus_ids": campus_ids,
        "game_preset_id": game_preset_id,
        "auto_generate_sessions": False,
        "start_date": "2026-06-01",
        "end_date": "2026-08-31",
    }


def ops_scenario_payload(
    campus_ids: List[int],
    scenario: str = "smoke_test",
    *,
    player_count: int = 0,
    tournament_type_code: str = "knockout",
    tournament_format: str = "HEAD_TO_HEAD",
) -> dict:
    """
    Payload for POST /api/v1/tournaments/ops/run-scenario.

    Uses OpsScenarioRequest schema:
    - campus_ids: Required. List of campus IDs for session distribution.
    - scenario: Required. One of "large_field_monitor", "smoke_test", "scale_test"
    - player_count=0 skips the auto-enrollment loop (fastest path).
    - tournament_type_code: "knockout", "league", "group_knockout"
    - tournament_format: "HEAD_TO_HEAD" or "INDIVIDUAL_RANKING"
    """
    return {
        "scenario": scenario,
        "campus_ids": campus_ids,
        "player_count": player_count,
        "tournament_type_code": tournament_type_code,
        "tournament_format": tournament_format,
    }


def generate_sessions_payload(campus_ids: List[int]) -> dict:
    """Payload for POST /api/v1/tournaments/{id}/generate-sessions."""
    return {
        "campus_ids": campus_ids,
        "sessions_per_round": 1,
        "session_duration_minutes": 90,
        "break_between_sessions_minutes": 15,
    }


def reward_config_payload(tournament_id: int) -> dict:
    """
    Payload for POST/PUT /api/v1/tournaments/{id}/reward-config.

    Uses TournamentRewardConfig schema (app/schemas/reward_config.py):
    - skill_mappings: at least 1 enabled skill required
    - placement rewards: optional
    - template_name: optional
    """
    return {
        "skill_mappings": [
            {"skill": "pace", "weight": 1.5, "category": "PHYSICAL", "enabled": True},
            {"skill": "dribbling", "weight": 1.2, "category": "TECHNICAL", "enabled": True},
        ],
        "first_place": {"credits": 500, "xp_multiplier": 1.5, "badges": []},
        "participation": {"credits": 10, "xp_multiplier": 1.0, "badges": []},
        "template_name": "smoke_test",
        "custom_config": True,
    }


def batch_enroll_payload(player_ids: List[int]) -> dict:
    """Payload for POST /api/v1/tournaments/{id}/admin/batch-enroll."""
    return {"player_ids": player_ids}


def assign_instructor_payload(instructor_id: int) -> dict:
    """Payload for POST /api/v1/tournaments/{id}/assign-instructor."""
    return {"instructor_id": instructor_id}


def skill_mapping_payload(tournament_id: int, skill_name: str = "agility") -> dict:
    """
    Payload for POST /api/v1/tournaments/{id}/skill-mappings.

    Uses AddSkillMappingRequest schema (app/schemas/tournament_rewards.py):
    - tournament_id: int (required)
    - skill_name: str (required)
    - skill_category: str (required)
    - weight: float (default 1.0)
    """
    return {
        "tournament_id": tournament_id,
        "skill_name": skill_name,
        "skill_category": "Physical",
        "weight": 1.0,
    }


def cancel_tournament_payload(reason: str = "Test cancellation") -> dict:
    """Payload for POST /api/v1/tournaments/{id}/cancel."""
    return {"reason": reason}


def submit_results_payload(player_ids: List[int]) -> dict:
    """
    Payload for POST /api/v1/tournaments/{id}/submit-results.

    Generates minimal result entries — all players draw (0-0).
    """
    return {
        "results": [
            {"player_id": pid, "goals_scored": 0, "goals_conceded": 0, "outcome": "DRAW"}
            for pid in player_ids
        ]
    }
