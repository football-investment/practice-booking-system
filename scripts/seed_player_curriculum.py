"""
Seed PLAYER Curriculum Data
Run with: python scripts/seed_player_curriculum.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from sqlalchemy import text

def seed_player_curriculum():
    db = SessionLocal()

    try:
        print("🌱 Seeding PLAYER curriculum...")

        # 1. INSERT CURRICULUM TRACK
        db.execute(text("""
            INSERT INTO curriculum_tracks (specialization_id, name, description, total_lessons, total_hours, is_active)
            VALUES ('PLAYER', 'GanCuju Player Development Program',
                    'Teljes 4 leckés program: Ganball alapok, bőrérzékelés, challenge rendszer, edzésvezetés',
                    4, 12, true)
            RETURNING id
        """))
        track_result = db.execute(text("SELECT id FROM curriculum_tracks WHERE specialization_id = 'PLAYER'"))
        track_id = track_result.scalar()
        print(f"✅ Curriculum track created: ID={track_id}")

        # 2. LESSON 1
        db.execute(text(f"""
            INSERT INTO lessons (curriculum_track_id, level_id, order_number, title, description, estimated_hours, xp_reward, is_mandatory)
            VALUES ({track_id}, 1, 1, 'Ganball™️ Eszköz Alapjai',
                    'Ismerkedés a Ganball eszközzel: összeszerelés, biztonsági protokoll, eszköz variációk',
                    3, 3000, true)
        """))
        lesson1_result = db.execute(text(f"SELECT id FROM lessons WHERE curriculum_track_id = {track_id} AND order_number = 1"))
        lesson1_id = lesson1_result.scalar()
        print(f"✅ Lesson 1 created: ID={lesson1_id}")

        # LESSON 1 MODULES (5 modules)
        modules_l1 = [
            (1, 'Ganball™️ Történet és Filozófia', 'THEORY', '<h2>Mi a Ganball™️?</h2><p>A Ganball™️ egy innovatív labdarúgó fejlesztő eszköz.</p>', 30, 500),
            (2, 'Eszköz Összeszerelése - Video', 'VIDEO', '<h2>Video útmutató</h2>', 45, 750),
            (3, 'Biztonsági Protokoll', 'THEORY', '<h2>Biztonsági Szabályok</h2>', 30, 500),
            (4, 'Összeszerelési Gyakorlat', 'EXERCISE', '<h2>Gyakorlati feladat</h2>', 60, 1000),
            (5, 'Lecke 1 Záró Kvíz', 'QUIZ', '<h2>Záró teszt</h2>', 15, 250)
        ]

        for order, title, mod_type, content, minutes, xp in modules_l1:
            db.execute(text(f"""
                INSERT INTO lesson_modules (lesson_id, order_number, title, module_type, content, estimated_minutes, xp_reward, is_mandatory)
                VALUES ({lesson1_id}, {order}, :title, :mod_type, :content, {minutes}, {xp}, true)
            """), {"title": title, "mod_type": mod_type, "content": content})
        print(f"✅ Lesson 1: {len(modules_l1)} modules created")

        # 3. LESSON 2
        db.execute(text(f"""
            INSERT INTO lessons (curriculum_track_id, level_id, order_number, title, description, estimated_hours, xp_reward, is_mandatory)
            VALUES ({track_id}, 2, 2, 'Bőrérzékelés Fejlesztés',
                    'Bőr receptorok fejlesztése, érzékelési technikák',
                    3, 3500, true)
        """))
        lesson2_result = db.execute(text(f"SELECT id FROM lessons WHERE curriculum_track_id = {track_id} AND order_number = 2"))
        lesson2_id = lesson2_result.scalar()
        print(f"✅ Lesson 2 created: ID={lesson2_id}")

        modules_l2 = [
            (1, 'Bőr Receptorok Anatómiája', 'THEORY', '<h2>Hogyan működik a tapintás?</h2>', 30, 600),
            (2, 'Érzékelési Technikák Video', 'VIDEO', '<h2>10 Technika</h2>', 45, 800),
            (3, 'Fejlesztési Gyakorlatok', 'PRACTICE', '<h2>10 Gyakorlat</h2>', 90, 1500),
            (4, 'Lecke 2 Záró Kvíz', 'QUIZ', '<h2>Teszt</h2>', 15, 600)
        ]

        for order, title, mod_type, content, minutes, xp in modules_l2:
            db.execute(text(f"""
                INSERT INTO lesson_modules (lesson_id, order_number, title, module_type, content, estimated_minutes, xp_reward, is_mandatory)
                VALUES ({lesson2_id}, {order}, :title, :mod_type, :content, {minutes}, {xp}, true)
            """), {"title": title, "mod_type": mod_type, "content": content})
        print(f"✅ Lesson 2: {len(modules_l2)} modules created")

        # 4. LESSON 3 (Challenge System)
        db.execute(text(f"""
            INSERT INTO lessons (curriculum_track_id, level_id, order_number, title, description, estimated_hours, xp_reward, is_mandatory)
            VALUES ({track_id}, 3, 3, 'Challenge Rendszer Mesteri Szint',
                    'Mind a 9 GanCuju challenge típus elsajátítása',
                    3, 4000, true)
        """))
        lesson3_result = db.execute(text(f"SELECT id FROM lessons WHERE curriculum_track_id = {track_id} AND order_number = 3"))
        lesson3_id = lesson3_result.scalar()
        print(f"✅ Lesson 3 created: ID={lesson3_id}")

        modules_l3 = [
            (1, 'Challenge Filozófia', 'THEORY', '<h2>Gamifikáció</h2>', 20, 400),
            (2, 'First Touch Challenge', 'PRACTICE', '<h2>1. Challenge</h2>', 20, 500),
            (3, 'Crossbar Challenge', 'PRACTICE', '<h2>2. Challenge</h2>', 20, 500),
            (4, 'Shooting Challenge', 'PRACTICE', '<h2>3. Challenge</h2>', 20, 500),
            (5, 'Multiple Touch Challenge', 'PRACTICE', '<h2>4. Challenge</h2>', 20, 500),
            (6, 'Touch and Pass Challenge', 'PRACTICE', '<h2>5. Challenge</h2>', 20, 500),
            (7, 'Juggling Challenge', 'PRACTICE', '<h2>6. Challenge</h2>', 20, 500),
            (8, 'Free Kick Challenge', 'PRACTICE', '<h2>7. Challenge</h2>', 20, 500),
            (9, 'Passing Challenge', 'PRACTICE', '<h2>8. Challenge</h2>', 20, 500),
            (10, 'Curve Challenge', 'PRACTICE', '<h2>9. Challenge</h2>', 20, 500),
            (11, 'Lecke 3 Záró Kvíz', 'QUIZ', '<h2>Teszt</h2>', 15, 600)
        ]

        for order, title, mod_type, content, minutes, xp in modules_l3:
            db.execute(text(f"""
                INSERT INTO lesson_modules (lesson_id, order_number, title, module_type, content, estimated_minutes, xp_reward, is_mandatory)
                VALUES ({lesson3_id}, {order}, :title, :mod_type, :content, {minutes}, {xp}, true)
            """), {"title": title, "mod_type": mod_type, "content": content})
        print(f"✅ Lesson 3: {len(modules_l3)} modules created")

        # 5. LESSON 4
        db.execute(text(f"""
            INSERT INTO lessons (curriculum_track_id, level_id, order_number, title, description, estimated_hours, xp_reward, is_mandatory)
            VALUES ({track_id}, 4, 4, 'Ganball™️ Edzésvezetés',
                    'Edzéstervezés, hibajavítás, technikai útmutatás',
                    3, 4500, true)
        """))
        lesson4_result = db.execute(text(f"SELECT id FROM lessons WHERE curriculum_track_id = {track_id} AND order_number = 4"))
        lesson4_id = lesson4_result.scalar()
        print(f"✅ Lesson 4 created: ID={lesson4_id}")

        modules_l4 = [
            (1, 'Edzéstervezés Alapok', 'THEORY', '<h2>Hatékony edzés</h2>', 45, 800),
            (2, 'Hibajavítási Technikák Video', 'VIDEO', '<h2>3 lépéses módszer</h2>', 45, 900),
            (3, 'Vezetési Gyakorlat', 'PRACTICE', '<h2>Vezess edzést</h2>', 90, 2000),
            (4, 'Lecke 4 Záró Kvíz', 'QUIZ', '<h2>Teszt</h2>', 15, 800)
        ]

        for order, title, mod_type, content, minutes, xp in modules_l4:
            db.execute(text(f"""
                INSERT INTO lesson_modules (lesson_id, order_number, title, module_type, content, estimated_minutes, xp_reward, is_mandatory)
                VALUES ({lesson4_id}, {order}, :title, :mod_type, :content, {minutes}, {xp}, true)
            """), {"title": title, "mod_type": mod_type, "content": content})
        print(f"✅ Lesson 4: {len(modules_l4)} modules created")

        db.commit()

        # Summary
        total_modules = len(modules_l1) + len(modules_l2) + len(modules_l3) + len(modules_l4)
        print(f"\n🎉 PLAYER Curriculum Seeded Successfully!")
        print(f"   📚 1 curriculum track")
        print(f"   📖 4 lessons")
        print(f"   📝 {total_modules} modules")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_player_curriculum()
