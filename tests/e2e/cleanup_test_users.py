"""
Clean up E2E test users and reset invitation codes

This script:
1. Deletes test users with "pwt." email prefix
2. Resets invitation codes used by these users
3. Allows E2E tests to be re-run with same invitation codes
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.invitation_code import InvitationCode

# Database URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    print("🧹 Cleaning up E2E test users...")

    # Find all users with "pwt." prefix
    test_users = db.query(User).filter(User.email.like('pwt.%@%')).all()

    if not test_users:
        print("✅ No test users found to clean up")
    else:
        print(f"Found {len(test_users)} test user(s):")
        for user in test_users:
            print(f"  - {user.email} (ID: {user.id})")

        # Reset invitation codes used by these users
        for user in test_users:
            invitation_code = db.query(InvitationCode).filter(
                InvitationCode.used_by_user_id == user.id
            ).first()

            if invitation_code:
                print(f"  📝 Resetting invitation code: {invitation_code.code}")
                invitation_code.is_used = False
                invitation_code.used_by_user_id = None
                invitation_code.used_at = None

        # Delete test users
        for user in test_users:
            print(f"  🗑️  Deleting user: {user.email}")
            db.delete(user)

        # Commit changes
        db.commit()
        print("✅ Test users cleaned up successfully!")
        print(f"✅ {len(test_users)} user(s) deleted, invitation codes reset")

except Exception as e:
    print(f"❌ Error during cleanup: {e}")
    db.rollback()
    sys.exit(1)
finally:
    db.close()
