"""
Script to manually trigger bronze match creation for tournament 38.

This script:
1. Finds the completed semifinals
2. Uses KnockoutProgressionService to create bronze match and final (if needed)
"""

import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.services.tournament.knockout_progression_service import KnockoutProgressionService
import json


def main():
    db: Session = SessionLocal()

    try:
        tournament_id = 38

        print(f"\n🏆 Processing knockout progression for tournament {tournament_id}")

        # Get tournament
        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
        if not tournament:
            print(f"❌ Tournament {tournament_id} not found")
            return

        print(f"   Tournament: {tournament.name}")

        # Get one of the completed semifinals
        semifinal = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.tournament_phase == "Knockout Stage",
            SessionModel.tournament_round == 1,
            SessionModel.game_results.isnot(None)
        ).first()

        if not semifinal:
            print("❌ No completed semifinals found")
            return

        print(f"   Reference semifinal: {semifinal.title} (ID: {semifinal.id})")

        # Parse game_results
        game_results = json.loads(semifinal.game_results) if isinstance(semifinal.game_results, str) else semifinal.game_results

        # Use knockout progression service
        service = KnockoutProgressionService(db)
        result = service.process_knockout_progression(
            session=semifinal,
            tournament=tournament,
            game_results=game_results
        )

        if result:
            print(f"\n✅ {result['message']}")

            if "created_sessions" in result:
                for created in result["created_sessions"]:
                    print(f"   - Created {created['type']} match (Session ID: {created['session_id']})")
                    print(f"     Participants: {created['participants']}")
        else:
            print("\n⚠️  No progression needed")

        # Show all knockout sessions
        print("\n📋 All Knockout Sessions:")
        all_knockout = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.tournament_phase == "Knockout Stage"
        ).order_by(SessionModel.tournament_round, SessionModel.id).all()

        for s in all_knockout:
            has_results = "✅" if s.game_results else "⏳"
            print(f"   {has_results} Round {s.tournament_round}: {s.title}")
            print(f"      Session ID: {s.id}, Participants: {s.participant_user_ids}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
