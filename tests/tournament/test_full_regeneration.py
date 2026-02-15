#!/usr/bin/env python3
"""
Test full regeneration cycle:
1. Tournament has 2 sessions
2. Admin changes number_of_rounds to 4
3. Start Tournament → should auto-delete 2 old sessions and create 4 new ones
"""
import requests
import json
import subprocess

API_BASE = "http://localhost:8000"

# Login
login = requests.post(f"{API_BASE}/api/v1/auth/login", json={"email":"admin@lfa.com","password":"admin123"})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=" * 70)
print("FULL REGENERATION TEST")
print("=" * 70)

# Step 1: Set number_of_rounds to 4 (while tournament is IN_PROGRESS with 2 sessions)
print("\nStep 1: Change number_of_rounds from 2 to 4...")
subprocess.run([
    "psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-c",
    "UPDATE semesters SET number_of_rounds = 4 WHERE id = 18;"
], capture_output=True)

# Check current state
result = subprocess.run([
    "psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-t", "-c",
    "SELECT number_of_rounds, (SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true) FROM semesters WHERE id = 18;"
], capture_output=True, text=True)
rounds, count = result.stdout.strip().split('|')
print(f"   DB: number_of_rounds = {rounds.strip()}, sessions = {count.strip()}")

# Step 2: Revert to ENROLLMENT_CLOSED → should auto-delete sessions
print("\nStep 2: Revert to ENROLLMENT_CLOSED (should auto-delete 2 sessions)...")
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18/status",
    headers=headers,
    json={"new_status": "ENROLLMENT_CLOSED", "reason": "Testing auto-delete"}
)
print(f"   Status: {response.status_code}")

# Check sessions deleted
result = subprocess.run([
    "psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", "-t", "-c",
    "SELECT COUNT(*) FROM sessions WHERE semester_id = 18 AND auto_generated = true;"
], capture_output=True, text=True)
print(f"   Sessions after revert: {result.stdout.strip()}")

# Step 3: Start Tournament → should generate 4 sessions
print("\nStep 3: Start Tournament (should generate 4 new sessions)...")
response = requests.patch(
    f"{API_BASE}/api/v1/tournaments/18/status",
    headers=headers,
    json={"new_status": "IN_PROGRESS", "reason": "Testing auto-generation with 4 rounds"}
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
    print("🎉 SUCCESS! Full regeneration cycle works perfectly!")
    print("   - Old 2 sessions deleted")
    print("   - New 4 sessions generated")
else:
    print(f"❌ FAILURE! Expected 4 sessions, got {session_count}")
print("=" * 70)
