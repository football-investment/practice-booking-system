import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.gamification import GamificationService
from app.models.user import User, UserRole
from app.models.gamification import UserStats, UserAchievement, BadgeType
from app.models.booking import Booking, BookingStatus
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.models.attendance import Attendance, AttendanceStatus
from app.models.feedback import Feedback


class TestGamificationService:
    """Test suite for GamificationService"""

    @pytest.fixture
    def gamification_service(self, test_db: Session):
        """Create GamificationService instance with test database"""
        return GamificationService(test_db)

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
    def test_semester(self, test_db: Session):
        """Create a test semester"""
        semester = Semester(
            name="Test Semester",
            start_date=datetime.now(timezone.utc) - timedelta(days=90),
            end_date=datetime.now(timezone.utc) + timedelta(days=90)
        )
        test_db.add(semester)
        test_db.commit()
        test_db.refresh(semester)
        return semester

    @pytest.fixture
    def test_session(self, test_db: Session, test_user, test_semester):
        """Create a test session"""
        session = SessionModel(
            title="Test Session",
            description="Test Description",
            instructor_id=test_user.id,
            semester_id=test_semester.id,
            date_start=datetime.now(timezone.utc) - timedelta(days=7),
            date_end=datetime.now(timezone.utc) - timedelta(days=7, hours=-2),
            capacity=10,
            location="Test Location"
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session

    def test_get_or_create_user_stats_new_user(self, gamification_service, test_user):
        """Test creating new user stats"""
        stats = gamification_service.get_or_create_user_stats(test_user.id)
        
        assert stats is not None
        assert stats.user_id == test_user.id

    def test_get_or_create_user_stats_existing_user(self, gamification_service, test_user, test_db):
        """Test retrieving existing user stats"""
        # Create existing stats
        existing_stats = UserStats(
            user_id=test_user.id,
            total_xp=100
        )
        test_db.add(existing_stats)
        test_db.commit()

        stats = gamification_service.get_or_create_user_stats(test_user.id)
        
        assert stats.user_id == test_user.id
        assert stats.total_xp == 100

    def test_calculate_user_stats_basic(self, gamification_service, test_user):
        """Test basic user stats calculation"""
        stats = gamification_service.calculate_user_stats(test_user.id)
        
        assert stats is not None
        assert stats.user_id == test_user.id
        assert hasattr(stats, 'total_xp')
        assert hasattr(stats, 'level')

    def test_award_achievement_new(self, gamification_service, test_user, test_db):
        """Test awarding a new achievement"""
        achievement = gamification_service.award_achievement(
            user_id=test_user.id,
            badge_type=BadgeType.RETURNING_STUDENT,
            title="Test Achievement",
            description="Test Description",
            icon="🏆"
        )
        
        assert achievement is not None
        assert achievement.user_id == test_user.id
        assert achievement.title == "Test Achievement"

    def test_award_achievement_existing(self, gamification_service, test_user, test_db):
        """Test awarding an existing achievement returns the existing one"""
        # Award first time
        achievement1 = gamification_service.award_achievement(
            user_id=test_user.id,
            badge_type=BadgeType.RETURNING_STUDENT,
            title="Test Achievement",
            description="Test Description",
            icon="🏆"
        )
        
        # Award again - should return existing
        achievement2 = gamification_service.award_achievement(
            user_id=test_user.id,
            badge_type=BadgeType.RETURNING_STUDENT,
            title="Test Achievement 2",
            description="Different Description",
            icon="🏆"
        )
        
        assert achievement1.id == achievement2.id

    def test_check_and_award_semester_achievements(self, gamification_service, test_user, test_session, test_db):
        """Test semester achievement checking"""
        # Create multiple semesters and bookings
        semester2 = Semester(
            name="Test Semester 2",
            start_date=datetime.now(timezone.utc) - timedelta(days=180),
            end_date=datetime.now(timezone.utc) - timedelta(days=90)
        )
        test_db.add(semester2)
        test_db.commit()

        session2 = SessionModel(
            title="Test Session 2",
            description="Test Description 2",
            instructor_id=test_user.id,
            semester_id=semester2.id,
            date_start=datetime.now(timezone.utc) - timedelta(days=180),
            date_end=datetime.now(timezone.utc) - timedelta(days=180, hours=-2),
            capacity=10,
            location="Test Location 2"
        )
        test_db.add(session2)
        test_db.commit()

        # Create bookings in both semesters
        booking1 = Booking(
            user_id=test_user.id,
            session_id=test_session.id,
            status=BookingStatus.CONFIRMED
        )
        booking2 = Booking(
            user_id=test_user.id,
            session_id=session2.id,
            status=BookingStatus.CONFIRMED
        )
        test_db.add_all([booking1, booking2])
        test_db.commit()

        achievements = gamification_service.check_and_award_semester_achievements(test_user.id)
        
        assert isinstance(achievements, list)
        # Should award returning student achievement (2+ semesters)
        assert len(achievements) >= 1

    def test_get_user_gamification_data(self, gamification_service, test_user):
        """Test getting complete gamification data"""
        data = gamification_service.get_user_gamification_data(test_user.id)
        
        assert isinstance(data, dict)
        assert 'stats' in data
        assert 'achievements' in data
        assert 'progress' in data