#!/usr/bin/env python3
"""
Quick seed script for tournament testing.
Creates minimal test data in test database.
"""
import sys
import os
from datetime import datetime, date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session as DBSession
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.location import Location
from app.models.campus import Campus
from app.core.security import get_password_hash

def main():
    """Create minimal test data"""
    print("=" * 80)
    print("🌱 Seeding test database for tournament testing...")
    print("=" * 80)

    db = SessionLocal()

    try:
        # 1. Create admin user
        admin = User(
            id=1,
            name="Admin User",
            email="admin@lfa.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            date_of_birth=date(1985, 1, 1),
            parental_consent=True,
            onboarding_completed=True
        )
        db.add(admin)

        # 2. Create master instructor (Marco)
        marco = User(
            id=2,
            name="Marco Bellini",
            email="marco.bellini@lfa.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            date_of_birth=date(1980, 5, 15),
            parental_consent=True,
            onboarding_completed=True,
            specialization="LFA_COACH"
        )
        db.add(marco)

        # 3. Create head coach (Maria)
        maria = User(
            id=3,
            name="Maria García",
            email="maria.garcia@lfa.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            date_of_birth=date(1988, 3, 20),
            parental_consent=True,
            onboarding_completed=True,
            specialization="LFA_COACH"
        )
        db.add(maria)

        # 4. Create test students (8 students for groups)
        student_base_id = 100
        for i in range(8):
            student = User(
                id=student_base_id + i,
                name=f"Test Student {i+1}",
                email=f"student{i+1}@test.com",
                password_hash=get_password_hash("student123"),
                role=UserRole.STUDENT,
                is_active=True,
                date_of_birth=date(2010, 1, 1) + timedelta(days=i*30),  # Different ages
                parental_consent=True,
                onboarding_completed=True
            )
            db.add(student)

        # 5. Create location
        location = Location(
            id=1,
            name="Budapest",
            city="Budapest",
            country="Hungary",
            is_active=True
        )
        db.add(location)

        # 6. Create campus
        campus = Campus(
            id=1,
            name="Main Campus",
            location_id=1,
            address="123 Football Street",
            is_active=True
        )
        db.add(campus)

        db.commit()

        print("✅ Created users:")
        print(f"   - Admin: admin@lfa.com / admin123")
        print(f"   - Master Instructor: marco.bellini@lfa.com / admin123")
        print(f"   - Head Coach: maria.garcia@lfa.com / admin123")
        print(f"   - 8 test students: student1@test.com - student8@test.com / student123")
        print("✅ Created Location: Budapest")
        print("✅ Created Campus: Main Campus")
        print("=" * 80)
        print("✅ Test database seeding complete!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
