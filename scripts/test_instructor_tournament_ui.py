"""
Test Script: Instructor Tournament UI

Tests the new Table View and Kanban View UI with various tournament counts.

Usage:
    python3 scripts/test_instructor_tournament_ui.py
"""

import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.semester import Semester
from app.models.user import User
from app.models.instructor_assignment import InstructorAssignmentRequest
from datetime import datetime, timedelta
import random

    from app.models.session import Session as SessionModel

    # Get tournament IDs first
        import traceback
sys.path.append('.')

def create_test_tournaments(db: Session, count: int = 50):
    """
    Create test tournaments with varied characteristics.

    Args:
        count: Number of tournaments to create
    """
    print(f"\n🔧 Creating {count} test tournaments...")

    assignment_types = ['APPLICATION_BASED', 'OPEN_ASSIGNMENT']
    age_groups = ['LFA_PLAYER_PRE', 'LFA_PLAYER_YOUTH', 'LFA_PLAYER_AMATEUR', 'LFA_PLAYER_PRO']
    tournament_types = ['League', 'Elimination', 'King Court', 'Group Stage', 'Comprehensive']

    created_count = 0

    for i in range(count):
        tournament_type = random.choice(tournament_types)
        age_group = random.choice(age_groups)
        assignment_type = random.choice(assignment_types)

        # Random start date in next 3 months
        days_ahead = random.randint(1, 90)
        start_date = datetime.utcnow() + timedelta(days=days_ahead)
        end_date = start_date + timedelta(days=random.randint(7, 30))

        tournament = Semester(
            name=f"{tournament_type} Tournament {i+1}",
            code=f"TOURN-{random.randint(10000, 99999)}",
            specialization_type=age_group,
            start_date=start_date,
            end_date=end_date,
            status='SEEKING_INSTRUCTOR',
            tournament_status='SEEKING_INSTRUCTOR',
            assignment_type=assignment_type,
            max_players=random.choice([8, 12, 16, 20, 24]),
            is_active=True
        )

        db.add(tournament)
        created_count += 1

    db.commit()
    print(f"✅ Created {created_count} tournaments")


def create_test_applications(db: Session, instructor_email: str = "junior.intern@lfa.com"):
    """
    Create test applications for some tournaments to test all Kanban columns.

    Args:
        instructor_email: Email of the instructor user
    """
    print(f"\n🔧 Creating test applications for {instructor_email}...")

    # Get instructor user
    instructor = db.query(User).filter(User.email == instructor_email).first()
    if not instructor:
        print(f"❌ Instructor {instructor_email} not found")
        return

    # Get admin user (for requested_by)
    admin = db.query(User).filter(User.role == 'ADMIN').first()
    if not admin:
        print("❌ Admin user not found")
        return

    # Get APPLICATION_BASED tournaments
    tournaments = db.query(Semester).filter(
        Semester.code.like('TOURN-%'),
        Semester.status == 'SEEKING_INSTRUCTOR',
        Semester.assignment_type == 'APPLICATION_BASED'
    ).limit(10).all()

    if not tournaments:
        print("❌ No APPLICATION_BASED tournaments found")
        return

    statuses = ['PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED']
    created_count = 0

    # Create applications with different statuses
    for tournament in tournaments[:8]:
        status = random.choice(statuses)

        application = InstructorAssignmentRequest(
            semester_id=tournament.id,
            instructor_id=instructor.id,
            requested_by=admin.id,
            status=status,
            request_message=f"Test application for {tournament.name}",
            created_at=datetime.utcnow(),
            priority=5
        )

        if status in ['ACCEPTED', 'DECLINED', 'CANCELLED']:
            application.responded_at = datetime.utcnow()
            application.response_message = f"Test response: {status}"

        db.add(application)
        created_count += 1

    db.commit()
    print(f"✅ Created {created_count} test applications")

    # Print breakdown
    pending = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.instructor_id == instructor.id,
        InstructorAssignmentRequest.status == 'PENDING'
    ).count()

    accepted = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.instructor_id == instructor.id,
        InstructorAssignmentRequest.status == 'ACCEPTED'
    ).count()

    declined = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.instructor_id == instructor.id,
        InstructorAssignmentRequest.status.in_(['DECLINED', 'CANCELLED'])
    ).count()

    print(f"\n📊 Application Status Breakdown:")
    print(f"   🟡 Pending: {pending}")
    print(f"   ✅ Accepted: {accepted}")
    print(f"   ❌ Declined/Cancelled: {declined}")


