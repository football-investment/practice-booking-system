"""
Recalculate tournament rankings from scratch based on all match results.

This script:
1. Resets all tournament_rankings for tournament 38
2. Replays all match results to rebuild rankings
3. Shows final standings
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.models.tournament_ranking import TournamentRanking
from app.services.tournament.result_processor import ResultProcessor
import json


def main():
    db: Session = SessionLocal()

    try:
        tournament_id = 38

        print(f"\n🏆 Recalculating rankings for tournament {tournament_id}")

        # Get tournament
        tournament = db.query(Semester).filter(Semester.id == tournament_id).first()
        if not tournament:
            print(f"❌ Tournament {tournament_id} not found")
            return

        print(f"   Tournament: {tournament.name}")

        # Step 1: Reset all rankings
        print(f"\n📝 Step 1: Resetting all rankings...")
        deleted_count = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).delete()
        db.commit()
        print(f"   Deleted {deleted_count} ranking entries")

        # Step 2: Get all tournament sessions with results
        print(f"\n📋 Step 2: Finding all matches with results...")
        sessions = db.query(SessionModel).filter(
            SessionModel.semester_id == tournament_id,
            SessionModel.is_tournament_game == True,
            SessionModel.game_results.isnot(None)
        ).order_by(SessionModel.id).all()

        print(f"   Found {len(sessions)} matches with results")

        # Step 3: Replay each match
        print(f"\n🔄 Step 3: Replaying all matches...")
        processor = ResultProcessor(db)

        for idx, session in enumerate(sessions, 1):
            game_results = json.loads(session.game_results) if isinstance(session.game_results, str) else session.game_results
            raw_results = game_results.get('raw_results', [])

            if not raw_results:
                print(f"   ⏭️  Skipping session {session.id} (no raw_results)")
                continue

            print(f"   [{idx}/{len(sessions)}] Processing: {session.title}")
            print(f"       Phase: {session.tournament_phase}, Round: {session.tournament_round}")
            print(f"       Participants: {session.participant_user_ids}")
            print(f"       Results: {raw_results}")

            # Re-process the results
            try:
                processor._process_head_to_head_tournament(
                    db=db,
                    session=session,
                    tournament=tournament,
                    raw_results=raw_results,
                    match_notes=game_results.get('match_notes'),
                    recorded_by_user_id=game_results.get('recorded_by'),
                    recorded_by_name=game_results.get('recorded_by_name')
                )
                db.commit()
                print(f"       ✅ Processed successfully")
            except Exception as e:
                print(f"       ❌ Error: {e}")
                db.rollback()
                raise

        # Step 4: Show final standings
        print(f"\n🏅 Step 4: Final Standings")
        rankings = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tournament_id
        ).order_by(TournamentRanking.rank, TournamentRanking.points.desc()).all()

        print(f"\n   Rank | Player ID | Points | W-L-D | Goals")
        print(f"   -----|-----------|--------|-------|------")
        for r in rankings[:8]:
            print(f"   {r.rank:>4} | {r.user_id:>9} | {r.points:>6.2f} | {r.wins}-{r.losses}-{r.draws} | {r.goals_for}-{r.goals_against}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
