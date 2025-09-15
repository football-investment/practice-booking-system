#!/usr/bin/env python3
"""
Authentication testing script
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_authentication():
    """Test authentication for all users"""
    
    print("🔐 TESTING AUTHENTICATION")
    print("=" * 40)
    
    test_users = [
        {"email": "admin@yourcompany.com", "password": "SecureAdminPass2024!@#$", "role": "admin"},
        {"email": "alex@example.com", "password": "password123", "role": "student"},
        {"email": "instructor@example.com", "password": "instructor123", "role": "instructor"}
    ]
    
    tokens = {}
    
    for user in test_users:
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": user["email"], "password": user["password"]},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                tokens[user["role"]] = token
                print(f"✅ {user['role'].title()} login successful")
                print(f"   Email: {user['email']}")
                print(f"   Token: {token[:50]}...")
            else:
                print(f"❌ {user['role'].title()} login failed")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ {user['role'].title()} login error: {e}")
    
    return tokens

def test_alex_bookings(alex_token):
    """Test Alex's bookings"""
    
    print("\n📚 TESTING ALEX BOOKINGS")
    print("=" * 40)
    
    try:
        response = requests.get(
            f"{BASE_URL}/bookings/me",
            headers={"Authorization": f"Bearer {alex_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            bookings = data.get("bookings", [])
            print(f"✅ Alex has {len(bookings)} bookings")
            
            for booking in bookings:
                session = booking.get("session", {})
                attended_status = booking.get("attended_status", "not_marked")
                attended = booking.get("attended", False)
                print(f"   - {session.get('title', 'Unknown')} | Attended Status: {attended_status} | Attended: {attended} | Status: {booking.get('status', 'Unknown')}")
            
            return bookings
        else:
            print(f"❌ Failed to get Alex bookings: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Alex bookings error: {e}")
        return []

def test_alex_feedback(alex_token):
    """Test Alex's feedback"""
    
    print("\n💬 TESTING ALEX FEEDBACK")
    print("=" * 40)
    
    try:
        response = requests.get(
            f"{BASE_URL}/feedback/me",
            headers={"Authorization": f"Bearer {alex_token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            feedback_list = data.get("feedbacks", [])
            print(f"✅ Alex has {len(feedback_list)} feedback entries")
            
            for feedback in feedback_list:
                print(f"   - Rating: {feedback.get('rating', 'N/A')} | Comment: {feedback.get('comment', 'No comment')[:50]}...")
            
            return feedback_list
        else:
            print(f"❌ Failed to get Alex feedback: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Alex feedback error: {e}")
        return []

if __name__ == "__main__":
    tokens = test_authentication()
    
    if "student" in tokens:
        bookings = test_alex_bookings(tokens["student"])
        feedback = test_alex_feedback(tokens["student"])
        
        print("\n🎯 ANALYSIS")
        print("=" * 40)
        
        # Check for attended past sessions that need feedback
        current_time = "2025-09-06"  # Approximation for testing
        attended_past_sessions = []
        
        for booking in bookings:
            session = booking.get("session", {})
            session_date = session.get("date_start", "")
            attended = booking.get("attended", False)
            
            if attended and session_date < current_time:
                attended_past_sessions.append(booking)
        
        awaiting_feedback = len(attended_past_sessions) - len(feedback)
        
        print(f"Total bookings: {len(bookings)}")
        print(f"Attended past sessions: {len(attended_past_sessions)}")
        print(f"Existing feedback: {len(feedback)}")
        print(f"Sessions awaiting feedback: {awaiting_feedback}")
        
        if awaiting_feedback > 0:
            print("✅ Alex should see sessions awaiting feedback")
        else:
            print("❌ Alex will not see any sessions awaiting feedback")
    else:
        print("❌ Cannot test Alex - student login failed")