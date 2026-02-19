#!/usr/bin/env python3
"""
Automated Sandbox Validation - API-Based
==========================================

Executes S1-S5 validation scenarios via /sandbox/run-test API endpoint.
Eliminates manual UI interaction - fully automated.

Usage:
    python run_validation_api.py

Requires:
    - Backend API running on http://localhost:8000
    - Admin credentials: admin@lfa.com / admin123
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

# Validation scenarios (aligned with actual skills_config.py keys)
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
        "tournament_type": "league",  # hybrid not in DB
        "player_count": 8,
        "skills": ["passing", "shot_power", "tackle", "ball_control"]
    },
    "S4": {
        "name": "Individual Ranking (7 players)",
        "tournament_type": "league",  # Using league for head-to-head
        "player_count": 7,
        "skills": ["dribbling", "finishing", "sprint_speed"]
    },
    "S5": {
        "name": "Group Stage Only",
        "tournament_type": "league",  # Pure league = group stage only
        "player_count": 6,
        "skills": ["passing", "ball_control", "shot_power"]
    }
}


def get_admin_token():
    """Authenticate as admin"""
    print("\\n🔑 Authenticating as admin...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )

    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return None

    token = response.json()["access_token"]
    print("✅ Admin authenticated")
    return token


def run_scenario(scenario_id: str, config: dict, token: str):
    """Execute single validation scenario via API"""
    print(f"\\n{'='*80}")
    print(f"SCENARIO {scenario_id}: {config['name']}")
    print(f"{'='*80}")
    print(f"  Type: {config['tournament_type']}")
    print(f"  Players: {config['player_count']}")
    print(f"  Skills: {', '.join(config['skills'])}")

    headers = {"Authorization": f"Bearer {token}"}

    request_payload = {
        "tournament_type": config["tournament_type"],
        "skills_to_test": config["skills"],
        "player_count": config["player_count"],
        "test_config": {
            "performance_variation": "MEDIUM",
            "ranking_distribution": "NORMAL"
        }
    }

    print(f"\\n📤 Sending API request...")
    start_time = time.time()

    response = requests.post(
        f"{API_BASE_URL}/sandbox/run-test",
        headers=headers,
        json=request_payload
    )

    elapsed_time = time.time() - start_time
    print(f"⏱️  Execution time: {elapsed_time:.2f}s")

    if response.status_code != 200:
        print(f"❌ API call failed: HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        return None

    result = response.json()
    verdict = result.get("verdict")

    print(f"\\n{'✅' if verdict == 'WORKING' else '❌'} Verdict: {verdict}")

    # Save full result to JSON
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = output_dir / f"sandbox_{scenario_id}_{timestamp}.json"

    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"💾 Full result saved: {result_file.name}")

    # Extract key metrics
    top_performers = result.get("top_performers", [])
    bottom_performers = result.get("bottom_performers", [])
    skill_progression = result.get("skill_progression", {})

    print(f"\\n📊 VALIDATION CHECKS:")
    print(f"   Top performers: {len(top_performers)}")
    print(f"   Bottom performers: {len(bottom_performers)}")

    # Check 1: Top performer gained skills
    if top_performers:
        top_player = top_performers[0]
        skill_delta = top_player.get("skill_delta", {})
        avg_delta = sum(skill_delta.values()) / len(skill_delta) if skill_delta else 0
        check1 = avg_delta > 0
        print(f"   [{'✅' if check1 else '❌'}] Top player gained skills: {avg_delta:.2f}")

    # Check 2: Bottom performer lost skills
    if bottom_performers:
        bottom_player = bottom_performers[-1]
        skill_delta = bottom_player.get("skill_delta", {})
        avg_delta = sum(skill_delta.values()) / len(skill_delta) if skill_delta else 0
        check2 = avg_delta < 0
        print(f"   [{'✅' if check2 else '❌'}] Bottom player lost skills: {avg_delta:.2f}")

    # Generate markdown summary
    summary_file = output_dir / f"sandbox_{scenario_id}_summary.md"
    with open(summary_file, 'w') as f:
        f.write(f"# Sandbox Validation Summary - {scenario_id}\\n\\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
        f.write(f"**Scenario:** {config['name']}\\n")
        f.write(f"**Verdict:** {'✅ PASS' if verdict == 'WORKING' else '❌ FAIL'}\\n\\n")

        f.write("## Configuration\\n\\n")
        f.write(f"- Tournament Type: {config['tournament_type']}\\n")
        f.write(f"- Player Count: {config['player_count']}\\n")
        f.write(f"- Skills Tested: {', '.join(config['skills'])}\\n\\n")

        f.write("## Top 3 Performers\\n\\n")
        for i, player in enumerate(top_performers[:3], 1):
            f.write(f"**{i}. {player.get('name', 'Unknown')}**\\n")
            f.write(f"- Final Rank: {player.get('final_rank')}\\n")
            skill_delta = player.get("skill_delta", {})
            avg_delta = sum(skill_delta.values()) / len(skill_delta) if skill_delta else 0
            f.write(f"- Avg Skill Δ: {avg_delta:.2f}\\n\\n")

        f.write("## Bottom 3 Performers\\n\\n")
        for i, player in enumerate(bottom_performers[-3:], 1):
            f.write(f"**{i}. {player.get('name', 'Unknown')}**\\n")
            f.write(f"- Final Rank: {player.get('final_rank')}\\n")
            skill_delta = player.get("skill_delta", {})
            avg_delta = sum(skill_delta.values()) / len(skill_delta) if skill_delta else 0
            f.write(f"- Avg Skill Δ: {avg_delta:.2f}\\n\\n")

    print(f"📝 Summary saved: {summary_file.name}")

    return result


def main():
    """Execute all validation scenarios"""
    print("\\n" + "="*80)
    print("SANDBOX VALIDATION - AUTOMATED API EXECUTION")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Authenticate
    token = get_admin_token()
    if not token:
        print("\\n❌ Authentication failed. Exiting.")
        return

    # Execute scenarios
    results = {}
    for scenario_id, config in SCENARIOS.items():
        try:
            result = run_scenario(scenario_id, config, token)
            results[scenario_id] = result
            time.sleep(2)  # Brief pause between scenarios
        except Exception as e:
            print(f"\\n❌ Scenario {scenario_id} failed with exception: {e}")
            results[scenario_id] = None

    # Final summary
    print(f"\\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")

    passed = 0
    failed = 0

    for scenario_id, result in results.items():
        if result and result.get("verdict") == "WORKING":
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"{scenario_id}: {status} - {SCENARIOS[scenario_id]['name']}")

    print(f"\\nTotal: {passed}/{len(SCENARIOS)} scenarios passed")

    if passed == len(SCENARIOS):
        print("\\n🎉 ALL SCENARIOS PASSED - Skill progression logic validated!")
    else:
        print(f"\\n⚠️ {failed} scenarios failed - Review results in tests/sandbox_validation/results/")

    print(f"\\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
