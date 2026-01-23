#!/usr/bin/env python3
"""
Migration Script: Update Legacy Sessions with Match Format Metadata

This script updates all existing sessions that have NULL match_format
and scoring_type fields with default values.

Usage:
    DATABASE_URL="postgresql://..." python scripts/migrate_legacy_sessions.py

What it does:
    - Sets match_format = 'INDIVIDUAL_RANKING' for NULL values
    - Sets scoring_type = 'PLACEMENT' for NULL values
    - Sets structure_config with basic ranking criteria
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings


def migrate_legacy_sessions():
    """Update legacy sessions with default match format metadata"""

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("🔄 Starting migration: Update legacy sessions with match format metadata")
        print("=" * 80)

        # Check how many sessions need updating
        count_query = text("""
            SELECT COUNT(*)
            FROM sessions
            WHERE match_format IS NULL OR scoring_type IS NULL
        """)

        result = db.execute(count_query)
        total_sessions = result.scalar()

        if total_sessions == 0:
            print("✅ No sessions need updating. All sessions have match_format set.")
            return

        print(f"📊 Found {total_sessions} sessions with NULL match_format or scoring_type")
        print()

        # Show sample of sessions to be updated
        sample_query = text("""
            SELECT id, title, match_format, scoring_type
            FROM sessions
            WHERE match_format IS NULL OR scoring_type IS NULL
            LIMIT 5
        """)

        sample_results = db.execute(sample_query).fetchall()
        print("📋 Sample sessions to be updated:")
        for row in sample_results:
            print(f"  • ID {row.id}: {row.title[:60]}...")

        if total_sessions > 5:
            print(f"  ... and {total_sessions - 5} more")
        print()

        # Ask for confirmation
        confirm = input("🤔 Proceed with migration? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("❌ Migration cancelled by user")
            return

        print()
        print("🚀 Starting migration...")
        print()

        # Update sessions with NULL match_format
        update_query = text("""
            UPDATE sessions
            SET
                match_format = 'INDIVIDUAL_RANKING',
                scoring_type = 'PLACEMENT',
                structure_config = COALESCE(
                    structure_config,
                    '{"ranking_criteria": "final_placement"}'::jsonb
                )
            WHERE match_format IS NULL OR scoring_type IS NULL
        """)

        result = db.execute(update_query)
        db.commit()

        print(f"✅ Updated {result.rowcount} sessions successfully!")
        print()

        # Verify update
        verify_query = text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN match_format = 'INDIVIDUAL_RANKING' THEN 1 END) as individual_ranking,
                COUNT(CASE WHEN match_format IS NULL THEN 1 END) as still_null
            FROM sessions
        """)

        verify_result = db.execute(verify_query).fetchone()

        print("📊 Migration Summary:")
        print(f"  • Total sessions: {verify_result.total}")
        print(f"  • INDIVIDUAL_RANKING format: {verify_result.individual_ranking}")
        print(f"  • Still NULL: {verify_result.still_null}")
        print()

        if verify_result.still_null > 0:
            print("⚠️  Warning: Some sessions still have NULL match_format!")
        else:
            print("✅ All sessions now have match_format set!")

        print()
        print("=" * 80)
        print("🎉 Migration completed successfully!")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_legacy_sessions()
