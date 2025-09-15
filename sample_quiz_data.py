#!/usr/bin/env python3
"""
Sample quiz data script for populating the quiz system with test data
"""

from app.database import SessionLocal
from app.models.quiz import Quiz, QuizQuestion, QuizAnswerOption, QuestionType, QuizCategory, QuizDifficulty

def create_sample_quizzes():
    db = SessionLocal()
    
    try:
        # Marketing Quiz
        marketing_quiz = Quiz(
            title="Digital Marketing Fundamentals",
            description="Test your knowledge in digital marketing!",
            category=QuizCategory.MARKETING,
            difficulty=QuizDifficulty.MEDIUM,
            time_limit_minutes=12,
            xp_reward=75,
            passing_score=70.0
        )
        db.add(marketing_quiz)
        db.flush()
        
        # Marketing questions
        marketing_questions = [
            {
                "text": "What is the most important KPI for social media campaigns?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Engagement rate", "correct": True},
                    {"text": "Number of followers", "correct": False},
                    {"text": "Number of posts", "correct": False},
                    {"text": "Number of comments", "correct": False}
                ],
                "explanation": "The engagement rate is the most accurate metric for measuring social media success."
            },
            {
                "text": "SEO stands for Search Engine Optimization.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "SEO indeed stands for Search Engine Optimization, which means optimizing content for search engines."
            },
            {
                "text": "_____ marketing aims to create valuable content for the target audience.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "content", "correct": True},
                    {"text": "tartalmi", "correct": True},
                    {"text": "tartalom", "correct": True}
                ],
                "explanation": "Content marketing is all about creating valuable content for your audience."
            },
            {
                "text": "What is the first step in planning a successful marketing campaign?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Target audience identification", "correct": True},
                    {"text": "Budget planning", "correct": False},
                    {"text": "Creating creatives", "correct": False},
                    {"text": "Media selection", "correct": False}
                ],
                "explanation": "Without precise target audience identification, you cannot plan an effective campaign."
            },
            {
                "text": "Email marketing remains a relevant marketing channel in 2024.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "Email marketing continues to be one of the highest ROI marketing channels."
            }
        ]
        
        for i, q_data in enumerate(marketing_questions):
            question = QuizQuestion(
                quiz_id=marketing_quiz.id,
                question_text=q_data["text"],
                question_type=q_data["type"],
                order_index=i,
                explanation=q_data.get("explanation")
            )
            db.add(question)
            db.flush()
            
            for j, opt_data in enumerate(q_data["options"]):
                option = QuizAnswerOption(
                    question_id=question.id,
                    option_text=opt_data["text"],
                    is_correct=opt_data["correct"],
                    order_index=j
                )
                db.add(option)
        
        # Economics Quiz
        economics_quiz = Quiz(
            title="Vállalati Gazdaságtan",
            description="Alapvető gazdaságtani fogalmak és elvek tesztje.",
            category=QuizCategory.ECONOMICS,
            difficulty=QuizDifficulty.MEDIUM,
            time_limit_minutes=15,
            xp_reward=80,
            passing_score=75.0
        )
        db.add(economics_quiz)
        db.flush()
        
        economics_questions = [
            {
                "text": "Mi a különbség a fix és változó költségek között?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Fix költségek nem változnak a termelési volumen függvényében", "correct": True},
                    {"text": "Fix költségek mindig magasabbak", "correct": False},
                    {"text": "Változó költségek állandóak", "correct": False},
                    {"text": "Nincs különbség köztük", "correct": False}
                ],
                "explanation": "Fix költségek függetlenek a termelési volumintől (pl. bérleti díj), változó költségek arányosak vele."
            },
            {
                "text": "Az infláció a pénz értékének csökkenését jelenti.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "Az infláció során az árak emelkednek, így a pénz vásárlóereje csökken."
            },
            {
                "text": "A _____ mutató alapján mérjük egy vállalat jövedelmezőségét.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "ROI", "correct": True},
                    {"text": "profitabilitás", "correct": True},
                    {"text": "nyereség", "correct": True}
                ],
                "explanation": "A ROI (Return on Investment) a befektetés megtérülését mutatja."
            },
            {
                "text": "Mi a break-even pont?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Ahol a bevétel megegyezik a költségekkel", "correct": True},
                    {"text": "A maximális profit pontja", "correct": False},
                    {"text": "A minimális árrés", "correct": False},
                    {"text": "A legmagasabb eladási ár", "correct": False}
                ],
                "explanation": "Break-even pont az a termelési/értékesítési szint, ahol nincs sem nyereség, sem veszteség."
            }
        ]
        
        for i, q_data in enumerate(economics_questions):
            question = QuizQuestion(
                quiz_id=economics_quiz.id,
                question_text=q_data["text"],
                question_type=q_data["type"],
                order_index=i,
                explanation=q_data.get("explanation")
            )
            db.add(question)
            db.flush()
            
            for j, opt_data in enumerate(q_data["options"]):
                option = QuizAnswerOption(
                    question_id=question.id,
                    option_text=opt_data["text"],
                    is_correct=opt_data["correct"],
                    order_index=j
                )
                db.add(option)
        
        # Informatics Quiz
        informatics_quiz = Quiz(
            title="Informatikai Alapismeretek",
            description="Számítástechnika és programozás alapjai.",
            category=QuizCategory.INFORMATICS,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=10,
            xp_reward=60,
            passing_score=70.0
        )
        db.add(informatics_quiz)
        db.flush()
        
        informatics_questions = [
            {
                "text": "Melyik programozási nyelv objektumorientált?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Python", "correct": True},
                    {"text": "HTML", "correct": False},
                    {"text": "CSS", "correct": False},
                    {"text": "SQL", "correct": False}
                ],
                "explanation": "A Python többparadigmás nyelv, támogatja az objektumorientált programozást."
            },
            {
                "text": "A HTTP protokoll titkosított változata a HTTPS.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "A HTTPS a HTTP SSL/TLS titkosítással kiegészített változata."
            },
            {
                "text": "A _____ egy relációs adatbázis-kezelő rendszer.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "MySQL", "correct": True},
                    {"text": "PostgreSQL", "correct": True},
                    {"text": "Oracle", "correct": True},
                    {"text": "SQL Server", "correct": True}
                ],
                "explanation": "Több RDBMS rendszer létezik, mint MySQL, PostgreSQL, Oracle, SQL Server."
            },
            {
                "text": "Mi a felhő-alapú szolgáltatások (cloud computing) fő előnye?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Skálázhatóság és rugalmasság", "correct": True},
                    {"text": "Mindig olcsóbb", "correct": False},
                    {"text": "Nincs internetkapcsolat szükséges", "correct": False},
                    {"text": "Teljes adatbiztonság garantált", "correct": False}
                ],
                "explanation": "A felhő szolgáltatások főleg a rugalmas erőforrás-kezelés miatt népszerűek."
            }
        ]
        
        for i, q_data in enumerate(informatics_questions):
            question = QuizQuestion(
                quiz_id=informatics_quiz.id,
                question_text=q_data["text"],
                question_type=q_data["type"],
                order_index=i,
                explanation=q_data.get("explanation")
            )
            db.add(question)
            db.flush()
            
            for j, opt_data in enumerate(q_data["options"]):
                option = QuizAnswerOption(
                    question_id=question.id,
                    option_text=opt_data["text"],
                    is_correct=opt_data["correct"],
                    order_index=j
                )
                db.add(option)
        
        # Sports Physiology Quiz
        sports_quiz = Quiz(
            title="Sportélettan Alapok",
            description="Testedzés és sportolás élettani háttere.",
            category=QuizCategory.SPORTS_PHYSIOLOGY,
            difficulty=QuizDifficulty.MEDIUM,
            time_limit_minutes=12,
            xp_reward=85,
            passing_score=75.0
        )
        db.add(sports_quiz)
        db.flush()
        
        sports_questions = [
            {
                "text": "Mi az aerob edzés fő jellemzője?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Oxigénfelhasználás mellett történik", "correct": True},
                    {"text": "Rövid, intenzív terhelés", "correct": False},
                    {"text": "Kizárólag anaerob úton", "correct": False},
                    {"text": "Csak futással végezhető", "correct": False}
                ],
                "explanation": "Az aerob edzés során elegendő oxigén áll rendelkezésre az energia termeléséhez."
            },
            {
                "text": "A laktát felhalmozódása izomfáradtságot okoz.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "A laktát (tejsav) felhalmozódása az izmokban fáradtságot és égő érzést okoz."
            },
            {
                "text": "Az emberi test kb. ___% víztartalommal rendelkezik.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "60", "correct": True},
                    {"text": "hatvan", "correct": True},
                    {"text": "60%", "correct": True}
                ],
                "explanation": "Az ember teste körülbelül 60% vízből áll, amit fontos pótolni sportolás során."
            },
            {
                "text": "Melyik az ideális pulzusszám edzés közben egy 30 éves sportoló számára?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "133-152 ütés/perc (70-80% max HR)", "correct": True},
                    {"text": "95-114 ütés/perc (50-60% max HR)", "correct": False},
                    {"text": "171-190 ütés/perc (90-100% max HR)", "correct": False},
                    {"text": "60-80 ütés/perc (nyugalmi)", "correct": False}
                ],
                "explanation": "30 évesnek max HR ~190, edzéshez 70-80% ideális (133-152 ütés/perc)."
            }
        ]
        
        for i, q_data in enumerate(sports_questions):
            question = QuizQuestion(
                quiz_id=sports_quiz.id,
                question_text=q_data["text"],
                question_type=q_data["type"],
                order_index=i,
                explanation=q_data.get("explanation")
            )
            db.add(question)
            db.flush()
            
            for j, opt_data in enumerate(q_data["options"]):
                option = QuizAnswerOption(
                    question_id=question.id,
                    option_text=opt_data["text"],
                    is_correct=opt_data["correct"],
                    order_index=j
                )
                db.add(option)
        
        # Nutrition Quiz
        nutrition_quiz = Quiz(
            title="Sporttáplálkozás",
            description="Táplálkozási ismeretek sportolóknak.",
            category=QuizCategory.NUTRITION,
            difficulty=QuizDifficulty.MEDIUM,
            time_limit_minutes=10,
            xp_reward=70,
            passing_score=70.0
        )
        db.add(nutrition_quiz)
        db.flush()
        
        nutrition_questions = [
            {
                "text": "Melyik makronutriens a fő energiaforrás sportolók számára?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Szénhidrát", "correct": True},
                    {"text": "Fehérje", "correct": False},
                    {"text": "Zsír", "correct": False},
                    {"text": "Vitamin", "correct": False}
                ],
                "explanation": "A szénhidrátok biztosítják a leggyorsabban felhasználható energiát edzés során."
            },
            {
                "text": "Edzés után 30 percen belül érdemes fehérjét fogyasztani az izomnövekedéshez.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "Az edzés utáni 30 perces 'anabolikus ablak' optimális az izomépítéshez."
            },
            {
                "text": "Sportolóknak napi _____ g/kg fehérjebevitel javasolt.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "1.2-2.0", "correct": True},
                    {"text": "1,2-2,0", "correct": True},
                    {"text": "1.6", "correct": True}
                ],
                "explanation": "Sportolóknak 1.2-2.0 g/kg fehérje ajánlott naponta testsúlyuk alapján."
            },
            {
                "text": "Melyik vitamin segíti a vas felszívódását?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "C-vitamin", "correct": True},
                    {"text": "D-vitamin", "correct": False},
                    {"text": "B12-vitamin", "correct": False},
                    {"text": "E-vitamin", "correct": False}
                ],
                "explanation": "A C-vitamin jelentősen javítja a vas felszívódását a szervezetben."
            }
        ]
        
        for i, q_data in enumerate(nutrition_questions):
            question = QuizQuestion(
                quiz_id=nutrition_quiz.id,
                question_text=q_data["text"],
                question_type=q_data["type"],
                order_index=i,
                explanation=q_data.get("explanation")
            )
            db.add(question)
            db.flush()
            
            for j, opt_data in enumerate(q_data["options"]):
                option = QuizAnswerOption(
                    question_id=question.id,
                    option_text=opt_data["text"],
                    is_correct=opt_data["correct"],
                    order_index=j
                )
                db.add(option)
        
        db.commit()
        print("✅ Sample quiz data created successfully!")
        print(f"Created {5} quizzes with questions:")
        print(f"- Marketing: {len(marketing_questions)} questions")
        print(f"- Economics: {len(economics_questions)} questions") 
        print(f"- Informatics: {len(informatics_questions)} questions")
        print(f"- Sports Physiology: {len(sports_questions)} questions")
        print(f"- Nutrition: {len(nutrition_questions)} questions")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_quizzes()