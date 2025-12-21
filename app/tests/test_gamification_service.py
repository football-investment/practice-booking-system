import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.gamification import GamificationService
from app.models.user import User, UserRole
from app.models.gamification import UserStats, UserAchievement, BadgeType
from app.models.booking import Booking, BookingStatus
from app.models.session import Session as SessionTypel
from app.models.semester import Semester
from app.models.attendance import Attendance, AttendanceStatus
from app.models.feedback import Feedback


class TestGamificationService:
    """Test suite for GamificationService"""

    @pytest.fixture
    def gamification_service(self, db_session: Session):
        """Create GamificationService instance with test database"""
        return GamificationService(db_session)

    @pytest.fixture
    def test_user(self, db_session: Session):
        """Create a test user"""
        user = User(
            name="Test User",
            email="test@example.com", 
            password_hash="test_hash",
            role=UserRole.STUDENT,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def test_semester(self, db_session: Session):
        """Create a test semester"""
        semester = Semester(
            code="TEST/2025",
            name="Test Semester",
            start_date=datetime.now(timezone.utc) - timedelta(days=90),
            end_date=datetime.now(timezone.utc) + timedelta(days=90)
        )
        db_session.add(semester)
        db_session.commit()
        db_session.refresh(semester)
        return semester

    @pytest.fixture
    def test_session(self, db_session: Session, test_user, test_semester):
        """Create a test session"""
        session = SessionTypel(
            title="Test Session",
            description="Test Description",
            instructor_id=test_user.id,
            semester_id=test_semester.id,
            date_start=datetime.now(timezone.utc) - timedelta(days=7),
            date_end=datetime.now(timezone.utc) - timedelta(days=7, hours=-2),
            capacity=10,
            location="Test Location"
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    def test_get_or_create_user_stats_new_user(self, gamification_service, test_user):
        """Test creating new user stats"""
        stats = gamification_service.get_or_create_user_stats(test_user.id)
        
        assert stats is not None
        assert stats.user_id == test_user.id

    def test_get_or_create_user_stats_existing_user(self, gamification_service, test_user, db_session):
        """Test retrieving existing user stats"""
        # Create existing stats
        existing_stats = UserStats(
            user_id=test_user.id,
            total_xp=100
        )
        db_session.add(existing_stats)
        db_session.commit()

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

    def test_award_achievement_new(self, gamification_service, test_user, db_session):
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

    def test_award_achievement_existing(self, gamification_service, test_user, db_session):
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

    def test_check_and_award_semester_achievements(self, gamification_service, test_user, test_session, db_session):
        """Test semester achievement checking"""
        # Create multiple semesters and bookings
        semester2 = Semester(
            code="TEST/2024",
            name="Test Semester 2",
            start_date=datetime.now(timezone.utc) - timedelta(days=180),
            end_date=datetime.now(timezone.utc) - timedelta(days=90)
        )
        db_session.add(semester2)
        db_session.commit()

        session2 = SessionTypel(
            title="Test Session 2",
            description="Test Description 2",
            instructor_id=test_user.id,
            semester_id=semester2.id,
            date_start=datetime.now(timezone.utc) - timedelta(days=180),
            date_end=datetime.now(timezone.utc) - timedelta(days=180, hours=-2),
            capacity=10,
            location="Test Location 2"
        )
        db_session.add(session2)
        db_session.commit()

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
        db_session.add_all([booking1, booking2])
        db_session.commit()

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
        assert 'next_level' in data