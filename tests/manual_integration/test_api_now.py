import requests

API_BASE = "http://localhost:8000"

print("=" * 70)
print("API CREDIT_COST TEST - Session 209")
print("=" * 70)

# Login
print("\n1. Login...")
login_resp = requests.post(
    f"{API_BASE}/api/v1/auth/login",
    json={"email": "grandmaster@lfa.com", "password": "grandmaster2024"}
)

if login_resp.status_code == 200:
    token = login_resp.json()['access_token']
    print(f"   ✅ Logged in successfully\n")
    
    # Get session 209
    print("2. GET /api/v1/sessions/209")
    session_resp = requests.get(
        f"{API_BASE}/api/v1/sessions/209",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if session_resp.status_code == 200:
        session = session_resp.json()
        print(f"   ✅ Response:")
        print(f"      ID: {session.get('id')}")
        print(f"      Title: {session.get('title')}")
        print(f"      💳 Credit Cost: {session.get('credit_cost')} ⭐⭐⭐")
        print(f"      Capacity: {session.get('capacity')}")
        
        # Compare with database
        print("\n3. Database verification:")
        import subprocess
        result = subprocess.run(
            ["psql", "-U", "postgres", "-h", "localhost", "-d", "lfa_intern_system", 
             "-t", "-c", f"SELECT credit_cost FROM sessions WHERE id = 209;"],
            capture_output=True, text=True
        )
        db_credit = result.stdout.strip()
        print(f"   Database credit_cost: {db_credit}")
        
        print("\n" + "=" * 70)
        if str(session.get('credit_cost')) == db_credit:
            print("✅✅✅ API MATCHES DATABASE! ✅✅✅")
        else:
            print(f"❌❌❌ MISMATCH! API={session.get('credit_cost')}, DB={db_credit} ❌❌❌")
        print("=" * 70)
    else:
        print(f"   ❌ Failed: {session_resp.status_code}")
        print(f"   {session_resp.text}")
else:
    print(f"   ❌ Login failed: {login_resp.status_code}")
    print(f"   {login_resp.text}")
