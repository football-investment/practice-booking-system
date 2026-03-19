#!/usr/bin/env python3
"""
Game Design KPI Dashboard — Sprint F

Pure Python simulation (NO DB writes).
Validates skill progression design and measures game balance KPIs.

TASKS:
  3. Preset Differentiation — proves passing_focus→passing grows more,
     shooting_focus→finishing grows more (quantitative comparison).
  4. Real User Simulation — 80 virtual players, 3 skill tiers × 8 tournaments.
  5. KPI Refinement — skill delta variance, top performer spread,
     improvement per tournament, positive-experience rate.

Run: python scripts/game_design_kpi.py
"""

import sys
import os
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.skill_progression_service import (
    calculate_skill_value_from_placement,
    PLACEMENT_SKILL_FLOOR,
    MIN_SKILL_VALUE,
    MAX_SKILL_CAP,
)

# ── Preset definitions (mirrors seed_game_presets.py) ──────────────────────────

PRESETS = {
    "outfield_default": {
        "skills": ["ball_control", "dribbling", "finishing", "passing", "vision",
                   "positioning_off", "sprint_speed", "agility", "stamina"],
        "weights": {
            "ball_control": 1.2, "dribbling": 1.5, "finishing": 1.4,
            "passing": 1.3, "vision": 1.1, "positioning_off": 1.1,
            "sprint_speed": 1.0, "agility": 1.0, "stamina": 0.9,
        },
    },
    "passing_focus": {
        "skills": ["passing", "vision", "ball_control", "positioning_off", "agility", "stamina"],
        "weights": {
            "passing": 1.8, "vision": 1.6, "ball_control": 1.4,
            "positioning_off": 1.3, "agility": 1.0, "stamina": 0.8,
        },
    },
    "shooting_focus": {
        "skills": ["finishing", "sprint_speed", "dribbling", "ball_control", "agility", "positioning_off"],
        "weights": {
            "finishing": 2.0, "sprint_speed": 1.6, "dribbling": 1.5,
            "ball_control": 1.2, "agility": 1.1, "positioning_off": 0.9,
        },
    },
}

# ── Player tiers ───────────────────────────────────────────────────────────────

TIER_CONFIGS = [
    {"name": "Beginner",     "skill_range": (42, 57),  "count": 25},
    {"name": "Developing",   "skill_range": (58, 72),  "count": 30},
    {"name": "Intermediate", "skill_range": (73, 88),  "count": 25},
]

ALL_SKILLS = list(set(
    s for p in PRESETS.values() for s in p["skills"]
))

TOURNAMENT_COUNT = 8


# ── Simulation helpers ─────────────────────────────────────────────────────────

def make_player(tier: dict, rng: random.Random) -> dict:
    lo, hi = tier["skill_range"]
    skills = {s: round(rng.uniform(lo, hi), 1) for s in ALL_SKILLS}
    return {"tier": tier["name"], "skills": skills}


def simulate_tournament(
    players: list[dict],
    preset_name: str,
    tournament_count: int,
    rng: random.Random,
) -> list[dict]:
    """Simulate one tournament: assign random placements, update skills via EMA."""
    preset = PRESETS[preset_name]
    n = len(players)
    # Shuffle players to assign random placements
    order = list(range(n))
    rng.shuffle(order)
    placements = {player_idx: rank + 1 for rank, player_idx in enumerate(order)}

    deltas = []  # per-player summary
    for idx, player in enumerate(players):
        placement = placements[idx]
        skill_deltas = {}
        for skill in preset["skills"]:
            weight = preset["weights"][skill]
            prev = player["skills"].get(skill, 65.0)
            new_val = calculate_skill_value_from_placement(
                baseline=prev,
                placement=placement,
                total_players=n,
                tournament_count=tournament_count,
                skill_weight=weight,
                prev_value=prev,
            )
            skill_deltas[skill] = round(new_val - prev, 2)
            player["skills"][skill] = new_val
        total_delta = round(sum(skill_deltas.values()), 2)
        deltas.append({
            "placement": placement,
            "total_delta": total_delta,
            "skill_deltas": skill_deltas,
            "net_positive": total_delta > 0,
        })
    return deltas


