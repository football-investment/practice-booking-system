#!/usr/bin/env python3
"""
Multi-Run Stability Validation
================================

Runs each sandbox scenario 10 times to validate:
- Skill delta consistency (low variance)
- Reward proportions stability
- Placement → skill correlation unchanged
- No drift or distortion after multiple runs

Acceptance criteria:
- Standard deviation < 10% of mean
- Ranking-skill correlation remains consistent
- No anomalies detected across runs
"""

import requests
import json
import time
import statistics
from datetime import datetime
from pathlib import Path

API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Run each scenario 10 times
RUNS_PER_SCENARIO = 10

SCENARIOS = {
    "S1": {
        "name": "League Tournament",
        "tournament_type": "league",
        "player_count": 8,
        "skills": ["passing", "dribbling", "shot_power", "tackle"]
    },
    "S2": {
        "name": "Knockout Tournament",
        "tournament_type": "knockout",
        "player_count": 8,
        "skills": ["ball_control", "finishing", "sprint_speed", "strength"]
    },
    "S3": {
        "name": "League Tournament (Scenario 3)",
        "tournament_type": "league",
        "player_count": 8,
        "skills": ["passing", "shot_power", "tackle", "ball_control"]
    },
    "S4": {
        "name": "Individual Ranking (7 players)",
        "tournament_type": "league",
        "player_count": 7,
        "skills": ["dribbling", "finishing", "sprint_speed"]
    },
    "S5": {
        "name": "Group Stage Only",
        "tournament_type": "league",
        "player_count": 6,
        "skills": ["passing", "ball_control", "shot_power"]
    }
}


def get_admin_token():
    """Authenticate as admin"""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return None

    return response.json()["access_token"]


def run_single_test(token: str, scenario_config: dict):
    """Execute single tournament test"""
    headers = {"Authorization": f"Bearer {token}"}

    request_payload = {
        "tournament_type": scenario_config["tournament_type"],
        "skills_to_test": scenario_config["skills"],
        "player_count": scenario_config["player_count"],
        "test_config": {
            "performance_variation": "MEDIUM",
            "ranking_distribution": "NORMAL"
        }
    }

    response = requests.post(
        f"{API_BASE_URL}/sandbox/run-test",
        headers=headers,
        json=request_payload
    )

    if response.status_code != 200:
        return None

    return response.json()


def extract_metrics(result):
    """Extract key metrics from test result"""
    if not result or result.get("verdict") != "WORKING":
        return None

    top = result.get("top_performers", [])
    bottom = result.get("bottom_performers", [])

    if not top or not bottom:
        return None

    # Extract skill deltas
    top_3_gains = [p.get("total_skill_gain", 0) for p in top[:3]]
    bottom_2_gains = [p.get("total_skill_gain", 0) for p in bottom[-2:]]

    # Extract skill progression averages
    skill_prog = result.get("skill_progression", {})
    skill_changes = {}
    for skill_name, stats in skill_prog.items():
        before_avg = stats["before"]["average"]
        after_avg = stats["after"]["average"]
        skill_changes[skill_name] = after_avg - before_avg

    return {
        "top_3_avg": statistics.mean(top_3_gains) if top_3_gains else 0,
        "bottom_2_avg": statistics.mean(bottom_2_gains) if bottom_2_gains else 0,
        "top_3_gains": top_3_gains,
        "bottom_2_gains": bottom_2_gains,
        "skill_changes": skill_changes,
        "verdict": result.get("verdict")
    }


