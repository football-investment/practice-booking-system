#!/usr/bin/env python3

import requests
import json

def debug_frontend_sessions():
    try:
        # Test the exact same API call as frontend
        headers = {
            'Content-Type': 'application/json'
        }
        
        # First login (use a simple auth that works)
        print("🔐 Testing API login...")
        login_response = requests.post(
            'http://localhost:8000/api/v1/auth/login',
            json={
                'email': 'admin@yourcompany.com',
                'password': 'admin'
            },
            headers=headers
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return
        
        token = login_response.json().get('access_token')
        if not token:
            print(f"❌ No access token in response: {login_response.json()}")
            return
        
        print(f"✅ Login successful, got token")
        
        # Test getSessions API with auth
        auth_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        sessions_response = requests.get(
            'http://localhost:8000/api/v1/sessions/',
            headers=auth_headers
        )
        
        if sessions_response.status_code != 200:
            print(f"❌ Sessions API failed: {sessions_response.status_code}")
            print(f"Response: {sessions_response.text}")
            return
        
        sessions_data = sessions_response.json()
        sessions = sessions_data.get('sessions', [])
        
        print(f"✅ Sessions API response:")
        print(f"   Total: {sessions_data.get('total', 0)}")
        print(f"   Returned: {len(sessions)}")
        
        # Check first 10 sessions and look for 223
        print(f"\n📅 First 10 sessions:")
        session_223_found = False
        session_223_data = None
        
        for i, session in enumerate(sessions[:10]):
            session_id = session.get('id')
            title = session.get('title', 'No title')[:50]
            date_start = session.get('date_start')
            
            if session_id == 223:
                session_223_found = True
                session_223_data = session
                print(f"   {i+1}. 🎯 ID: {session_id}, Start: {date_start}, Title: {title} <<<< SESSION 223 FOUND!")
            else:
                print(f"   {i+1}. ID: {session_id}, Start: {date_start}, Title: {title}")
        
        if not session_223_found:
            # Check all sessions for 223
            for session in sessions:
                if session.get('id') == 223:
                    session_223_found = True
                    session_223_data = session
                    break
        
        if session_223_found:
            print(f"\n✅ Session 223 IS in API response!")
            print(f"   Full data: {json.dumps(session_223_data, indent=2)}")
        else:
            print(f"\n❌ Session 223 NOT in API response")
            print(f"   All session IDs: {[s.get('id') for s in sessions[:20]]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_frontend_sessions()