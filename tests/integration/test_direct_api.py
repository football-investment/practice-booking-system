import requests
import json

# Login
login_resp = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@lfa.com", "password": "admin123"}
)
token = login_resp.json()["access_token"]
print(f"Token: {token[:30]}...")

# Get semesters
headers = {"Authorization": f"Bearer {token}"}
sem_resp = requests.get("http://localhost:8000/api/v1/semesters/", headers=headers)

print(f"\nStatus: {sem_resp.status_code}")
print(f"Response: {json.dumps(sem_resp.json(), indent=2)}")
