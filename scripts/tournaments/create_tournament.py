#!/usr/bin/env python3
"""
Tournament Generator CLI

Quick command-line tool to create one-day tournaments for testing or production use.

Usage:
  # Create tournament for tomorrow with default template (full-day)
  python scripts/tournaments/create_tournament.py --date tomorrow --name "Winter Cup"

  # Create tournament for specific date with custom sessions
  python scripts/tournaments/create_tournament.py \
    --date 2025-12-27 \
    --name "Holiday Tournament" \
    --instructor-id 2 \
    --sessions 3 \
    --auto-book

  # Use template
  python scripts/tournaments/create_tournament.py \
    --date 2025-12-28 \
    --name "Spring Cup" \
    --template half_day
"""
import sys
import os
import argparse
from datetime import date, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.specialization import SpecializationType
from app.services.tournament_service import TournamentService


# ============================================================================
# TEMPLATES
# ============================================================================

TOURNAMENT_TEMPLATES = {
    "half_day": {
        "name": "Half-Day Tournament",
        "sessions": [
            {"time": "09:00", "title": "Morning Session", "duration_minutes": 90, "capacity": 20},
            {"time": "11:00", "title": "Late Morning Session", "duration_minutes": 90, "capacity": 20}
        ]
    },
    "full_day": {
        "name": "Full-Day Tournament",
        "sessions": [
            {"time": "09:00", "title": "Morning Session", "duration_minutes": 90, "capacity": 20},
            {"time": "13:00", "title": "Afternoon Session", "duration_minutes": 90, "capacity": 20},
            {"time": "16:00", "title": "Evening Session", "duration_minutes": 90, "capacity": 16}
        ]
    },
    "intensive": {
        "name": "Intensive Tournament",
        "sessions": [
            {"time": "08:00", "title": "Early Morning", "duration_minutes": 90, "capacity": 16},
            {"time": "10:00", "title": "Mid Morning", "duration_minutes": 90, "capacity": 20},
            {"time": "13:00", "title": "Afternoon", "duration_minutes": 90, "capacity": 20},
            {"time": "15:30", "title": "Late Afternoon", "duration_minutes": 90, "capacity": 16},
            {"time": "18:00", "title": "Evening", "duration_minutes": 90, "capacity": 16}
        ]
    }
}


# ============================================================================
# CLI FUNCTIONS
# ============================================================================

def parse_date(date_str: str) -> date:
    """Parse date string (supports 'tomorrow', 'today', or YYYY-MM-DD)"""
    if date_str.lower() == "today":
        return date.today()
    elif date_str.lower() == "tomorrow":
        return date.today() + timedelta(days=1)
    else:
        # Parse YYYY-MM-DD
        from datetime import datetime
        return datetime.strptime(date_str, "%Y-%m-%d").date()


def get_default_instructor(db: Session) -> int:
    """Get first instructor ID as default"""
    instructor = db.query(User).filter(User.role == UserRole.INSTRUCTOR).first()
    if instructor:
        return instructor.id
    raise ValueError("No instructors found in database")


