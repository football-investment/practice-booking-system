#!/usr/bin/env python3
"""
Seed initial data for fresh database.

Creates:
- 4 Specializations (GANCUJU_PLAYER, LFA_FOOTBALL_PLAYER, LFA_COACH, INTERNSHIP)
- 1 Admin user
- 5 Test students (different ages for testing age validation)
- 1 Active semester
- 2 Sample sessions per specialization
"""
import sys
import os
from datetime import datetime, timedelta, date
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.user_progress import Specialization
from app.models.semester import Semester
from app.models.session import Session as SessionModel, SessionMode
from app.models.specialization import SpecializationType
from app.core.security import get_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def seed_specializations(db: Session):
    """Create 4 specializations"""
    logger.info("Creating specializations...")

    specializations = [
        Specialization(id="GANCUJU_PLAYER", is_active=True),
        Specialization(id="LFA_FOOTBALL_PLAYER", is_active=True),
        Specialization(id="LFA_COACH", is_active=True),
        Specialization(id="INTERNSHIP", is_active=True),
    ]

    for spec in specializations:
        db.add(spec)

    db.commit()
    logger.info(f"✅ Created {len(specializations)} specializations")


def seed_users(db: Session):
    """Create admin and test student users"""
    logger.info("Creating users...")

    # Admin user
    admin = User(
        name="Admin User",
        email="admin@gancuju.com",
        password_hash=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
        date_of_birth=datetime(1990, 1, 1),
        parental_consent=True  # Adult
    )
    db.add(admin)

    # Test students with different ages
    today = date.today()

    students = [
        # 13 years old - too young for LFA_COACH
        User(
            name="Student 13yo",
            email="student13@test.com",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=datetime(today.year - 13, 6, 15),
            parental_consent=True
        ),
        # 14 years old WITH consent - can do LFA_COACH
        User(
            name="Student 14yo (consent)",
            email="student14@test.com",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=datetime(today.year - 14, 6, 15),
            parental_consent=True
        ),
        # 14 years old NO consent - cannot do LFA_COACH
        User(
            name="Student 14yo (no consent)",
            email="student14_noconsent@test.com",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=datetime(today.year - 14, 6, 15),
            parental_consent=False
        ),
        # 18 years old - adult, no consent needed
        User(
            name="Student 18yo (adult)",
            email="student18@test.com",
            password_hash=get_password_hash("student123"),
            role=UserRole.STUDENT,
            is_active=True,
            date_of_birth=datetime(today.year - 18, 6, 15),
            parental_consent=True
        ),
        # Instructor
        User(
            name="Instructor Test",
            email="instructor@test.com",
            password_hash=get_password_hash("instructor123"),
            role=UserRole.INSTRUCTOR,
            is_active=True,
            date_of_birth=datetime(1985, 3, 20),
            parental_consent=True
        ),
    ]

    for student in students:
        db.add(student)

    db.commit()
    logger.info(f"✅ Created {len(students) + 1} users (1 admin, 4 students, 1 instructor)")


def seed_semester(db: Session):
    """Create one active semester"""
    logger.info("Creating semester...")

    today = date.today()
    semester = Semester(
        code="2025/1",
        name="Fall 2025",
        start_date=today - timedelta(days=30),  # Started 1 month ago
        end_date=today + timedelta(days=60),     # Ends in 2 months
        is_active=True
    )
    db.add(semester)
    db.commit()
    db.refresh(semester)

    logger.info(f"✅ Created semester: {semester.name} (ID: {semester.id})")
    return semester.id


def seed_sessions(db: Session, semester_id: int):
    """Create sample sessions"""
    logger.info("Creating sample sessions...")

    instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).first()

    if not instructor:
        logger.warning("No instructor found, skipping session creation")
        return

    today = datetime.now()

    sessions = [
        # GANCUJU_PLAYER sessions
        SessionModel(
            title="GānCuju Player Training - Basics",
            description="Introduction to GānCuju player fundamentals",
            date_start=today + timedelta(days=2, hours=10),
            date_end=today + timedelta(days=2, hours=12),
            mode=SessionMode.OFFLINE,
            capacity=20,
            location="GānCuju Training Field",
            semester_id=semester_id,
            instructor_id=instructor.id,
            target_specialization=SpecializationType.GANCUJU_PLAYER,
            mixed_specialization=False
        ),
        # LFA_COACH sessions
        SessionModel(
            title="LFA Coach Training - Level 1",
            description="LFA coaching fundamentals and methodology",
            date_start=today + timedelta(days=3, hours=14),
            date_end=today + timedelta(days=3, hours=16),
            mode=SessionMode.HYBRID,
            capacity=15,
            location="LFA Training Center",
            meeting_link="https://zoom.us/j/example",
            semester_id=semester_id,
            instructor_id=instructor.id,
            target_specialization=SpecializationType.LFA_COACH,
            mixed_specialization=False
        ),
        # Mixed session
        SessionModel(
            title="Mixed Training - All Specializations",
            description="Open training for all specialization tracks",
            date_start=today + timedelta(days=5, hours=10),
            date_end=today + timedelta(days=5, hours=12),
            mode=SessionMode.OFFLINE,
            capacity=30,
            location="Main Training Ground",
            semester_id=semester_id,
            instructor_id=instructor.id,
            target_specialization=None,
            mixed_specialization=True
        ),
    ]

    for session in sessions:
        db.add(session)

    db.commit()
    logger.info(f"✅ Created {len(sessions)} sample sessions")


def main():
    """Main seeding function"""
    logger.info("=" * 80)
    logger.info("🌱 Starting database seeding...")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # Check if already seeded
        existing_specs = db.query(Specialization).count()
        if existing_specs > 0:
            logger.warning(f"⚠️ Database already has {existing_specs} specializations")
            logger.warning("Skipping seeding to avoid duplicates")
            logger.warning("Drop and recreate DB if you want fresh seed data")
            return

        seed_specializations(db)
        seed_users(db)
        semester_id = seed_semester(db)
        seed_sessions(db, semester_id)

        logger.info("=" * 80)
        logger.info("🎉 Database seeding complete!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Test accounts:")
        logger.info("  Admin:     admin@gancuju.com / admin123")
        logger.info("  Student:   student13@test.com / student123 (13yo)")
        logger.info("  Student:   student14@test.com / student123 (14yo, consent)")
        logger.info("  Student:   student14_noconsent@test.com / student123 (14yo, no consent)")
        logger.info("  Student:   student18@test.com / student123 (18yo, adult)")
        logger.info("  Instructor: instructor@test.com / instructor123")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Start backend: uvicorn app.main:app --reload")
        logger.info("  2. Visit: http://localhost:8000/docs")
        logger.info("  3. Test login with any account above")

    except Exception as e:
        logger.error(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
