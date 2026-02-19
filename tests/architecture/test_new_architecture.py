#!/usr/bin/env python3
"""
Test NEW ARCHITECTURE: 1 session with rounds_data for INDIVIDUAL_RANKING
"""
import requests
import json
import subprocess

API_BASE = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

access_token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

print("=" * 70)
print("🔄 Testing NEW Architecture: 1 session with rounds_data")
print("=" * 70)

# Change status to IN_PROGRESS (should auto-generate 1 session)
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18/status",
    headers=headers,
    json={
        "new_status": "IN_PROGRESS",
        "reason": "Testing new architecture: 1 session with 7 rounds"
    }
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    # Check database
    result = subprocess.run([
        "psql", "-U", "postgres", "-h", "localhost",
        "-d", "lfa_intern_system", "-c",
        """
        SELECT
            s.tournament_status,
            s.number_of_rounds,
            s.sessions_generated,
            (SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true) as session_count
        FROM semesters s
        WHERE s.id = 18;
        """
    ], capture_output=True, text=True)

    print("\n" + "=" * 70)
    print("Database verification:")
    print("=" * 70)
    print(result.stdout)

    # Show generated session
    result2 = subprocess.run([
        "psql", "-U", "postgres", "-h", "localhost",
        "-d", "lfa_intern_system", "-c",
        """
        SELECT id, title, tournament_round,
               rounds_data->'total_rounds' as total_rounds,
               rounds_data->'completed_rounds' as completed_rounds
        FROM sessions
        WHERE semester_id = 18 AND auto_generated = true;
        """
    ], capture_output=True, text=True)

    print("\nGenerated session:")
    print("=" * 70)
    print(result2.stdout)

    # Count sessions
    count_result = subprocess.run([
        "psql", "-U", "postgres", "-h", "localhost",
        "-d", "lfa_intern_system", "-t", "-c",
        "SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true;"
    ], capture_output=True, text=True)

    session_count = int(count_result.stdout.strip())

    print("\n" + "=" * 70)
    if session_count == 1:
        print("🎉 SUCCESS! Auto-generated 1 session as expected (NEW ARCHITECTURE)!")
        print("   OLD: 7 sessions (1 per round)")
        print("   NEW: 1 session with rounds_data containing 7 rounds")
    else:
        print(f"❌ FAILURE! Expected 1 session, got {session_count}")
    print("=" * 70)
else:
    print(f"\n❌ Failed to start tournament")
