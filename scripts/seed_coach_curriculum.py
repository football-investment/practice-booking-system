"""
Seed COACH Curriculum Data
Run with: python scripts/seed_coach_curriculum.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from sqlalchemy import text

def seed_coach_curriculum():
    db = SessionLocal()

    try:
        print("🌱 Seeding COACH curriculum...")

        # 1. INSERT CURRICULUM TRACK
        db.execute(text("""
            INSERT INTO curriculum_tracks (specialization_id, name, description, total_lessons, total_hours, is_active)
            VALUES ('COACH', 'LFA Coaching License Program',
                    '8-level professional coaching certification from Pre Football to PRO level',
                    8, 150, true)
        """))
        track_result = db.execute(text("SELECT id FROM curriculum_tracks WHERE specialization_id = 'COACH'"))
        track_id = track_result.scalar()
        print(f"✅ Curriculum track created: ID={track_id}")

        # Define all 8 coach levels with their lessons
        coach_levels = [
            # Level 1: Pre Football Asszisztens
            {
                'level': 1,
                'order': 1,
                'title': 'PRE Football Asszisztens - Elméleti Alapok',
                'desc': 'Ganball alapok, edzésvezetési alapelvek, Cuju történet, biztonsági protokollok, kommunikáció',
                'hours': 30,
                'xp': 5000,
                'modules': [
                    (1, 'Ganball™️ Alapismeretek', 'THEORY', 'Mi a Ganball? Eszköz használat, módszertan', 360, 800),
                    (2, 'Edzésvezetési Alapelvek', 'THEORY', 'Hogyan vezess edzést hatékonyan?', 420, 900),
                    (3, 'Cuju Történet és Szabályrendszer', 'THEORY', '4000 év története és modern adaptáció', 300, 700),
                    (4, 'Biztonsági Protokollok', 'THEORY', 'Balesetmegelőzés, elsősegély alapok', 180, 500),
                    (5, 'Kommunikációs Alapok', 'THEORY', 'Hatékony kommunikáció gyerekekkel és szülőkkel', 240, 600),
                    (6, 'Elméleti Záróvizsga', 'QUIZ', 'PRE Football Asszisztens Elméleti Teszt', 60, 1500)
                ]
            },
            {
                'level': 1,
                'order': 2,
                'title': 'PRE Football Asszisztens - Gyakorlati Képzés',
                'desc': 'Eszközhasználat, alapgyakorlatok vezetése, challenge rendszer, bemelegítés, asszisztensi feladatok',
                'hours': 50,
                'xp': 7000,
                'modules': [
                    (1, 'Eszközhasználat Gyakorlat', 'PRACTICE', 'Ganball összeszerelés, beállítás, karbantartás', 300, 1000),
                    (2, 'Alapgyakorlatok Vezetése', 'PRACTICE', '10 alapgyakorlat gyakorlati vezetése', 600, 1500),
                    (3, 'Challenge Rendszer Alkalmazás', 'PRACTICE', '9 challenge típus vezetése', 480, 1200),
                    (4, 'Bemelegítés Vezetése', 'PRACTICE', 'Hatékony bemelegítő rutinok', 240, 800),
                    (5, 'Asszisztensi Feladatok', 'PRACTICE', 'Segédedző szerepkör gyakorlat', 360, 1000),
                    (6, 'Gyakorlati Záróvizsga', 'EXERCISE', 'Vezess egy komplett edzést!', 120, 2500)
                ]
            },
            {
                'level': 1,
                'order': 3,
                'title': 'PRE Football Asszisztens - Mentorált Gyakorlat',
                'desc': '3 hónapos mentorált gyakorlati időszak valós környezetben',
                'hours': 70,
                'xp': 3000,
                'modules': [
                    (1, 'Mentorálási Program Bevezetés', 'THEORY', 'Mit vársz el a mentorálási időszaktól?', 60, 300),
                    (2, 'Heti Gyakorlati Feladatok', 'PRACTICE', '12 hét strukturált gyakorlat', 3600, 2000),
                    (3, 'Mentori Visszajelzések', 'INTERACTIVE', 'Folyamatos fejlesztés mentorral', 480, 400),
                    (4, 'Végső Értékelés', 'EXERCISE', 'Kompetencia mérés és licensz megszerzés', 60, 300)
                ]
            },

            # Level 2: Pre Football Vezetőedző
            {
                'level': 2,
                'order': 4,
                'title': 'PRE Football Vezetőedző - Haladó Képzés',
                'desc': 'Edzéstervezés, periodizáció, csapatvezetés, 4-7 éves korosztály specialitásai',
                'hours': 60,
                'xp': 8000,
                'modules': [
                    (1, 'Edzéstervezés Mesterkurzus', 'THEORY', 'Éves tervezés, periodizáció, célkitűzések', 600, 1500),
                    (2, 'Korosztályos Módszertan', 'THEORY', '4-7 éves gyerekek fejlesztési specialitásai', 480, 1200),
                    (3, 'Csapatvezetési Alapok', 'THEORY', 'Csoportdinamika, motiváció, fegyelmezés', 420, 1100),
                    (4, 'Gyakorlati Vezetőedzői Feladatok', 'PRACTICE', 'Komplett edzéstervezés és vezetés', 900, 2500),
                    (5, 'Vezetőedzői Záróvizsga', 'QUIZ', 'PRE Football Vezetőedző Teszt', 90, 1700)
                ]
            },

            # Level 3: Youth Football Asszisztens
            {
                'level': 3,
                'order': 5,
                'title': 'Youth Football Asszisztens - Ifjúsági Korosztály',
                'desc': 'U8-U12 korosztályos módszertan, tehetségazonosítás, fejlesztési utak',
                'hours': 55,
                'xp': 10000,
                'modules': [
                    (1, 'U8-U12 Fejlődési Szakaszok', 'THEORY', 'Fizikai, mentális, érzelmi fejlődés', 480, 1200),
                    (2, 'Tehetségazonosítás Alapjai', 'THEORY', 'Hogyan ismerd fel a tehetséget?', 360, 900),
                    (3, 'Ifjúsági Gyakorlatok', 'PRACTICE', 'Korosztály-specifikus gyakorlatok', 1200, 3000),
                    (4, 'Youth Asszisztens Záróvizsga', 'QUIZ', 'Ifjúsági Edző Teszt', 90, 1900)
                ]
            },

            # Level 4: Youth Football Vezetőedző
            {
                'level': 4,
                'order': 6,
                'title': 'Youth Football Vezetőedző - Program Vezetés',
                'desc': 'Ifjúsági program tervezése és vezetése, U8-U16 komplex fejlesztés',
                'hours': 65,
                'xp': 12000,
                'modules': [
                    (1, 'Ifjúsági Program Tervezés', 'THEORY', 'Éves program, szezonális tervezés', 600, 1500),
                    (2, 'Komplex Fejlesztési Módszertan', 'THEORY', 'Technikai, taktikai, fizikai, mentális', 720, 1800),
                    (3, 'Vezetői Gyakorlat', 'PRACTICE', 'Teljes ifjúsági program vezetése', 1500, 4000),
                    (4, 'Youth Vezetőedző Záróvizsga', 'QUIZ', 'Komprehenzív teszt', 120, 2700)
                ]
            },

            # Level 5: Amateur Football Asszisztens
            {
                'level': 5,
                'order': 7,
                'title': 'Amateur Football Asszisztens - Felnőtt Futball',
                'desc': 'Amatőr szint, taktikai elemzés, játékosmenedzsment',
                'hours': 60,
                'xp': 15000,
                'modules': [
                    (1, 'Felnőtt Futball Alapok', 'THEORY', 'Amatőr szint specialitásai', 540, 1400),
                    (2, 'Taktikai Elemzés', 'THEORY', 'Mérkőzéselemzés, ellenfél megfigyelés', 600, 1600),
                    (3, 'Játékosmenedzsment', 'THEORY', 'Felnőtt játékosok kezelése', 480, 1300),
                    (4, 'Amateur Asszisztens Gyakorlat', 'PRACTICE', 'Segédedzői feladatok', 1200, 3200),
                    (5, 'Amateur Asszisztens Vizsga', 'QUIZ', 'Amatőr Edző Teszt', 90, 2500)
                ]
            },

            # Level 6: Amateur Football Vezetőedző
            {
                'level': 6,
                'order': 8,
                'title': 'Amateur Football Vezetőedző - Stratégiai Tervezés',
                'desc': 'Amatőr program teljes vezetése, mérkőzéselemzés, stratégiai tervezés',
                'hours': 70,
                'xp': 18000,
                'modules': [
                    (1, 'Amatőr Program Vezetés', 'THEORY', 'Teljes szezon tervezése és vezetése', 720, 2000),
                    (2, 'Mérkőzéselemzés Haladó', 'THEORY', 'Video analízis, statisztikai elemzés', 600, 1700),
                    (3, 'Stratégiai Tervezés', 'THEORY', 'Játékstratégiák, formációk, taktikák', 780, 2200),
                    (4, 'Vezetőedzői Gyakorlat', 'PRACTICE', 'Komplett csapat vezetése', 1800, 5000),
                    (5, 'Amateur Vezetőedző Vizsga', 'QUIZ', 'Vezetőedzői Teszt', 120, 3100)
                ]
            }
        ]

        # Insert lessons and modules for levels 1-6
        lesson_count = 0
        module_count = 0

        for lesson_data in coach_levels:
            # Insert lesson
            db.execute(text(f"""
                INSERT INTO lessons (curriculum_track_id, level_id, order_number, title, description, estimated_hours, xp_reward, is_mandatory)
                VALUES ({track_id}, {lesson_data['level']}, {lesson_data['order']}, :title, :desc, {lesson_data['hours']}, {lesson_data['xp']}, true)
            """), {"title": lesson_data['title'], "desc": lesson_data['desc']})

            lesson_result = db.execute(text(f"SELECT id FROM lessons WHERE curriculum_track_id = {track_id} AND order_number = {lesson_data['order']}"))
            lesson_id = lesson_result.scalar()
            lesson_count += 1
            print(f"✅ Lesson {lesson_data['order']} (Level {lesson_data['level']}): {lesson_data['title'][:50]}...")

            # Insert modules
            for order, title, mod_type, content, minutes, xp in lesson_data['modules']:
                db.execute(text(f"""
                    INSERT INTO lesson_modules (lesson_id, order_number, title, module_type, content, estimated_minutes, xp_reward, is_mandatory)
                    VALUES ({lesson_id}, {order}, :title, :mod_type, :content, {minutes}, {xp}, true)
                """), {"title": title, "mod_type": mod_type, "content": content})
                module_count += 1

        db.commit()

        print(f"\n🎉 COACH Curriculum Seeded Successfully!")
        print(f"   📚 1 curriculum track")
        print(f"   📖 {lesson_count} lessons (Levels 1-6 of 8)")
        print(f"   📝 {module_count} modules")
        print(f"\n⚠️  Note: Levels 7-8 (PRO) coming next...")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_coach_curriculum()
