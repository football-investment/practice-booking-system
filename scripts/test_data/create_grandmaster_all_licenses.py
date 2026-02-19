#!/usr/bin/env python3
"""
Create All Licenses for Grand Master
=====================================

Grand Master should have ALL licenses across all specializations:
- 8 GānCuju PLAYER belts (Level 1-8)
- 8 LFA COACH levels (Level 1-8)
- 5 INTERNSHIP levels (Level 1-5)

Total: 21 licenses
"""
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def create_all_grandmaster_licenses():
    """
    Create all 21 licenses for Grand Master.
    """
    session = Session()

    try:
        print("=" * 80)
        print("CREATE ALL LICENSES FOR GRAND MASTER")
        print("=" * 80)
        print()

        # 1. Get Grand Master user ID
        result = session.execute(text("""
            SELECT id, email, name FROM users WHERE email = 'grandmaster@lfa.com'
        """))

        gm = result.fetchone()

        if not gm:
            print("❌ Grand Master not found!")
            return

        gm_id, gm_email, gm_name = gm
        print(f"👤 User: {gm_name} ({gm_email}) - ID: {gm_id}")
        print()

        # 2. Define all licenses to create
        licenses_to_create = []

        # === GānCuju PLAYER (8 belts) ===
        player_belts = [
            (1, "🤍 Bamboo Student (White)"),
            (2, "💛 Morning Dew (Yellow)"),
            (3, "💚 Flexible Reed (Green)"),
            (4, "💙 Sky River (Blue)"),
            (5, "🤎 Strong Root (Brown)"),
            (6, "🩶 Winter Moon (Dark Gray)"),
            (7, "🖤 Midnight Guardian (Black)"),
            (8, "❤️ Dragon Wisdom (Red)")
        ]

        print("🥋 GānCuju PLAYER Belts (8):")
        print("-" * 80)
        for level, name in player_belts:
            licenses_to_create.append(("PLAYER", level, name))
            print(f"  Level {level}: {name}")
        print()

        # === LFA COACH (8 levels) ===
        coach_levels = [
            (1, "👨‍🏫 LFA PRE Assistant"),
            (2, "👨‍🏫 LFA PRE Head"),
            (3, "👨‍🏫 LFA YOUTH Assistant"),
            (4, "👨‍🏫 LFA YOUTH Head"),
            (5, "👨‍🏫 LFA AMATEUR Assistant"),
            (6, "👨‍🏫 LFA AMATEUR Head"),
            (7, "👨‍🏫 LFA PRO Assistant"),
            (8, "👨‍🏫 LFA PRO Head")
        ]

        print("👨‍🏫 LFA COACH Levels (8):")
        print("-" * 80)
        for level, name in coach_levels:
            licenses_to_create.append(("COACH", level, name))
            print(f"  Level {level}: {name}")
        print()

        # === INTERNSHIP (5 levels) ===
        intern_levels = [
            (1, "🔰 Junior Intern"),
            (2, "📈 Mid-level Intern"),
            (3, "🎯 Senior Intern"),
            (4, "👑 Lead Intern"),
            (5, "🚀 Principal Intern")
        ]

        print("📚 INTERNSHIP Levels (5):")
        print("-" * 80)
        for level, name in intern_levels:
            licenses_to_create.append(("INTERNSHIP", level, name))
            print(f"  Level {level}: {name}")
        print()

        print("=" * 80)
        print(f"📊 TOTAL LICENSES TO CREATE: {len(licenses_to_create)}")
        print("=" * 80)
        print()

        # 3. Delete existing licenses for Grand Master (clean slate)
        print("🧹 Cleaning up existing licenses...")
        result = session.execute(text("""
            DELETE FROM user_licenses WHERE user_id = :user_id
        """), {"user_id": gm_id})

        deleted_count = result.rowcount
        session.commit()
        print(f"   Deleted {deleted_count} old licenses")
        print()

        # 4. Create all licenses
        print("🏗️  Creating licenses...")
        print()

        base_date = datetime(2024, 1, 1, 10, 0, 0)
        created_count = 0

        for spec_type, level, display_name in licenses_to_create:
            # Stagger the started_at dates (each level 30 days apart for progression)
            started_at = base_date + timedelta(days=(level - 1) * 30)
            last_advanced = started_at + timedelta(days=15) if level > 1 else None

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
                    :level,
                    :level,  -- max_achieved = current for now
                    :started_at,
                    :last_advanced_at,
                    true,
                    true,
                    0,
                    0,
                    NOW(),
                    NOW()
                )
            """), {
                "user_id": gm_id,
                "spec_type": spec_type,
                "level": level,
                "started_at": started_at,
                "last_advanced_at": last_advanced
            })

            created_count += 1
            print(f"   ✅ {spec_type} Level {level} - {display_name}")

        # Commit all changes
        session.commit()

        print()
        print("=" * 80)
        print(f"✅ SUCCESS! Created {created_count} licenses for Grand Master")
        print("=" * 80)
        print()

        # 5. Show final state
        print("🏆 GRAND MASTER FINAL LICENSE STATE:")
        print("=" * 80)

        final_result = session.execute(text("""
            SELECT
                id,
                specialization_type,
                current_level,
                max_achieved_level,
                started_at
            FROM user_licenses
            WHERE user_id = :user_id
            ORDER BY specialization_type, current_level
        """), {"user_id": gm_id})

        final_licenses = final_result.fetchall()

        current_spec = None
        for lic in final_licenses:
            lic_id, spec_type, current, max_level, started = lic

            if spec_type != current_spec:
                print()
                if spec_type == "PLAYER":
                    print("🥋 GānCuju PLAYER:")
                elif spec_type == "COACH":
                    print("👨‍🏫 LFA COACH:")
                elif spec_type == "INTERNSHIP":
                    print("📚 INTERNSHIP:")
                print("-" * 80)
                current_spec = spec_type

            print(f"  License #{lic_id:3d} | Level {current}/{max_level} | Started: {started}")

        print()
        print("=" * 80)
        print(f"📊 TOTAL LICENSES: {len(final_licenses)}")
        print("=" * 80)

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_all_grandmaster_licenses()