# ── Task 3: Preset Differentiation ────────────────────────────────────────────

def task3_preset_differentiation():
    """Prove that each preset creates measurably different skill trajectories."""
    print("=" * 70)
    print("TASK 3 — PRESET DIFFERENTIATION ANALYSIS")
    print("=" * 70)
    print()
    print("Setup: 1 player at skill level 65 across all skills, 8 tournaments,")
    print("       always mid-table (rank 4/8). Compare skill growth per preset.")
    print()

    BASE_SKILL = 65.0
    N_PLAYERS = 8    # 8-player tournament
    PLACEMENT = 4    # always mid-table

    results = {}
    for preset_name, preset in PRESETS.items():
        skills = {s: BASE_SKILL for s in ALL_SKILLS}
        history = defaultdict(list)
        for t in range(1, TOURNAMENT_COUNT + 1):
            for skill in preset["skills"]:
                weight = preset["weights"][skill]
                prev = skills[skill]
                new_val = calculate_skill_value_from_placement(
                    baseline=BASE_SKILL,
                    placement=PLACEMENT,
                    total_players=N_PLAYERS,
                    tournament_count=t,
                    skill_weight=weight,
                    prev_value=prev,
                )
                history[skill].append(round(new_val - BASE_SKILL, 2))
                skills[skill] = new_val

        # Final deltas after 8 tournaments
        final_deltas = {s: round(skills[s] - BASE_SKILL, 2) for s in preset["skills"]}
        results[preset_name] = {"final_deltas": final_deltas, "skills": skills}

        print(f"  [{preset_name}] (mid-table, {TOURNAMENT_COUNT} tournaments from L=65):")
        sorted_skills = sorted(final_deltas.items(), key=lambda x: -x[1])
        for skill, delta in sorted_skills:
            bar = "█" * int(abs(delta) * 2) if abs(delta) > 0 else "·"
            sign = "+" if delta >= 0 else ""
            w = preset["weights"].get(skill, 1.0)
            print(f"    {skill:<22} w={w:.1f}  {sign}{delta:+.1f}  {bar}")
        print()

    # Cross-preset comparison for key skills
    print("  CROSS-PRESET COMPARISON (key skills):")
    print(f"  {'Skill':<22} {'outfield':>10} {'passing_focus':>14} {'shooting_focus':>15}")
    print("  " + "-" * 65)
    key_skills = ["passing", "finishing", "dribbling", "vision", "ball_control"]
    for skill in key_skills:
        vals = {}
        for pn in PRESETS:
            fd = results[pn]["final_deltas"]
            vals[pn] = fd.get(skill, 0.0)
        print(
            f"  {skill:<22} {vals['outfield_default']:>+10.1f}"
            f" {vals['passing_focus']:>+14.1f}"
            f" {vals['shooting_focus']:>+15.1f}"
        )

    # Validation assertions
    print()
    passing_in_pass = results["passing_focus"]["final_deltas"].get("passing", 0)
    passing_in_shoot = results["shooting_focus"]["final_deltas"].get("passing", 0)
    finishing_in_shoot = results["shooting_focus"]["final_deltas"].get("finishing", 0)
    finishing_in_pass = results["passing_focus"]["final_deltas"].get("finishing", 0)

    print("  DIFFERENTIATION PROOF:")
    ok_passing = passing_in_pass > passing_in_shoot
    ok_finishing = finishing_in_shoot > finishing_in_pass
    print(f"  passing_focus.passing ({passing_in_pass:+.1f}) > shooting_focus.passing ({passing_in_shoot:+.1f}): {'✅' if ok_passing else '❌'}")
    print(f"  shooting_focus.finishing ({finishing_in_shoot:+.1f}) > passing_focus.finishing ({finishing_in_pass:+.1f}): {'✅' if ok_finishing else '❌'}")
    print()
    return ok_passing and ok_finishing


# ── Task 4+5: Real User Simulation + KPIs ─────────────────────────────────────

