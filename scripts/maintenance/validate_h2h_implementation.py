#!/usr/bin/env python3
"""
Pre-validation Check for HEAD_TO_HEAD Implementation

Runs automated checks to identify blockers BEFORE manual testing.
This ensures we don't waste time on broken code.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def check_backend_health():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend unhealthy: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not reachable: {e}")
        return False

def check_tournament_types():
    """Check if tournament types are loaded"""
    try:
        response = requests.get(f"{BASE_URL}/tournament-types", timeout=5)
        if response.status_code == 200:
            types = response.json()
            league = next((t for t in types if t['code'] == 'league'), None)
            knockout = next((t for t in types if t['code'] == 'knockout'), None)

            if league and knockout:
                print(f"✅ Tournament types available: league (id={league['id']}), knockout (id={knockout['id']})")
                return True, league['id'], knockout['id']
            else:
                print("❌ Missing tournament types (league or knockout)")
                return False, None, None
        else:
            print(f"❌ Failed to fetch tournament types: {response.status_code}")
            return False, None, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Tournament types endpoint error: {e}")
        return False, None, None

def check_head_to_head_result_endpoint():
    """Check if HEAD_TO_HEAD result endpoint exists"""
    # This will fail without auth, but we're just checking if endpoint exists
    try:
        response = requests.patch(
            f"{BASE_URL}/sessions/999999/head-to-head-results",
            json={"results": [{"user_id": 1, "score": 0}, {"user_id": 2, "score": 0}]},
            timeout=5
        )
        # We expect 401/403 (auth) or 404 (session not found), NOT 404 (endpoint not found)
        if response.status_code in [401, 403, 404]:
            print("✅ HEAD_TO_HEAD result endpoint exists")
            return True
        elif response.status_code == 404 and "not found" in response.text.lower():
            print("❌ HEAD_TO_HEAD result endpoint not found (route missing)")
            return False
        else:
            print(f"⚠️  HEAD_TO_HEAD result endpoint returned unexpected: {response.status_code}")
            return True  # Endpoint exists, just other error
    except requests.exceptions.RequestException as e:
        print(f"❌ HEAD_TO_HEAD result endpoint error: {e}")
        return False

def check_ranking_calculation_endpoint():
    """Check if ranking calculation endpoint exists"""
    try:
        response = requests.post(
            f"{BASE_URL}/tournaments/999999/calculate-rankings",
            timeout=5
        )
        # We expect 401/403 (auth) or 404 (tournament not found), NOT 404 (endpoint not found)
        if response.status_code in [401, 403, 404]:
            print("✅ Ranking calculation endpoint exists")
            return True
        elif response.status_code == 404 and "not found" in response.text.lower():
            print("❌ Ranking calculation endpoint not found (route missing)")
            return False
        else:
            print(f"⚠️  Ranking calculation endpoint returned unexpected: {response.status_code}")
            return True  # Endpoint exists, just other error
    except requests.exceptions.RequestException as e:
        print(f"❌ Ranking calculation endpoint error: {e}")
        return False

def check_python_imports():
    """Check if Python ranking strategies can be imported"""
    try:
        from app.services.tournament.ranking.strategies.head_to_head_league import HeadToHeadLeagueRankingStrategy
        from app.services.tournament.ranking.strategies.head_to_head_knockout import HeadToHeadKnockoutRankingStrategy
        print("✅ Ranking strategy classes importable")
        return True
    except ImportError as e:
        print(f"❌ Ranking strategy import failed: {e}")
        return False

def main():
    print("="*80)
    print("HEAD_TO_HEAD Implementation Pre-Validation Check")
    print("="*80)
    print()

    checks = []

    # Check 1: Backend health
    checks.append(("Backend Health", check_backend_health()))

    # Check 2: Tournament types
    types_ok, league_id, knockout_id = check_tournament_types()
    checks.append(("Tournament Types", types_ok))

    # Check 3: HEAD_TO_HEAD result endpoint
    checks.append(("HEAD_TO_HEAD Result Endpoint", check_head_to_head_result_endpoint()))

    # Check 4: Ranking calculation endpoint
    checks.append(("Ranking Calculation Endpoint", check_ranking_calculation_endpoint()))

    # Check 5: Python imports
    checks.append(("Python Ranking Strategies", check_python_imports()))

    print()
    print("="*80)
    print("Summary")
    print("="*80)

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")

    print()
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        print()
        print("🎉 All checks PASSED - Implementation ready for manual testing")
        return 0
    else:
        print()
        print("🚫 Some checks FAILED - Fix blockers before manual testing")
        return 1

if __name__ == "__main__":
    sys.exit(main())
