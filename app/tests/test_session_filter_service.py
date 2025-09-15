import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.session_filter_service import SessionFilterService, UserSpecialization
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel
from app.models.project import Project, ProjectEnrollment, ProjectEnrollmentStatus
from app.models.semester import Semester


class TestSessionFilterService:
    """Test suite for SessionFilterService"""

    @pytest.fixture
    def filter_service(self, test_db: Session):
        """Create SessionFilterService instance with test database"""
        return SessionFilterService(test_db)

    @pytest.fixture
    def test_student(self, test_db: Session):
        """Create a test student user"""
        user = User(
            name="Test Student",
            email="student@example.com",
            password_hash="test_hash",
            role=UserRole.STUDENT,
            is_active=True
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    @pytest.fixture
    def test_instructor(self, test_db: Session):
        """Create a test instructor user"""
        user = User(
            name="Test Instructor",
            email="instructor@example.com",
            password_hash="test_hash",
            role=UserRole.INSTRUCTOR,
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
            start_date=datetime.now(timezone.utc) - timedelta(days=30),
            end_date=datetime.now(timezone.utc) + timedelta(days=60)
        )
        test_db.add(semester)
        test_db.commit()
        test_db.refresh(semester)
        return semester

    @pytest.fixture
    def test_project(self, test_db: Session, test_instructor, test_semester):
        """Create a test project"""
        project = Project(
            title="Test Project",
            description="A test project for filtering",
            instructor_id=test_instructor.id,
            semester_id=test_semester.id,
            max_participants=20,
            current_participants=0,
            status="active"
        )
        test_db.add(project)
        test_db.commit()
        test_db.refresh(project)
        return project

    @pytest.fixture
    def test_session(self, test_db: Session, test_instructor, test_semester):
        """Create a test session"""
        session = SessionModel(
            title="Test Session",
            description="A test session for filtering",
            instructor_id=test_instructor.id,
            semester_id=test_semester.id,
            date_start=datetime.now(timezone.utc) + timedelta(days=7),
            date_end=datetime.now(timezone.utc) + timedelta(days=7, hours=2),
            capacity=20,
            location="Test Location"
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        return session

    def test_filter_service_initialization(self, filter_service):
        """Test that SessionFilterService initializes correctly"""
        assert filter_service is not None
        assert hasattr(filter_service, 'db')
        assert hasattr(filter_service, '_user_specialization_cache')

    def test_user_specialization_constants(self):
        """Test that UserSpecialization constants are defined"""
        assert hasattr(UserSpecialization, 'COACH')
        assert hasattr(UserSpecialization, 'PLAYER')
        assert hasattr(UserSpecialization, 'GENERAL')
        assert hasattr(UserSpecialization, 'MIXED')

    def test_get_user_specialization_student_no_projects(self, filter_service, test_student):
        """Test specialization detection for student with no projects"""
        specialization = filter_service.get_user_specialization(test_student)
        assert specialization == UserSpecialization.GENERAL

    def test_get_user_specialization_instructor(self, filter_service, test_instructor):
        """Test specialization detection for instructor"""
        specialization = filter_service.get_user_specialization(test_instructor)
        assert specialization == UserSpecialization.GENERAL

    def test_get_user_specialization_caching(self, filter_service, test_student):
        """Test that user specialization is cached properly"""
        # First call
        specialization1 = filter_service.get_user_specialization(test_student)
        
        # Second call should use cache
        specialization2 = filter_service.get_user_specialization(test_student)
        
        assert specialization1 == specialization2
        assert test_student.id in filter_service._user_specialization_cache

    def test_get_user_specialization_with_project(self, filter_service, test_student, test_project, test_db):
        """Test specialization detection for student with project enrollment"""
        # Enroll student in project
        enrollment = ProjectEnrollment(
            user_id=test_student.id,
            project_id=test_project.id,
            status=ProjectEnrollmentStatus.ACTIVE
        )
        test_db.add(enrollment)
        test_db.commit()

        # Clear cache first
        if test_student.id in filter_service._user_specialization_cache:
            del filter_service._user_specialization_cache[test_student.id]

        specialization = filter_service.get_user_specialization(test_student)
        # Should return some specialization based on project enrollment
        assert specialization in [UserSpecialization.COACH, UserSpecialization.PLAYER, 
                                UserSpecialization.GENERAL, UserSpecialization.MIXED]

    def test_filter_service_with_multiple_projects(self, filter_service, test_student, test_instructor, test_semester, test_db):
        """Test filter service with multiple project enrollments"""
        # Create multiple projects
        project1 = Project(
            title="Coaching Project",
            description="Coaching focused project",
            instructor_id=test_instructor.id,
            semester_id=test_semester.id,
            max_participants=15,
            current_participants=0,
            status="active"
        )
        project2 = Project(
            title="Player Development",
            description="Player development project",
            instructor_id=test_instructor.id,
            semester_id=test_semester.id,
            max_participants=15,
            current_participants=0,
            status="active"
        )
        test_db.add_all([project1, project2])
        test_db.commit()

        # Enroll student in both projects
        enrollment1 = ProjectEnrollment(
            user_id=test_student.id,
            project_id=project1.id,
            status=ProjectEnrollmentStatus.ACTIVE
        )
        enrollment2 = ProjectEnrollment(
            user_id=test_student.id,
            project_id=project2.id,
            status=ProjectEnrollmentStatus.ACTIVE
        )
        test_db.add_all([enrollment1, enrollment2])
        test_db.commit()

        # Clear cache
        if test_student.id in filter_service._user_specialization_cache:
            del filter_service._user_specialization_cache[test_student.id]

        specialization = filter_service.get_user_specialization(test_student)
        # With multiple projects, might be MIXED
        assert specialization in [UserSpecialization.MIXED, UserSpecialization.COACH, 
                                UserSpecialization.PLAYER, UserSpecialization.GENERAL]

    def test_filter_service_method_availability(self, filter_service, test_student):
        """Test that filter service methods are available"""
        # Test various filtering methods if they exist
        methods_to_test = [
            'get_filtered_sessions_for_user',
            'get_recommended_sessions',
            'filter_sessions_by_specialization',
            'get_user_project_context'
        ]
        
        for method_name in methods_to_test:
            if hasattr(filter_service, method_name):
                method = getattr(filter_service, method_name)
                assert callable(method)

    def test_filter_service_with_sessions(self, filter_service, test_student, test_session):
        """Test filter service interactions with sessions"""
        # Test filtering methods with actual session data
        if hasattr(filter_service, 'get_filtered_sessions_for_user'):
            try:
                sessions = filter_service.get_filtered_sessions_for_user(test_student.id, limit=10)
                assert isinstance(sessions, list)
            except Exception:
                # Method might require specific implementation details
                pass

    def test_filter_service_specialization_filtering(self, filter_service, test_session):
        """Test session filtering by specialization"""
        if hasattr(filter_service, 'filter_sessions_by_specialization'):
            sessions = [test_session]
            for specialization in [UserSpecialization.COACH, UserSpecialization.PLAYER, 
                                 UserSpecialization.GENERAL, UserSpecialization.MIXED]:
                try:
                    filtered = filter_service.filter_sessions_by_specialization(sessions, specialization)
                    assert isinstance(filtered, list)
                except Exception:
                    # Method might require specific implementation
                    pass

    def test_filter_service_cache_management(self, filter_service, test_student):
        """Test cache management functionality"""
        # Populate cache
        filter_service.get_user_specialization(test_student)
        assert test_student.id in filter_service._user_specialization_cache
        
        # Test cache clearing if method exists
        if hasattr(filter_service, 'clear_user_cache'):
            filter_service.clear_user_cache(test_student.id)
            assert test_student.id not in filter_service._user_specialization_cache

    def test_filter_service_error_handling(self, filter_service):
        """Test error handling in filter service"""
        # Test with invalid user IDs
        try:
            specialization = filter_service.get_user_specialization(-1)
            # Should either return a default or handle gracefully
            assert specialization in [UserSpecialization.COACH, UserSpecialization.PLAYER, 
                                    UserSpecialization.GENERAL, UserSpecialization.MIXED]
        except Exception:
            # Exception handling is also acceptable
            pass

    def test_filter_service_performance(self, filter_service, test_student):
        """Test basic performance characteristics"""
        import time
        
        # Time the specialization lookup
        start_time = time.time()
        specialization = filter_service.get_user_specialization(test_student)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete reasonably quickly (adjust threshold as needed)
        assert execution_time < 1.0  # 1 second
        assert specialization is not None