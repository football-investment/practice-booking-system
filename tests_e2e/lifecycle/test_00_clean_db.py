"""
Phase 0: Clean DB Setup
========================

Creates reproducible, minimal starting state for E2E lifecycle.

Prerequisites: None (this is the first phase)
Postcondition: Snapshot "00_clean_db" created

Performance: ~10-15 seconds
Idempotent: Yes (can run multiple times)
"""

import os
import sys
import subprocess
import json
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests_e2e.utils.snapshot_manager import SnapshotManager
from tests_e2e.utils.db_helpers import count_tables, get_invitation_code


@pytest.mark.lifecycle
@pytest.mark.phase_0
@pytest.mark.nondestructive
def test_00_clean_db_setup(snapshot_manager: SnapshotManager):
    """
    Phase 0: Clean DB Setup

    Steps:
    1. Terminate all DB connections
    2. Drop all tables (DROP SCHEMA public CASCADE)
    3. Recreate schema
    4. Run Alembic migrations
    5. Seed minimal system data (NO user data - that's tested in Phase 1)
    6. Verify DB integrity
    7. Save snapshot: "00_clean_db"

    Seed data (minimal):
    - 1 specialization_type: LFA_FOOTBALL_PLAYER
    - 1 semester: FALL_2026 (ACTIVE)
    - 1 invitation_code: TEST-E2E-2026-AUTO (for Phase 1 registration)
    - Basic game_types (required for tournament creation)

    CRITICAL: NO USER REGISTRATION via seed - that must be tested via UI in Phase 1
    """

    print("\n" + "="*80)
    print("🧪 PHASE 0: Clean DB Setup")
    print("="*80)

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
    )

    # Step 1: Parse DB URL
    parts = db_url.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")

    db_user = user_pass[0]
    db_password = user_pass[1] if len(user_pass) > 1 else ""
    db_host = host_port[0]
    db_port = host_port[1] if len(host_port) > 1 else "5432"
    db_name = host_db[1].split("?")[0]

    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    env["DATABASE_URL"] = db_url

    print(f"📊 Database: {db_name}@{db_host}:{db_port}")

    # Step 2: Terminate connections
    print("\n🔌 Terminating active connections...")
    terminate_sql = f"""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
    """

    subprocess.run([
        "psql",
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-d", "postgres",
        "-c", terminate_sql
    ], env=env, capture_output=True)

    print("   ✅ Connections terminated")

    # Step 3: Drop DATABASE and recreate (cleanest approach)
    print("\n🗑️  Dropping and recreating database...")

    # Drop database
    subprocess.run([
        "psql",
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-d", "postgres",
        "-c", f"DROP DATABASE IF EXISTS {db_name};"
    ], env=env, capture_output=True)

    # Create database
    result = subprocess.run([
        "psql",
        "-h", db_host,
        "-p", db_port,
        "-U", db_user,
        "-d", "postgres",
        "-c", f"CREATE DATABASE {db_name};"
    ], env=env, capture_output=True, text=True)

    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"   ❌ Database creation failed: {result.stderr}")
        pytest.fail("Database creation failed")

    print("   ✅ Database recreated")

    # Step 4: Create tables via SQLAlchemy (faster, avoid migration conflicts)
    print("\n📦 Creating tables via SQLAlchemy...")

    import app.models  # Import models module (triggers model registration)
    from app.database import engine, Base

    try:
        Base.metadata.create_all(bind=engine)
        print("   ✅ Tables created via SQLAlchemy")
    except Exception as e:
        print(f"   ❌ Table creation failed: {e}")
        pytest.fail(f"Table creation failed: {e}")

    # Verify tables created
    table_count = count_tables()
    print(f"   ✅ Tables created: {table_count}")

    assert table_count > 10, f"Expected >10 tables, got {table_count}"

    # Step 5: Seed minimal system data
    print("\n🌱 Seeding minimal system data...")

    import psycopg2
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    try:
        # Seed: Admin user (id=1) — required for UI-driven invite code generation
        # Password: admin123
        cursor.execute("""
            INSERT INTO users (
                id, email, password_hash, name, role,
                is_active, onboarding_completed,
                payment_verified, credit_balance, credit_purchased,
                xp_balance, nda_accepted, parental_consent,
                created_at, updated_at
            )
            VALUES (
                1,
                'admin@lfa.com',
                '$2b$10$lFn5DF6TlPIA72O.X6W5JuPasU.YvvHBIMjfIddEWd8DRFDiE4tw6',
                'System Administrator',
                'ADMIN',
                true, true,
                true, 0, 0,
                0, false, false,
                NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active,
                onboarding_completed = EXCLUDED.onboarding_completed
        """)
        print("   ✅ Admin user seeded: admin@lfa.com / admin123")

        # Seed: Grandmaster user (id=2) — INSTRUCTOR role, all 21 licenses
        # Password: GrandMaster2026!
        cursor.execute("""
            INSERT INTO users (
                id, email, password_hash, name, role,
                is_active, onboarding_completed,
                payment_verified, credit_balance, credit_purchased,
                xp_balance, nda_accepted, parental_consent,
                date_of_birth, created_at, updated_at, created_by
            )
            VALUES (
                2,
                'grandmaster@lfa.com',
                '$2b$10$2MfzovB3gjQu9vndjIYkyubB30GXkLYWv54tAixvoJHmZpSVUOb4y',
                'Grand Master',
                'INSTRUCTOR',
                true, true,
                true, 5000, 0,
                0, false, false,
                '1985-01-01', NOW(), NOW(), 1
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active,
                onboarding_completed = EXCLUDED.onboarding_completed,
                credit_balance = EXCLUDED.credit_balance
        """)
        print("   ✅ Grandmaster user seeded: grandmaster@lfa.com / GrandMaster2026!")

        # Seed: Grandmaster licenses (21 db)
        # GANCUJU_PLAYER: 8 belt levels (NOT LFA_FOOTBALL_PLAYER!)
        # LFA_COACH: 8 levels
        # INTERNSHIP: 5 levels
        gm_licenses = (
            [("GANCUJU_PLAYER", lvl) for lvl in range(1, 9)] +
            [("LFA_COACH", lvl) for lvl in range(1, 9)] +
            [("INTERNSHIP", lvl) for lvl in range(1, 6)]
        )
        for spec_type, level in gm_licenses:
            cursor.execute("""
                INSERT INTO user_licenses (
                    user_id, specialization_type,
                    current_level, max_achieved_level,
                    is_active, payment_verified, onboarding_completed,
                    credit_balance, credit_purchased,
                    renewal_cost,
                    started_at, payment_verified_at,
                    created_at, updated_at
                )
                VALUES (
                    2, %s,
                    %s, %s,
                    true, true, true,
                    0, 0,
                    0,
                    NOW(), NOW(),
                    NOW(), NOW()
                )
                ON CONFLICT DO NOTHING
            """, (spec_type, level, level))
        print(f"   ✅ Grandmaster licenses seeded: {len(gm_licenses)} licenses")

        # Seed: Specialization (id is the specialization code)
        cursor.execute("""
            INSERT INTO specializations (id, is_active, created_at)
            VALUES ('LFA_FOOTBALL_PLAYER', true, NOW())
            ON CONFLICT (id) DO NOTHING
        """)
        print("   ✅ Specialization seeded: LFA_FOOTBALL_PLAYER")

        # Seed: Semester (ONGOING status, is_active for tournament creation)
        cursor.execute("""
            INSERT INTO semesters (
                code, name, specialization_type,
                start_date, end_date, status, is_active, enrollment_cost
            )
            VALUES (
                'FALL_2026', 'Fall 2026 Semester', 'LFA_FOOTBALL_PLAYER',
                '2026-09-01', '2026-12-31', 'ONGOING', true, 0
            )
            ON CONFLICT (code) DO NOTHING
        """)
        print("   ✅ Semester seeded: FALL_2026")

        # Seed: Invitation code (for Phase 1 registration)
        cursor.execute("""
            INSERT INTO invitation_codes (
                code, invited_name, invited_email, bonus_credits, is_used,
                created_by_admin_id, expires_at
            )
            VALUES (
                'TEST-E2E-2026-AUTO',
                'E2E Test User',
                'e2e.test@lfa.com',
                0,
                false,
                NULL,
                '2027-12-31'
            )
            ON CONFLICT (code) DO UPDATE SET
                is_used = false,
                expires_at = '2027-12-31'
        """)
        print("   ✅ Invitation code seeded: TEST-E2E-2026-AUTO")

        # Seed: Production game presets (full skill configs)
        cursor.execute("""
            INSERT INTO game_presets (code, name, description, game_config, is_active, is_recommended, is_locked)
            VALUES
            (
                'gan_footvolley',
                'GānFootvolley',
                'Advanced footvolley game testing multiple technical skills',
                '{
                    "version": "1.0",
                    "metadata": {"game_category": "general", "difficulty_level": "advanced",
                                 "recommended_player_count": {"min": 4, "max": 16}},
                    "skill_config": {
                        "skills_tested": ["ball_control","volleys","heading","positioning_off",
                                          "positioning_def","vision","reactions","composure",
                                          "consistency","tactical_awareness","acceleration",
                                          "agility","stamina","balance"],
                        "skill_weights": {"ball_control":0.5425,"volleys":0.0366,"heading":0.0366,
                                          "positioning_off":0.0366,"positioning_def":0.0366,
                                          "vision":0.0366,"reactions":0.0366,"composure":0.0366,
                                          "consistency":0.0366,"tactical_awareness":0.0366,
                                          "acceleration":0.0366,"agility":0.0329,"stamina":0.022,
                                          "balance":0.0366},
                        "skill_impact_on_matches": true
                    },
                    "format_config": {"HEAD_TO_HEAD": {"ranking_rules": {"primary": "points",
                        "tiebreakers": ["goal_difference","goals_for","user_id"],
                        "points_system": {"win":3,"draw":1,"loss":0}},
                        "match_simulation": {"score_ranges": {"win":{"loser_max":2,"winner_max":5},
                        "draw":{"max":2,"min":0}},"draw_probability":0.15,
                        "away_win_probability":0.4,"home_win_probability":0.45}}},
                    "simulation_config": {"player_selection": "auto",
                        "ranking_distribution": "NORMAL", "performance_variation": "MEDIUM"}
                }'::jsonb,
                true, true, false
            ),
            (
                'gan_foottennis',
                'GanFoottennis',
                'Racquet sports style game testing ball control, agility and reactions',
                '{
                    "version": "1.0",
                    "metadata": {"game_category": "racquet_sports", "difficulty_level": "advanced",
                                 "recommended_player_count": {"min": 4, "max": 12}},
                    "skill_config": {
                        "skills_tested": ["ball_control","agility","reactions"],
                        "skill_weights": {"ball_control":0.40,"agility":0.30,"reactions":0.30},
                        "skill_impact_on_matches": true
                    },
                    "format_config": {"HEAD_TO_HEAD": {"ranking_rules": {"primary": "points",
                        "tiebreakers": ["goal_difference","goals_for","user_id"],
                        "points_system": {"win":3,"draw":1,"loss":0}},
                        "match_simulation": {"score_ranges": {"win":{"loser_max":3,"winner_max":4},
                        "draw":{"max":1,"min":0}},"draw_probability":0.1,
                        "away_win_probability":0.4,"home_win_probability":0.5}}},
                    "simulation_config": {"player_selection": "auto",
                        "ranking_distribution": "NORMAL", "performance_variation": "LOW"}
                }'::jsonb,
                true, false, false
            ),
            (
                'stole_my_goal',
                'Stole My Goal',
                'Small-sided game testing finishing, marking and stamina',
                '{
                    "version": "1.0",
                    "metadata": {"game_category": "small_sided_games", "difficulty_level": "beginner",
                                 "recommended_player_count": {"min": 6, "max": 20}},
                    "skill_config": {
                        "skills_tested": ["finishing","marking","stamina"],
                        "skill_weights": {"finishing":0.40,"marking":0.35,"stamina":0.25},
                        "skill_impact_on_matches": true
                    },
                    "format_config": {"HEAD_TO_HEAD": {"ranking_rules": {"primary": "points",
                        "tiebreakers": ["goal_difference","goals_for","user_id"],
                        "points_system": {"win":3,"draw":1,"loss":0}},
                        "match_simulation": {"score_ranges": {"win":{"loser_max":5,"winner_max":6},
                        "draw":{"max":3,"min":0}},"draw_probability":0.25,
                        "away_win_probability":0.35,"home_win_probability":0.40}}},
                    "simulation_config": {"player_selection": "auto",
                        "ranking_distribution": "NORMAL", "performance_variation": "HIGH"}
                }'::jsonb,
                true, false, false
            )
            ON CONFLICT (code) DO UPDATE SET
                name        = EXCLUDED.name,
                description = EXCLUDED.description,
                game_config = EXCLUDED.game_config,
                is_active   = EXCLUDED.is_active,
                is_recommended = EXCLUDED.is_recommended
        """)
        print("   ✅ Game presets seeded: GānFootvolley (⭐), GanFoottennis, Stole My Goal")

        # Seed: Onboarding coupons for star users (Phase 3 prerequisite)
        # Loaded from tests/e2e/test_users.json → onboarding_coupons
        import json as _json
        _test_users_path = str(Path(__file__).parent.parent.parent / "tests" / "e2e" / "test_users.json")
        with open(_test_users_path) as _f:
            _test_users_data = _json.load(_f)

        for coupon in _test_users_data["onboarding_coupons"]:
            cursor.execute("""
                INSERT INTO coupons (
                    code, type, discount_value, description,
                    is_active, expires_at, max_uses, current_uses,
                    requires_purchase, requires_admin_approval,
                    created_at, updated_at
                )
                VALUES (
                    %s, 'BONUS_CREDITS', %s,
                    %s,
                    true, NULL, %s, 0,
                    false, false,
                    NOW(), NOW()
                )
                ON CONFLICT (code) DO UPDATE SET
                    current_uses = 0,
                    is_active = true
            """, (
                coupon["code"],
                coupon["credits"],
                f"E2E onboarding test: +{coupon['credits']} bonus credits",
                coupon["max_uses"]
            ))
        print(f"   ✅ Onboarding coupons seeded: {len(_test_users_data['onboarding_coupons'])} coupons")

        # Reset sequences so next INSERT gets id > max existing
        cursor.execute("""
            SELECT setval('users_id_seq',          (SELECT MAX(id) FROM users));
            SELECT setval('user_licenses_id_seq',  (SELECT MAX(id) FROM user_licenses));
        """)
        print("   ✅ Sequences reset (users, user_licenses)")

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"   ❌ Seed failed: {e}")
        pytest.fail(f"Seed failed: {e}")

    finally:
        cursor.close()
        conn.close()

    # Step 6: Verify seed data integrity
    print("\n🔍 Verifying seed data...")

    invitation = get_invitation_code("TEST-E2E-2026-AUTO")
    assert invitation is not None, "Invitation code not found"
    assert invitation["is_used"] == False, f"Invitation code already used: {invitation['is_used']}"
    assert invitation["invited_name"] == "E2E Test User"

    print(f"   ✅ Invitation code valid: {invitation['code']}")

    # Step 7: Save snapshot
    print("\n📸 Saving snapshot...")

    elapsed = snapshot_manager.save_snapshot("00_clean_db", verbose=False)

    print(f"   ✅ Snapshot saved: 00_clean_db ({elapsed:.2f}s)")

    # Final summary
    print("\n" + "="*80)
    print("✅ PHASE 0 COMPLETE")
    print("="*80)
    print(f"Database: {table_count} tables created")
    print("Seed data:")
    print("  - admin@lfa.com (ADMIN, password: admin123)")
    print("  - grandmaster@lfa.com (INSTRUCTOR, password: GrandMaster2026!, 21 licenses: 8 GANCUJU + 8 LFA_COACH + 5 INTERNSHIP)")
    print("  - 1 specialization: LFA_FOOTBALL_PLAYER")
    print("  - 1 semester: FALL_2026 (ONGOING)")
    print("  - 1 invitation_code: TEST-E2E-2026-AUTO")
    print("  - 1 game_preset: GANFOOTVOLLEY")
    print("  - 4 onboarding coupons: E2E-BONUS-50-USER1/2/3/4 (from tests/e2e/test_users.json)")
    print("\nSnapshot: tests_e2e/snapshots/00_clean_db.dump")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Allow running directly for quick testing
    import pytest
    pytest.main([__file__, "-v", "-s"])
