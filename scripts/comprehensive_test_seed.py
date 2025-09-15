#!/usr/bin/env python3
"""
🌱 COMPREHENSIVE TEST DATA SEED
Specific test scenarios és edge cases számára
"""

import sys
import os
from datetime import datetime, timedelta, timezone
import random
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import *
from app.core.security import get_password_hash

class ComprehensiveTestSeed:
    def __init__(self):
        self.db = SessionLocal()
        
    def seed_quiz_system(self):
        """Create quiz test data - simplified for MVP testing"""
        print("📝 Skipping quiz system (complex model structure - not needed for fresh testing)")
        print("✅ Quiz system seeding skipped!")
        
    def seed_gamification_system(self):
        """Create achievement and gamification test data - simplified"""
        print("🏆 Skipping gamification system (not needed for fresh core testing)")
        print("✅ Gamification system seeding skipped!")
        
    def seed_messaging_system(self):
        """Create message test data"""
        print("💬 Seeding messaging system...")
        
        admin = self.db.query(User).filter(User.role == UserRole.ADMIN).first()
        students = self.db.query(User).filter(User.role == UserRole.STUDENT).all()
        instructors = self.db.query(User).filter(User.role == UserRole.INSTRUCTOR).all()
        
        # System welcome messages for newcomers
        for student in students[:3]:  # First 3 newcomers
            welcome_msg = Message(
                sender_id=admin.id,
                recipient_id=student.id,
                subject="Welcome to the System!",
                content=f"Hello {student.name}! Welcome to our practice booking system. Complete your onboarding to get started.",
                is_system_message=True,
                is_read=False
            )
            self.db.add(welcome_msg)
            
        # Instructor announcement
        for student in students:
            announcement = Message(
                sender_id=instructors[0].id,
                recipient_id=student.id,
                subject="Fall 2025 Schedule Update",
                content="New sessions have been added for this week. Check the schedule and book your spots early!",
                is_system_message=False,
                is_read=False
            )
            self.db.add(announcement)
            
        self.db.commit()
        print("✅ Messaging system seeded!")
        
    def seed_edge_case_scenarios(self):
        """Create specific test scenarios for edge cases"""
        print("⚠️  Seeding edge case scenarios...")
        
        # Get test data
        sessions = self.db.query(Session).limit(5).all()
        students = self.db.query(User).filter(User.role == UserRole.STUDENT).all()
        
        if sessions and students:
            # Full capacity session + waitlist
            full_session = sessions[0]
            full_session.capacity = 3  # Small capacity for testing
            
            # Book to capacity
            for i in range(3):
                booking = Booking(
                    user_id=students[i].id,
                    session_id=full_session.id,
                    status=BookingStatus.CONFIRMED
                )
                self.db.add(booking)
                
            # Add waitlist entries
            for i in range(3, min(6, len(students))):
                booking = Booking(
                    user_id=students[i].id,
                    session_id=full_session.id,
                    status=BookingStatus.WAITLISTED,
                    waitlist_position=i-2
                )
                self.db.add(booking)
                
            # Session with cancellations
            if len(sessions) > 1:
                cancel_session = sessions[1]
                cancel_booking = Booking(
                    user_id=students[0].id,
                    session_id=cancel_session.id,
                    status=BookingStatus.CANCELLED,
                    cancelled_at=datetime.now() - timedelta(days=1)
                )
                self.db.add(cancel_booking)
                
        self.db.commit()
        print("✅ Edge case scenarios seeded!")
        
    def run_comprehensive_seed(self):
        """Execute core test data seeding for fresh testing"""
        print("🚀 Starting core test seeding...\n")
        
        try:
            # Skip complex systems for fresh testing
            self.seed_quiz_system() 
            self.seed_gamification_system()
            # Only seed edge cases for booking system
            self.seed_edge_case_scenarios()
            
            print("\n🎉 CORE TEST SEEDING COMPLETE!")
            print("\n🧪 TEST SCENARIOS AVAILABLE:")
            print("- Fresh newcomer onboarding flow")
            print("- Full capacity sessions + waitlist")
            print("- Cancelled bookings")
            print("- Basic session booking flow")
            print("\n✅ Ready for core functionality testing!")
            
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            self.db.rollback()
            raise
        finally:
            self.db.close()

if __name__ == "__main__":
    seed = ComprehensiveTestSeed()
    seed.run_comprehensive_seed()