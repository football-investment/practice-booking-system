#!/usr/bin/env python3
"""
Test session generation via API (simulating what Streamlit does)
"""
import requests
import json

API_BASE = "http://localhost:8000"

# Try to get a session cookie
cookies_response = requests.get(f"{API_BASE}/sessions")
print(f"Cookies response: {cookies_response.status_code}")
print(f"Cookies: {cookies_response.cookies}")

# Login
login_data = {
    "email": "admin@lfa.com",
    "password": "admin123"
}

print("\n" + "=" * 70)
print("Step 1: Login")
print("=" * 70)

login_response = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json=login_data
)

print(f"Status: {login_response.status_code}")

if login_response.status_code == 200:
    tokens = login_response.json()
    access_token = tokens.get("access_token")
    print(f"✅ Got access token: {access_token[:50]}...")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Check current tournament state
    print("\n" + "=" * 70)
    print("Step 2: Check Tournament State")
    print("=" * 70)

    tournament_response = requests.get(
        f"{API_BASE}/api/v1/semesters/18",
        headers=headers
    )

    print(f"Status: {tournament_response.status_code}")
    if tournament_response.status_code == 200:
        tournament = tournament_response.json()
        print(f"✅ Tournament: {tournament.get('name')}")
        print(f"   Number of rounds: {tournament.get('number_of_rounds')}")
        print(f"   Sessions generated: {tournament.get('sessions_generated')}")

    # Generate sessions
    print("\n" + "=" * 70)
    print("Step 3: Generate Sessions")
    print("=" * 70)

    generate_payload = {
        "parallel_fields": 4,
        "session_duration_minutes": 1,
        "break_minutes": 1,
        "number_of_rounds": 3
    }

    print(f"Payload: {json.dumps(generate_payload, indent=2)}")

    generate_response = requests.post(
        f"{API_BASE}/api/v1/tournaments/18/generate-sessions",
        headers=headers,
        json=generate_payload
    )

    print(f"\nStatus: {generate_response.status_code}")
    print(f"Response: {json.dumps(generate_response.json(), indent=2)}")

    if generate_response.status_code == 200:
        result = generate_response.json()
        print(f"\n✅ SUCCESS!")
        print(f"   Sessions created: {result.get('sessions_generated_count')}")

        # Verify in database
        print("\n" + "=" * 70)
        print("Step 4: Verify Database")
        print("=" * 70)

        import subprocess
        db_result = subprocess.run([
            "psql", "-U", "postgres", "-h", "localhost",
            "-d", "lfa_intern_system",
            "-c", """
SELECT id, title, tournament_round, date_start, date_end
FROM sessions
WHERE semester_id = 18 AND auto_generated = true
ORDER BY tournament_round;
            """
        ], capture_output=True, text=True)

        print(db_result.stdout)

        # Count sessions
        count_result = subprocess.run([
            "psql", "-U", "postgres", "-h", "localhost",
            "-d", "lfa_intern_system", "-t", "-c",
            "SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true;"
        ], capture_output=True, text=True)

        session_count = int(count_result.stdout.strip())

        print("\n" + "=" * 70)
        if session_count == 3:
            print("🎉 SUCCESS! Generated 3 sessions as expected!")
        else:
            print(f"❌ FAILURE! Expected 3 sessions, got {session_count}")
        print("=" * 70)

    else:
        print(f"\n❌ FAILED to generate sessions")
        print(f"Error: {generate_response.text}")

else:
    print(f"❌ Login failed: {login_response.text}")
