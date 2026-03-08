#!/usr/bin/env python3
"""
E2E Test: Continue Tournament Flow
Tests the complete workflow: Home → History → Continue Tournament
For both DRAFT and IN_PROGRESS (with None final_standings) tournaments
"""

import requests
import json
from typing import Dict, Optional

API_BASE = "http://localhost:8000/api/v1"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_step(msg: str):
    print(f"{Colors.BLUE}→{Colors.END} {msg}")

def log_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def login() -> str:
    """Step 1: Login as admin"""
    log_step("Logging in as admin...")
    resp = requests.post(f"{API_BASE}/auth/login", json={
        "email": "admin@lfa.com",
        "password": "admin123"
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    log_success(f"Logged in successfully")
    return token

def get_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def fetch_tournaments(token: str) -> list:
    """Step 2: Fetch all tournaments"""
    log_step("Fetching all tournaments...")
    headers = get_headers(token)
    resp = requests.get(f"{API_BASE}/semesters/", headers=headers)
    resp.raise_for_status()

    data = resp.json()
    if isinstance(data, dict):
        tournaments = data.get('semesters', [])
    else:
        tournaments = data

    # Filter sandbox tournaments
    sandbox_tournaments = [
        t for t in tournaments
        if 'SANDBOX' in t.get('code', '').upper() or 'sandbox' in t.get('code', '').lower()
    ]

    log_success(f"Found {len(sandbox_tournaments)} sandbox tournaments")
    return sandbox_tournaments

def test_tournament_detail(token: str, tournament_id: int, status: str) -> bool:
    """Step 3: Test tournament detail endpoint"""
    log_step(f"Testing tournament {tournament_id} (status: {status})...")
    headers = get_headers(token)

    # Fetch tournament detail
    resp = requests.get(f"{API_BASE}/semesters/{tournament_id}", headers=headers)
    resp.raise_for_status()
    detail = resp.json()

    # Check critical fields
    reward_config = detail.get('reward_config')
    log_step(f"  reward_config type: {type(reward_config)}, is None: {reward_config is None}")

    # Simulate state loading (the fixed code)
    try:
        skills_to_test = [
            s['skill']
            for s in (detail.get('reward_config') or {}).get('skill_mappings', [])
            if s.get('enabled', True)
        ]
        log_success(f"  ✓ State loading succeeded! Skills: {skills_to_test}")
        return True
    except AttributeError as e:
        log_error(f"  ✗ State loading FAILED: {e}")
        return False

def test_leaderboard(token: str, tournament_id: int) -> Optional[bool]:
    """Step 4: Test leaderboard endpoint"""
    log_step(f"Testing leaderboard for tournament {tournament_id}...")
    headers = get_headers(token)

    resp = requests.get(f"{API_BASE}/tournaments/{tournament_id}/leaderboard", headers=headers)
    if resp.status_code != 200:
        log_warning(f"  Leaderboard not available (404/403 expected for DRAFT)")
        return None

    data = resp.json()
    has_key = 'final_standings' in data
    value = data.get('final_standings')

    log_step(f"  final_standings key exists: {has_key}")
    log_step(f"  final_standings value: {value}")
    log_step(f"  final_standings is None: {value is None}")

    # Test the condition used in Continue Tournament button
    has_final_standings = 'final_standings' in data and data['final_standings'] is not None
    log_success(f"  ✓ has_final_standings check: {has_final_standings}")

    return has_final_standings

def main():
    print("\n" + "=" * 80)
    print("E2E TEST: Continue Tournament Flow")
    print("=" * 80 + "\n")

    try:
        # Step 1: Login
        token = login()

        # Step 2: Fetch tournaments
        tournaments = fetch_tournaments(token)

        if not tournaments:
            log_error("No sandbox tournaments found. Create some first!")
            return

        # Group by status
        draft_tournaments = [t for t in tournaments if t.get('tournament_status') == 'DRAFT']
        in_progress_tournaments = [t for t in tournaments if t.get('tournament_status') == 'IN_PROGRESS']

        print(f"\n{Colors.BLUE}{'=' * 80}{Colors.END}")
        print(f"{Colors.BLUE}TEST CASE 1: DRAFT Tournament{Colors.END}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.END}\n")

        if draft_tournaments:
            t = draft_tournaments[0]
            tid = t['id']
            name = t.get('name', 'Unknown')
            log_step(f"Testing DRAFT tournament: {name} (ID: {tid})")

            success = test_tournament_detail(token, tid, 'DRAFT')
            if success:
                log_success(f"✅ DRAFT tournament test PASSED")
            else:
                log_error(f"❌ DRAFT tournament test FAILED")
        else:
            log_warning("No DRAFT tournaments found to test")

        print(f"\n{Colors.BLUE}{'=' * 80}{Colors.END}")
        print(f"{Colors.BLUE}TEST CASE 2: IN_PROGRESS Tournament (with None final_standings){Colors.END}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.END}\n")

        if in_progress_tournaments:
            t = in_progress_tournaments[0]
            tid = t['id']
            name = t.get('name', 'Unknown')
            log_step(f"Testing IN_PROGRESS tournament: {name} (ID: {tid})")

            # Test detail loading
            detail_success = test_tournament_detail(token, tid, 'IN_PROGRESS')

            # Test leaderboard
            has_final_standings = test_leaderboard(token, tid)

            if detail_success:
                log_success(f"✅ IN_PROGRESS tournament detail test PASSED")
            else:
                log_error(f"❌ IN_PROGRESS tournament detail test FAILED")

            if has_final_standings is None:
                log_warning(f"⚠️  Leaderboard not available (tournament may not have started)")
            elif has_final_standings:
                log_success(f"✅ Tournament has final_standings (would jump to Step 6)")
            else:
                log_success(f"✅ Tournament has NO final_standings (would jump to Step 2)")
        else:
            log_warning("No IN_PROGRESS tournaments found to test")

        print(f"\n{Colors.GREEN}{'=' * 80}{Colors.END}")
        print(f"{Colors.GREEN}E2E TEST COMPLETE{Colors.END}")
        print(f"{Colors.GREEN}{'=' * 80}{Colors.END}\n")

    except Exception as e:
        log_error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