def task4_5_simulation_and_kpis():
    """Simulate 80 virtual players across 8 tournaments, compute game-design KPIs."""
    print("=" * 70)
    print("TASK 4+5 — SIMULATION (80 players, 8 tournaments) + KPI ANALYSIS")
    print("=" * 70)
    print()

    rng = random.Random(42)  # deterministic

    # Build player pool
    players = []
    for tier_cfg in TIER_CONFIGS:
        for _ in range(tier_cfg["count"]):
            players.append(make_player(tier_cfg, rng))
    total_players = len(players)
    tier_str = " / ".join(str(t["count"]) + " " + t["name"] for t in TIER_CONFIGS)
    print(f"  Players: {total_players} ({tier_str})")
    print(f"  Preset: outfield_default (9 skills) · {TOURNAMENT_COUNT} tournaments")
    print(f"  PLACEMENT_SKILL_FLOOR: {PLACEMENT_SKILL_FLOOR} (new balancing floor)")
    print()

    # Track KPI data
    all_round_deltas = []      # every delta from every player-tournament
    per_player_deltas = [[] for _ in range(total_players)]  # list of per-tournament totals
    positive_count = 0
    total_results = 0

    # Split into groups of ~10 for each tournament round (8 players = 1 tournament)
    # Actually: simulate one 80-player tournament per round (everyone competes)
    PRESET = "outfield_default"
    for t in range(1, TOURNAMENT_COUNT + 1):
        round_deltas = simulate_tournament(players, PRESET, t, rng)
        for idx, rd in enumerate(round_deltas):
            all_round_deltas.append(rd["total_delta"])
            per_player_deltas[idx].append(rd["total_delta"])
            if rd["net_positive"]:
                positive_count += 1
            total_results += 1

    # ── KPI: Positive Experience Rate ──────────────────────────────────────────
    positive_rate = positive_count / total_results
    print(f"  KPI 1 — POSITIVE EXPERIENCE RATE")
    print(f"    {positive_count}/{total_results} results net-positive = {positive_rate:.1%}")
    target_ok = 0.60 <= positive_rate <= 0.75
    print(f"    Target: 60–75%  →  {'✅ ON TARGET' if target_ok else '⚠️ OUT OF RANGE'}")
    print()

    # ── KPI: Skill Delta Distribution ──────────────────────────────────────────
    mean_delta = statistics.mean(all_round_deltas)
    stdev_delta = statistics.stdev(all_round_deltas)
    median_delta = statistics.median(all_round_deltas)
    q25 = sorted(all_round_deltas)[int(len(all_round_deltas) * 0.25)]
    q75 = sorted(all_round_deltas)[int(len(all_round_deltas) * 0.75)]
    print(f"  KPI 2 — SKILL DELTA DISTRIBUTION (per tournament per player)")
    print(f"    Mean:    {mean_delta:+.2f} pts")
    print(f"    Median:  {median_delta:+.2f} pts")
    print(f"    StdDev:  {stdev_delta:.2f} pts")
    print(f"    Q25/Q75: {q25:+.2f} / {q75:+.2f} pts")
    print(f"    Min/Max: {min(all_round_deltas):+.2f} / {max(all_round_deltas):+.2f} pts")
    print()

    # ── KPI: Cumulative growth per tier ────────────────────────────────────────
    print(f"  KPI 3 — CUMULATIVE GROWTH BY TIER (after {TOURNAMENT_COUNT} tournaments)")
    tier_starts = {}
    tier_ends = {}
    for i, player in enumerate(players):
        tier = player["tier"]
        if tier not in tier_starts:
            tier_starts[tier] = []
            tier_ends[tier] = []
        # Average skill across all skills
        avg = statistics.mean(player["skills"].values())
        tier_ends[tier].append(avg)

    # Recompute starting averages from config
    for tier_cfg in TIER_CONFIGS:
        lo, hi = tier_cfg["skill_range"]
        tier_starts[tier_cfg["name"]] = [(lo + hi) / 2] * tier_cfg["count"]

    for tier_cfg in TIER_CONFIGS:
        name = tier_cfg["name"]
        start_avg = statistics.mean(tier_starts[name])
        end_avg = statistics.mean(tier_ends[name])
        growth = end_avg - start_avg
        print(f"    {name:<14} start≈{start_avg:.1f}  end={end_avg:.1f}  Δ={growth:+.1f} pts")
    print()

    # ── KPI: Top Performer Spread ───────────────────────────────────────────────
    total_growth = []
    for player_deltas in per_player_deltas:
        total_growth.append(sum(player_deltas))
    total_growth_sorted = sorted(total_growth, reverse=True)
    top10 = statistics.mean(total_growth_sorted[:8])
    bottom10 = statistics.mean(total_growth_sorted[-8:])
    print(f"  KPI 4 — TOP/BOTTOM PERFORMER SPREAD (after {TOURNAMENT_COUNT} tournaments)")
    print(f"    Top 8 avg cumulative delta:    {top10:+.2f} pts")
    print(f"    Bottom 8 avg cumulative delta: {bottom10:+.2f} pts")
    print(f"    Spread: {top10 - bottom10:.2f} pts")
    spread_ok = top10 > 0 and bottom10 > -50  # bottom should not crater
    print(f"    Bottom cohort viable: {'✅' if spread_ok else '❌'}")
    print()

    # ── KPI: Variance by tournament round (fatigue check) ─────────────────────
    print(f"  KPI 5 — VARIANCE BY ROUND (skill delta volatility over time)")
    print(f"    {'Round':<8} {'Mean':>7} {'StdDev':>8} {'Positive%':>10}")
    print(f"    {'─'*40}")
    for t in range(TOURNAMENT_COUNT):
        round_vals = [per_player_deltas[p][t] for p in range(total_players)]
        pos = sum(1 for v in round_vals if v > 0)
        print(
            f"    T{t+1:<7} {statistics.mean(round_vals):>+7.2f}"
            f" {statistics.stdev(round_vals):>8.2f}"
            f" {pos/total_players:>9.1%}"
        )
    print()

    # ── KPI: Dropout Risk (players who never improved) ─────────────────────────
    never_improved = sum(1 for deltas in per_player_deltas if all(d <= 0 for d in deltas))
    dropout_risk = never_improved / total_players
    print(f"  KPI 6 — DROPOUT RISK (players who NEVER had a net-positive tournament)")
    print(f"    {never_improved}/{total_players} players ({dropout_risk:.1%}) — target: <5%")
    print(f"    {'✅ LOW RISK' if dropout_risk < 0.05 else '⚠️ HIGH RISK'}")
    print()

    return positive_rate, mean_delta, stdev_delta, dropout_risk


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           GAME DESIGN KPI DASHBOARD — Sprint F                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  PLACEMENT_SKILL_FLOOR = {PLACEMENT_SKILL_FLOOR}  (Sprint F balancing change)")
    print(f"  MIN_SKILL_VALUE       = {MIN_SKILL_VALUE}  (hard clamp, unchanged)")
    print()

    preset_ok = task3_preset_differentiation()

    positive_rate, mean_delta, stdev_delta, dropout_risk = task4_5_simulation_and_kpis()

    print("=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)
    print(f"  Preset differentiation:     {'✅ PROVEN' if preset_ok else '❌ FAILED'}")
    print(f"  Positive experience rate:   {positive_rate:.1%}  (target 60–75%)")
    print(f"    → {'✅ ON TARGET' if 0.60 <= positive_rate <= 0.75 else ('⬆️ TOO POSITIVE' if positive_rate > 0.75 else '⬇️ TOO NEGATIVE')}")
    print(f"  Mean delta per tournament:  {mean_delta:+.2f} pts  (healthy if > 0)")
    print(f"  Delta std dev:              {stdev_delta:.2f} pts  (spread in experience)")
    print(f"  Dropout risk (0 wins):      {dropout_risk:.1%}  (target < 5%)")
    print()


if __name__ == "__main__":
    main()
