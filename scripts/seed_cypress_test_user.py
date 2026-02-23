#!/usr/bin/env python3
"""Seed test user for Cypress E2E tests"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.database import SessionLocal

def seed_cypress_test_user():
    """Seed player account for Cypress enrollment_409_live.cy.js test"""
    db = SessionLocal()
    
    # Expected credentials from cypress.config.js
    player_email = 'rdias@manchestercity.com'
    player_password = 'TestPlayer2026'
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == player_email).first()
        
        if existing_user:
            print(f"✓ Player {player_email} already exists (ID={existing_user.id})")
            print(f"  Role: {existing_user.role}")
            print(f"  Active: {existing_user.is_active}")
            
            # Update password if needed
            existing_user.password_hash = get_password_hash(player_password)
            db.commit()
            print(f"✓ Password updated for {player_email}")
            return existing_user.id
        
        # Create new player (STUDENT role)
        player = User(
            name='Ruben Dias',
            email=player_email,
            password_hash=get_password_hash(player_password),
            first_name='Ruben',
            last_name='Dias',
            role=UserRole.STUDENT,
            is_active=True
        )
        
        db.add(player)
        db.commit()
        db.refresh(player)
        
        print(f"✓ Created player {player_email} (ID={player.id})")
        print(f"  Password: {player_password}")
        print(f"  Role: {player.role}")
        
        return player.id
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        return None
    finally:
        db.close()

if __name__ == '__main__':
    print("Seeding Cypress test user...")
    user_id = seed_cypress_test_user()
    
    if user_id:
        print(f"\n✓ Success! User ID: {user_id}")
        print(f"\nNext: Run Cypress tests")
        print(f"  cd tests_cypress")
        print(f"  npm run cy:run:critical")
        sys.exit(0)
    else:
        print(f"\n✗ Failed to seed test user")
        sys.exit(1)
