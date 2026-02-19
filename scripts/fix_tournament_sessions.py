#!/usr/bin/env python3
"""
Fix tournament sessions for tournament ID 7
Manually trigger session generation
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app.database import SessionLocal
from app.services.tournament_session_generator import TournamentSessionGenerator

def main():
    db = SessionLocal()
    try:
        tournament_id = 7

        print(f"🔧 Generating sessions for tournament {tournament_id}...")

        generator = TournamentSessionGenerator(db)

        # Check if can generate
        can_generate, reason = generator.can_generate_sessions(tournament_id)

        if not can_generate:
            print(f"❌ Cannot generate sessions: {reason}")
            return

        # Generate sessions
        success, message, sessions_created = generator.generate_sessions(
            tournament_id=tournament_id,
            parallel_fields=1,
            session_duration_minutes=90,
            break_minutes=15
        )

        if success:
            print(f"✅ {message}")
            print(f"📊 Created {len(sessions_created)} sessions")
        else:
            print(f"❌ Failed: {message}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
