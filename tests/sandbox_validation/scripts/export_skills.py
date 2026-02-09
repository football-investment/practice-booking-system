#!/usr/bin/env python3
"""
Export Player Skills - Sandbox Validation

Usage:
    python export_skills.py --scenario S1 --phase pre
    python export_skills.py --scenario S1 --phase post

Exports all 29 skills for test players to CSV for delta calculation.
"""

import psycopg2
import pandas as pd
import argparse
from datetime import datetime
from pathlib import Path

# Database connection
DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Test player IDs (update based on actual test data)
TEST_PLAYER_IDS = [
    # Star players (3)
    # Average players (4)
    # Beginner players (3)
    # TODO: Populate after test users are seeded
]

def export_skills(scenario_id: str, phase: str):
    """
    Export player skills to CSV.

    Args:
        scenario_id: Scenario identifier (e.g., "S1")
        phase: "pre" or "post" tournament
    """
    print(f"📊 Exporting {phase}-tournament skills for {scenario_id}...")

    conn = psycopg2.connect(DB_URL)

    # Query all 29 skills + user info
    query = """
        SELECT
            u.id,
            u.email,
            u.name,
            ps.passing,
            ps.dribbling,
            ps.shooting,
            ps.defending,
            ps.physical,
            ps.pace,
            ps.ball_control,
            ps.crossing,
            ps.finishing,
            ps.heading,
            ps.short_passing,
            ps.volleys,
            ps.curve,
            ps.free_kick,
            ps.long_passing,
            ps.ball_control_dribbling,
            ps.acceleration,
            ps.sprint_speed,
            ps.agility,
            ps.reactions,
            ps.balance,
            ps.shot_power,
            ps.jumping,
            ps.stamina,
            ps.strength,
            ps.long_shots,
            ps.aggression,
            ps.interceptions,
            ps.positioning,
            ps.vision,
            ps.penalties,
            ps.composure,
            ps.marking,
            ps.standing_tackle,
            ps.sliding_tackle,
            u.experience_points AS xp,
            u.level
        FROM users u
        LEFT JOIN player_skills ps ON u.id = ps.user_id
        WHERE u.specialization = 'LFA_FOOTBALL_PLAYER'
        ORDER BY u.id;
    """

    df = pd.read_sql(query, conn)
    conn.close()

    # Generate output filename
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sandbox_{scenario_id}_{phase}_{timestamp}.csv"
    output_path = output_dir / filename

    df.to_csv(output_path, index=False)

    print(f"✅ Exported {len(df)} players to {output_path}")
    print(f"   Columns: {len(df.columns)} (user info + 29 skills + XP + level)")

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export player skills for sandbox validation")
    parser.add_argument("--scenario", required=True, help="Scenario ID (e.g., S1)")
    parser.add_argument("--phase", required=True, choices=["pre", "post"], help="Tournament phase")

    args = parser.parse_args()

    export_skills(args.scenario, args.phase)