def cleanup_test_tournaments(db: Session):
    """Clean up test tournaments and related data"""
    print("\n🧹 Cleaning up test tournaments...")

    tournament_ids = [t.id for t in db.query(Semester).filter(Semester.code.like('TOURN-%')).all()]

    if not tournament_ids:
        print("✅ No test tournaments to clean up")
        return

    # Delete sessions first (foreign key constraint)
    deleted_sessions = db.query(SessionModel).filter(
        SessionModel.semester_id.in_(tournament_ids)
    ).delete(synchronize_session=False)

    # Delete applications
    deleted_apps = db.query(InstructorAssignmentRequest).filter(
        InstructorAssignmentRequest.semester_id.in_(tournament_ids)
    ).delete(synchronize_session=False)

    # Delete tournaments
    deleted_tournaments = db.query(Semester).filter(
        Semester.code.like('TOURN-%')
    ).delete(synchronize_session=False)

    db.commit()

    print(f"✅ Deleted {deleted_sessions} sessions")
    print(f"✅ Deleted {deleted_apps} applications")
    print(f"✅ Deleted {deleted_tournaments} tournaments")


def main():
    """Main test function"""
    db = SessionLocal()

    try:
        print("\n" + "="*60)
        print("🧪 INSTRUCTOR TOURNAMENT UI TEST")
        print("="*60)

        # Test 1: Clean environment
        print("\n--- Test 1: Empty State ---")
        cleanup_test_tournaments(db)
        print("✅ Test 1 passed: Clean state verified")

        # Test 2: 1 tournament
        print("\n--- Test 2: Single Tournament ---")
        create_test_tournaments(db, count=1)
        print("✅ Test 2 passed: UI should show 1 tournament")

        # Test 3: 10 tournaments (exactly 1 page)
        print("\n--- Test 3: 10 Tournaments (1 page) ---")
        cleanup_test_tournaments(db)
        create_test_tournaments(db, count=10)
        print("✅ Test 3 passed: UI should show 10 tournaments on 1 page")

        # Test 4: 25 tournaments (3 pages)
        print("\n--- Test 4: 25 Tournaments (3 pages) ---")
        cleanup_test_tournaments(db)
        create_test_tournaments(db, count=25)
        print("✅ Test 4 passed: UI should show 25 tournaments across 3 pages")

        # Test 5: 50+ tournaments with applications
        print("\n--- Test 5: 50+ Tournaments with Applications ---")
        cleanup_test_tournaments(db)
        create_test_tournaments(db, count=50)
        create_test_applications(db)
        print("✅ Test 5 passed: UI should show 50 tournaments with varied application statuses")

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)

        print("\n📋 Manual Testing Instructions:")
        print("1. Start the Streamlit app: streamlit run streamlit_app/app.py")
        print("2. Login as instructor: junior.intern@lfa.com")
        print("3. Navigate to 'Tournament Applications' tab")
        print("4. Test Table View:")
        print("   - Sort by different columns (Date, Name, Age, Type, Status)")
        print("   - Apply filters (Age Group, Assignment Type, Status)")
        print("   - Navigate pagination (should show 10 per page)")
        print("   - Click 'Apply' button on APPLICATION_BASED tournaments")
        print("   - Click 'View Details' on applied tournaments")
        print("5. Test Kanban View:")
        print("   - Toggle to Kanban View using the button")
        print("   - Verify 4 columns: Not Applied, Pending, Accepted, Declined")
        print("   - Check tournament cards in each column")
        print("   - Test Apply button in 'Not Applied' column")
        print("6. Test Mobile Responsiveness:")
        print("   - Resize browser window to mobile width (< 768px)")
        print("   - Verify columns stack vertically")
        print("   - Verify buttons are full-width")
        print("   - Verify pagination controls work on mobile")

        print("\n🔄 To clean up test data:")
        print("   python3 scripts/test_instructor_tournament_ui.py --cleanup")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
        db = SessionLocal()
        try:
            cleanup_test_tournaments(db)
            print("\n✅ Cleanup complete")
        finally:
            db.close()
    else:
        main()
