#!/usr/bin/env python3
"""
Create Comprehensive Quizzes with Different Difficulty Levels
Creates easy, medium, hard quizzes both general and project-specific
"""

import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import (
    Quiz, QuizQuestion, QuizAnswerOption, Project,
    QuestionType, QuizCategory, QuizDifficulty
)

def create_comprehensive_quizzes():
    """Create comprehensive quiz system with different difficulty levels"""
    db = next(get_db())
    
    try:
        print("🧠 Creating Comprehensive Quiz System")
        print("=" * 40)
        
        # Get existing projects for project-specific quizzes
        projects = db.query(Project).all()
        print(f"📁 Found {len(projects)} projects for project-specific quizzes")
        
        # GENERAL QUIZZES - Different difficulty levels
        general_quizzes_data = [
            # EASY LEVEL QUIZZES
            {
                'title': 'Football Basics - Easy',
                'description': 'Basic football knowledge for beginners',
                'category': QuizCategory.SPORTS_PHYSIOLOGY,
                'difficulty': QuizDifficulty.EASY,
                'xp_reward': 50,
                'questions': [
                    {
                        'text': 'How many players are on the field for each team in football?',
                        'options': ['10', '11', '12', '13'],
                        'correct': 1,
                        'points': 5
                    },
                    {
                        'text': 'What color card is shown for a serious foul?',
                        'options': ['Green', 'Yellow', 'Red', 'Blue'],
                        'correct': 2,
                        'points': 5
                    },
                    {
                        'text': 'How long is a standard football match?',
                        'options': ['80 minutes', '90 minutes', '100 minutes', '120 minutes'],
                        'correct': 1,
                        'points': 5
                    },
                    {
                        'text': 'What is the maximum number of substitutions allowed?',
                        'options': ['3', '4', '5', '6'],
                        'correct': 2,
                        'points': 5
                    }
                ]
            },
            
            # MEDIUM LEVEL QUIZZES
            {
                'title': 'Football Rules & Tactics - Medium',
                'description': 'Intermediate knowledge of football rules and basic tactics',
                'category': QuizCategory.GENERAL,
                'difficulty': QuizDifficulty.MEDIUM,
                'xp_reward': 100,
                'questions': [
                    {
                        'text': 'What constitutes an offside offense?',
                        'options': [
                            'Player closer to goal line than ball when ball is played by teammate',
                            'Player in opponent half when ball is played',
                            'Player ahead of last defender when ball is played by teammate',
                            'Player touching the ball with hands'
                        ],
                        'correct': 2,
                        'points': 10
                    },
                    {
                        'text': 'In a 4-4-2 formation, how many midfielders are there?',
                        'options': ['2', '3', '4', '5'],
                        'correct': 2,
                        'points': 10
                    },
                    {
                        'text': 'When is a penalty kick awarded?',
                        'options': [
                            'For any foul in the opponent half',
                            'For a serious foul anywhere on the field',
                            'For a direct free kick offense inside the penalty area',
                            'For dissent towards the referee'
                        ],
                        'correct': 2,
                        'points': 10
                    },
                    {
                        'text': 'What is the "offside trap" tactic?',
                        'options': [
                            'Defending deep in your own half',
                            'Moving defensive line forward to catch opponents offside',
                            'Playing with extra defenders',
                            'Marking each opponent individually'
                        ],
                        'correct': 1,
                        'points': 15
                    }
                ]
            },
            
            # HARD LEVEL QUIZZES
            {
                'title': 'Advanced Football Knowledge - Hard',
                'description': 'Advanced tactics, laws, and professional-level concepts',
                'category': QuizCategory.GENERAL,
                'difficulty': QuizDifficulty.HARD,
                'xp_reward': 200,
                'questions': [
                    {
                        'text': 'According to Law 11, a player is NOT offside when:',
                        'options': [
                            'Receiving ball from throw-in, corner kick, or goal kick',
                            'In their own half of the field',
                            'Level with or behind the ball when played by teammate',
                            'All of the above'
                        ],
                        'correct': 3,
                        'points': 20
                    },
                    {
                        'text': 'What is "false 9" tactical role?',
                        'options': [
                            'A striker who drops deep to create space and link play',
                            'A defender who moves forward during attacks',
                            'A goalkeeper who acts as sweeper',
                            'A midfielder who plays as winger'
                        ],
                        'correct': 0,
                        'points': 25
                    },
                    {
                        'text': 'In "tiki-taka" style, what is the primary objective?',
                        'options': [
                            'Play long balls and crosses',
                            'Maintain possession through short passing and movement',
                            'Press high and win ball quickly',
                            'Play defensive and counter-attack'
                        ],
                        'correct': 1,
                        'points': 25
                    },
                    {
                        'text': 'What is "gegenpressing" in modern football?',
                        'options': [
                            'Slow build-up play from the back',
                            'Immediate pressing after losing possession',
                            'Playing with 3 center-backs',
                            'Using wing-backs instead of wingers'
                        ],
                        'correct': 1,
                        'points': 30
                    }
                ]
            },
            
            # NUTRITION & FITNESS QUIZZES
            {
                'title': 'Sports Nutrition - Medium',
                'description': 'Understanding nutrition for football performance',
                'category': QuizCategory.NUTRITION,
                'difficulty': QuizDifficulty.MEDIUM,
                'xp_reward': 120,
                'questions': [
                    {
                        'text': 'What is the recommended carbohydrate intake before training?',
                        'options': ['1-2g per kg body weight', '3-4g per kg body weight', '5-6g per kg body weight', '7-8g per kg body weight'],
                        'correct': 1,
                        'points': 15
                    },
                    {
                        'text': 'When should protein be consumed after training?',
                        'options': ['Immediately', 'Within 30 minutes', 'Within 2 hours', 'Next day'],
                        'correct': 2,
                        'points': 15
                    },
                    {
                        'text': 'What is the primary fuel source during high-intensity exercise?',
                        'options': ['Fats', 'Proteins', 'Carbohydrates', 'Vitamins'],
                        'correct': 2,
                        'points': 10
                    }
                ]
            },
            
            # SPORTS PHYSIOLOGY QUIZ
            {
                'title': 'Sports Physiology - Hard',
                'description': 'Advanced understanding of body systems in sport',
                'category': QuizCategory.SPORTS_PHYSIOLOGY,
                'difficulty': QuizDifficulty.HARD,
                'xp_reward': 180,
                'questions': [
                    {
                        'text': 'What is VO2 Max?',
                        'options': [
                            'Maximum heart rate during exercise',
                            'Maximum oxygen consumption during exercise',
                            'Maximum muscle contraction force',
                            'Maximum breathing rate'
                        ],
                        'correct': 1,
                        'points': 25
                    },
                    {
                        'text': 'What energy system is primarily used in short bursts (0-10 seconds)?',
                        'options': ['Aerobic system', 'Lactic acid system', 'Phosphocreatine system', 'Protein system'],
                        'correct': 2,
                        'points': 20
                    },
                    {
                        'text': 'What is lactate threshold?',
                        'options': [
                            'Point where lactate production exceeds clearance',
                            'Maximum muscle strength',
                            'Highest sustainable heart rate',
                            'Optimal training intensity'
                        ],
                        'correct': 0,
                        'points': 25
                    }
                ]
            }
        ]
        
        # CREATE GENERAL QUIZZES
        print("\n📊 Creating General Knowledge Quizzes...")
        created_general_quizzes = []
        
        for quiz_data in general_quizzes_data:
            quiz = Quiz(
                title=quiz_data['title'],
                description=quiz_data['description'],
                category=quiz_data['category'],
                difficulty=quiz_data['difficulty'],
                xp_reward=quiz_data['xp_reward'],
                passing_score=70.0,
                time_limit_minutes=20 if quiz_data['difficulty'] == QuizDifficulty.EASY else (30 if quiz_data['difficulty'] == QuizDifficulty.MEDIUM else 45),
                is_active=True
            )
            db.add(quiz)
            db.flush()
            created_general_quizzes.append(quiz)
            
            # Add questions
            for q_data in quiz_data['questions']:
                question = QuizQuestion(
                    quiz_id=quiz.id,
                    question_text=q_data['text'],
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    points=q_data['points'],
                    order_index=0
                )
                db.add(question)
                db.flush()
                
                # Add answer options
                for i, option_text in enumerate(q_data['options']):
                    option = QuizAnswerOption(
                        question_id=question.id,
                        option_text=option_text,
                        is_correct=(i == q_data['correct']),
                        order_index=i
                    )
                    db.add(option)
            
            print(f"  ✅ Created: {quiz.title} ({quiz.difficulty.value}) - {quiz.xp_reward} XP")
        
        # PROJECT-SPECIFIC QUIZZES
        print(f"\n📁 Creating Project-Specific Quizzes...")
        created_project_quizzes = []
        
        if projects:
            # Project-specific quiz data
            project_quizzes_data = {
                'Football Fundamentals': {
                    'title': 'Football Fundamentals Assessment',
                    'description': 'Test your knowledge of basic football skills and techniques',
                    'difficulty': QuizDifficulty.EASY,
                    'xp_reward': 80,
                    'questions': [
                        {
                            'text': 'What is the correct technique for a basic pass?',
                            'options': [
                                'Use the toe of your foot',
                                'Use the inside of your foot for accuracy',
                                'Always use maximum power',
                                'Keep your head down throughout'
                            ],
                            'correct': 1,
                            'points': 10
                        },
                        {
                            'text': 'When dribbling, you should:',
                            'options': [
                                'Keep the ball close to your feet',
                                'Always run at maximum speed',
                                'Never look up',
                                'Use only your dominant foot'
                            ],
                            'correct': 0,
                            'points': 10
                        },
                        {
                            'text': 'What is the most important aspect of shooting?',
                            'options': [
                                'Maximum power',
                                'Accuracy and placement',
                                'Using your weaker foot',
                                'Shooting from distance'
                            ],
                            'correct': 1,
                            'points': 15
                        }
                    ]
                },
                
                'Advanced Tactics': {
                    'title': 'Advanced Tactics Mastery',
                    'description': 'Deep dive into tactical understanding and strategic thinking',
                    'difficulty': QuizDifficulty.HARD,
                    'xp_reward': 150,
                    'questions': [
                        {
                            'text': 'What is the purpose of "pressing triggers" in modern football?',
                            'options': [
                                'To signal when to start organized pressing',
                                'To increase the tempo of play',
                                'To confuse opponents',
                                'To change formation mid-game'
                            ],
                            'correct': 0,
                            'points': 20
                        },
                        {
                            'text': 'In a 3-5-2 formation, wing-backs must:',
                            'options': [
                                'Stay in defensive positions only',
                                'Provide width in both attack and defense',
                                'Focus only on attacking',
                                'Play as central midfielders'
                            ],
                            'correct': 1,
                            'points': 25
                        },
                        {
                            'text': 'What is "positional play" in football tactics?',
                            'options': [
                                'Players staying in fixed positions',
                                'Structured movement to create space and overloads',
                                'Playing without tactical instructions',
                                'Only defending in organized lines'
                            ],
                            'correct': 1,
                            'points': 25
                        }
                    ]
                },
                
                'Goalkeeping Mastery': {
                    'title': 'Goalkeeping Excellence Quiz',
                    'description': 'Specialized knowledge for aspiring goalkeepers',
                    'difficulty': QuizDifficulty.MEDIUM,
                    'xp_reward': 110,
                    'questions': [
                        {
                            'text': 'What is the correct stance for a goalkeeper?',
                            'options': [
                                'Feet together, hands by sides',
                                'Wide stance, hands ready, on balls of feet',
                                'One foot forward, hands clasped',
                                'Standing completely upright'
                            ],
                            'correct': 1,
                            'points': 15
                        },
                        {
                            'text': 'When distributing the ball, goalkeepers should:',
                            'options': [
                                'Always kick long',
                                'Always throw short',
                                'Choose distribution based on tactical situation',
                                'Never throw the ball'
                            ],
                            'correct': 2,
                            'points': 20
                        },
                        {
                            'text': 'What is "narrowing the angle" in goalkeeping?',
                            'options': [
                                'Moving towards the attacker to reduce shooting options',
                                'Standing still in goal center',
                                'Moving side to side quickly',
                                'Diving to corners immediately'
                            ],
                            'correct': 0,
                            'points': 15
                        }
                    ]
                }
            }
            
            # Create project-specific quizzes
            for project in projects:
                if project.title in project_quizzes_data:
                    quiz_data = project_quizzes_data[project.title]
                    
                    quiz = Quiz(
                        title=quiz_data['title'],
                        description=quiz_data['description'],
                        category=QuizCategory.GENERAL,
                        difficulty=quiz_data['difficulty'],
                        xp_reward=quiz_data['xp_reward'],
                        passing_score=75.0,  # Slightly higher for project-specific
                        time_limit_minutes=25,
                        is_active=True
                    )
                    db.add(quiz)
                    db.flush()
                    created_project_quizzes.append(quiz)
                    
                    # Add questions
                    for q_data in quiz_data['questions']:
                        question = QuizQuestion(
                            quiz_id=quiz.id,
                            question_text=q_data['text'],
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            points=q_data['points'],
                            order_index=0
                        )
                        db.add(question)
                        db.flush()
                        
                        # Add answer options
                        for i, option_text in enumerate(q_data['options']):
                            option = QuizAnswerOption(
                                question_id=question.id,
                                option_text=option_text,
                                is_correct=(i == q_data['correct']),
                                order_index=i
                            )
                            db.add(option)
                    
                    print(f"  ✅ Created: {quiz.title} for '{project.title}' project")
        
        # Commit all changes
        db.commit()
        
        # Summary
        print("\n🎯 Comprehensive Quiz System Created!")
        print("=" * 45)
        print(f"📊 General Quizzes: {len(created_general_quizzes)}")
        print(f"📁 Project-Specific Quizzes: {len(created_project_quizzes)}")
        print(f"🎖️  Total XP Available: {sum(q.xp_reward for q in created_general_quizzes + created_project_quizzes)}")
        
        print("\n📈 Difficulty Breakdown:")
        easy_count = sum(1 for q in created_general_quizzes if q.difficulty == QuizDifficulty.EASY)
        medium_count = sum(1 for q in created_general_quizzes if q.difficulty == QuizDifficulty.MEDIUM)
        hard_count = sum(1 for q in created_general_quizzes if q.difficulty == QuizDifficulty.HARD)
        
        print(f"  🟢 Easy: {easy_count} quizzes")
        print(f"  🟡 Medium: {medium_count + len(created_project_quizzes)} quizzes")
        print(f"  🔴 Hard: {hard_count} quizzes")
        
        print("\n🔍 Students can now:")
        print("  - Take quizzes of different difficulty levels")
        print("  - Earn XP and level up based on performance")
        print("  - Complete project-specific assessments")
        print("  - Test knowledge in multiple categories:")
        print("    • General Football Knowledge")
        print("    • Sports Physiology")
        print("    • Nutrition")
        print("    • Project-Specific Skills")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating quizzes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_comprehensive_quizzes()