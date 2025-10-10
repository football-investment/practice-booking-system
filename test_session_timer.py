#!/usr/bin/env python3
"""
Test script for the session timer functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Login to get token
def login():
    login_data = {
        "email": "george.clooney@student.devstudio.com",
        "password": "testpass123"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None

# Test session timer functionality
def test_session_timer():
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🚀 Testing Session Timer Functionality...")
    
    # 1. Start session with 10 second timer (for testing)
    print("\n1️⃣ Starting session with 10-second timer...")
    session_data = {
        "category": "general",
        "session_duration_seconds": 10
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/start-session",
        json=session_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start session: {response.status_code} - {response.text}")
        return
    
    session_info = response.json()
    session_id = session_info["session_id"]
    print(f"✅ Session started with ID: {session_id}")
    print(f"   Duration: {session_info['session_duration_seconds']} seconds")
    
    # 2. Get first question
    print("\n2️⃣ Getting first question...")
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get question: {response.status_code} - {response.text}")
        return
    
    question_data = response.json()
    
    if question_data.get("session_complete"):
        print(f"❌ Session completed immediately: {question_data}")
        return
    
    print(f"✅ Got question: {question_data.get('question_text', 'No text')[:50]}...")
    print(f"   Time remaining: {question_data.get('session_time_remaining')} seconds")
    
    # 3. Wait 5 seconds and get next question to see timer update
    print("\n3️⃣ Waiting 5 seconds...")
    time.sleep(5)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    if response.status_code == 200:
        question_data = response.json()
        if question_data.get("session_complete"):
            print(f"✅ Session completed due to timeout: {question_data}")
        else:
            print(f"⏱️ Updated time remaining: {question_data.get('session_time_remaining')} seconds")
    
    # 4. Wait for full timeout
    print("\n4️⃣ Waiting for full timeout...")
    time.sleep(6)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    if response.status_code == 200:
        question_data = response.json()
        if question_data.get("session_complete"):
            print(f"✅ Session timed out properly: {question_data}")
            if question_data.get("reason") == "Session time limit reached":
                print("🎯 Timer functionality working correctly!")
            else:
                print(f"⚠️ Unexpected completion reason: {question_data.get('reason')}")
        else:
            print("❌ Session should have timed out by now")
    else:
        print(f"❌ Error checking timeout: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   Error details: {error_data}")
        except:
            print(f"   Raw error: {response.text}")

if __name__ == "__main__":
    test_session_timer()