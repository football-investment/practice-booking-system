"""
Debug script to test registration with invitation code via HTTP POST
"""
import requests
from datetime import datetime

# Test data (same as Playwright test)
registration_data = {
    "email": "pwt.k1sqx1@f1stteam.hu",
    "password": "password123",
    "name": "Kristóf Kis",  # Keep for backward compatibility
    "first_name": "Kristóf",
    "last_name": "Kis",
    "nickname": "Krisz",
    "phone": "+36 20 123 4567",
    "date_of_birth": "2016-05-15",  # YYYY-MM-DD format (like Streamlit)
    "nationality": "Hungarian",
    "gender": "Male",
    "street_address": "Fő utca 12",
    "city": "Budapest",
    "postal_code": "1011",
    "country": "Hungary",
    "invitation_code": "INV-20260107-09P7U7"  # From E2E test d1
}

print("🔍 Testing registration with HTTP POST...")
print(f"Email: {registration_data['email']}")
print(f"Invitation Code: {registration_data['invitation_code']}")
print(f"Date of Birth: {registration_data['date_of_birth']}")
print()

# Make POST request
response = requests.post(
    "http://localhost:8000/api/v1/auth/register-with-invitation",
    json=registration_data
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
print()

if response.status_code != 200:
    print("❌ Registration failed!")
    try:
        error_detail = response.json()
        print(f"Error detail: {error_detail}")
    except:
        pass
else:
    print("✅ Registration successful!")
