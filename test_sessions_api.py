#!/usr/bin/env python3

import requests
import json

def test_sessions_api():
    try:
        # Login first to get token
        login_response = requests.post(
            'http://localhost:8000/api/v1/auth/login',
            json={
                'email': 'alex@example.com',
                'password': 'studentpass'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return
            
        token = login_response.json()['access_token']
        
        # Test getSessions API
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        sessions_response = requests.get(
            'http://localhost:8000/api/v1/sessions/',
            headers=headers
        )
        
        if sessions_response.status_code != 200:
            print(f"❌ Sessions API failed: {sessions_response.status_code}")
            return
        
        sessions_data = sessions_response.json()
        sessions = sessions_data.get('sessions', [])
        
        print(f"✅ Sessions API response:")
        print(f"   Total: {sessions_data.get('total', 0)}")
        print(f"   Returned: {len(sessions)}")
        
        # Check first 10 sessions
        print(f"\n📅 First 10 sessions:")
        session_223_found = False
        for i, session in enumerate(sessions[:10]):
            status = "🟢 FUTURE" if session['date_start'] > '2025-09-07T05:30:00' else "🔴 PAST"
            print(f"   {i+1}. ID: {session['id']}, Start: {session['date_start']}, Title: {session['title'][:50]}... {status}")
            
            if session['id'] == 223:
                session_223_found = True
                print(f"      🎯 >>> SESSION 223 FOUND! <<<")
        
        if not session_223_found:
            print(f"\n❌ Session 223 NOT in first 10 results")
        else:
            print(f"\n✅ Session 223 IS in first 10 results")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_sessions_api()