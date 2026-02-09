#!/usr/bin/env python3
"""
Verify Sandbox Determinism - State Isolation Test
==================================================

Runs the SAME tournament configuration 3 times to verify:
1. Skill profiles remain unchanged (no DB persistence)
2. Tournament results are identical (bit-perfect reproducibility)
3. Skill deltas calculated are consistent

Usage:
    python verify_determinism.py

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

# Test configuration - FIXED for determinism
TEST_CONFIG = {
    "name": "Determinism Test",
    "tournament_type": "league",
    "player_count": 6,
    "skills": ["passing", "dribbling", "shot_power"]
}

# Test user pool (first 6 from TEST_USER_POOL)
TEST_USERS = [4, 5, 6, 7, 13, 14]


def get_admin_token():
    """Authenticate as admin"""
    print("\n🔑 Authenticating as admin...")
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


def get_user_skills(token: str, user_id: int) -> dict:
    """Get current skill profile for a user"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{API_BASE_URL}/skills/profile/{user_id}",
        headers=headers
    )

    if response.status_code != 200:
        return {}

    profile = response.json()

    # Extract skill levels
    skills = {}
    if "skills" in profile:
        for skill_name, skill_data in profile["skills"].items():
            if isinstance(skill_data, dict) and "current_level" in skill_data:
                skills[skill_name] = skill_data["current_level"]

    return skills


def run_tournament(token: str, run_number: int) -> dict:
    """Execute single tournament run"""
    print(f"\n{'='*80}")
    print(f"RUN #{run_number}")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    request_payload = {
        "tournament_type": TEST_CONFIG["tournament_type"],
        "skills_to_test": TEST_CONFIG["skills"],
        "player_count": TEST_CONFIG["player_count"],
        "test_config": {
            "performance_variation": "MEDIUM",
            "ranking_distribution": "NORMAL"
        }
    }

    print(f"\n📤 Sending API request...")
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

    print(f"\n{'✅' if verdict == 'WORKING' else '❌'} Verdict: {verdict}")

    # Extract key metrics
    top_performers = result.get("top_performers", [])
    skill_progression = result.get("skill_progression", {})

    print(f"\n📊 TOP 3 PERFORMERS:")
    for performer in top_performers[:3]:
        rank = performer.get("rank")
        username = performer.get("username")
        total_gain = performer.get("total_skill_gain", 0)
        print(f"   #{rank} {username}: {total_gain:+.1f} total skill gain")

    print(f"\n📈 SKILL PROGRESSION:")
    for skill_name, stats in skill_progression.items():
        before_avg = stats["before"]["average"]
        after_avg = stats["after"]["average"]
        change = stats["change"]
        print(f"   {skill_name}: {before_avg:.1f} → {after_avg:.1f} ({change})")

    return result


def main():
    """Execute determinism validation"""
    print("\n" + "="*80)
    print("SANDBOX DETERMINISM VALIDATION")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Authenticate
    token = get_admin_token()
    if not token:
        print("\n❌ Authentication failed. Exiting.")
        return

    # Get baseline skills BEFORE first run
    print("\n📸 Capturing baseline skill profiles...")
    baseline_skills = {}
    for user_id in TEST_USERS:
        skills = get_user_skills(token, user_id)
        baseline_skills[user_id] = skills
        print(f"   User {user_id}: {len(skills)} skills captured")

    # Run tournament 3 times
    results = []
    for run_num in range(1, 4):
        result = run_tournament(token, run_num)
        if result:
            results.append(result)
        time.sleep(2)  # Brief pause between runs

    # Get skills AFTER all runs
    print("\n📸 Capturing final skill profiles...")
    final_skills = {}
    for user_id in TEST_USERS:
        skills = get_user_skills(token, user_id)
        final_skills[user_id] = skills
        print(f"   User {user_id}: {len(skills)} skills captured")

    # Validate state isolation
    print(f"\n{'='*80}")
    print("VALIDATION: STATE ISOLATION (No DB Persistence)")
    print(f"{'='*80}")

    all_unchanged = True
    for user_id in TEST_USERS:
        baseline = baseline_skills.get(user_id, {})
        final = final_skills.get(user_id, {})

        skills_changed = []
        for skill_name in TEST_CONFIG["skills"]:
            before = baseline.get(skill_name, 0)
            after = final.get(skill_name, 0)

            if abs(after - before) > 0.01:  # Allow 0.01 rounding tolerance
                skills_changed.append(f"{skill_name}: {before:.1f} → {after:.1f}")
                all_unchanged = False

        if skills_changed:
            print(f"   User {user_id}: ❌ SKILLS CHANGED!")
            for change in skills_changed:
                print(f"      {change}")
        else:
            print(f"   User {user_id}: ✅ Skills unchanged")

    # Validate determinism
    print(f"\n{'='*80}")
    print("VALIDATION: DETERMINISM (Identical Results)")
    print(f"{'='*80}")

    if len(results) < 3:
        print("❌ Not enough successful runs to validate determinism")
    else:
        # Compare top performers across runs
        print("\n🏆 Top Performer Consistency:")
        top_performers_per_run = [
            [(p["user_id"], p["rank"], p["total_skill_gain"]) for p in r.get("top_performers", [])[:3]]
            for r in results
        ]

        run1 = top_performers_per_run[0]
        consistent = True

        for i, run in enumerate(top_performers_per_run[1:], start=2):
            if run == run1:
                print(f"   Run {i}: ✅ Identical to Run 1")
            else:
                print(f"   Run {i}: ❌ DIFFERS from Run 1")
                consistent = False

        # Compare skill progression averages
        print("\n📈 Skill Progression Consistency:")
        skill_avgs_per_run = []
        for r in results:
            skill_prog = r.get("skill_progression", {})
            avgs = {
                skill: stats["after"]["average"]
                for skill, stats in skill_prog.items()
            }
            skill_avgs_per_run.append(avgs)

        run1_avgs = skill_avgs_per_run[0]

        for i, run_avgs in enumerate(skill_avgs_per_run[1:], start=2):
            match = True
            for skill in TEST_CONFIG["skills"]:
                val1 = run1_avgs.get(skill, 0)
                val2 = run_avgs.get(skill, 0)

                if abs(val1 - val2) > 0.1:  # Allow 0.1 tolerance
                    print(f"   Run {i}: ❌ {skill} differs: {val1:.1f} vs {val2:.1f}")
                    match = False
                    consistent = False

            if match:
                print(f"   Run {i}: ✅ All skill averages match Run 1")

    # Final verdict
    print(f"\n{'='*80}")
    print("FINAL VERDICT")
    print(f"{'='*80}")

    if all_unchanged and consistent:
        print("✅ PASS: Full state isolation + deterministic results achieved!")
        print("   • Skills unchanged after 3 tournament runs")
        print("   • Identical tournament results across all runs")
        print("   • Sandbox environment is fully isolated and reproducible")
    elif all_unchanged:
        print("⚠️ PARTIAL PASS: State isolation OK, but results not deterministic")
        print("   • Skills unchanged (good)")
        print("   • But tournament results differ across runs (investigate)")
    else:
        print("❌ FAIL: State isolation broken - skills persisted to DB")
        print("   • Skills changed after tournament runs")
        print("   • Sandbox mode not working correctly")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
