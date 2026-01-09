"""Debug script to test status transition"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)

token = login_response.json()["access_token"]
print(f"Got token")

# Transition status
response = requests.patch(
    f"{BASE_URL}/api/v1/tournaments/38/status",
    headers={"Authorization": f"Bearer {token}"},
    json={"new_status": "CANCELLED", "reason": "Test cancellation"}
)

print(f"Status transition response: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
