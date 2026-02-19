"""
Quick Tournament Regeneration Script

Creates Tournament ID 14 with:
- 8 players enrolled
- 2 groups (A, B) with 4 players each
- Sessions generated with explicit participant_user_ids
- Tournament status: IN_PROGRESS (ready for match recording)
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def regenerate_tournament():
    """Regenerate Tournament ID 14 from scratch"""
    db = SessionLocal()

    try:
        print("🚀 Starting tournament regeneration...")

        # ============================================================================
        # 1. CREATE TOURNAMENT
        # ============================================================================
        print("\n1️⃣ Creating tournament...")

        db.execute(text("""
            INSERT INTO semesters (
                id,
                name,
                specialization_type,
                start_date,
                end_date,
                enrollment_start,
                enrollment_end,
                max_students,
                is_active,
                tournament_status,
                location_venue,
                tournament_type_id
            ) VALUES (
                14,
                '🇭🇺 HU - "Neymar''s - GānFootvolley PUMA Cup™️ " - BDPST',
                'LFA_PLAYER',
                '2026-01-23',
                '2026-01-23',
                '2026-01-15',
                '2026-01-22',
                8,
                true,
                'IN_PROGRESS',
                'TBD',
                3
            )
        """))

        print("   ✅ Tournament created (ID: 14)")

        # ============================================================================
        # 2. ENROLL 8 PLAYERS
        # ============================================================================
        print("\n2️⃣ Enrolling 8 players...")

        player_ids = [13, 14, 15, 16, 4, 5, 6, 7]

        for user_id in player_ids:
            db.execute(text("""
                INSERT INTO semester_enrollments (
                    semester_id,
                    user_id,
                    is_active,
                    request_status,
                    enrollment_date
                ) VALUES (
                    14,
                    :user_id,
                    true,
                    'APPROVED',
                    NOW()
                )
            """), {"user_id": user_id})

        print(f"   ✅ {len(player_ids)} players enrolled")

        # ============================================================================
        # 3. GENERATE SESSIONS WITH EXPLICIT PARTICIPANT_USER_IDS
        # ============================================================================
        print("\n3️⃣ Generating sessions with explicit participants...")

        # Group assignments
        group_a = [13, 15, 4, 6]  # Kylian, Cole, Tamás, Péter Barna
        group_b = [14, 16, 5, 7]  # Lamine, Martin, Péter Nagy, Tibor

        session_id = 47
        current_time = datetime(2026, 1, 23, 0, 0, 0)

        sessions = []

        # Group A - 3 rounds
        for round_num in range(1, 4):
            sessions.append({
                'id': session_id,
                'title': f'🇭🇺 HU - "Neymar''s - GānFootvolley PUMA Cup™️ " - BDPST - Group A - Round {round_num}',
                'description': f'Group A ranking round (4 players)',
                'date_start': current_time,
                'date_end': current_time + timedelta(minutes=90),
                'tournament_phase': 'Group Stage',
                'tournament_round': round_num,
                'group_identifier': 'A',
                'ranking_mode': 'GROUP_ISOLATED',
                'expected_participants': 4,
                'participant_filter': 'group_membership',
                'match_format': 'INDIVIDUAL_RANKING',
                'scoring_type': 'PLACEMENT',
                'participant_user_ids': group_a
            })
            session_id += 1
            current_time += timedelta(minutes=105)

        # Group B - 3 rounds
        for round_num in range(1, 4):
            sessions.append({
                'id': session_id,
                'title': f'🇭🇺 HU - "Neymar''s - GānFootvolley PUMA Cup™️ " - BDPST - Group B - Round {round_num}',
                'description': f'Group B ranking round (4 players)',
                'date_start': current_time,
                'date_end': current_time + timedelta(minutes=90),
                'tournament_phase': 'Group Stage',
                'tournament_round': round_num,
                'group_identifier': 'B',
                'ranking_mode': 'GROUP_ISOLATED',
                'expected_participants': 4,
                'participant_filter': 'group_membership',
                'match_format': 'INDIVIDUAL_RANKING',
                'scoring_type': 'PLACEMENT',
                'participant_user_ids': group_b
            })
            session_id += 1
            current_time += timedelta(minutes=105)

        # Knockout - Semi-finals (2 matches)
        for match_num in range(1, 3):
            sessions.append({
                'id': session_id,
                'title': f'🇭🇺 HU - "Neymar''s - GānFootvolley PUMA Cup™️ " - BDPST - Round of 4 - Match {match_num}',
                'description': 'Knockout stage match - top 4 qualifiers',
                'date_start': current_time,
                'date_end': current_time + timedelta(minutes=90),
                'tournament_phase': 'Knockout Stage',
                'tournament_round': 1,
                'group_identifier': None,
                'ranking_mode': 'QUALIFIED_ONLY',
                'expected_participants': 4,
                'participant_filter': 'top_group_qualifiers',
                'match_format': 'INDIVIDUAL_RANKING',
                'scoring_type': 'PLACEMENT',
                'participant_user_ids': None  # Will be populated after group stage
            })
            session_id += 1
            current_time += timedelta(minutes=105)

        # Final
        sessions.append({
            'id': session_id,
            'title': f'🇭🇺 HU - "Neymar''s - GānFootvolley PUMA Cup™️ " - BDPST - Round of 2 - Match 1',
            'description': 'Final match',
            'date_start': current_time,
            'date_end': current_time + timedelta(minutes=90),
            'tournament_phase': 'Knockout Stage',
            'tournament_round': 2,
            'group_identifier': None,
            'ranking_mode': 'QUALIFIED_ONLY',
            'expected_participants': 2,
            'participant_filter': 'top_group_qualifiers',
            'match_format': 'INDIVIDUAL_RANKING',
            'scoring_type': 'PLACEMENT',
            'participant_user_ids': None  # Will be populated after semi-finals
        })

        # Insert all sessions
        for session in sessions:
            participant_ids_str = None
            if session['participant_user_ids']:
                participant_ids_str = '{' + ','.join(map(str, session['participant_user_ids'])) + '}'

            db.execute(text("""
                INSERT INTO sessions (
                    id,
                    title,
                    description,
                    date_start,
                    date_end,
                    semester_id,
                    session_type,
                    capacity,
                    location,
                    is_tournament_game,
                    tournament_phase,
                    tournament_round,
                    group_identifier,
                    ranking_mode,
                    expected_participants,
                    participant_filter,
                    match_format,
                    scoring_type,
                    participant_user_ids
                ) VALUES (
                    :id,
                    :title,
                    :description,
                    :date_start,
                    :date_end,
                    14,
                    'on_site',
                    8,
                    'TBD',
                    true,
                    :tournament_phase,
                    :tournament_round,
                    :group_identifier,
                    :ranking_mode,
                    :expected_participants,
                    :participant_filter,
                    :match_format,
                    :scoring_type,
                    :participant_user_ids::integer[]
                )
            """), {
                'id': session['id'],
                'title': session['title'],
                'description': session['description'],
                'date_start': session['date_start'],
                'date_end': session['date_end'],
                'tournament_phase': session['tournament_phase'],
                'tournament_round': session['tournament_round'],
                'group_identifier': session['group_identifier'],
                'ranking_mode': session['ranking_mode'],
                'expected_participants': session['expected_participants'],
                'participant_filter': session['participant_filter'],
                'match_format': session['match_format'],
                'scoring_type': session['scoring_type'],
                'participant_user_ids': participant_ids_str
            })

        print(f"   ✅ {len(sessions)} sessions created")
        print(f"      - Group A: 3 sessions (participants: {group_a})")
        print(f"      - Group B: 3 sessions (participants: {group_b})")
        print(f"      - Knockout: 3 sessions (participants: NULL - awaiting group results)")

        # ============================================================================
        # 4. CREATE BOOKINGS FOR ALL SESSIONS
        # ============================================================================
        print("\n4️⃣ Creating bookings...")

        booking_id = 217
        for session in sessions:
            if session['participant_user_ids']:
                for user_id in session['participant_user_ids']:
                    db.execute(text("""
                        INSERT INTO bookings (
                            id,
                            session_id,
                            user_id,
                            status
                        ) VALUES (
                            :booking_id,
                            :session_id,
                            :user_id,
                            'CONFIRMED'
                        )
                    """), {
                        'booking_id': booking_id,
                        'session_id': session['id'],
                        'user_id': user_id
                    })
                    booking_id += 1

        print(f"   ✅ Bookings created for all group stage matches")

        # ============================================================================
        # 5. MARK TOURNAMENT AS SESSIONS_GENERATED
        # ============================================================================
        print("\n5️⃣ Updating tournament status...")

        db.execute(text("""
            UPDATE semesters
            SET
                sessions_generated = true,
                sessions_generated_at = NOW()
            WHERE id = 14
        """))

        print("   ✅ Tournament status: IN_PROGRESS, sessions generated")

        # Commit all changes
        db.commit()

        print("\n✅ Tournament 14 regenerated successfully!")
        print("\n📊 Summary:")
        print("   - Tournament ID: 14")
        print("   - Players: 8 (2 groups of 4)")
        print("   - Sessions: 9 (6 group + 3 knockout)")
        print("   - Status: IN_PROGRESS")
        print("   - Ready for: Match attendance & results recording")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    regenerate_tournament()
