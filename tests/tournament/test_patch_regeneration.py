#!/usr/bin/env python3
"""
Test regeneration using ADMIN PATCH (bypass status validation):
1. Tournament IN_PROGRESS with 2 sessions
2. Admin patches number_of_rounds = 4  
3. Admin patches status = ENROLLMENT_CLOSED (bypass validation)
4. Admin patches status = IN_PROGRESS → should regenerate with 4 sessions
"""
import requests
import subprocess

API_BASE = "http://localhost:8000"

# Login
login = requests.post(f"{API_BASE}/api/v1/auth/login", json={"email":"admin@lfa.com","password":"admin123"})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=" * 70)
print("ADMIN PATCH REGENERATION TEST")
print("=" * 70)

# Step 1: Patch number_of_rounds to 4
print("\n✅ Step 1: Patch number_of_rounds to 4...")
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18",
    headers=headers,
    json={"number_of_rounds": 4}
)
print(f"   Status: {response.status_code}")

# Step 2: Admin PATCH status to ENROLLMENT_CLOSED (bypass validation)
print("\n✅ Step 2: Admin patch status to ENROLLMENT_CLOSED (bypass)...")
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18",
    headers=headers,
    json={"tournament_status": "ENROLLMENT_CLOSED"}
)
print(f"   Status: {response.status_code}")

# Check sessions deleted
result = subprocess.run([
    "psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-t", "-c",
    "SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true;"
], capture_output=True, text=True)
print(f"   Sessions after status patch: {result.stdout.strip()}")

# Step 3: Admin PATCH status to IN_PROGRESS → should regenerate 4 sessions
print("\n✅ Step 3: Admin patch status to IN_PROGRESS (should regenerate 4)...")
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18",
    headers=headers,
    json={"tournament_status": "IN_PROGRESS"}
)
print(f"   Status: {response.status_code}")

# Verify result
result = subprocess.run([
    "psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-c",
    "SELECT id, title, tournament_round FROM sessions WHERE semester_id = 18 AND auto_generated = true ORDER BY tournament_round;"
], capture_output=True, text=True)

print("\n" + "=" * 70)
print("RESULT:")
print("=" * 70)
print(result.stdout)

count_result = subprocess.run([
    "psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-t", "-c",
    "SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true;"
], capture_output=True, text=True)

session_count = int(count_result.stdout.strip())

print("=" * 70)
if session_count == 4:
    print("🎉 SUCCESS! Admin patch regeneration works!")
    print("   - Changed number_of_rounds to 4")
    print("   - Reverted status (deleted 2 old sessions)")
    print("   - Regenerated 4 new sessions")
else:
    print(f"❌ FAILURE! Expected 4 sessions, got {session_count}")
print("=" * 70)
