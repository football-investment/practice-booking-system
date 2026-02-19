"""
Seed INTERNSHIP Curriculum Data
Run with: python scripts/seed_internship_curriculum.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from sqlalchemy import text

def seed_internship_curriculum():
    db = SessionLocal()

    try:
        print("🌱 Seeding INTERNSHIP curriculum...")

        # 1. INSERT CURRICULUM TRACK
        db.execute(text("""
            INSERT INTO curriculum_tracks (specialization_id, name, description, total_lessons, total_hours, is_active)
            VALUES ('INTERNSHIP', 'Startup Spirit Internship Program',
                    'Real-world office experience from Explorer to Leader level',
                    3, 330, true)
        """))
        track_result = db.execute(text("SELECT id FROM curriculum_tracks WHERE specialization_id = 'INTERNSHIP'"))
        track_id = track_result.scalar()
        print(f"✅ Curriculum track created: ID={track_id}")

        # Define all 3 internship levels
        internship_levels = [
            # Level 1: Startup Explorer
            {
                'level': 1,
                'order': 1,
                'title': 'Startup Explorer - Office Operations & LFA Ecosystem',
                'desc': 'Irodai alapok, LFA ökoszisztéma megismerése, startup kultúra, csapatmunka',
                'hours': 80,
                'xp': 10000,
                'modules': [
                    (1, 'LFA Ecosystem Orientation', 'THEORY', 'LFA projektek, víziók, értékek megismerése', 240, 1200),
                    (2, 'Office Systems & Tools', 'THEORY', 'Email, CRM, Project Management eszközök', 300, 1500),
                    (3, 'Startup Mindset', 'THEORY', 'Agilis gondolkodás, MVP, lean startup alapok', 360, 1800),
                    (4, 'Team Collaboration', 'PRACTICE', 'Csapatmunka, kommunikáció, konfliktuskezelés', 480, 2400),
                    (5, 'Department Shadowing', 'PRACTICE', '4 hét különböző részlegeken: marketing, sales, operations, product', 1920, 2500),
                    (6, 'Explorer Final Project', 'EXERCISE', 'Kis kutatási projekt prezentációval', 480, 600)
                ]
            },

            # Level 2: Growth Hacker
            {
                'level': 2,
                'order': 2,
                'title': 'Growth Hacker - Department Projects & Client Relations',
                'desc': 'Growth marketing, data-driven döntések, MVP tesztelés, ügyfélkapcsolatok',
                'hours': 99.99,
                'xp': 18000,
                'modules': [
                    (1, 'Growth Marketing Fundamentals', 'THEORY', 'AARRR framework, growth hacking technikák', 480, 2000),
                    (2, 'Data-Driven Decisions', 'THEORY', 'Analytics, KPIs, A/B tesztelés, reporting', 540, 2200),
                    (3, 'MVP Testing & Validation', 'THEORY', 'Customer development, lean validation', 420, 1800),
                    (4, 'Client Communication', 'PRACTICE', 'Email, meeting, prezentáció ügyfélnek', 600, 2500),
                    (5, 'Department Project Work', 'PRACTICE', '8 hét valós projekt egy részlegen', 3840, 5000),
                    (6, 'Event Support', 'PRACTICE', 'Rendezvényszervezés, networking események', 720, 2000),
                    (7, 'Growth Hacker Final Project', 'EXERCISE', 'Growth campaign terv + végrehajtás', 600, 2500)
                ]
            },

            # Level 3: Startup Leader
            {
                'level': 3,
                'order': 3,
                'title': 'Startup Leader - Leadership & Independent Projects',
                'desc': 'Vezetői képességek, független projektek, hálózatépítés, karrierfejlesztés',
                'hours': 99.99,
                'xp': 28000,
                'modules': [
                    (1, 'Entrepreneurial Leadership', 'THEORY', 'Vezetői stílusok, döntéshozatal, delegálás', 600, 2500),
                    (2, 'Global Expansion Strategies', 'THEORY', 'Nemzetközi piacra lépés, skalázás', 540, 2300),
                    (3, 'Fundraising & Investor Relations', 'THEORY', 'Pitch deck, fundraising, befektetői kommunikáció', 480, 2200),
                    (4, 'Exit Strategies', 'THEORY', 'Acquisition, IPO, stratégiai partnerség', 360, 1800),
                    (5, 'Independent Project Leadership', 'PRACTICE', 'Saját projekt vezetése elejétől a végéig', 4800, 8000),
                    (6, 'Network Building', 'PRACTICE', 'Networking események, mentorálás, LinkedIn stratégia', 720, 2000),
                    (7, 'Career Development', 'INTERACTIVE', 'CV, LinkedIn, interview prep, career coaching', 600, 2200),
                    (8, 'Startup Leader Capstone', 'EXERCISE', 'Komplex startup business plan + pitch', 720, 4000),
                    (9, 'Final Evaluation & Certification', 'QUIZ', 'Startup Leader komprehenzív teszt', 180, 3000)
                ]
            }
        ]

        # Insert lessons and modules
        lesson_count = 0
        module_count = 0

        for lesson_data in internship_levels:
            # Insert lesson
            db.execute(text(f"""
                INSERT INTO lessons (curriculum_track_id, level_id, order_number, title, description, estimated_hours, xp_reward, is_mandatory)
                VALUES ({track_id}, {lesson_data['level']}, {lesson_data['order']}, :title, :desc, {lesson_data['hours']}, {lesson_data['xp']}, true)
            """), {"title": lesson_data['title'], "desc": lesson_data['desc']})

            lesson_result = db.execute(text(f"SELECT id FROM lessons WHERE curriculum_track_id = {track_id} AND order_number = {lesson_data['order']}"))
            lesson_id = lesson_result.scalar()
            lesson_count += 1
            print(f"✅ Lesson {lesson_data['order']} (Level {lesson_data['level']}): {lesson_data['title'][:60]}...")

            # Insert modules
            for order, title, mod_type, content, minutes, xp in lesson_data['modules']:
                db.execute(text(f"""
                    INSERT INTO lesson_modules (lesson_id, order_number, title, module_type, content, estimated_minutes, xp_reward, is_mandatory)
                    VALUES ({lesson_id}, {order}, :title, :mod_type, :content, {minutes}, {xp}, true)
                """), {"title": title, "mod_type": mod_type, "content": content})
                module_count += 1

        db.commit()

        print(f"\n🎉 INTERNSHIP Curriculum Seeded Successfully!")
        print(f"   📚 1 curriculum track")
        print(f"   📖 {lesson_count} lessons (3 levels)")
        print(f"   📝 {module_count} modules")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_internship_curriculum()
