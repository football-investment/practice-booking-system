"""
Test instructor session edit functionality
"""
import requests

API_BASE_URL = "http://localhost:8000"

print("="*60)
print("INSTRUCTOR SESSION EDIT TEST")
print("="*60)

# Step 1: Login as Grand Master instructor
print("\n1. Logging in as Grand Master...")
login_response = requests.post(
    f"{API_BASE_URL}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster123"}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.json())
    exit(1)

token = login_response.json()['access_token']
print(f"✅ Logged in successfully")
print(f"   Token: {token[:50]}...")

# Step 2: Get semesters where instructor is master
print("\n2. Fetching semesters...")
semesters_response = requests.get(
    f"{API_BASE_URL}/api/v1/semesters",
    headers={"Authorization": f"Bearer {token}"}
)

if semesters_response.status_code != 200:
    print(f"❌ Failed to fetch semesters: {semesters_response.status_code}")
    exit(1)

all_semesters = semesters_response.json()
print(f"✅ Fetched {len(all_semesters)} total semesters")

# Filter for master instructor semesters
my_semesters = [s for s in all_semesters if s.get('master_instructor_id') == 3]
print(f"✅ {len(my_semesters)} semesters where you are master instructor")

if not my_semesters:
    print("❌ No semesters found where you are master instructor")
    exit(1)

selected_semester = my_semesters[0]
print(f"\n   Selected: {selected_semester['name']} (ID: {selected_semester['id']})")

# Step 3: Get sessions for this semester
print("\n3. Fetching sessions for semester...")
sessions_response = requests.get(
    f"{API_BASE_URL}/api/v1/sessions",
    headers={"Authorization": f"Bearer {token}"},
    params={"semester_id": selected_semester['id']}
)

if sessions_response.status_code != 200:
    print(f"❌ Failed to fetch sessions: {sessions_response.status_code}")
    exit(1)

sessions_data = sessions_response.json()
if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
    sessions = sessions_data['sessions']
else:
    sessions = sessions_data

print(f"✅ Found {len(sessions)} sessions")

if not sessions:
    print("❌ No sessions found")
    exit(1)

# Show current state
session = sessions[0]
print(f"\n   Session: {session['title']} (ID: {session['id']})")
print(f"   Current credit_cost: {session.get('credit_cost', 'NOT FOUND')}")
print(f"   Current capacity: {session.get('capacity', 'NOT FOUND')}")

# Step 4: Try to PATCH the session
print("\n4. Testing PATCH /api/v1/sessions/{id}...")
new_credit_cost = 7
new_capacity = 12

update_payload = {
    "credit_cost": new_credit_cost,
    "capacity": new_capacity
}

print(f"   Sending: credit_cost={new_credit_cost}, capacity={new_capacity}")

patch_response = requests.patch(
    f"{API_BASE_URL}/api/v1/sessions/{session['id']}",
    json=update_payload,
    headers={"Authorization": f"Bearer {token}"}
)

print(f"\n   Response status: {patch_response.status_code}")

if patch_response.status_code == 200:
    print("✅ PATCH successful")
    updated_session = patch_response.json()
    print(f"   Updated credit_cost: {updated_session.get('credit_cost')}")
    print(f"   Updated capacity: {updated_session.get('capacity')}")

    # Verify
    if updated_session.get('credit_cost') == new_credit_cost:
        print("   ✅ credit_cost updated correctly!")
    else:
        print(f"   ❌ credit_cost NOT updated! Still {updated_session.get('credit_cost')}")

    if updated_session.get('capacity') == new_capacity:
        print("   ✅ capacity updated correctly!")
    else:
        print(f"   ❌ capacity NOT updated! Still {updated_session.get('capacity')}")
else:
    print(f"❌ PATCH failed!")
    print(f"   Response: {patch_response.json()}")

# Step 5: Re-fetch to verify database update
print("\n5. Re-fetching session to verify database...")
refetch_response = requests.get(
    f"{API_BASE_URL}/api/v1/sessions/{session['id']}",
    headers={"Authorization": f"Bearer {token}"}
)

if refetch_response.status_code == 200:
    refetched = refetch_response.json()
    print(f"✅ Re-fetched session")
    print(f"   credit_cost in DB: {refetched.get('credit_cost')}")
    print(f"   capacity in DB: {refetched.get('capacity')}")

    if refetched.get('credit_cost') == new_credit_cost:
        print("   ✅ DATABASE UPDATED with correct credit_cost!")
    else:
        print(f"   ❌ DATABASE NOT UPDATED! credit_cost is {refetched.get('credit_cost')}")
else:
    print(f"❌ Re-fetch failed: {refetch_response.status_code}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
