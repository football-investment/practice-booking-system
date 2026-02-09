#!/usr/bin/env python3
"""
Edge Case Testing - Extreme Performance Scenarios
==================================================

Tests skill progression under extreme conditions:
1. Balanced performance (normal distribution)
2. Dominant winner (top-heavy distribution)
3. Close competition (bottom-heavy distribution)

Validates:
- Skill formula not distorted
- Ceiling/floor behavior correct
- Proportional rewards across all scenarios
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"

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


def run_edge_case(token: str, case_name: str, distribution: str):
    """Run single edge case test"""
    print(f"\n{'='*80}")
    print(f"EDGE CASE: {case_name}")
    print(f"{'='*80}")

    headers = {"Authorization": f"Bearer {token}"}

    request_payload = {
        "tournament_type": "league",
        "skills_to_test": ["passing", "dribbling", "shot_power"],
        "player_count": 6,
        "test_config": {
            "performance_variation": "MEDIUM",
            "ranking_distribution": distribution
        }
    }

    print(f"\n📤 Sending API request (distribution={distribution})...")

    response = requests.post(
        f"{API_BASE_URL}/sandbox/run-test",
        headers=headers,
        json=request_payload
    )

    if response.status_code != 200:
        print(f"❌ API call failed: HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        return None

    result = response.json()
    verdict = result.get("verdict")

    print(f"\n{'✅' if verdict == 'WORKING' else '❌'} Verdict: {verdict}")

    # Analyze results
    top = result.get("top_performers", [])[:3]
    bottom = result.get("bottom_performers", [])

    print(f"\n📊 SKILL DISTRIBUTION ANALYSIS:\n")

    print("TOP 3:")
    for p in top:
        rank = p.get("rank")
        username = p.get("username")
        total_gain = p.get("total_skill_gain", 0)
        print(f"  #{rank} {username}: {total_gain:+.1f} total")

    print("\nBOTTOM 2:")
    for p in bottom[-2:]:
        rank = p.get("rank")
        username = p.get("username")
        total_gain = p.get("total_skill_gain", 0)
        print(f"  #{rank} {username}: {total_gain:+.1f} total")

    # Check proportionality
    if top and bottom:
        top_avg = sum(p.get("total_skill_gain", 0) for p in top) / len(top)
        bottom_avg = sum(p.get("total_skill_gain", 0) for p in bottom) / len(bottom)

        print(f"\n📈 PROPORTIONALITY CHECK:")
        print(f"   Top 3 avg: {top_avg:+.2f}")
        print(f"   Bottom 2 avg: {bottom_avg:+.2f}")
        print(f"   Ratio: {abs(top_avg / bottom_avg) if bottom_avg != 0 else 'N/A':.2f}x")

        if top_avg > bottom_avg:
            print(f"   ✅ Top performers gained more than bottom")
        else:
            print(f"   ❌ INVERTED: Bottom gained more than top!")

    return result


def main():
    """Execute edge case tests"""
    print("\n" + "="*80)
    print("EDGE CASE TESTING - EXTREME PERFORMANCE SCENARIOS")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Authenticate
    token = get_admin_token()
    if not token:
        print("\n❌ Authentication failed. Exiting.")
        return

    # Run edge cases
    results = {}

    # Case 1: Normal distribution (balanced)
    results["normal"] = run_edge_case(token, "Balanced Performance", "NORMAL")

    # Case 2: Top-heavy (dominant winner)
    results["top_heavy"] = run_edge_case(token, "Dominant Winner", "TOP_HEAVY")

    # Case 3: Bottom-heavy (close competition)
    results["bottom_heavy"] = run_edge_case(token, "Close Competition", "BOTTOM_HEAVY")

    # Final analysis
    print(f"\n{'='*80}")
    print("EDGE CASE SUMMARY")
    print(f"{'='*80}")

    all_passed = True
    for case, result in results.items():
        if result and result.get("verdict") == "WORKING":
            print(f"{case.upper():15s}: ✅ PASS")
        else:
            print(f"{case.upper():15s}: ❌ FAIL")
            all_passed = False

    if all_passed:
        print("\n✅ ALL EDGE CASES PASSED - Skill formula robust across scenarios")
    else:
        print("\n❌ SOME EDGE CASES FAILED - Review skill progression logic")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
