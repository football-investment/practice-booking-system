"""
Unit Tests for Lifecycle Helpers

Validates that helpers respect domain rules WITHOUT bypassing validation.
"""
import pytest
from sqlalchemy.orm import Session

from tests.integration.api_smoke.lifecycle_helpers import (
    transition_tournament_to_seeking_instructor,
    create_instructor_application
)
from app.models.semester import Semester, SemesterStatus
from app.models.user import User, UserRole
from app.models.instructor_assignment import InstructorAssignmentRequest, AssignmentRequestStatus


class TestTransitionToSeekingInstructor:
    """Test tournament status transition from DRAFT to SEEKING_INSTRUCTOR"""

    def test_valid_transition_from_draft(self, test_db: Session, test_tournament: dict):
        """Happy path: DRAFT → SEEKING_INSTRUCTOR"""
        tournament_id = test_tournament["tournament_id"]

        # Verify initial state is DRAFT
        tournament = test_db.query(Semester).filter(Semester.id == tournament_id).first()
        initial_status = tournament.status
        assert initial_status == SemesterStatus.DRAFT, f"Precondition failed: expected DRAFT, got {initial_status}"

        # Execute transition
        updated = transition_tournament_to_seeking_instructor(tournament_id, test_db)

        # Verify enum field updated
        assert updated.status == SemesterStatus.SEEKING_INSTRUCTOR, \
            f"Enum status not updated: {updated.status}"

        # Verify legacy string field synced
        assert updated.tournament_status == "SEEKING_INSTRUCTOR", \
            f"Legacy string not synced: {updated.tournament_status}"

        # Verify DB persistence (direct query)
        db_tournament = test_db.query(Semester).filter(Semester.id == tournament_id).first()
        assert db_tournament.status == SemesterStatus.SEEKING_INSTRUCTOR, \
            "Status not persisted to DB"

    def test_reject_non_draft_status(self, test_db: Session, test_tournament: dict):
        """Invalid: Cannot transition from non-DRAFT status"""
        tournament_id = test_tournament["tournament_id"]

        # Force tournament to ONGOING (simulating invalid precondition)
        tournament = test_db.query(Semester).filter(Semester.id == tournament_id).first()
        tournament.status = SemesterStatus.ONGOING
        test_db.commit()

        # Verify transition is rejected
        with pytest.raises(ValueError, match="must be in DRAFT status"):
            transition_tournament_to_seeking_instructor(tournament_id, test_db)

    def test_reject_nonexistent_tournament(self, test_db: Session):
        """Invalid: Tournament does not exist"""
        with pytest.raises(LookupError, match="not found"):
            transition_tournament_to_seeking_instructor(tournament_id=999999, db=test_db)


class TestCreateInstructorApplication:
    """Test instructor application creation"""

    def test_valid_application_creation(self, test_db: Session, test_tournament: dict, instructor_token: str):
        """Happy path: Create assignment request for SEEKING_INSTRUCTOR tournament"""
        tournament_id = test_tournament["tournament_id"]

        # Setup: Transition tournament to SEEKING_INSTRUCTOR
        transition_tournament_to_seeking_instructor(tournament_id, test_db)

        # Get instructor ID from token fixture
        instructor = test_db.query(User).filter(
            User.email == "smoke.instructor@generated.test"
        ).first()
        assert instructor is not None, "Instructor fixture not found"
        instructor_id = instructor.id

        # Execute: Create assignment request
        request = create_instructor_application(tournament_id, instructor_id, test_db)

        # Verify: Request created with correct status
        assert request.status == AssignmentRequestStatus.PENDING, \
            f"Wrong status: {request.status}"
        assert request.semester_id == tournament_id
        assert request.instructor_id == instructor_id

        # Verify: DB persistence (direct query)
        db_request = test_db.query(InstructorAssignmentRequest).filter(
            InstructorAssignmentRequest.id == request.id
        ).first()
        assert db_request is not None, "Request not persisted to DB"
        assert db_request.status == AssignmentRequestStatus.PENDING

    def test_reject_wrong_tournament_status(self, test_db: Session, test_tournament: dict, instructor_token: str):
        """Invalid: Cannot apply to tournament not in SEEKING_INSTRUCTOR"""
        tournament_id = test_tournament["tournament_id"]

        # Tournament is in DRAFT (not SEEKING_INSTRUCTOR)
        tournament = test_db.query(Semester).filter(Semester.id == tournament_id).first()
        assert tournament.status == SemesterStatus.DRAFT, "Precondition: tournament should be DRAFT"

        # Get instructor
        instructor = test_db.query(User).filter(
            User.email == "smoke.instructor@generated.test"
        ).first()

        # Verify: Application creation rejected
        with pytest.raises(ValueError, match="must be SEEKING_INSTRUCTOR"):
            create_instructor_application(tournament_id, instructor.id, test_db)

    def test_reject_duplicate_application(self, test_db: Session, test_tournament: dict, instructor_token: str):
        """Invalid: Instructor cannot have multiple assignment requests for same tournament"""
        tournament_id = test_tournament["tournament_id"]

        # Setup: Tournament in SEEKING_INSTRUCTOR
        transition_tournament_to_seeking_instructor(tournament_id, test_db)

        # Get instructor
        instructor = test_db.query(User).filter(
            User.email == "smoke.instructor@generated.test"
        ).first()

        # Create first request (should succeed)
        create_instructor_application(tournament_id, instructor.id, test_db)

        # Verify: Second request rejected
        with pytest.raises(ValueError, match="already has an assignment request"):
            create_instructor_application(tournament_id, instructor.id, test_db)

    def test_reject_nonexistent_tournament(self, test_db: Session, instructor_token: str):
        """Invalid: Tournament does not exist"""
        instructor = test_db.query(User).filter(
            User.email == "smoke.instructor@generated.test"
        ).first()

        with pytest.raises(LookupError, match="Tournament.*not found"):
            create_instructor_application(tournament_id=999999, instructor_id=instructor.id, db=test_db)

    def test_reject_nonexistent_instructor(self, test_db: Session, test_tournament: dict):
        """Invalid: Instructor does not exist"""
        tournament_id = test_tournament["tournament_id"]

        # Setup: Tournament in SEEKING_INSTRUCTOR
        transition_tournament_to_seeking_instructor(tournament_id, test_db)

        with pytest.raises(LookupError, match="Instructor.*not found"):
            create_instructor_application(tournament_id, instructor_id=999999, db=test_db)
