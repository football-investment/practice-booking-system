"""
Create test student account for session rules testing
"""
import sys
sys.path.insert(0, '/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system')

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import text

def create_test_student():
    db = SessionLocal()
    try:
        # Check if test student exists
        existing = db.query(User).filter(User.email == "test.student@lfa.com").first()

        if existing:
            # Update password
            existing.password_hash = get_password_hash("teststudent2024")
            db.commit()
            print(f"✅ Updated test student: test.student@lfa.com / teststudent2024")
        else:
            # Create new
            test_student = User(
                email="test.student@lfa.com",
                name="Test Student",
                password_hash=get_password_hash("teststudent2024"),
                role=UserRole.STUDENT,
                specialization=None,  # Will be set during onboarding
                onboarding_completed=True  # Skip onboarding for testing
            )
            db.add(test_student)
            db.commit()
            print(f"✅ Created test student: test.student@lfa.com / teststudent2024")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    create_test_student()
