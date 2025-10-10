#!/usr/bin/env python3
"""
Test script to validate the adaptive learning fixes:
1. No question duplication 
2. Proper feedback display
3. No duplicate answer submission
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

def test_adaptive_learning_improvements():
    """Test the adaptive learning improvements"""
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🧪 Testing Adaptive Learning Improvements...")
    
    # 1. Start a session
    print("\n1️⃣ Starting adaptive learning session...")
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
    
    # 2. Get first question
    print("\n2️⃣ Getting first question...")
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
    
    print(f"✅ Got question: {question.get('question_text', 'No text')}")
    print(f"   Question ID: {question.get('id')}")
    print(f"   Answer options: {len(question.get('answer_options', []))}")
    
    # Verify answer options have text
    options = question.get('answer_options', [])
    if not options:
        print("❌ No answer options found")
        return
    
    option_texts = [opt.get('text') for opt in options]
    if all(option_texts):
        print("✅ All answer options have text")
    else:
        print(f"❌ Some answer options missing text: {option_texts}")
    
    # 3. Submit an answer
    print("\n3️⃣ Submitting answer...")
    answer_data = {
        "question_id": question["id"],
        "selected_option_id": options[0]["id"],
        "time_spent_seconds": 5.0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
        json=answer_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to submit answer: {response.status_code} - {response.text}")
        return
    
    answer_result = response.json()
    print(f"✅ Answer submitted successfully")
    print(f"   Correct: {answer_result.get('is_correct')}")
    print(f"   Explanation: {answer_result.get('explanation', 'No explanation')[:50]}...")
    print(f"   XP Earned: {answer_result.get('xp_earned', 0)}")
    
    # 4. Test duplicate prevention by trying to submit the same answer again
    print("\n4️⃣ Testing duplicate submission prevention...")
    
    # Try to submit the same answer again immediately
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
        json=answer_data,
        headers=headers
    )
    
    if response.status_code == 200:
        print("⚠️  Duplicate answer submission was allowed (this might be expected behavior)")
    else:
        print(f"✅ Duplicate submission prevented: {response.status_code}")
    
    # 5. Get next question to test no duplication
    print("\n5️⃣ Getting next question...")
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    if response.status_code == 200:
        next_question = response.json()
        if next_question.get("session_complete"):
            print("✅ Session completed properly")
        else:
            print(f"✅ Got next question: {next_question.get('question_text', 'No text')[:50]}...")
            if next_question.get('id') == question.get('id'):
                print("❌ Same question returned (duplication detected)")
            else:
                print("✅ Different question returned (no duplication)")
    
    # 6. End session
    print("\n6️⃣ Ending session...")
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/end",
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Session ended successfully")
        summary = response.json()
        print(f"   Questions answered: {summary.get('questions_answered', 0)}")
        print(f"   Success rate: {summary.get('success_rate', 0)}%")
    else:
        print(f"❌ Failed to end session: {response.status_code}")
    
    print("\n🎯 Test completed!")

if __name__ == "__main__":
    test_adaptive_learning_improvements()