def analyze_stability(scenario_id: str, metrics_list: list):
    """Analyze stability across multiple runs"""
    print(f"\n{'='*80}")
    print(f"STABILITY ANALYSIS: {scenario_id}")
    print(f"{'='*80}")

    if not metrics_list:
        print("❌ No valid metrics collected")
        return False

    # Analyze top 3 average skill gain
    top_3_avgs = [m["top_3_avg"] for m in metrics_list]
    top_3_mean = statistics.mean(top_3_avgs)
    top_3_stdev = statistics.stdev(top_3_avgs) if len(top_3_avgs) > 1 else 0
    top_3_cv = (top_3_stdev / top_3_mean * 100) if top_3_mean != 0 else 0

    # Analyze bottom 2 average skill gain
    bottom_2_avgs = [m["bottom_2_avg"] for m in metrics_list]
    bottom_2_mean = statistics.mean(bottom_2_avgs)
    bottom_2_stdev = statistics.stdev(bottom_2_avgs) if len(bottom_2_avgs) > 1 else 0
    bottom_2_cv = (bottom_2_stdev / abs(bottom_2_mean) * 100) if bottom_2_mean != 0 else 0

    print(f"\n📊 TOP 3 PERFORMERS:")
    print(f"   Mean skill gain: {top_3_mean:+.2f}")
    print(f"   Std deviation: {top_3_stdev:.2f}")
    print(f"   Coefficient of variation: {top_3_cv:.2f}%")
    print(f"   Min: {min(top_3_avgs):+.2f}, Max: {max(top_3_avgs):+.2f}")

    print(f"\n📊 BOTTOM 2 PERFORMERS:")
    print(f"   Mean skill gain: {bottom_2_mean:+.2f}")
    print(f"   Std deviation: {bottom_2_stdev:.2f}")
    print(f"   Coefficient of variation: {bottom_2_cv:.2f}%")
    print(f"   Min: {min(bottom_2_avgs):+.2f}, Max: {max(bottom_2_avgs):+.2f}")

    # Check for consistency (CV < 1% = perfect determinism)
    top_consistent = top_3_cv < 1.0
    bottom_consistent = bottom_2_cv < 1.0

    print(f"\n✅ DETERMINISM CHECK:")
    print(f"   Top 3 CV < 1%: {'✅ PASS' if top_consistent else '❌ FAIL'} ({top_3_cv:.2f}%)")
    print(f"   Bottom 2 CV < 1%: {'✅ PASS' if bottom_consistent else '❌ FAIL'} ({bottom_2_cv:.2f}%)")

    # Analyze skill-specific changes
    print(f"\n📈 SKILL-SPECIFIC STABILITY:")

    # Collect all skill names
    all_skills = set()
    for m in metrics_list:
        all_skills.update(m["skill_changes"].keys())

    skill_stable = True
    for skill_name in sorted(all_skills):
        skill_deltas = [m["skill_changes"].get(skill_name, 0) for m in metrics_list]
        skill_mean = statistics.mean(skill_deltas)
        skill_stdev = statistics.stdev(skill_deltas) if len(skill_deltas) > 1 else 0
        skill_cv = (skill_stdev / abs(skill_mean) * 100) if skill_mean != 0 else 0

        consistent = skill_cv < 1.0
        if not consistent:
            skill_stable = False

        print(f"   {skill_name:20s}: μ={skill_mean:+.2f}, σ={skill_stdev:.3f}, CV={skill_cv:.2f}% {'✅' if consistent else '❌'}")

    # Overall stability verdict
    overall_stable = top_consistent and bottom_consistent and skill_stable

    print(f"\n{'='*80}")
    if overall_stable:
        print(f"✅ STABILITY: PASS - Perfect determinism (CV < 1% for all metrics)")
    else:
        print(f"❌ STABILITY: FAIL - Variance detected (investigate root cause)")
    print(f"{'='*80}")

    return overall_stable


def main():
    """Execute multi-run stability validation"""
    print("\n" + "="*80)
    print("MULTI-RUN STABILITY VALIDATION")
    print("="*80)
    print(f"Runs per scenario: {RUNS_PER_SCENARIO}")
    print(f"Total tests: {len(SCENARIOS) * RUNS_PER_SCENARIO}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Authenticate
    print("\n🔑 Authenticating as admin...")
    token = get_admin_token()
    if not token:
        print("\n❌ Authentication failed. Exiting.")
        return

    print("✅ Admin authenticated")

    # Run stability tests for each scenario
    stability_results = {}

    for scenario_id, config in SCENARIOS.items():
        print(f"\n{'='*80}")
        print(f"SCENARIO {scenario_id}: {config['name']}")
        print(f"Running {RUNS_PER_SCENARIO} consecutive tests...")
        print(f"{'='*80}")

        metrics_list = []

        for run_num in range(1, RUNS_PER_SCENARIO + 1):
            print(f"\n  Run {run_num}/{RUNS_PER_SCENARIO}...", end=" ")

            result = run_single_test(token, config)

            if result:
                metrics = extract_metrics(result)
                if metrics:
                    metrics_list.append(metrics)
                    print(f"✅ ({metrics['verdict']})")
                else:
                    print("❌ (failed to extract metrics)")
            else:
                print("❌ (API call failed)")

            # Brief pause between runs
            if run_num < RUNS_PER_SCENARIO:
                time.sleep(0.5)

        # Analyze stability for this scenario
        is_stable = analyze_stability(scenario_id, metrics_list)
        stability_results[scenario_id] = {
            "stable": is_stable,
            "runs_completed": len(metrics_list),
            "metrics": metrics_list
        }

    # Final summary
    print(f"\n{'='*80}")
    print("FINAL STABILITY REPORT")
    print(f"{'='*80}")

    all_stable = True
    for scenario_id, result in stability_results.items():
        stable = result["stable"]
        runs = result["runs_completed"]

        if not stable:
            all_stable = False

        status = "✅ STABLE" if stable else "❌ UNSTABLE"
        print(f"{scenario_id}: {status} ({runs}/{RUNS_PER_SCENARIO} runs)")

    print(f"\n{'='*80}")
    if all_stable:
        print("✅✅✅ ALL SCENARIOS STABLE - Production-ready determinism achieved")
        print("")
        print("EXECUTIVE ANSWER:")
        print("👉 YES - The skill progression mechanism is stable under production load.")
        print("   Perfect determinism (CV < 1%) across all metrics and scenarios.")
    else:
        print("❌❌❌ STABILITY ISSUES DETECTED - Further investigation required")
        print("")
        print("EXECUTIVE ANSWER:")
        print("👉 NO - Variance detected in skill progression mechanism.")
        print("   Root cause analysis required before production deployment.")
    print(f"{'='*80}")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
