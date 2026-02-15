"""
Helper script to create tournament via API with specific preset
"""
import requests

API_BASE = "http://localhost:8000/api/v1"

# Login as admin
login_resp = requests.post(f"{API_BASE}/auth/login", json={
    "email": "admin@lfa.com",
    "password": "admin123"
})
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create tournament with Group+Knockout preset (ID=13)
tournament_data = {
    "name": "LFA Golden Path Test Tournament",
    "game_preset_id": 13,  # Group+Knockout (7 players)
    "max_players": 7,
    "start_date": "2026-02-10T10:00:00",
    "end_date": "2026-02-10T18:00:00"
}

response = requests.post(f"{API_BASE}/tournaments/create", json=tournament_data, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
