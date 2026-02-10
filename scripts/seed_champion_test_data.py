"""
seed_champion_test_data.py
==========================
Seeds the minimum data required for the Champion Badge Regression E2E test.

Creates (idempotently):
  - junior.intern@lfa.com  (STUDENT, LFA_FOOTBALL_PLAYER, onboarding complete)
  - A COMPLETED semester (code: E2E-TEST-CHAMPION)
  - A CHAMPION badge linked to the user + semester
    badge_metadata: {"placement": 1, "total_participants": 24}

Safe to run multiple times — uses INSERT ... ON CONFLICT DO NOTHING or
UPDATE for existing rows so re-runs are idempotent.

Usage:
  DATABASE_URL=postgresql://... python scripts/seed_champion_test_data.py
"""

import os
import sys
import bcrypt
from datetime import datetime, timezone, date
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/lfa_intern_system",
)

engine = create_engine(DATABASE_URL)

print("=" * 60)
print("SEED: Champion Badge E2E Test Data")
print("=" * 60)

with engine.begin() as conn:

    # ── 1. Upsert test user ────────────────────────────────────────────────
    print("\n1. Upserting test user: junior.intern@lfa.com ...")
    pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()

    conn.execute(text("""
        INSERT INTO users (
            name, email, password_hash, role, is_active,
            onboarding_completed, payment_verified,
            credit_balance, credit_purchased,
            nda_accepted, parental_consent,
            specialization,
            created_at, updated_at
        ) VALUES (
            'Junior Intern E2E', 'junior.intern@lfa.com', :pw_hash, 'STUDENT', true,
            true, true,
            0, 2500,
            true, true,
            'LFA_FOOTBALL_PLAYER',
            NOW(), NOW()
        )
        ON CONFLICT (email) DO UPDATE SET
            password_hash        = :pw_hash,
            onboarding_completed = true,
            payment_verified     = true,
            specialization       = 'LFA_FOOTBALL_PLAYER',
            is_active            = true,
            nda_accepted         = true,
            parental_consent     = true,
            updated_at           = NOW()
        RETURNING id
    """), {"pw_hash": pw_hash})

    user_row = conn.execute(text(
        "SELECT id FROM users WHERE email = 'junior.intern@lfa.com'"
    )).fetchone()
    user_id = user_row[0]
    print(f"   ✅ user_id = {user_id}")

    # ── 2. Upsert user_license ─────────────────────────────────────────────
    print("\n2. Upserting user_license ...")
    conn.execute(text("""
        INSERT INTO user_licenses (
            user_id, specialization_type, current_level, max_achieved_level,
            started_at, payment_verified, onboarding_completed, is_active,
            credit_balance, credit_purchased, renewal_cost,
            created_at, updated_at
        ) VALUES (
            :uid, 'LFA_FOOTBALL_PLAYER', 1, 1,
            NOW(), true, true, true,
            0, 0, 0,
            NOW(), NOW()
        )
        ON CONFLICT DO NOTHING
    """), {"uid": user_id})

    lic_row = conn.execute(text("""
        SELECT id FROM user_licenses
        WHERE user_id = :uid AND specialization_type = 'LFA_FOOTBALL_PLAYER'
    """), {"uid": user_id}).fetchone()

    if lic_row:
        conn.execute(text("""
            UPDATE user_licenses SET
                onboarding_completed = true,
                payment_verified     = true,
                is_active            = true,
                updated_at           = NOW()
            WHERE id = :lid
        """), {"lid": lic_row[0]})
    print(f"   ✅ license ok")

    # ── 3. Upsert semester ─────────────────────────────────────────────────
    print("\n3. Upserting semester: E2E-TEST-CHAMPION ...")
    conn.execute(text("""
        INSERT INTO semesters (
            code, name, start_date, end_date, status,
            enrollment_cost, is_active,
            specialization_type,
            created_at, updated_at
        ) VALUES (
            'E2E-TEST-CHAMPION', 'E2E Champion Test Semester',
            '2024-01-01', '2024-06-30', 'COMPLETED',
            0, false,
            'LFA_FOOTBALL_PLAYER',
            NOW(), NOW()
        )
        ON CONFLICT (code) DO NOTHING
    """))

    sem_row = conn.execute(text(
        "SELECT id FROM semesters WHERE code = 'E2E-TEST-CHAMPION'"
    )).fetchone()
    semester_id = sem_row[0]
    print(f"   ✅ semester_id = {semester_id}")

    # ── 4. Upsert CHAMPION badge ───────────────────────────────────────────
    print("\n4. Upserting CHAMPION badge ...")
    existing = conn.execute(text("""
        SELECT id FROM tournament_badges
        WHERE user_id = :uid AND badge_type = 'CHAMPION'
          AND semester_id = :sid
    """), {"uid": user_id, "sid": semester_id}).fetchone()

    if existing:
        conn.execute(text("""
            UPDATE tournament_badges SET
                badge_metadata = '{"placement": 1, "total_participants": 24,
                                   "tournament_name": "E2E Test Championship"}'::jsonb,
                rarity         = 'LEGENDARY'
            WHERE id = :bid
        """), {"bid": existing[0]})
        print(f"   ✅ updated existing badge id={existing[0]}")
    else:
        conn.execute(text("""
            INSERT INTO tournament_badges (
                user_id, semester_id, badge_type, badge_category,
                title, description, icon, rarity,
                badge_metadata, earned_at
            ) VALUES (
                :uid, :sid, 'CHAMPION', 'PLACEMENT',
                '🥇 Champion', 'First place finish', '🥇', 'LEGENDARY',
                '{"placement": 1, "total_participants": 24,
                  "tournament_name": "E2E Test Championship"}'::jsonb,
                NOW()
            )
        """), {"uid": user_id, "sid": semester_id})
        print(f"   ✅ CHAMPION badge created")

print("\n" + "=" * 60)
print("✅ SEED COMPLETE")
print(f"   user:     junior.intern@lfa.com  (id={user_id})")
print(f"   password: password123")
print(f"   badge:    CHAMPION / LEGENDARY / placement=1 / total=24")
print("=" * 60)
