#!/usr/bin/env python3
"""
Sample quiz data script for populating the quiz system with test data - English version
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
                    {"text": "Content", "correct": True},
                    {"text": "CONTENT", "correct": True}
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
            title="Business Economics",
            description="Test of fundamental economic concepts and principles.",
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
                "text": "What is the difference between fixed and variable costs?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Fixed costs do not change with production volume", "correct": True},
                    {"text": "Fixed costs are always higher", "correct": False},
                    {"text": "Variable costs are constant", "correct": False},
                    {"text": "There is no difference between them", "correct": False}
                ],
                "explanation": "Fixed costs are independent of production volume (e.g. rent), variable costs are proportional to it."
            },
            {
                "text": "Inflation means a decrease in the value of money.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "During inflation, prices rise, so the purchasing power of money decreases."
            },
            {
                "text": "We measure a company's profitability based on the _____ indicator.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "ROI", "correct": True},
                    {"text": "profitability", "correct": True},
                    {"text": "profit", "correct": True}
                ],
                "explanation": "ROI (Return on Investment) shows the return on investment."
            },
            {
                "text": "What is the break-even point?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Where revenue equals costs", "correct": True},
                    {"text": "The point of maximum profit", "correct": False},
                    {"text": "The minimum margin", "correct": False},
                    {"text": "The highest selling price", "correct": False}
                ],
                "explanation": "Break-even point is the production/sales level where there is neither profit nor loss."
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
        
        # Computer Science Quiz
        informatics_quiz = Quiz(
            title="Computer Science Fundamentals",
            description="Basics of computer science and programming.",
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
                "text": "Which programming language is object-oriented?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Python", "correct": True},
                    {"text": "HTML", "correct": False},
                    {"text": "CSS", "correct": False},
                    {"text": "SQL", "correct": False}
                ],
                "explanation": "Python is a multi-paradigm language that supports object-oriented programming."
            },
            {
                "text": "HTTPS is the encrypted version of the HTTP protocol.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "HTTPS is HTTP enhanced with SSL/TLS encryption."
            },
            {
                "text": "_____ is a relational database management system.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "MySQL", "correct": True},
                    {"text": "PostgreSQL", "correct": True},
                    {"text": "Oracle", "correct": True},
                    {"text": "SQL Server", "correct": True}
                ],
                "explanation": "There are several RDBMS systems like MySQL, PostgreSQL, Oracle, SQL Server."
            },
            {
                "text": "What is the main advantage of cloud computing services?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Scalability and flexibility", "correct": True},
                    {"text": "Always cheaper", "correct": False},
                    {"text": "No internet connection needed", "correct": False},
                    {"text": "Complete data security guaranteed", "correct": False}
                ],
                "explanation": "Cloud services are popular mainly for flexible resource management."
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
            title="Sports Physiology Basics",
            description="Physiological background of exercise and sports.",
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
                "text": "What is the main characteristic of aerobic exercise?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "It occurs with oxygen utilization", "correct": True},
                    {"text": "Short, intense workload", "correct": False},
                    {"text": "Only through anaerobic pathways", "correct": False},
                    {"text": "Can only be done by running", "correct": False}
                ],
                "explanation": "During aerobic exercise, sufficient oxygen is available for energy production."
            },
            {
                "text": "Lactate accumulation causes muscle fatigue.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "Lactate (lactic acid) accumulation in muscles causes fatigue and burning sensation."
            },
            {
                "text": "The human body has approximately _____% water content.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "60", "correct": True},
                    {"text": "sixty", "correct": True},
                    {"text": "60%", "correct": True}
                ],
                "explanation": "The human body consists of approximately 60% water, which is important to replenish during sports."
            },
            {
                "text": "What is the ideal heart rate during exercise for a 30-year-old athlete?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "133-152 beats/min (70-80% max HR)", "correct": True},
                    {"text": "95-114 beats/min (50-60% max HR)", "correct": False},
                    {"text": "171-190 beats/min (90-100% max HR)", "correct": False},
                    {"text": "60-80 beats/min (resting)", "correct": False}
                ],
                "explanation": "For a 30-year-old, max HR ~190, ideal for training is 70-80% (133-152 beats/min)."
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
        
        # Sports Nutrition Quiz
        nutrition_quiz = Quiz(
            title="Sports Nutrition",
            description="Nutritional knowledge for athletes.",
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
                "text": "Which macronutrient is the main energy source for athletes?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Carbohydrates", "correct": True},
                    {"text": "Protein", "correct": False},
                    {"text": "Fat", "correct": False},
                    {"text": "Vitamins", "correct": False}
                ],
                "explanation": "Carbohydrates provide the fastest available energy during exercise."
            },
            {
                "text": "It is recommended to consume protein within 30 minutes after exercise for muscle growth.",
                "type": QuestionType.TRUE_FALSE,
                "options": [
                    {"text": "True", "correct": True},
                    {"text": "False", "correct": False}
                ],
                "explanation": "The 30-minute 'anabolic window' after exercise is optimal for muscle building."
            },
            {
                "text": "Athletes should consume _____ g/kg of protein daily.",
                "type": QuestionType.FILL_IN_BLANK,
                "options": [
                    {"text": "1.2-2.0", "correct": True},
                    {"text": "1,2-2,0", "correct": True},
                    {"text": "1.6", "correct": True}
                ],
                "explanation": "Athletes should consume 1.2-2.0 g/kg protein daily based on their body weight."
            },
            {
                "text": "Which vitamin helps iron absorption?",
                "type": QuestionType.MULTIPLE_CHOICE,
                "options": [
                    {"text": "Vitamin C", "correct": True},
                    {"text": "Vitamin D", "correct": False},
                    {"text": "Vitamin B12", "correct": False},
                    {"text": "Vitamin E", "correct": False}
                ],
                "explanation": "Vitamin C significantly improves iron absorption in the body."
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
        print("✅ English sample quiz data created successfully!")
        print(f"Created {5} quizzes with questions:")
        print(f"- Marketing: {len(marketing_questions)} questions")
        print(f"- Economics: {len(economics_questions)} questions") 
        print(f"- Computer Science: {len(informatics_questions)} questions")
        print(f"- Sports Physiology: {len(sports_questions)} questions")
        print(f"- Sports Nutrition: {len(nutrition_questions)} questions")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_quizzes()