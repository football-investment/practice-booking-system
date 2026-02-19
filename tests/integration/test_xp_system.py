"""
Test XP System - Opció A
Test that XP is awarded correctly for attendance
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.session import Session
from app.models.booking import Booking, BookingStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.services.gamification import GamificationService

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/internship_only_test")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def test_xp_system():
    db = SessionLocal()
    gamification = GamificationService(db)

    try:
        # Get student
        student = db.query(User).filter(User.email == "junior.intern@lfa.com").first()
        if not student:
            print("❌ Student not found!")
            return

        print(f"✅ Found student: {student.email} (ID: {student.id})")

        # Get student's bookings
        bookings = db.query(Booking).filter(Booking.user_id == student.id).all()
        print(f"📚 Student has {len(bookings)} bookings")

        # Create test attendance for first 3 sessions
        test_attendances = []
        for i, booking in enumerate(bookings[:3]):
            session = db.query(Session).filter(Session.id == booking.session_id).first()

            # Check if attendance already exists
            existing = db.query(Attendance).filter(
                Attendance.user_id == student.id,
                Attendance.session_id == session.id
            ).first()

            if existing:
                print(f"⏭️  Attendance already exists for session {session.id}: {session.title}")
                test_attendances.append(existing)
                continue

            # Create new attendance
            attendance = Attendance(
                user_id=student.id,
                session_id=session.id,
                booking_id=booking.id,
                status=AttendanceStatus.present
            )
            db.add(attendance)
            db.commit()
            db.refresh(attendance)

            test_attendances.append(attendance)
            print(f"✅ Created attendance #{i+1} for session: {session.title} (Type: {session.session_type.value}, Base XP: {session.base_xp})")

        print(f"\n🎯 Testing XP Award System...")
        print("="*60)

        total_xp = 0
        for attendance in test_attendances:
            session = db.query(Session).filter(Session.id == attendance.session_id).first()
            xp = gamification.award_attendance_xp(attendance.id)
            total_xp += xp
            print(f"Session: {session.title}")
            print(f"  Type: {session.session_type.value.upper()}")
            print(f"  Base XP: {session.base_xp}")
            print(f"  XP Earned: {xp}")
            print()

        print("="*60)
        print(f"✅ Total XP Earned: {total_xp}")

        # Check user stats
        stats = gamification.calculate_user_stats(student.id)
        print(f"\n📊 User Stats:")
        print(f"  Total XP: {stats.total_xp}")
        print(f"  Level: {stats.level}")
        print(f"  Total Attended: {stats.total_attended}")
        print(f"  Attendance Rate: {stats.attendance_rate:.1f}%")

        # Calculate semester progress
        all_sessions = db.query(Session).all()
        total_semester_xp = sum(s.base_xp for s in all_sessions)
        progress_percent = (stats.total_xp / total_semester_xp * 100) if total_semester_xp > 0 else 0

        print(f"\n🎓 Semester Progress:")
        print(f"  Total Available XP: {total_semester_xp}")
        print(f"  Current Progress: {stats.total_xp}/{total_semester_xp} ({progress_percent:.1f}%)")
        print(f"  Pass (70%): {int(total_semester_xp * 0.7)} XP")
        print(f"  Good (83%): {int(total_semester_xp * 0.83)} XP")
        print(f"  Excellence (92%): {int(total_semester_xp * 0.92)} XP")

        if progress_percent >= 70:
            print(f"  ✅ PASSED!")
        else:
            print(f"  ⏳ Need {int(total_semester_xp * 0.7) - stats.total_xp} more XP to pass")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_xp_system()
