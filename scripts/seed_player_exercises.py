"""
Seed Exercises for PLAYER Curriculum
Run with: python scripts/seed_player_exercises.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from sqlalchemy import text
import json

def seed_player_exercises():
    db = SessionLocal()

    try:
        print("🏋️ Seeding PLAYER curriculum exercises...")

        # Get PLAYER lessons
        lessons = db.execute(text("""
            SELECT l.id, l.title, l.order_number
            FROM lessons l
            JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
            WHERE ct.specialization_id = 'PLAYER'
            ORDER BY l.order_number
        """)).fetchall()

        print(f"Found {len(lessons)} PLAYER lessons")

        exercises_data = [
            # LESSON 1: Ganball™️ Eszköz Alapjai
            {
                'lesson_order': 1,
                'exercises': [
                    {
                        'title': 'Ganball™️ Összeszerelési Videó',
                        'description': 'Készíts videót arról, hogyan szereled össze a Ganball eszközt a tanult protokoll szerint.',
                        'exercise_type': 'VIDEO_UPLOAD',
                        'instructions': '''
                            <h3>Feladat</h3>
                            <p>Készíts egy 2-3 perces videót, amelyben bemutatod a Ganball eszköz teljes összeszerelési folyamatát.</p>

                            <h3>Követelmények</h3>
                            <ul>
                                <li>Videó hossza: 2-3 perc</li>
                                <li>Formátum: MP4, MOV vagy AVI</li>
                                <li>Minőség: minimum 720p</li>
                                <li>Lásd az összes lépést tisztán</li>
                                <li>Kommentáld a biztonsági szabályokat</li>
                            </ul>

                            <h3>Értékelési szempontok</h3>
                            <ul>
                                <li>Helyes sorrend (30 pont)</li>
                                <li>Biztonsági protokoll említése (30 pont)</li>
                                <li>Videó minőség és érthetőség (20 pont)</li>
                                <li>Időzítés és tempó (20 pont)</li>
                            </ul>
                        ''',
                        'requirements': {
                            'file_type': ['video/mp4', 'video/quicktime', 'video/x-msvideo'],
                            'max_size_mb': 100,
                            'min_duration': 120,
                            'max_duration': 180,
                            'resolution': '720p',
                            'criteria': [
                                {'name': 'Helyes sorrend', 'max_points': 30},
                                {'name': 'Biztonsági protokoll', 'max_points': 30},
                                {'name': 'Videó minőség', 'max_points': 20},
                                {'name': 'Időzítés', 'max_points': 20}
                            ]
                        },
                        'max_points': 100,
                        'passing_score': 70.0,
                        'xp_reward': 1000,
                        'estimated_time_minutes': 60,
                        'is_mandatory': True,
                        'allow_resubmission': True,
                        'deadline_days': 7
                    }
                ]
            },

            # LESSON 2: Bőrérzékelés Fejlesztés
            {
                'lesson_order': 2,
                'exercises': [
                    {
                        'title': 'Bőrérzékelési Gyakorlatok Dokumentációja',
                        'description': '7 napos gyakorlási napló: dokumentáld az érzékelési gyakorlataid eredményeit.',
                        'exercise_type': 'DOCUMENT',
                        'instructions': '''
                            <h3>Feladat</h3>
                            <p>Végezd el a 7 napos bőrérzékelés gyakorlatokat és dokumentáld az eredményeidet.</p>

                            <h3>Napló tartalma (minden napra)</h3>
                            <ul>
                                <li>Dátum és időpont</li>
                                <li>Melyik gyakorlatot végezted (vibráció, nyomás, hőmérséklet)</li>
                                <li>Időtartam (perc)</li>
                                <li>Észlelt változások, fejlődés</li>
                                <li>Érzések, reflexiók</li>
                            </ul>

                            <h3>Formátum</h3>
                            <p>PDF vagy DOCX formátumban, strukturáltan, táblázatos formában.</p>
                        ''',
                        'requirements': {
                            'file_type': ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                            'max_size_mb': 10,
                            'min_days': 7,
                            'criteria': [
                                {'name': 'Napló teljessége (7 nap)', 'max_points': 40},
                                {'name': 'Részletesség', 'max_points': 30},
                                {'name': 'Reflexiók minősége', 'max_points': 30}
                            ]
                        },
                        'max_points': 100,
                        'passing_score': 70.0,
                        'xp_reward': 1200,
                        'estimated_time_minutes': 420,  # 7 days * 60 mins
                        'is_mandatory': True,
                        'allow_resubmission': True,
                        'deadline_days': 14
                    },
                    {
                        'title': 'Érzékelési Teszt Videó',
                        'description': 'Demonstráld az érzékelési képességeidet bekötött szemmel.',
                        'exercise_type': 'VIDEO_UPLOAD',
                        'instructions': '''
                            <h3>Feladat</h3>
                            <p>Rögzíts videót, amelyen bekötött szemmel azonosítasz különböző felületeket és textúrákat a Ganball eszközzel.</p>

                            <h3>Követelmények</h3>
                            <ul>
                                <li>Bekötött szem</li>
                                <li>Minimum 5 különböző felület azonosítása</li>
                                <li>Videó hossza: 3-5 perc</li>
                                <li>Kommentáld, mit érzel, mit azonosítasz</li>
                            </ul>
                        ''',
                        'requirements': {
                            'file_type': ['video/mp4', 'video/quicktime'],
                            'max_size_mb': 150,
                            'min_duration': 180,
                            'max_duration': 300,
                            'criteria': [
                                {'name': 'Azonosítások pontossága', 'max_points': 50},
                                {'name': 'Technikai kivitelezés', 'max_points': 30},
                                {'name': 'Verbális leírás', 'max_points': 20}
                            ]
                        },
                        'max_points': 100,
                        'passing_score': 70.0,
                        'xp_reward': 1500,
                        'estimated_time_minutes': 45,
                        'is_mandatory': True,
                        'allow_resubmission': True,
                        'deadline_days': 14
                    }
                ]
            },

            # LESSON 3: Challenge Rendszer Mesteri Szint
            {
                'lesson_order': 3,
                'exercises': [
                    {
                        'title': 'Challenge Gyakorlat Teljesítése',
                        'description': 'Teljesíts egy Mesteri szintű challenge-et és dokumentáld.',
                        'exercise_type': 'PROJECT',
                        'instructions': '''
                            <h3>Feladat</h3>
                            <p>Válassz egy Mesteri szintű challenge-et (időzített, pontossági vagy kombinált) és teljesítsd.</p>

                            <h3>Leadandók</h3>
                            <ol>
                                <li><strong>Videó</strong>: A teljes challenge végrehajtása (5-10 perc)</li>
                                <li><strong>Dokumentum</strong>: Előkészítés, stratégia, reflexió (1-2 oldal PDF)</li>
                            </ol>

                            <h3>Értékelés</h3>
                            <ul>
                                <li>Challenge teljesítése (50 pont)</li>
                                <li>Technikai kivitelezés (25 pont)</li>
                                <li>Reflexió minősége (25 pont)</li>
                            </ul>
                        ''',
                        'requirements': {
                            'deliverables': ['video', 'document'],
                            'video': {
                                'file_type': ['video/mp4'],
                                'max_size_mb': 200,
                                'min_duration': 300
                            },
                            'document': {
                                'file_type': ['application/pdf'],
                                'max_size_mb': 5,
                                'min_pages': 1,
                                'max_pages': 2
                            },
                            'criteria': [
                                {'name': 'Challenge teljesítése', 'max_points': 50},
                                {'name': 'Technikai kivitelezés', 'max_points': 25},
                                {'name': 'Reflexió', 'max_points': 25}
                            ]
                        },
                        'max_points': 100,
                        'passing_score': 70.0,
                        'xp_reward': 2000,
                        'estimated_time_minutes': 180,
                        'is_mandatory': True,
                        'allow_resubmission': True,
                        'deadline_days': 21
                    }
                ]
            },

            # LESSON 4: Ganball™️ Edzésvezetés
            {
                'lesson_order': 4,
                'exercises': [
                    {
                        'title': 'Edzésterv Kidolgozása',
                        'description': 'Készíts egy 30 perces kezdő szintű Ganball edzéstervet.',
                        'exercise_type': 'DOCUMENT',
                        'instructions': '''
                            <h3>Feladat</h3>
                            <p>Tervezz meg egy 30 perces kezdő szintű Ganball edzést, amely tartalmazza:</p>

                            <h3>Tartalmi elemek</h3>
                            <ul>
                                <li>Bemelegítés (5 perc)</li>
                                <li>Alapgyakorlatok (15 perc)</li>
                                <li>Játékos feladatok (8 perc)</li>
                                <li>Levezetés (2 perc)</li>
                            </ul>

                            <h3>Formátum</h3>
                            <p>PDF vagy DOCX, részletes időzítéssel, gyakorlat leírásokkal, felszerelési listával.</p>
                        ''',
                        'requirements': {
                            'file_type': ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                            'max_size_mb': 10,
                            'min_pages': 2,
                            'criteria': [
                                {'name': 'Strukturáltság', 'max_points': 30},
                                {'name': 'Gyakorlatok megfelelősége', 'max_points': 40},
                                {'name': 'Részletesség', 'max_points': 30}
                            ]
                        },
                        'max_points': 100,
                        'passing_score': 70.0,
                        'xp_reward': 1500,
                        'estimated_time_minutes': 120,
                        'is_mandatory': True,
                        'allow_resubmission': True,
                        'deadline_days': 10
                    },
                    {
                        'title': 'Edzésvezetés Gyakorlat Videó',
                        'description': 'Vezess le egy 10 perces Ganball edzést és rögzítsd videón.',
                        'exercise_type': 'VIDEO_UPLOAD',
                        'instructions': '''
                            <h3>Feladat</h3>
                            <p>Vezess le egy 10 perces gyakorlati edzést legalább 1 másik résztvevővel.</p>

                            <h3>Követelmények</h3>
                            <ul>
                                <li>Minimum 1 résztvevő (lehet családtag, barát)</li>
                                <li>Tiszta instrukciók, jó hangerő</li>
                                <li>Demonstrálod a gyakorlatokat</li>
                                <li>Javítasz hibákat</li>
                                <li>Videó hossza: 10-12 perc</li>
                            </ul>
                        ''',
                        'requirements': {
                            'file_type': ['video/mp4', 'video/quicktime'],
                            'max_size_mb': 300,
                            'min_duration': 600,
                            'max_duration': 720,
                            'criteria': [
                                {'name': 'Instrukciók tisztasága', 'max_points': 30},
                                {'name': 'Demonstráció minősége', 'max_points': 30},
                                {'name': 'Hibajavítás', 'max_points': 20},
                                {'name': 'Edzés szerkezete', 'max_points': 20}
                            ]
                        },
                        'max_points': 100,
                        'passing_score': 70.0,
                        'xp_reward': 2000,
                        'estimated_time_minutes': 90,
                        'is_mandatory': True,
                        'allow_resubmission': True,
                        'deadline_days': 14
                    }
                ]
            }
        ]

        exercise_count = 0

        for ex_group in exercises_data:
            # Find lesson
            lesson = next((l for l in lessons if l[2] == ex_group['lesson_order']), None)
            if not lesson:
                print(f"⚠️  Lesson order {ex_group['lesson_order']} not found, skipping...")
                continue

            lesson_id = lesson[0]
            lesson_title = lesson[1]

            print(f"\n📝 Processing lesson: {lesson_title}")

            for order_num, ex in enumerate(ex_group['exercises'], start=1):
                # Insert exercise
                db.execute(text("""
                    INSERT INTO exercises (
                        lesson_id, title, description, exercise_type, instructions,
                        requirements, max_points, passing_score, xp_reward,
                        order_number, estimated_time_minutes, is_mandatory,
                        allow_resubmission, deadline_days
                    ) VALUES (
                        :lesson_id, :title, :description, :exercise_type, :instructions,
                        :requirements, :max_points, :passing_score, :xp_reward,
                        :order_number, :estimated_time_minutes, :is_mandatory,
                        :allow_resubmission, :deadline_days
                    )
                """), {
                    'lesson_id': lesson_id,
                    'title': ex['title'],
                    'description': ex['description'],
                    'exercise_type': ex['exercise_type'],
                    'instructions': ex['instructions'],
                    'requirements': json.dumps(ex['requirements']),
                    'max_points': ex['max_points'],
                    'passing_score': ex['passing_score'],
                    'xp_reward': ex['xp_reward'],
                    'order_number': order_num,
                    'estimated_time_minutes': ex['estimated_time_minutes'],
                    'is_mandatory': ex['is_mandatory'],
                    'allow_resubmission': ex['allow_resubmission'],
                    'deadline_days': ex['deadline_days']
                })

                exercise_count += 1
                print(f"  ✅ Exercise {order_num}: {ex['title']}")

        db.commit()

        print(f"\n🎉 PLAYER Exercises Seeded Successfully!")
        print(f"   🏋️ {exercise_count} exercises created across {len(lessons)} lessons")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_player_exercises()
