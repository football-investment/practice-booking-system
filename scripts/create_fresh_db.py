#!/usr/bin/env python3
"""
Create all database tables directly from SQLAlchemy models.

This bypasses Alembic migrations and creates tables from scratch.
Use this for fresh database setup when migration chain is broken.
"""
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base, engine
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def import_all_models():
    """Import all models to register them with Base.metadata"""
    logger.info("Importing all models...")

    # Import all model modules to register tables
    from app.models import (
        user,
        session,
        booking,
        attendance,
        feedback,
        semester,
        group,
        specialization,
        user_progress,
        project,
        quiz,
        gamification,
        license,
        certificate,
        message,
        notification,
        track
    )

    logger.info(f"✅ Imported {len(Base.metadata.tables)} table definitions")
    return Base.metadata.tables.keys()


def create_tables():
    """Create all tables directly from SQLAlchemy models"""

    logger.info(f"🚀 Creating tables in database: {settings.DATABASE_URL}")
    logger.info("=" * 80)

    # Import all models first
    table_names = import_all_models()

    # Create all tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("=" * 80)
    logger.info(f"✅ Successfully created {len(Base.metadata.tables)} tables!")
    logger.info("=" * 80)

    # List created tables
    logger.info("Created tables:")
    for i, table_name in enumerate(sorted(table_names), 1):
        logger.info(f"  {i:2d}. {table_name}")

    logger.info("=" * 80)
    logger.info("🎉 Database creation complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Verify tables: psql gancuju_education_center_prod -c '\\dt'")
    logger.info("  2. Stamp alembic: alembic stamp head")
    logger.info("  3. Run seed script: python scripts/seed_initial_data.py")


if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
