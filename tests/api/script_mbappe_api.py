"""Test Mbappé API login"""
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "kylian.mbappe@f1rstteam.hu", "password": "password123"}
)

print("Status:", response.status_code)
if response.status_code == 200:
    data = response.json()
    token = data.get("access_token")
    user = data.get("user", {})

    print(f"User ID: {user.get('id')}")
    print(f"Email: {user.get('email')}")
    print(f"Specialization: {user.get('specialization')}")
    print(f"Onboarding completed: {user.get('onboarding_completed')}")

    licenses = user.get('licenses', [])
    print(f"\nLicenses ({len(licenses)}):")
    for lic in licenses:
        print(f"  - ID {lic.get('id')}: {lic.get('specialization_type')}")
        print(f"    Active: {lic.get('is_active')}, Onboarding: {lic.get('onboarding_completed')}")

    # Get current user with token
    print("\n--- Fetching current user ---")
    me_response = requests.get(
        "http://localhost:8000/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    if me_response.status_code == 200:
        me_data = me_response.json()
        me_licenses = me_data.get('licenses', [])
        print(f"Current user licenses: {len(me_licenses)}")
        for lic in me_licenses:
            print(f"  - ID {lic.get('id')}: {lic.get('specialization_type')} (active={lic.get('is_active')})")
else:
    print("Error:", response.text)
