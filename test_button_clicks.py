#!/usr/bin/env python3
"""
Test script to investigate the button clicking issue
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def login():
    """Login to get authentication token"""
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

def test_button_interaction():
    """Test the button interaction functionality"""
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔘 Testing Button Click Investigation...")
    
    # 1. Start session
    print("\n1️⃣ Starting session...")
    session_data = {"category": "general"}
    
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
    print(f"✅ Session started: {session_id}")
    
    # 2. Get question
    print("\n2️⃣ Getting question...")
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get question: {response.status_code} - {response.text}")
        return
    
    question = response.json()
    
    if question.get("session_complete"):
        print("❌ Session completed immediately")
        return
    
    print(f"✅ Got question: {question.get('question_text')}")
    print(f"   Question ID: {question.get('id')}")
    
    # Check answer options format
    options = question.get('answer_options', [])
    print(f"   Answer options ({len(options)}):")
    for i, option in enumerate(options):
        print(f"     {i+1}. ID: {option.get('id')}, Text: '{option.get('text', 'NO TEXT')}'")
    
    if not options:
        print("❌ No answer options - this could cause UI issues")
        return
    
    # 3. Test multiple rapid answer submissions (simulate UI problem)
    print("\n3️⃣ Testing answer submission...")
    
    answer_data = {
        "question_id": question["id"],
        "selected_option_id": options[0]["id"],
        "time_spent_seconds": 2.0
    }
    
    # Submit first answer
    response1 = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
        json=answer_data,
        headers=headers
    )
    
    print(f"First submission: {response1.status_code}")
    if response1.status_code == 200:
        result = response1.json()
        print(f"  ✅ Is correct: {result.get('is_correct')}")
        print(f"  ✅ XP earned: {result.get('xp_earned')}")
    
    # Immediately try to submit another answer (simulate double-click)
    response2 = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
        json=answer_data,
        headers=headers
    )
    
    print(f"Second submission (rapid): {response2.status_code}")
    
    # Test getting next question
    print("\n4️⃣ Testing next question...")
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    print(f"Next question request: {response.status_code}")
    if response.status_code == 200:
        next_q = response.json()
        if next_q.get("session_complete"):
            print("✅ Session completed")
        else:
            print(f"✅ Got next question: {next_q.get('question_text', 'No text')[:30]}...")
    
    # End session
    print("\n5️⃣ Ending session...")
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/end",
        headers=headers
    )
    
    print(f"End session: {response.status_code}")
    
    print("\n🎯 Button interaction test completed!")

if __name__ == "__main__":
    test_button_interaction()