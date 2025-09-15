#!/usr/bin/env python3
"""
Add missing test users for feedback testing
"""

import sys
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def add_test_users():
    """Add missing test users"""
    
    print("🚀 ADDING TEST USERS")
    print("=" * 50)
    
    try:
        db = SessionLocal()
        
        # Test users to add (skip admin since it exists)
        test_users = [
            {"email": "alex@example.com", "password": "password123", "name": "Alex Smith", "role": UserRole.STUDENT},
            {"email": "maria@example.com", "password": "password123", "name": "Maria Garcia", "role": UserRole.STUDENT},
            {"email": "instructor@example.com", "password": "instructor123", "name": "Dr. Johnson", "role": UserRole.INSTRUCTOR}
        ]
        
        added_count = 0
        for user_data in test_users:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                print(f"ℹ️ User {user_data['email']} already exists, skipping")
                continue
            
            # Create user
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                name=user_data["name"],
                role=user_data["role"],
                is_active=True
            )
            db.add(user)
            added_count += 1
            print(f"✅ Added user: {user_data['email']} ({user_data['role'].value})")
        
        db.commit()
        db.close()
        
        print(f"\n🎉 TEST USERS SETUP COMPLETED!")
        print(f"✅ Added {added_count} new users")
        print("🎯 You can now test authentication with:")
        print("- admin@yourcompany.com / SecureAdminPass2024!@#$")
        print("- alex@example.com / password123")
        print("- instructor@example.com / instructor123")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add test users: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_test_users()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")