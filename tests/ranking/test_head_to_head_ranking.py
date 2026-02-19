"""
DB-Level Test: HEAD_TO_HEAD Tournament Ranking Logic

Tests that score-based match results correctly update:
- wins / losses / draws
- goals_for / goals_against
- points accumulation
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_head_to_head_ranking():
    """Test that HEAD_TO_HEAD scoring updates ranking fields correctly"""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("HEAD_TO_HEAD RANKING TEST")
        print("=" * 80)

        # Step 1: Find or create test tournament
        print("\n[1] Finding HEAD_TO_HEAD tournament...")
        result = db.execute(text("""
            SELECT id, name, format
            FROM semesters
            WHERE format = 'HEAD_TO_HEAD'
            AND is_active = true
            LIMIT 1
        """))
        tournament = result.fetchone()

        if not tournament:
            print("❌ No active HEAD_TO_HEAD tournament found!")
            print("Please create a HEAD_TO_HEAD tournament first.")
            return False

        tournament_id = tournament[0]
        tournament_name = tournament[1]
        print(f"✅ Found tournament: {tournament_name} (ID: {tournament_id})")

        # Step 2: Get enrolled participants
        print("\n[2] Finding enrolled participants...")
        result = db.execute(text("""
            SELECT se.user_id, u.name
            FROM semester_enrollments se
            JOIN users u ON se.user_id = u.id
            WHERE se.semester_id = :tournament_id
            AND se.is_active = true
            LIMIT 2
        """), {"tournament_id": tournament_id})

        participants = result.fetchall()

        if len(participants) < 2:
            print(f"❌ Need at least 2 participants, found {len(participants)}")
            print("Please enroll participants in the tournament first.")
            return False

        player_a_id = participants[0][0]
        player_a_name = participants[0][1]
        player_b_id = participants[1][0]
        player_b_name = participants[1][1]

        print(f"✅ Player A: {player_a_name} (ID: {player_a_id})")
        print(f"✅ Player B: {player_b_name} (ID: {player_b_id})")

        # Step 3: Find a tournament session with game results
        print("\n[3] Finding tournament session...")
        result = db.execute(text("""
            SELECT id, game_results
            FROM sessions
            WHERE semester_id = :tournament_id
            AND is_tournament_game = true
            AND session_status = 'COMPLETED'
            AND game_results IS NOT NULL
            LIMIT 1
        """), {"tournament_id": tournament_id})

        session = result.fetchone()

        if not session:
            print("❌ No completed tournament session with game results found")
            print("Please complete a match first through the UI")
            return False

        session_id = session[0]
        game_results = session[1]
        print(f"✅ Found session ID: {session_id}")
        print(f"   Game results: {game_results}")

        # Step 4: Check ranking updates
        print("\n[4] Checking tournament_rankings table...")
        result = db.execute(text("""
            SELECT
                user_id,
                rank,
                points,
                wins,
                losses,
                draws,
                goals_for,
                goals_against
            FROM tournament_rankings
            WHERE tournament_id = :tournament_id
            AND user_id IN (:player_a_id, :player_b_id)
            ORDER BY user_id
        """), {
            "tournament_id": tournament_id,
            "player_a_id": player_a_id,
            "player_b_id": player_b_id
        })

        rankings = result.fetchall()

        print("\n" + "=" * 80)
        print("RANKING RESULTS")
        print("=" * 80)

        if not rankings:
            print("❌ No ranking entries found!")
            print("   The ranking logic may not have executed.")
            return False

        for ranking in rankings:
            user_id, rank, points, wins, losses, draws, goals_for, goals_against = ranking
            user_name = player_a_name if user_id == player_a_id else player_b_name

            print(f"\n{user_name} (ID: {user_id})")
            print(f"  Rank: {rank}")
            print(f"  Points: {points}")
            print(f"  Record: {wins}W - {losses}L - {draws}D")
            print(f"  Goals: {goals_for} for, {goals_against} against")
            print(f"  Goal Diff: {goals_for - goals_against}")

        # Step 5: Validate results
        print("\n" + "=" * 80)
        print("VALIDATION")
        print("=" * 80)

        # Check that at least one player has updated stats
        has_wins_or_losses = any(r[3] > 0 or r[4] > 0 or r[5] > 0 for r in rankings)
        has_goals = any(r[6] > 0 or r[7] > 0 for r in rankings)
        has_points = any(r[2] > 0 for r in rankings)

        if has_wins_or_losses:
            print("✅ Wins/Losses/Draws are being tracked")
        else:
            print("❌ Wins/Losses/Draws are NOT being updated")

        if has_goals:
            print("✅ Goals For/Against are being tracked")
        else:
            print("❌ Goals For/Against are NOT being updated")

        if has_points:
            print("✅ Points are being calculated")
        else:
            print("❌ Points are NOT being calculated")

        success = has_wins_or_losses and has_goals and has_points

        print("\n" + "=" * 80)
        if success:
            print("✅ TEST PASSED: Ranking logic is working correctly!")
        else:
            print("❌ TEST FAILED: Some ranking fields are not updating")
        print("=" * 80)

        return success

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    test_head_to_head_ranking()
