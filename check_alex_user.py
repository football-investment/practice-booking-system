#!/usr/bin/env python3

import sys
import os
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User

def check_alex_user():
    db = SessionLocal()
    
    try:
        # Find Alex Johnson user
        user = db.query(User).filter(User.email == "alex.johnson@student.devstudio.com").first()
        if user:
            print(f"✅ Alex Johnson user exists:")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Name: {user.name}")
            print(f"   Full Name: {user.full_name}")
            print(f"   Role: {user.role}")
            print(f"   Active: {user.is_active}")
            print(f"   Password hash: {user.password_hash[:50]}...")
        else:
            print("❌ Alex Johnson user NOT FOUND!")
            
            # Show all users with alex in email
            alex_users = db.query(User).filter(User.email.contains("alex")).all()
            print(f"\nUsers with 'alex' in email:")
            for u in alex_users:
                print(f"   - {u.email} ({u.name}) - Active: {u.is_active}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_alex_user()