def create_tournament_cli(
    db: Session,
    tournament_date: date,
    name: str,
    specialization_type: SpecializationType,
    sessions: List[Dict[str, Any]],
    master_instructor_id: int = None,
    auto_book: bool = False,
    booking_capacity_pct: int = 70,
    location_id: int = None,
    age_group: str = None
):
    """Create tournament via CLI"""
    print("=" * 80)
    print("🏆 Creating Tournament")
    print("=" * 80)
    print(f"Name: {name}")
    print(f"Date: {tournament_date}")
    print(f"Specialization: {specialization_type.value}")
    print(f"Sessions: {len(sessions)}")
    if master_instructor_id:
        print(f"Master Instructor ID: {master_instructor_id}")
    if auto_book:
        print(f"Auto-booking: {booking_capacity_pct}% of capacity")
    print("=" * 80)

    # Create tournament semester (no instructor yet)
    print("\n🔨 Creating tournament semester...")
    semester = TournamentService.create_tournament_semester(
        db=db,
        tournament_date=tournament_date,
        name=name,
        specialization_type=specialization_type,
        location_id=location_id,
        age_group=age_group
    )
    print(f"✅ Semester created (ID: {semester.id}, Status: {semester.status})")

    # Create sessions (no instructor yet)
    print(f"\n🔨 Creating {len(sessions)} sessions...")
    created_sessions = TournamentService.create_tournament_sessions(
        db=db,
        semester_id=semester.id,
        session_configs=sessions,
        tournament_date=tournament_date
    )
    print(f"✅ Sessions created:")
    for session in created_sessions:
        print(f"   - {session.title} ({session.date_start.strftime('%H:%M')}) - Capacity: {session.capacity}")

    # Assign master instructor if provided
    if master_instructor_id:
        print(f"\n🔨 Assigning master instructor (ID: {master_instructor_id})...")
        try:
            semester = TournamentService.assign_master_instructor(
                db=db,
                semester_id=semester.id,
                master_instructor_id=master_instructor_id
            )
            print(f"✅ Master instructor assigned. Status: {semester.status}")
        except ValueError as e:
            print(f"❌ Error assigning master instructor: {e}")
            return None

    # Auto-book if requested
    total_bookings = 0
    if auto_book:
        if semester.status != "READY_FOR_ENROLLMENT":
            print(f"\n⚠️  WARNING: Cannot auto-book - tournament status is {semester.status}")
            print("   Assign master instructor first to activate tournament.")
        else:
            print(f"\n🔨 Auto-booking students ({booking_capacity_pct}% of capacity)...")
            session_ids = [s.id for s in created_sessions]
            bookings_map = TournamentService.auto_book_students(
                db=db,
                session_ids=session_ids,
                capacity_percentage=booking_capacity_pct
            )
            total_bookings = sum(len(user_ids) for user_ids in bookings_map.values())
            print(f"✅ Booked {total_bookings} students across {len(sessions)} sessions")

    # Get summary
    print("\n📊 Tournament Summary:")
    summary = TournamentService.get_tournament_summary(db, semester.id)
    print(f"   Tournament ID: {summary['semester_id']}")
    print(f"   Status: {semester.status}")
    print(f"   Master Instructor: {semester.master_instructor_id or 'Not assigned'}")
    print(f"   Sessions: {summary['session_count']}")
    print(f"   Total Capacity: {summary['total_capacity']}")
    print(f"   Total Bookings: {summary['total_bookings']}")
    print(f"   Fill Rate: {summary['fill_percentage']}%")

    print("\n" + "=" * 80)
    if semester.status == "SEEKING_INSTRUCTOR":
        print("⚠️  Tournament created but needs master instructor!")
        print("   Use --instructor-id to assign master instructor")
    else:
        print("🎉 Tournament created successfully!")
    print("=" * 80)

    return semester.id


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Create one-day tournament",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create tournament for tomorrow
  %(prog)s --date tomorrow --name "Winter Cup"

  # Create tournament with specific template
  %(prog)s --date 2025-12-27 --name "Holiday Cup" --template half_day

  # Create tournament with custom sessions count
  %(prog)s --date tomorrow --name "Test Tournament" --sessions 2 --auto-book
        """
    )

    parser.add_argument("--date", required=True, help="Tournament date (YYYY-MM-DD, 'today', or 'tomorrow')")
    parser.add_argument("--name", required=True, help="Tournament name")
    parser.add_argument("--instructor-id", type=int,
                       help="Master instructor ID to assign (optional - tournament created with SEEKING_INSTRUCTOR status if not provided)")
    parser.add_argument("--specialization", default="LFA_FOOTBALL_PLAYER",
                       help="Specialization type (default: LFA_FOOTBALL_PLAYER)")
    parser.add_argument("--age-group", help="Age group (e.g., PRE, YOUTH)")
    parser.add_argument("--location-id", type=int, help="Location ID")
    parser.add_argument("--template", choices=TOURNAMENT_TEMPLATES.keys(),
                       help="Use predefined template (half_day, full_day, intensive)")
    parser.add_argument("--sessions", type=int, default=3,
                       help="Number of sessions (ignored if --template is used)")
    parser.add_argument("--auto-book", action="store_true",
                       help="Auto-book students (for testing - requires master instructor)")
    parser.add_argument("--booking-pct", type=int, default=70,
                       help="Booking fill percentage (default: 70)")

    args = parser.parse_args()

    # Parse date
    try:
        tournament_date = parse_date(args.date)
    except ValueError as e:
        print(f"❌ Error parsing date: {e}")
        sys.exit(1)

    # Validate future date
    if tournament_date < date.today():
        print(f"❌ Error: Tournament date must be today or in the future")
        sys.exit(1)

    # Get sessions config
    if args.template:
        template = TOURNAMENT_TEMPLATES[args.template]
        sessions = template["sessions"]
        if not args.name:
            tournament_name = f"{template['name']} - {tournament_date}"
        else:
            tournament_name = args.name
    else:
        # Generate simple sessions
        tournament_name = args.name
        sessions = []
        session_times = ["09:00", "13:00", "16:00", "18:30", "20:00"]
        for i in range(min(args.sessions, 5)):
            sessions.append({
                "time": session_times[i],
                "title": f"Session {i+1}",
                "duration_minutes": 90,
                "capacity": 20
            })

    # Get database session
    db = SessionLocal()

    try:
        # Get instructor ID (optional - for assigning master instructor)
        master_instructor_id = args.instructor_id
        if not master_instructor_id and args.auto_book:
            # For testing with auto-book, we need an instructor
            master_instructor_id = get_default_instructor(db)
            print(f"ℹ️ Using default instructor ID for testing: {master_instructor_id}")

        # Parse specialization
        try:
            specialization_type = SpecializationType[args.specialization.upper()]
        except KeyError:
            print(f"❌ Error: Invalid specialization type: {args.specialization}")
            print(f"Valid types: {', '.join([s.name for s in SpecializationType])}")
            sys.exit(1)

        # Create tournament
        create_tournament_cli(
            db=db,
            tournament_date=tournament_date,
            name=tournament_name,
            specialization_type=specialization_type,
            sessions=sessions,
            master_instructor_id=master_instructor_id,
            auto_book=args.auto_book,
            booking_capacity_pct=args.booking_pct,
            location_id=args.location_id,
            age_group=args.age_group
        )

    except Exception as e:
        print(f"\n❌ Error creating tournament: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
