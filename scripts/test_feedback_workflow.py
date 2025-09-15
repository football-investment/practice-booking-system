#!/usr/bin/env python3
"""
Complete feedback workflow testing
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def run_complete_feedback_test():
    """Run complete feedback workflow test"""
    
    print("🎯 COMPLETE FEEDBACK WORKFLOW TEST")
    print("=" * 50)
    
    # Step 1: Login as Alex
    print("1. Alex Login...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "alex@example.com", "password": "password123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Alex login failed: {login_response.text}")
        return False
    
    alex_token = login_response.json()["access_token"]
    print("✅ Alex logged in successfully")
    
    # Step 2: Get Alex bookings
    print("2. Getting Alex bookings...")
    bookings_response = requests.get(
        f"{BASE_URL}/bookings/me",
        headers={"Authorization": f"Bearer {alex_token}"}
    )
    
    if bookings_response.status_code != 200:
        print(f"❌ Failed to get bookings: {bookings_response.text}")
        return False
    
    bookings_data = bookings_response.json()
    bookings = bookings_data.get("bookings", [])
    print(f"✅ Retrieved {len(bookings)} bookings")
    
    # Step 3: Analyze awaiting feedback
    current_date = datetime.now()
    attended_past_bookings = []
    
    print("\n📊 Booking Analysis:")
    for booking in bookings:
        session = booking.get("session", {})
        session_title = session.get("title", "Unknown")
        session_date_str = session.get("date_start", "")
        attended = booking.get("attended", False)
        
        print(f"   - {session_title}")
        print(f"     Date: {session_date_str}")
        print(f"     Attended: {attended}")
        
        if session_date_str:
            try:
                # Parse ISO format date
                session_date = datetime.fromisoformat(session_date_str.replace("Z", "+00:00"))
                is_past = session_date < current_date
                print(f"     Is Past: {is_past}")
                
                if attended and is_past:
                    attended_past_bookings.append(booking)
                    print(f"     ✅ Eligible for feedback")
                else:
                    print(f"     ➖ Not eligible for feedback")
            except Exception as e:
                print(f"     ❌ Date parsing error: {e}")
        print()
    
    print(f"✅ Found {len(attended_past_bookings)} attended past sessions")
    
    # Step 4: Get existing feedback
    print("3. Getting existing feedback...")
    feedback_response = requests.get(
        f"{BASE_URL}/feedback/me",
        headers={"Authorization": f"Bearer {alex_token}"}
    )
    
    if feedback_response.status_code != 200:
        print(f"❌ Failed to get feedback: {feedback_response.text}")
        return False
    
    feedback_data = feedback_response.json()
    existing_feedback = feedback_data.get("feedbacks", [])
    print(f"✅ Retrieved {len(existing_feedback)} existing feedback entries")
    
    # Print existing feedback details
    print("\n📝 Existing Feedback:")
    for feedback in existing_feedback:
        session_id = feedback.get("session_id")
        rating = feedback.get("rating")
        comment = feedback.get("comment", "")[:50] + "..."
        print(f"   - Session ID {session_id}: Rating {rating}, Comment: {comment}")
    
    # Step 5: Calculate awaiting feedback
    awaiting_feedback_bookings = []
    for booking in attended_past_bookings:
        session_id = booking["session"]["id"]
        has_feedback = any(f.get("session_id") == session_id for f in existing_feedback)
        if not has_feedback:
            awaiting_feedback_bookings.append(booking)
    
    print(f"\n✅ Sessions awaiting feedback: {len(awaiting_feedback_bookings)}")
    
    # Print awaiting feedback details
    if awaiting_feedback_bookings:
        print("\n🔄 Sessions Awaiting Feedback:")
        for booking in awaiting_feedback_bookings:
            session_title = booking["session"]["title"]
            print(f"   - {session_title}")
    
    # Step 6: Test feedback submission if sessions are awaiting
    if awaiting_feedback_bookings:
        test_booking = awaiting_feedback_bookings[0]
        session_title = test_booking["session"]["title"]
        print(f"\n4. Testing feedback submission for: {session_title}")
        
        feedback_data = {
            "session_id": test_booking["session"]["id"],
            "rating": 4.0,
            "comment": "Automated test feedback submission - this is a test",
            "is_anonymous": False
        }
        
        feedback_response = requests.post(
            f"{BASE_URL}/feedback/",
            json=feedback_data,
            headers={"Authorization": f"Bearer {alex_token}"}
        )
        
        if feedback_response.status_code in [200, 201]:
            print("✅ Feedback submitted successfully")
            
            # Verify feedback appears in list
            time.sleep(1)
            updated_feedback_response = requests.get(
                f"{BASE_URL}/feedback/me",
                headers={"Authorization": f"Bearer {alex_token}"}
            )
            
            if updated_feedback_response.status_code == 200:
                updated_feedback = updated_feedback_response.json().get("feedbacks", [])
                print(f"✅ Updated feedback count: {len(updated_feedback)}")
                
                # Re-calculate awaiting feedback after submission
                new_awaiting_count = len(awaiting_feedback_bookings) - 1
                print(f"✅ Expected new awaiting feedback count: {new_awaiting_count}")
            
        else:
            print(f"❌ Feedback submission failed: {feedback_response.text}")
            return False
    
    else:
        print("ℹ️ No sessions awaiting feedback - this might indicate a problem with test data")
    
    # Step 7: Final verification
    print("\n🎯 FINAL VERIFICATION")
    print("=" * 30)
    print(f"Total bookings: {len(bookings)}")
    print(f"Attended past sessions: {len(attended_past_bookings)}")
    print(f"Existing feedback: {len(existing_feedback)}")
    print(f"Sessions awaiting feedback: {len(awaiting_feedback_bookings)}")
    
    # Success criteria
    success_criteria = [
        len(bookings) >= 4,  # Alex should have 4 bookings
        len(attended_past_bookings) >= 2,  # At least 2 past attended sessions
        len(awaiting_feedback_bookings) >= 1  # At least 1 session awaiting feedback (before submission)
    ]
    
    all_success = all(success_criteria)
    
    print(f"\n🏆 TEST RESULTS:")
    print(f"   - Has bookings: {'✅' if len(bookings) >= 4 else '❌'} ({len(bookings)} >= 4)")
    print(f"   - Has attended sessions: {'✅' if len(attended_past_bookings) >= 2 else '❌'} ({len(attended_past_bookings)} >= 2)")
    print(f"   - Has feedback workflow: {'✅' if len(awaiting_feedback_bookings) >= 1 else '❌'} ({len(awaiting_feedback_bookings)} >= 1)")
    
    return all_success

if __name__ == "__main__":
    success = run_complete_feedback_test()
    if success:
        print("\n✅ FEEDBACK WORKFLOW TEST PASSED")
        print("\n🎯 NEXT STEPS:")
        print("1. Start frontend: cd frontend && npm start")
        print("2. Login as Alex: alex@example.com / password123")
        print("3. Navigate to feedback page")
        print("4. Verify 'Sessions Awaiting Feedback' appears")
        print("5. Submit feedback and verify it moves to 'My Previous Feedback'")
    else:
        print("\n❌ FEEDBACK WORKFLOW TEST NEEDS FIXING")
        print("Check the issues above and run the test again.")