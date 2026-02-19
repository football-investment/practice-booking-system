#!/usr/bin/env python3
"""
Calculate Skill Deltas - Sandbox Validation

Usage:
    python calculate_deltas.py --scenario S1

Computes skill changes (Δ = post - pre) and validates business logic.
"""

import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime

def calculate_deltas(scenario_id: str):
    """
    Calculate skill deltas and generate validation report.

    Args:
        scenario_id: Scenario identifier (e.g., "S1")
    """
    print(f"📊 Calculating deltas for {scenario_id}...")

    results_dir = Path(__file__).parent.parent / "results"

    # Find most recent pre/post files for scenario
    pre_files = list(results_dir.glob(f"sandbox_{scenario_id}_pre_*.csv"))
    post_files = list(results_dir.glob(f"sandbox_{scenario_id}_post_*.csv"))

    if not pre_files or not post_files:
        print(f"❌ ERROR: Missing pre/post files for {scenario_id}")
        print(f"   Pre files found: {len(pre_files)}")
        print(f"   Post files found: {len(post_files)}")
        return

    # Use most recent files
    pre_file = sorted(pre_files)[-1]
    post_file = sorted(post_files)[-1]

    print(f"   Pre:  {pre_file.name}")
    print(f"   Post: {post_file.name}")

    # Load data
    pre_df = pd.read_csv(pre_file)
    post_df = pd.read_csv(post_file)

    # Merge on player ID
    merged = pre_df.merge(
        post_df,
        on='id',
        suffixes=('_pre', '_post')
    )

    # Calculate deltas for all skill columns
    skill_columns = [
        'passing', 'dribbling', 'shooting', 'defending', 'physical', 'pace',
        'ball_control', 'crossing', 'finishing', 'heading', 'short_passing',
        'volleys', 'curve', 'free_kick', 'long_passing', 'ball_control_dribbling',
        'acceleration', 'sprint_speed', 'agility', 'reactions', 'balance',
        'shot_power', 'jumping', 'stamina', 'strength', 'long_shots',
        'aggression', 'interceptions', 'positioning', 'vision', 'penalties',
        'composure', 'marking', 'standing_tackle', 'sliding_tackle'
    ]

    delta_df = merged[['id', 'email_pre', 'name_pre']].copy()
    delta_df.rename(columns={'email_pre': 'email', 'name_pre': 'name'}, inplace=True)

    for skill in skill_columns:
        if f'{skill}_pre' in merged.columns and f'{skill}_post' in merged.columns:
            delta_df[f'{skill}_delta'] = merged[f'{skill}_post'] - merged[f'{skill}_pre']

    # XP and level deltas
    delta_df['xp_delta'] = merged['xp_post'] - merged['xp_pre']
    delta_df['level_delta'] = merged['level_post'] - merged['level_pre']

    # Calculate average skill delta per player
    delta_cols = [col for col in delta_df.columns if col.endswith('_delta') and col != 'xp_delta' and col != 'level_delta']
    delta_df['avg_skill_delta'] = delta_df[delta_cols].mean(axis=1)

    # Sort by average skill delta (winners first)
    delta_df = delta_df.sort_values('avg_skill_delta', ascending=False)

    # Save delta report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    delta_file = results_dir / f"sandbox_{scenario_id}_delta_{timestamp}.csv"
    delta_df.to_csv(delta_file, index=False)

    print(f"✅ Delta calculation complete: {delta_file.name}")

    # Validation checks
    print("\n🔍 VALIDATION CHECKS:")

    # Check 1: Top player has positive delta
    top_player = delta_df.iloc[0]
    check1 = top_player['avg_skill_delta'] > 0
    print(f"   [{'✅' if check1 else '❌'}] Top player gained skills: {top_player['avg_skill_delta']:.2f}")

    # Check 2: Bottom player has negative delta
    bottom_player = delta_df.iloc[-1]
    check2 = bottom_player['avg_skill_delta'] < 0
    print(f"   [{'✅' if check2 else '❌'}] Bottom player lost skills: {bottom_player['avg_skill_delta']:.2f}")

    # Check 3: No skill exceeds bounds
    post_skills = post_df[skill_columns]
    check3_max = (post_skills <= 100).all().all()
    check3_min = (post_skills >= 10).all().all()
    check3 = check3_max and check3_min
    print(f"   [{'✅' if check3 else '❌'}] All skills within bounds (10-100)")

    # Check 4: XP changes align with skill changes
    xp_skill_correlation = delta_df[['avg_skill_delta', 'xp_delta']].corr().iloc[0, 1]
    check4 = xp_skill_correlation > 0.5
    print(f"   [{'✅' if check4 else '❌'}] XP/Skill correlation: {xp_skill_correlation:.2f}")

    # Overall result
    all_checks = check1 and check2 and check3 and check4
    print(f"\n{'✅ VALIDATION PASSED' if all_checks else '❌ VALIDATION FAILED'}")

    # Generate summary report
    summary_file = results_dir / f"sandbox_{scenario_id}_summary.md"
    with open(summary_file, 'w') as f:
        f.write(f"# Sandbox Validation Summary - {scenario_id}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Result:** {'✅ PASS' if all_checks else '❌ FAIL'}\n\n")
        f.write("## Top 3 Players\n\n")
        for i, row in delta_df.head(3).iterrows():
            f.write(f"**{i+1}. {row['name']}**\n")
            f.write(f"- Avg Skill Δ: {row['avg_skill_delta']:.2f}\n")
            f.write(f"- XP Δ: {row['xp_delta']:.0f}\n")
            f.write(f"- Level Δ: {row['level_delta']:.0f}\n\n")

        f.write("## Bottom 3 Players\n\n")
        for i, row in delta_df.tail(3).iterrows():
            f.write(f"**{len(delta_df)-i}. {row['name']}**\n")
            f.write(f"- Avg Skill Δ: {row['avg_skill_delta']:.2f}\n")
            f.write(f"- XP Δ: {row['xp_delta']:.0f}\n")
            f.write(f"- Level Δ: {row['level_delta']:.0f}\n\n")

        f.write("## Validation Checks\n\n")
        f.write(f"- [{'x' if check1 else ' '}] Top player gained skills\n")
        f.write(f"- [{'x' if check2 else ' '}] Bottom player lost skills\n")
        f.write(f"- [{'x' if check3 else ' '}] Skills within bounds (10-100)\n")
        f.write(f"- [{'x' if check4 else ' '}] XP/Skill correlation positive\n")

    print(f"✅ Summary report: {summary_file.name}")

    return all_checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate skill deltas for sandbox validation")
    parser.add_argument("--scenario", required=True, help="Scenario ID (e.g., S1)")

    args = parser.parse_args()

    passed = calculate_deltas(args.scenario)
    exit(0 if passed else 1)
