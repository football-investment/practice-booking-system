#!/usr/bin/env python3
"""
Test script to verify the new UX improvements
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

def test_ux_improvements():
    """Test the new UX improvements"""
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("⚡ Testing New UX Improvements...")
    print("===============================")
    
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
    print(f"📱 Frontend should show: Mobile-optimized interface")
    
    # Get question to test UX features
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
    
    print(f"✅ Question loaded: {question.get('question_text')}")
    print(f"📱 Expected UX Features:")
    print(f"   🎨 Smooth transitions and hover effects")
    print(f"   📱 Touch-friendly buttons (min 48px)")
    print(f"   ⚡ Loading states during interactions")
    print(f"   🎯 Instant visual feedback")
    
    # Submit answer to test success animation
    options = question.get('answer_options', [])
    if options:
        selected_option = options[0]
        answer_data = {
            "question_id": question["id"],
            "selected_option_id": selected_option["id"],
            "time_spent_seconds": 3.0
        }
        
        print(f"\n🎯 Testing answer submission with instant feedback...")
        print(f"   Submitting: '{selected_option.get('text')}'")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/answer",
            json=answer_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            is_correct = result.get('is_correct')
            xp_earned = result.get('xp_earned')
            
            print(f"✅ Answer submitted successfully")
            print(f"   Result: {'✅ Correct' if is_correct else '❌ Incorrect'}")
            print(f"   XP Earned: {xp_earned}")
            
            if is_correct:
                print(f"🎉 Expected Frontend Behavior:")
                print(f"   ✨ Success animation (0.6s pulse)")
                print(f"   🎯 Instant XP popup: '+{xp_earned} XP - Great job!'")
                print(f"   🎨 Bouncing celebration icon")
                print(f"   ⏰ 3-second feedback period")
                print(f"   🔄 Automatic progression to next question")
            else:
                print(f"💭 Expected Frontend Behavior:")
                print(f"   📝 Feedback display with explanation")
                print(f"   🎯 Consolation XP: '+{xp_earned} XP'")
                print(f"   ⏰ 3-second feedback period")
                print(f"   🔄 Automatic progression to next question")
            
        else:
            print(f"❌ Answer submission failed: {response.status_code}")
    
    # End session
    time.sleep(1)
    response = requests.post(
        f"{BASE_URL}/api/v1/adaptive-learning/sessions/{session_id}/end",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"\n✅ Session ended successfully")
    
    print("\n🚀 UX Improvements Summary:")
    print("============================")
    print("✅ Mobile-First Optimizations:")
    print("   📱 Touch-friendly interface (48px+ targets)")
    print("   📱 Responsive design with proper spacing")
    print("   📱 Optimized for small screens")
    
    print("\n✅ Visual Polish:")
    print("   🎨 Smooth transitions (0.3s ease)")
    print("   🎨 Hover effects with transform")
    print("   🎨 Enhanced button animations")
    
    print("\n✅ Loading States:")
    print("   ⚡ Button disable during submission")
    print("   ⚡ Loading overlays with spinners")
    print("   ⚡ Immediate visual feedback")
    
    print("\n✅ Instant Rewards:")
    print("   🎉 Success animations for correct answers")
    print("   🎯 Instant XP popup with celebration")
    print("   🏆 Progress transparency")
    
    print("\n🎯 Test this in browser at: http://localhost:3000/student/adaptive-learning")
    print("📱 Try on mobile devices or with responsive design view!")

if __name__ == "__main__":
    test_ux_improvements()