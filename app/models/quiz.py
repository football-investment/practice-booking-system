from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class QuestionType(enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_IN_BLANK = "fill_in_blank"

class QuizCategory(enum.Enum):
    GENERAL = "general"
    MARKETING = "marketing"
    ECONOMICS = "economics"
    INFORMATICS = "informatics"
    SPORTS_PHYSIOLOGY = "sports_physiology"
    NUTRITION = "nutrition"

class QuizDifficulty(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(QuizCategory), nullable=False)
    difficulty = Column(SQLEnum(QuizDifficulty), nullable=False, default=QuizDifficulty.MEDIUM)
    time_limit_minutes = Column(Integer, nullable=False, default=15)  # időkorlát percekben
    xp_reward = Column(Integer, nullable=False, default=50)  # XP jutalom sikeres kitöltésért
    passing_score = Column(Float, nullable=False, default=70.0)  # minimum pont százalékban
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    points = Column(Integer, nullable=False, default=1)
    order_index = Column(Integer, nullable=False, default=0)  # kérdések sorrendje
    explanation = Column(Text, nullable=True)  # magyarázat a helyes válaszhoz
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answer_options = relationship("QuizAnswerOption", back_populates="question", cascade="all, delete-orphan")
    user_answers = relationship("QuizUserAnswer", back_populates="question")

class QuizAnswerOption(Base):
    __tablename__ = "quiz_answer_options"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    option_text = Column(String(500), nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    order_index = Column(Integer, nullable=False, default=0)  # válaszok sorrendje
    
    # Relationships
    question = relationship("QuizQuestion", back_populates="answer_options")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    time_spent_minutes = Column(Float, nullable=True)  # ténylegesen eltöltött idő
    score = Column(Float, nullable=True)  # elért pont százalékban
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False, default=0)
    xp_awarded = Column(Integer, nullable=False, default=0)
    passed = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    user = relationship("User")
    quiz = relationship("Quiz", back_populates="attempts")
    user_answers = relationship("QuizUserAnswer", back_populates="attempt", cascade="all, delete-orphan")

class QuizUserAnswer(Base):
    __tablename__ = "quiz_user_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    selected_option_id = Column(Integer, ForeignKey("quiz_answer_options.id"), nullable=True)  # többválasztásos és igaz/hamis kérdésekhez
    answer_text = Column(String(1000), nullable=True)  # kiegészítős feladatokhoz
    is_correct = Column(Boolean, nullable=False, default=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    attempt = relationship("QuizAttempt", back_populates="user_answers")
    question = relationship("QuizQuestion", back_populates="user_answers")
    selected_option = relationship("QuizAnswerOption")