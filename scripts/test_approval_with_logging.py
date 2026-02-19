#!/usr/bin/env python3
"""
Test tournament application approval with detailed logging
"""
import requests
import json

API_BASE_URL = "http://localhost:8000"

def main():
    print("=" * 80)
    print("Testing Tournament Application Approval with Detailed Logging")
    print("=" * 80)

    # Step 1: Login as admin
    print("\n[1] Logging in as admin...")
    login_response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={
            "email": "admin@lfa.com",
            "password": "admin123"
        }
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return

    token = login_response.json()["access_token"]
    print(f"✅ Logged in successfully")

    # Step 2: Approve the application
    tournament_id = 122
    application_id = 29

    print(f"\n[2] Approving application {application_id} for tournament {tournament_id}...")
    print("    Watch the backend logs for detailed debug output!")
    print()

    approval_response = requests.post(
        f"{API_BASE_URL}/api/v1/tournaments/{tournament_id}/instructor-applications/{application_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "response_message": "Congratulations! Your application has been approved."
        }
    )

    print(f"\n[3] Response Status: {approval_response.status_code}")
    print(f"[4] Response Body:")
    print(json.dumps(approval_response.json(), indent=2))

    if approval_response.status_code == 200:
        print("\n✅ SUCCESS: Application approved!")
    else:
        print(f"\n❌ FAILED: Status {approval_response.status_code}")
        if "error" in approval_response.json():
            error = approval_response.json()["error"]
            print(f"Error: {error}")

if __name__ == "__main__":
    main()
