"""
Tournament Session Snapshot Management

Mentés és visszaállítás tournament sessionökből különböző típusok teszteléséhez.

Usage:
    # Save current state
    python scripts/tournament_snapshot.py save 17 "round_robin"

    # List all snapshots
    python scripts/tournament_snapshot.py list

    # Restore a snapshot
    python scripts/tournament_snapshot.py restore 17 "round_robin"

    # Compare two snapshots
    python scripts/tournament_snapshot.py compare "round_robin" "swiss_system"

    # Delete sessions (before changing type)
    python scripts/tournament_snapshot.py delete 17
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Snapshot directory
SNAPSHOT_DIR = Path(__file__).parent.parent / "snapshots" / "tournaments"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def save_snapshot(tournament_id: int, snapshot_name: str) -> None:
    """
    Save tournament sessions to a snapshot file.

    Args:
        tournament_id: Tournament ID to snapshot
        snapshot_name: Name for the snapshot (e.g., "round_robin", "swiss_system")
    """
    db = SessionLocal()
    try:
        # Get tournament info
        tournament_query = text("""
            SELECT
                s.id, s.name, s.code, s.tournament_type_id,
                tt.display_name as tournament_type_name,
                s.sessions_generated, s.max_players, s.start_date, s.end_date
            FROM semesters s
            LEFT JOIN tournament_types tt ON s.tournament_type_id = tt.id
            WHERE s.id = :tournament_id
        """)
        tournament_result = db.execute(tournament_query, {"tournament_id": tournament_id}).fetchone()

        if not tournament_result:
            print(f"❌ Tournament {tournament_id} not found")
            return

        tournament_data = {
            "id": tournament_result[0],
            "name": tournament_result[1],
            "code": tournament_result[2],
            "tournament_type_id": tournament_result[3],
            "tournament_type_name": tournament_result[4],
            "sessions_generated": tournament_result[5],
            "max_players": tournament_result[6],
            "start_date": str(tournament_result[7]),
            "end_date": str(tournament_result[8])
        }

        # Get enrolled players
        players_query = text("""
            SELECT u.id, u.name, u.email
            FROM users u
            JOIN semester_enrollments se ON u.id = se.user_id
            WHERE se.semester_id = :tournament_id AND se.is_active = true
            ORDER BY u.name
        """)
        players_result = db.execute(players_query, {"tournament_id": tournament_id}).fetchall()
        players_data = [
            {"id": p[0], "name": p[1], "email": p[2]}
            for p in players_result
        ]

        # Get sessions
        sessions_query = text("""
            SELECT
                id, code, start_datetime, end_datetime, session_type, round_number,
                capacity, specialization_type, age_group, status,
                session_ranking_metadata, match_structure, participant_user_ids, game_results
            FROM sessions
            WHERE semester_id = :tournament_id
            ORDER BY round_number, start_datetime
        """)
        sessions_result = db.execute(sessions_query, {"tournament_id": tournament_id}).fetchall()
        sessions_data = []
        for s in sessions_result:
            sessions_data.append({
                "id": s[0],
                "code": s[1],
                "start_datetime": str(s[2]),
                "end_datetime": str(s[3]),
                "session_type": s[4],
                "round_number": s[5],
                "capacity": s[6],
                "specialization_type": s[7],
                "age_group": s[8],
                "status": s[9],
                "session_ranking_metadata": s[10],
                "match_structure": s[11],
                "participant_user_ids": s[12],
                "game_results": s[13]
            })

        # Create snapshot
        snapshot = {
            "snapshot_name": snapshot_name,
            "created_at": datetime.now().isoformat(),
            "tournament": tournament_data,
            "players": players_data,
            "sessions": sessions_data,
            "session_count": len(sessions_data)
        }

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tournament_{tournament_id}_{snapshot_name}_{timestamp}.json"
        filepath = SNAPSHOT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        print(f"✅ Snapshot saved: {filename}")
        print(f"   Tournament: {tournament_data['name']}")
        print(f"   Type: {tournament_data['tournament_type_name']}")
        print(f"   Players: {len(players_data)}")
        print(f"   Sessions: {len(sessions_data)}")
        print(f"   Location: {filepath}")

    finally:
        db.close()


def restore_snapshot(tournament_id: int, snapshot_name: str) -> None:
    """
    Restore tournament sessions from a snapshot file.

    Args:
        tournament_id: Tournament ID to restore to
        snapshot_name: Name of the snapshot to restore (or full filename)
    """
    db = SessionLocal()
    try:
        # Find snapshot file
        if snapshot_name.endswith('.json'):
            filepath = SNAPSHOT_DIR / snapshot_name
        else:
            # Find most recent snapshot with this name
            matching_files = sorted(
                SNAPSHOT_DIR.glob(f"tournament_{tournament_id}_{snapshot_name}_*.json"),
                reverse=True
            )
            if not matching_files:
                print(f"❌ No snapshot found matching: {snapshot_name}")
                return
            filepath = matching_files[0]

        if not filepath.exists():
            print(f"❌ Snapshot file not found: {filepath}")
            return

        # Load snapshot
        with open(filepath, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)

        print(f"📸 Restoring snapshot: {filepath.name}")
        print(f"   Created: {snapshot['created_at']}")
        print(f"   Tournament: {snapshot['tournament']['name']}")
        print(f"   Type: {snapshot['tournament']['tournament_type_name']}")

        # Delete existing sessions
        delete_query = text("DELETE FROM sessions WHERE semester_id = :tournament_id")
        result = db.execute(delete_query, {"tournament_id": tournament_id})
        print(f"   🗑️  Deleted {result.rowcount} existing sessions")

        # Restore sessions
        if snapshot['sessions']:
            for session in snapshot['sessions']:
                insert_query = text("""
                    INSERT INTO sessions (
                        code, semester_id, start_datetime, end_datetime, session_type, round_number,
                        capacity, specialization_type, age_group, status,
                        session_ranking_metadata, match_structure, participant_user_ids, game_results
                    ) VALUES (
                        :code, :semester_id, :start_datetime, :end_datetime, :session_type, :round_number,
                        :capacity, :specialization_type, :age_group, :status,
                        :session_ranking_metadata, :match_structure, :participant_user_ids, :game_results
                    )
                """)
                db.execute(insert_query, {
                    "code": session['code'],
                    "semester_id": tournament_id,
                    "start_datetime": session['start_datetime'],
                    "end_datetime": session['end_datetime'],
                    "session_type": session['session_type'],
                    "round_number": session['round_number'],
                    "capacity": session['capacity'],
                    "specialization_type": session['specialization_type'],
                    "age_group": session['age_group'],
                    "status": session['status'],
                    "session_ranking_metadata": json.dumps(session['session_ranking_metadata']) if session['session_ranking_metadata'] else None,
                    "match_structure": json.dumps(session['match_structure']) if session['match_structure'] else None,
                    "participant_user_ids": session['participant_user_ids'],
                    "game_results": json.dumps(session['game_results']) if session['game_results'] else None
                })
            print(f"   ✅ Restored {len(snapshot['sessions'])} sessions")

        # Update sessions_generated flag
        update_query = text("""
            UPDATE semesters
            SET sessions_generated = :sessions_generated,
                tournament_type_id = :tournament_type_id
            WHERE id = :tournament_id
        """)
        db.execute(update_query, {
            "sessions_generated": snapshot['tournament']['sessions_generated'],
            "tournament_type_id": snapshot['tournament']['tournament_type_id'],
            "tournament_id": tournament_id
        })

        db.commit()
        print(f"✅ Snapshot restored successfully")

    except Exception as e:
        db.rollback()
        print(f"❌ Error restoring snapshot: {e}")
        raise
    finally:
        db.close()


def delete_sessions(tournament_id: int) -> None:
    """
    Delete all sessions for a tournament.

    Args:
        tournament_id: Tournament ID to delete sessions from
    """
    db = SessionLocal()
    try:
        # Delete sessions
        delete_query = text("DELETE FROM sessions WHERE semester_id = :tournament_id")
        result = db.execute(delete_query, {"tournament_id": tournament_id})
        deleted_count = result.rowcount

        # Update sessions_generated flag
        update_query = text("UPDATE semesters SET sessions_generated = false WHERE id = :tournament_id")
        db.execute(update_query, {"tournament_id": tournament_id})

        db.commit()
        print(f"✅ Deleted {deleted_count} sessions from tournament {tournament_id}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting sessions: {e}")
        raise
    finally:
        db.close()


def list_snapshots(tournament_id: Optional[int] = None) -> None:
    """
    List all available snapshots.

    Args:
        tournament_id: Optional tournament ID to filter by
    """
    pattern = f"tournament_{tournament_id}_*.json" if tournament_id else "tournament_*.json"
    snapshots = sorted(SNAPSHOT_DIR.glob(pattern), reverse=True)

    if not snapshots:
        print("📸 No snapshots found")
        return

    print(f"📸 Available snapshots ({len(snapshots)}):\n")
    for snapshot_file in snapshots:
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"  {snapshot_file.name}")
            print(f"    Tournament: {data['tournament']['name']} (ID: {data['tournament']['id']})")
            print(f"    Type: {data['tournament']['tournament_type_name']}")
            print(f"    Sessions: {data['session_count']}")
            print(f"    Created: {data['created_at']}")
            print()
        except Exception as e:
            print(f"  ⚠️  {snapshot_file.name} - Error reading: {e}\n")


def compare_snapshots(snapshot1_name: str, snapshot2_name: str) -> None:
    """
    Compare two snapshots and show differences in pairings.

    Args:
        snapshot1_name: Name or filename of first snapshot
        snapshot2_name: Name or filename of second snapshot
    """
    # Find snapshot files
    snapshot1_files = sorted(SNAPSHOT_DIR.glob(f"*{snapshot1_name}*.json"), reverse=True)
    snapshot2_files = sorted(SNAPSHOT_DIR.glob(f"*{snapshot2_name}*.json"), reverse=True)

    if not snapshot1_files:
        print(f"❌ Snapshot not found: {snapshot1_name}")
        return
    if not snapshot2_files:
        print(f"❌ Snapshot not found: {snapshot2_name}")
        return

    # Load snapshots
    with open(snapshot1_files[0], 'r', encoding='utf-8') as f:
        snap1 = json.load(f)
    with open(snapshot2_files[0], 'r', encoding='utf-8') as f:
        snap2 = json.load(f)

    print(f"📊 Comparing snapshots:\n")
    print(f"  Snapshot 1: {snap1['tournament']['tournament_type_name']}")
    print(f"    Sessions: {snap1['session_count']}")
    print(f"    File: {snapshot1_files[0].name}\n")

    print(f"  Snapshot 2: {snap2['tournament']['tournament_type_name']}")
    print(f"    Sessions: {snap2['session_count']}")
    print(f"    File: {snapshot2_files[0].name}\n")

    print(f"  Difference: {abs(snap1['session_count'] - snap2['session_count'])} sessions\n")

    # Show first few sessions from each
    print("📋 First 5 sessions from Snapshot 1:")
    for i, session in enumerate(snap1['sessions'][:5]):
        print(f"    Round {session['round_number']}: {session['code']} - {len(session.get('participant_user_ids') or [])} players")

    print("\n📋 First 5 sessions from Snapshot 2:")
    for i, session in enumerate(snap2['sessions'][:5]):
        print(f"    Round {session['round_number']}: {session['code']} - {len(session.get('participant_user_ids') or [])} players")


def main():
    """Main entry point for CLI."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "save":
            if len(sys.argv) < 4:
                print("Usage: python tournament_snapshot.py save <tournament_id> <snapshot_name>")
                sys.exit(1)
            tournament_id = int(sys.argv[2])
            snapshot_name = sys.argv[3]
            save_snapshot(tournament_id, snapshot_name)

        elif command == "restore":
            if len(sys.argv) < 4:
                print("Usage: python tournament_snapshot.py restore <tournament_id> <snapshot_name>")
                sys.exit(1)
            tournament_id = int(sys.argv[2])
            snapshot_name = sys.argv[3]
            restore_snapshot(tournament_id, snapshot_name)

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Usage: python tournament_snapshot.py delete <tournament_id>")
                sys.exit(1)
            tournament_id = int(sys.argv[2])
            delete_sessions(tournament_id)

        elif command == "list":
            tournament_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
            list_snapshots(tournament_id)

        elif command == "compare":
            if len(sys.argv) < 4:
                print("Usage: python tournament_snapshot.py compare <snapshot1_name> <snapshot2_name>")
                sys.exit(1)
            snapshot1_name = sys.argv[2]
            snapshot2_name = sys.argv[3]
            compare_snapshots(snapshot1_name, snapshot2_name)

        else:
            print(f"❌ Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
