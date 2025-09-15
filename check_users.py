#!/usr/bin/env python3

import sys
import os
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User

def check_users():
    db = SessionLocal()
    
    try:
        # Find all users
        users = db.query(User).limit(10).all()
        print(f"First 10 users:")
        for user in users:
            print(f"   - {user.email} ({user.name}) - Role: {user.role} - Active: {user.is_active}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()