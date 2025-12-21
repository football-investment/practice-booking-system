#!/usr/bin/env python3
"""
Migrate Instructor Specializations to User Licenses
====================================================

Migrates old instructor_specializations table data to new user_licenses table.

Old system: instructor_specializations (no levels, no belt info)
New system: user_licenses (has levels, belt progression, license IDs)

Mapping:
- INTERNSHIP → user_licenses(specialization_type='INTERNSHIP', current_level=1)
- LFA_FOOTBALL_PLAYER → user_licenses(specialization_type='PLAYER', current_level=1)
- GANCUJU_PLAYER → user_licenses(specialization_type='PLAYER', current_level=1)
- LFA_COACH → user_licenses(specialization_type='COACH', current_level=1)
"""
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def migrate_instructor_specializations():
    """
    Migrate all active instructor_specializations to user_licenses.
    """
    session = Session()

    try:
        print("=" * 70)
        print("MIGRATION: instructor_specializations → user_licenses")
        print("=" * 70)

        # 1. Get all active instructor specializations
        result = session.execute(text("""
            SELECT
                id,
                user_id,
                specialization,
                certified_at,
                is_active
            FROM instructor_specializations
            WHERE is_active = true
            ORDER BY user_id, id
        """))

        old_specializations = result.fetchall()

        if not old_specializations:
            print("✅ No active specializations to migrate")
            return

        print(f"📋 Found {len(old_specializations)} active specializations to migrate")
        print()

        # 2. Mapping old → new specialization types
        SPECIALIZATION_MAPPING = {
            'INTERNSHIP': 'INTERNSHIP',
            'LFA_FOOTBALL_PLAYER': 'PLAYER',
            'GANCUJU_PLAYER': 'PLAYER',
            'LFA_COACH': 'COACH'
        }

        migrated_count = 0
        skipped_count = 0

        for spec in old_specializations:
            old_id, user_id, old_spec, certified_at, is_active = spec

            # Get user info
            user_result = session.execute(text("""
                SELECT email, name FROM users WHERE id = :user_id
            """), {"user_id": user_id})
            user = user_result.fetchone()

            if not user:
                print(f"⚠️  User {user_id} not found, skipping specialization {old_id}")
                skipped_count += 1
                continue

            user_email, user_name = user

            # Map old specialization to new
            new_spec_type = SPECIALIZATION_MAPPING.get(old_spec)

            if not new_spec_type:
                print(f"⚠️  Unknown specialization '{old_spec}' for user {user_email}, skipping")
                skipped_count += 1
                continue

            # Check if user already has this license
            existing = session.execute(text("""
                SELECT id FROM user_licenses
                WHERE user_id = :user_id AND specialization_type = :spec_type
            """), {"user_id": user_id, "spec_type": new_spec_type})

            if existing.fetchone():
                print(f"⏩ User {user_email} already has {new_spec_type} license, skipping")
                skipped_count += 1
                continue

            # Create new user_license
            started_at = certified_at if certified_at else datetime.now(timezone.utc)

            session.execute(text("""
                INSERT INTO user_licenses (
                    user_id,
                    specialization_type,
                    current_level,
                    max_achieved_level,
                    started_at,
                    last_advanced_at,
                    payment_verified,
                    onboarding_completed,
                    credit_balance,
                    credit_purchased,
                    created_at,
                    updated_at
                )
                VALUES (
                    :user_id,
                    :spec_type,
                    1,  -- Start at level 1
                    1,  -- Max achieved is also 1
                    :started_at,
                    NULL,  -- Never advanced yet
                    true,  -- Assume verified (old system)
                    true,  -- Assume onboarded (old system)
                    0,  -- No credits
                    0,  -- No credits purchased
                    NOW(),
                    NOW()
                )
            """), {
                "user_id": user_id,
                "spec_type": new_spec_type,
                "started_at": started_at
            })

            print(f"✅ Migrated: {user_name} ({user_email}) - {old_spec} → {new_spec_type} Level 1")
            migrated_count += 1

        # Commit all changes
        session.commit()

        print()
        print("=" * 70)
        print(f"✅ MIGRATION COMPLETE")
        print(f"   Migrated: {migrated_count}")
        print(f"   Skipped:  {skipped_count}")
        print("=" * 70)

        # Show final state for Grand Master
        print()
        print("🏆 Grand Master Final State:")
        print("-" * 70)

        gm_result = session.execute(text("""
            SELECT
                ul.id,
                ul.specialization_type,
                ul.current_level,
                ul.max_achieved_level,
                ul.started_at
            FROM user_licenses ul
            JOIN users u ON u.id = ul.user_id
            WHERE u.email = 'grandmaster@lfa.com'
            ORDER BY ul.id
        """))

        gm_licenses = gm_result.fetchall()

        if gm_licenses:
            for lic in gm_licenses:
                lic_id, spec_type, current, max_level, started = lic
                print(f"  License #{lic_id}: {spec_type} - Level {current}/{max_level} (Started: {started})")
        else:
            print("  ⚠️  No licenses found!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error during migration: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_instructor_specializations()
