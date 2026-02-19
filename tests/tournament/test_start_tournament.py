#!/usr/bin/env python3
"""
Test Start Tournament (ENROLLMENT_CLOSED → IN_PROGRESS) with auto-session generation
"""
import requests
import json

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
print("Testing Start Tournament with number_of_rounds = 2")
print("Testing regeneration when session count doesn't match")
print("=" * 70)

# Change status to IN_PROGRESS (this should auto-generate sessions)
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18/status",
    headers=headers,
    json={
        "new_status": "IN_PROGRESS",
        "reason": "Testing regeneration with number_of_rounds=2"
    }
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    # Check database
    import subprocess
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

    # Show generated sessions
    result2 = subprocess.run([
        "psql", "-U", "postgres", "-h", "localhost",
        "-d", "lfa_intern_system", "-c",
        """
        SELECT id, title, tournament_round
        FROM sessions
        WHERE semester_id = 18 AND auto_generated = true
        ORDER BY tournament_round;
        """
    ], capture_output=True, text=True)

    print("\nGenerated sessions:")
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
    if session_count == 2:
        print("🎉 SUCCESS! Auto-generated 2 sessions as expected!")
    else:
        print(f"❌ FAILURE! Expected 2 sessions, got {session_count}")
    print("=" * 70)
else:
    print(f"\n❌ Failed to start tournament")
