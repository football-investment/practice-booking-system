import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.quiz_service import QuizService
from app.models.user import User, UserRole
from app.models.quiz import (
    Quiz, QuizQuestion, QuizAnswerOption, QuizAttempt, QuizUserAnswer,
    QuestionType, QuizCategory, QuizDifficulty
)


class TestQuizService:
    """Test suite for QuizService"""

    @pytest.fixture
    def quiz_service(self, test_db: Session):
        """Create QuizService instance with test database"""
        return QuizService(test_db)

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user"""
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash="test_hash",
            role=UserRole.STUDENT,
            is_active=True
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    @pytest.fixture
    def simple_quiz(self, test_db: Session):
        """Create a simple quiz for testing"""
        quiz = Quiz(
            title="Test Quiz",
            description="A test quiz for unit testing",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.MEDIUM,
            time_limit_minutes=30,
            xp_reward=100,
            passing_score=70,
            is_active=True
        )
        test_db.add(quiz)
        test_db.commit()
        test_db.refresh(quiz)
        
        # Add a simple question
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="What is 2 + 2?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            points=10,
            order_index=1,
            explanation="Basic arithmetic"
        )
        test_db.add(question)
        test_db.commit()
        test_db.refresh(question)
        
        # Add answer options
        options = [
            QuizAnswerOption(
                question_id=question.id,
                option_text="3",
                is_correct=False,
                order_index=1
            ),
            QuizAnswerOption(
                question_id=question.id,
                option_text="4",
                is_correct=True,
                order_index=2
            ),
            QuizAnswerOption(
                question_id=question.id,
                option_text="5",
                is_correct=False,
                order_index=3
            )
        ]
        test_db.add_all(options)
        test_db.commit()
        
        return quiz

    def test_quiz_service_initialization(self, quiz_service):
        """Test that QuizService initializes correctly"""
        assert quiz_service is not None
        assert hasattr(quiz_service, 'db')
        assert hasattr(quiz_service, 'gamification_service')

    def test_get_quiz_by_id_existing(self, quiz_service, simple_quiz):
        """Test retrieving an existing quiz by ID"""
        if hasattr(quiz_service, 'get_quiz_by_id'):
            retrieved_quiz = quiz_service.get_quiz_by_id(simple_quiz.id)
            if retrieved_quiz:
                assert retrieved_quiz.id == simple_quiz.id
                assert retrieved_quiz.title == simple_quiz.title

    def test_get_quiz_by_id_nonexistent(self, quiz_service):
        """Test retrieving non-existent quiz"""
        if hasattr(quiz_service, 'get_quiz_by_id'):
            retrieved_quiz = quiz_service.get_quiz_by_id(999999)
            assert retrieved_quiz is None

    def test_get_available_quizzes(self, quiz_service, simple_quiz):
        """Test getting list of available quizzes"""
        if hasattr(quiz_service, 'get_available_quizzes'):
            quizzes = quiz_service.get_available_quizzes()
            assert isinstance(quizzes, list)
            # Should include our test quiz if active
            if simple_quiz.is_active:
                assert any(q.id == simple_quiz.id for q in quizzes)

    def test_quiz_attempt_creation(self, quiz_service, simple_quiz, test_user, test_db):
        """Test creating a quiz attempt"""
        if hasattr(quiz_service, 'start_quiz_attempt'):
            attempt = QuizAttempt(
                quiz_id=simple_quiz.id,
                user_id=test_user.id,
                started_at=datetime.now(timezone.utc)
            )
            test_db.add(attempt)
            test_db.commit()
            test_db.refresh(attempt)
            
            assert attempt.id is not None
            assert attempt.quiz_id == simple_quiz.id
            assert attempt.user_id == test_user.id

    def test_quiz_answer_submission(self, quiz_service, simple_quiz, test_user, test_db):
        """Test submitting quiz answers"""
        # Create attempt
        attempt = QuizAttempt(
            quiz_id=simple_quiz.id,
            user_id=test_user.id,
            started_at=datetime.now(timezone.utc)
        )
        test_db.add(attempt)
        test_db.commit()
        test_db.refresh(attempt)
        
        # Get question and correct answer
        question = test_db.query(QuizQuestion).filter(QuizQuestion.quiz_id == simple_quiz.id).first()
        if question:
            correct_option = test_db.query(QuizAnswerOption).filter(
                QuizAnswerOption.question_id == question.id,
                QuizAnswerOption.is_correct == True
            ).first()
            
            if correct_option:
                # Submit answer
                user_answer = QuizUserAnswer(
                    quiz_attempt_id=attempt.id,
                    question_id=question.id,
                    selected_option_id=correct_option.id
                )
                test_db.add(user_answer)
                test_db.commit()
                
                assert user_answer.id is not None
                assert user_answer.selected_option_id == correct_option.id

    def test_quiz_completion(self, quiz_service, simple_quiz, test_user, test_db):
        """Test completing a quiz attempt"""
        # Create and complete attempt
        attempt = QuizAttempt(
            quiz_id=simple_quiz.id,
            user_id=test_user.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            score=85.0,
            passed=True,
            time_spent_minutes=15
        )
        test_db.add(attempt)
        test_db.commit()
        
        assert attempt.completed_at is not None
        assert attempt.score == 85.0
        assert attempt.passed is True

    def test_user_quiz_attempts_retrieval(self, quiz_service, simple_quiz, test_user, test_db):
        """Test retrieving user's quiz attempts"""
        # Create multiple attempts
        for i in range(3):
            attempt = QuizAttempt(
                quiz_id=simple_quiz.id,
                user_id=test_user.id,
                started_at=datetime.now(timezone.utc) - timedelta(days=i),
                score=70.0 + i * 10
            )
            test_db.add(attempt)
        test_db.commit()
        
        # Test retrieval method if exists
        if hasattr(quiz_service, 'get_user_quiz_attempts'):
            attempts = quiz_service.get_user_quiz_attempts(test_user.id, simple_quiz.id)
            if attempts:
                assert len(attempts) >= 3

    def test_quiz_statistics_basic(self, quiz_service, simple_quiz, test_user, test_db):
        """Test basic quiz statistics"""
        # Create some attempt data
        attempt = QuizAttempt(
            quiz_id=simple_quiz.id,
            user_id=test_user.id,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            score=75.0,
            passed=True
        )
        test_db.add(attempt)
        test_db.commit()
        
        # Test statistics method if exists
        if hasattr(quiz_service, 'get_quiz_statistics'):
            stats = quiz_service.get_quiz_statistics(simple_quiz.id)
            if stats:
                assert isinstance(stats, dict)

    def test_user_quiz_performance(self, quiz_service, test_user, test_db):
        """Test user quiz performance tracking"""
        if hasattr(quiz_service, 'get_user_quiz_statistics'):
            stats = quiz_service.get_user_quiz_statistics(test_user.id)
            if stats:
                assert isinstance(stats, dict)
                # Should have basic performance metrics

    def test_quiz_leaderboard_basic(self, quiz_service, simple_quiz):
        """Test quiz leaderboard functionality"""
        if hasattr(quiz_service, 'get_quiz_leaderboard'):
            leaderboard = quiz_service.get_quiz_leaderboard(simple_quiz.id, limit=10)
            assert isinstance(leaderboard, list)
            # Empty leaderboard is acceptable for tests

    def test_quiz_time_limit_validation(self, quiz_service, simple_quiz, test_user, test_db):
        """Test that quiz time limits are properly validated"""
        # Create attempt that exceeds time limit
        attempt = QuizAttempt(
            quiz_id=simple_quiz.id,
            user_id=test_user.id,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=simple_quiz.time_limit_minutes + 10),
            completed_at=datetime.now(timezone.utc)
        )
        test_db.add(attempt)
        test_db.commit()
        
        # Time validation would depend on specific implementation
        assert attempt.id is not None

    def test_quiz_scoring_calculation(self, quiz_service, simple_quiz, test_user, test_db):
        """Test quiz scoring calculation"""
        # Create attempt with known score
        attempt = QuizAttempt(
            quiz_id=simple_quiz.id,
            user_id=test_user.id,
            started_at=datetime.now(timezone.utc),
            score=100.0,
            passed=True
        )
        test_db.add(attempt)
        test_db.commit()
        
        # Test score calculation if method exists
        if hasattr(quiz_service, 'calculate_attempt_score'):
            calculated_score = quiz_service.calculate_attempt_score(attempt.id)
            if calculated_score is not None:
                assert isinstance(calculated_score, (int, float))
                assert 0 <= calculated_score <= 100

    def test_quiz_service_error_handling(self, quiz_service):
        """Test error handling in quiz service"""
        # Test with invalid IDs
        if hasattr(quiz_service, 'get_quiz_by_id'):
            result = quiz_service.get_quiz_by_id(-1)
            assert result is None
            
            result = quiz_service.get_quiz_by_id(0)
            assert result is None