"""
Quick diagnostic: Check what API returns for session 209
"""
import requests
import json

API_BASE = "http://localhost:8000"

print("=" * 60)
print("API SESSION 209 DIAGNOSTIC")
print("=" * 60)

# Try to fetch session 209 directly
print("\n1. GET /api/v1/sessions/209 (no auth)")
try:
    response = requests.get(f"{API_BASE}/api/v1/sessions/209", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   credit_cost: {data.get('credit_cost')}")
        print(f"   capacity: {data.get('capacity')}")
        print(f"   title: {data.get('title')}")
    else:
        print(f"   Error: {response.text[:200]}")
except Exception as e:
    print(f"   Exception: {str(e)}")

# Check database directly
print("\n2. Database query (direct)")
import subprocess
result = subprocess.run(
    [
        "psql",
        "-U", "postgres",
        "-h", "localhost",
        "-d", "lfa_intern_system",
        "-c", "SELECT id, title, credit_cost, capacity FROM sessions WHERE id = 209;"
    ],
    capture_output=True,
    text=True
)
print(result.stdout)

print("=" * 60)
