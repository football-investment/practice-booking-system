"""
Seed Quiz Questions for Curriculum Lessons
Run with: python scripts/seed_lesson_quizzes.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.quiz import QuizCategory, QuizDifficulty, QuestionType
from sqlalchemy import text

def seed_lesson_quizzes():
    db = SessionLocal()

    try:
        print("🌱 Seeding lesson quizzes...")

        # Get PLAYER lessons
        lessons_result = db.execute(text("""
            SELECT l.id, l.order_number, l.title
            FROM lessons l
            JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
            WHERE ct.specialization_id = 'PLAYER'
            ORDER BY l.order_number
        """))
        player_lessons = lessons_result.fetchall()

        print(f"Found {len(player_lessons)} PLAYER lessons")

        # Quiz data for each lesson
        quizzes_data = [
            # Lesson 1: Ganball Eszköz Alapjai
            {
                'lesson_order': 1,
                'title': 'Ganball™️ Eszköz Alapjai - Záró Kvíz',
                'description': 'Teszteld tudásod a Ganball eszközről, összeszerelésről és biztonsági protokollokról',
                'time_limit': 15,
                'passing_score': 70,
                'xp': 250,
                'questions': [
                    {
                        'text': 'Hány modulból áll a Ganball alapkészlet?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('3 modul', False),
                            ('5 modul', True),
                            ('7 modul', False),
                            ('10 modul', False)
                        ]
                    },
                    {
                        'text': 'Mi a minimális távolság az eszköztől edzés közben?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('1 méter', False),
                            ('2 méter', True),
                            ('3 méter', False),
                            ('5 méter', False)
                        ]
                    },
                    {
                        'text': 'Mi a legfontosabb biztonsági szabály?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 15,
                        'options': [
                            ('Mindig vegyél részt bemelegítésben', False),
                            ('Ellenőrizd a csavarokat minden használat előtt', True),
                            ('Viselj védőfelszerelést', False),
                            ('Igyál sok vizet', False)
                        ]
                    },
                    {
                        'text': 'Mennyi idő alatt kell összeszerelni a Ganball-t a gyakorlat szerint?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('5 perc', False),
                            ('10 perc', False),
                            ('15 perc', True),
                            ('20 perc', False)
                        ]
                    },
                    {
                        'text': 'Milyen felületen lehet használni a Ganball-t?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('Bármilyen felületen', False),
                            ('Csak füvön', False),
                            ('Sima, szilárd, vízszintes felületen', True),
                            ('Csak aszfalton', False)
                        ]
                    }
                ]
            },

            # Lesson 2: Bőrérzékelés Fejlesztés
            {
                'lesson_order': 2,
                'title': 'Bőrérzékelés Fejlesztés - Záró Teszt',
                'description': 'Teszteld tudásod a bőr receptorokról és érzékelési technikákról',
                'time_limit': 15,
                'passing_score': 70,
                'xp': 600,
                'questions': [
                    {
                        'text': 'Melyik receptor érzékeli a vibrációt?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 15,
                        'options': [
                            ('Merkel sejtek', False),
                            ('Meissner testecskék', False),
                            ('Pacini testecskék', True),
                            ('Ruffini végződések', False)
                        ]
                    },
                    {
                        'text': 'Miért fontos a bőrérzékelés fejlesztése a futballban?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('Gyorsabban futsz', False),
                            ('Precízebb labdakezelés', True),
                            ('Erősebb lövés', False),
                            ('Jobb állóképesség', False)
                        ]
                    },
                    {
                        'text': 'Hány gyakorlatot tanultál a bőrérzékelés fejlesztésére?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('5', False),
                            ('10', True),
                            ('15', False),
                            ('20', False)
                        ]
                    }
                ]
            },

            # Lesson 3: Challenge Rendszer
            {
                'lesson_order': 3,
                'title': 'Challenge Rendszer - Mesteri Teszt',
                'description': 'Teszteld tudásod a 9 challenge típusról és pontozási rendszerről',
                'time_limit': 15,
                'passing_score': 70,
                'xp': 600,
                'questions': [
                    {
                        'text': 'Hány challenge típust tanultál?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('5', False),
                            ('7', False),
                            ('9', True),
                            ('12', False)
                        ]
                    },
                    {
                        'text': 'Hány pont kell a Mester szinthez?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('7-9 pont', False),
                            ('10 pont', True),
                            ('12 pont', False),
                            ('15 pont', False)
                        ]
                    },
                    {
                        'text': 'Mi a First Touch Challenge célja?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 15,
                        'options': [
                            ('Minél többször eltalálni a keresztlécet', False),
                            ('Egy érintéssel megállítani a labdát', True),
                            ('Minél gyorsabban futni', False),
                            ('Minél többet zsonglőrködni', False)
                        ]
                    }
                ]
            },

            # Lesson 4: Edzésvezetés
            {
                'lesson_order': 4,
                'title': 'Edzésvezetés és Technikai Alapok - Záró Vizsga',
                'description': 'Teszteld tudásod az edzéstervezésről, hibajavításról és vezetésről',
                'time_limit': 15,
                'passing_score': 70,
                'xp': 800,
                'questions': [
                    {
                        'text': 'Hány százalék az edzés főrésze az ideális struktúrában?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('50%', False),
                            ('60%', False),
                            ('70%', True),
                            ('80%', False)
                        ]
                    },
                    {
                        'text': 'Mi a SMART célkitűzés jelentése?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 15,
                        'options': [
                            ('Specific, Measurable, Achievable, Relevant, Time-bound', True),
                            ('Simple, Modern, Active, Ready, Tested', False),
                            ('Strong, Motivated, Aggressive, Real, Tough', False),
                            ('Smart, Modern, Athletic, Ready, Talented', False)
                        ]
                    },
                    {
                        'text': 'Hány lépésből áll a hibajavítási módszer?',
                        'type': 'MULTIPLE_CHOICE',
                        'points': 10,
                        'options': [
                            ('2', False),
                            ('3', True),
                            ('4', False),
                            ('5', False)
                        ]
                    }
                ]
            }
        ]

        # Create quizzes and questions
        quiz_count = 0
        question_count = 0

        for quiz_data in quizzes_data:
            # Find lesson
            lesson = next((l for l in player_lessons if l[1] == quiz_data['lesson_order']), None)
            if not lesson:
                print(f"⚠️  Lesson {quiz_data['lesson_order']} not found, skipping...")
                continue

            lesson_id = lesson[0]

            # Insert quiz (using enum string values)
            db.execute(text("""
                INSERT INTO quizzes (title, description, category, difficulty, time_limit_minutes, xp_reward, passing_score, specialization_id, lesson_id, unlock_next_lesson, is_active)
                VALUES (:title, :desc, :category, :difficulty, :time_limit, :xp, :passing_score, 'PLAYER', :lesson_id, true, true)
            """), {
                "title": quiz_data['title'],
                "desc": quiz_data['description'],
                "category": QuizCategory.LESSON.value,
                "difficulty": QuizDifficulty.MEDIUM.value,
                "time_limit": quiz_data['time_limit'],
                "xp": quiz_data['xp'],
                "passing_score": quiz_data['passing_score'],
                "lesson_id": lesson_id
            })

            # Get quiz ID
            quiz_result = db.execute(text("SELECT id FROM quizzes WHERE lesson_id = :lesson_id ORDER BY id DESC LIMIT 1"), {"lesson_id": lesson_id})
            quiz_id = quiz_result.scalar()
            quiz_count += 1
            print(f"✅ Quiz created for Lesson {quiz_data['lesson_order']}: {quiz_data['title'][:50]}...")

            # Link quiz to lesson
            db.execute(text("""
                INSERT INTO lesson_quizzes (lesson_id, quiz_id, is_prerequisite, order_number)
                VALUES (:lesson_id, :quiz_id, true, 99)
            """), {"lesson_id": lesson_id, "quiz_id": quiz_id})

            # Insert questions
            for q_idx, q_data in enumerate(quiz_data['questions']):
                db.execute(text("""
                    INSERT INTO quiz_questions (quiz_id, question_text, question_type, points, order_index)
                    VALUES (:quiz_id, :text, :type, :points, :order_idx)
                """), {
                    "quiz_id": quiz_id,
                    "text": q_data['text'],
                    "type": QuestionType[q_data['type']].value,
                    "points": q_data['points'],
                    "order_idx": q_idx
                })

                # Get question ID
                question_result = db.execute(text("SELECT id FROM quiz_questions WHERE quiz_id = :quiz_id ORDER BY id DESC LIMIT 1"), {"quiz_id": quiz_id})
                question_id = question_result.scalar()
                question_count += 1

                # Insert answer options
                for opt_idx, (option_text, is_correct) in enumerate(q_data['options']):
                    db.execute(text("""
                        INSERT INTO quiz_answer_options (question_id, option_text, is_correct, order_index)
                        VALUES (:question_id, :option_text, :is_correct, :order_idx)
                    """), {
                        "question_id": question_id,
                        "option_text": option_text,
                        "is_correct": is_correct,
                        "order_idx": opt_idx
                    })

        db.commit()

        print(f"\n🎉 Lesson Quizzes Seeded Successfully!")
        print(f"   📝 {quiz_count} quizzes created")
        print(f"   ❓ {question_count} questions created")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_lesson_quizzes()
