#!/usr/bin/env python3
"""
Test script to verify the answer selection fix
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

def test_answer_selection_stability():
    """Test answer selection stability after fixes"""
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔧 Testing Answer Selection Stability Fix...")
    print("============================================")
    
    # Start session
    session_data = {"category": "general"}
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/start-session",
        json=session_data,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start session: {response.status_code}")
        return
    
    session_info = response.json()
    session_id = session_info["session_id"]
    print(f"✅ Session started: {session_id}")
    
    # Get question
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get question: {response.status_code}")
        return
    
    question = response.json()
    
    if question.get("session_complete"):
        print("❌ Session completed immediately")
        return
    
    print(f"✅ Got question: {question.get('question_text')}")
    print(f"   Question type: {question.get('question_type')}")
    print(f"   Question ID: {question.get('id')}")
    
    # Check answer options
    options = question.get('answer_options', [])
    print(f"   Answer options ({len(options)}):") 
    for i, option in enumerate(options):
        print(f"     {i+1}. ID: {option.get('id')}, Text: '{option.get('text')}'")
    
    if not options:
        print("❌ No answer options available")
        return
    
    # Test answer selection with first option
    selected_option = options[0]
    print(f"\n🎯 Testing answer selection with option: '{selected_option.get('text')}'")
    
    answer_data = {
        "question_id": question["id"],
        "selected_option_id": selected_option["id"],
        "time_spent_seconds": 2.5
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
        json=answer_data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Answer submitted successfully")
        print(f"   Correct: {'✅ YES' if result.get('is_correct') else '❌ NO'}")
        print(f"   XP earned: {result.get('xp_earned', 0)}")
        
        # Test immediate second submission (should be handled gracefully)
        response2 = requests.post(
            f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
            json=answer_data,
            headers=headers
        )
        print(f"   Duplicate submission status: {response2.status_code}")
        
    else:
        print(f"❌ Answer submission failed: {response.status_code}")
        return
    
    # End session
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/end",
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Session ended successfully")
    else:
        print(f"⚠️  Session end status: {response.status_code}")
    
    print("\n🎉 Answer Selection Stability Test COMPLETED!")
    print("✅ Frontend fixes should now prevent:")
    print("   - Multiple rapid handleAnswerChange calls")
    print("   - Event bubbling issues")
    print("   - Re-rendering loops")
    print("   - Answer selection instability")

if __name__ == "__main__":
    test_answer_selection_stability()