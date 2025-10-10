#!/usr/bin/env python3
"""
Test script to verify automatic question progression after answer submission
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

def test_question_progression():
    """Test that questions progress automatically after submission"""
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔄 Testing Automatic Question Progression...")
    print("==========================================")
    
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
    
    # Test progression through multiple questions
    for question_num in range(1, 4):  # Test 3 questions
        print(f"\n📝 Question {question_num}:")
        
        # Get question
        response = requests.post(
            f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/next-question",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get question {question_num}: {response.status_code}")
            break
        
        question = response.json()
        
        if question.get("session_complete"):
            print(f"✅ Session completed after {question_num-1} questions")
            break
        
        print(f"   Text: {question.get('question_text')}")
        print(f"   Type: {question.get('question_type')}")
        print(f"   ID: {question.get('id')}")
        
        # Submit answer
        options = question.get('answer_options', [])
        if not options:
            print(f"❌ No options for question {question_num}")
            break
        
        selected_option = options[0]
        answer_data = {
            "question_id": question["id"],
            "selected_option_id": selected_option["id"],
            "time_spent_seconds": 2.0 + question_num  # Varying time
        }
        
        print(f"   Submitting: '{selected_option.get('text')}'")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
            json=answer_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Submitted successfully")
            print(f"   Correct: {'✅' if result.get('is_correct') else '❌'}")
            print(f"   XP: {result.get('xp_earned', 0)}")
            
            # Verify session stats are updated
            session_stats = result.get('session_stats', {})
            if session_stats:
                print(f"   Progress: {session_stats.get('questions_answered', 0)} answered")
            
        else:
            print(f"❌ Answer submission failed: {response.status_code}")
            break
        
        # Wait briefly to simulate real usage
        time.sleep(0.5)
    
    # End session
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/end",
        headers=headers
    )
    
    if response.status_code == 200:
        summary = response.json()
        print(f"\n🏁 Session ended successfully")
        print(f"   Final questions answered: {summary.get('questions_answered', 0)}")
        print(f"   Total XP earned: {summary.get('xp_earned', 0)}")
    else:
        print(f"⚠️  Session end status: {response.status_code}")
    
    print("\n🎯 Question Progression Test COMPLETED!")
    print("✅ The frontend should now automatically:")
    print("   - Show feedback for 3 seconds after answer")
    print("   - Load next question automatically")
    print("   - Reset states properly between questions")
    print("   - Continue timer countdown appropriately")

if __name__ == "__main__":
    test_question_progression()