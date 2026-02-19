#!/usr/bin/env python3
"""
Direct test of session generation for tournament 18
"""
import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

from app.database import SessionLocal
from app.services.tournament_session_generator import TournamentSessionGenerator

db = SessionLocal()

try:
    generator = TournamentSessionGenerator(db)

    print("=" * 70)
    print("Testing Session Generation for Tournament 18")
    print("=" * 70)

    # Check if can generate
    can_generate, reason = generator.can_generate_sessions(18)
    print(f"\n✅ Can generate: {can_generate}")
    print(f"   Reason: {reason}")

    if can_generate:
        # Generate sessions
        print("\n🔄 Generating sessions...")
        success, message, sessions_created = generator.generate_sessions(
            tournament_id=18,
            parallel_fields=4,
            session_duration_minutes=1,
            break_minutes=1,
            number_of_rounds=3  # ← CRITICAL: Testing with 3 rounds
        )

        print(f"\n✅ Success: {success}")
        print(f"   Message: {message}")
        print(f"   Sessions created: {len(sessions_created)}")

        # Show details of each session
        for i, session in enumerate(sessions_created, 1):
            print(f"\n   Session {i}:")
            print(f"      Title: {session['title']}")
            print(f"      Round: {session.get('tournament_round', 'N/A')}")
            print(f"      Start: {session['date_start']}")
            print(f"      End: {session['date_end']}")
    else:
        print(f"\n❌ Cannot generate: {reason}")

    # Check database
    print("\n" + "=" * 70)
    print("Verifying database...")
    print("=" * 70)

    from app.models.session import Session as SessionModel
    sessions_in_db = db.query(SessionModel).filter(
        SessionModel.semester_id == 18,
        SessionModel.auto_generated == True
    ).order_by(SessionModel.tournament_round).all()

    print(f"\n✅ Sessions in database: {len(sessions_in_db)}")

    for session in sessions_in_db:
        print(f"\n   ID: {session.id}")
        print(f"   Title: {session.title}")
        print(f"   Round: {session.tournament_round}")
        print(f"   Start: {session.date_start}")
        print(f"   End: {session.date_end}")

    print("\n" + "=" * 70)
    if len(sessions_in_db) == 3:
        print("🎉 SUCCESS! Generated 3 sessions as expected!")
    else:
        print(f"❌ FAILURE! Expected 3 sessions, got {len(sessions_in_db)}")
    print("=" * 70)

finally:
    db.close()
