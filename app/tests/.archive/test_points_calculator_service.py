"""
Unit Tests for PointsCalculatorService

Tests the Unified Points Calculation System with tier/pod support:
- ALL_PARTICIPANTS mode: Standard ranking points
- GROUP_ISOLATED mode: Group-specific points
- TIERED mode: Tier-based multipliers (Knockout)
- QUALIFIED_ONLY mode: Knockout stage points
- PERFORMANCE_POD mode: Pod-based modifiers (Swiss)
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.tournament.points_calculator_service import PointsCalculatorService
from app.models.user import User, UserRole
from app.models.session import Session as SessionModel
from app.models.semester import Semester
from app.models.tournament_type import TournamentType


class TestPointsCalculatorService:
    """Test suite for PointsCalculatorService"""

    @pytest.fixture
    def points_calculator(self, db_session: Session):
        """Create PointsCalculatorService instance"""
        return PointsCalculatorService(db_session)

    @pytest.fixture
    def test_instructor(self, db_session: Session):
        """Create test instructor"""
        user = User(
            name="Test Instructor",
            email="instructor@test.com",
            password_hash="test_hash",
            role=UserRole.INSTRUCTOR,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def test_tournament_type(self, db_session: Session):
        """Create test tournament type with custom point scheme"""
        tournament_type = TournamentType(
            code="test_league",
            display_name="Test League",
            description="Test tournament type",
            min_players=4,
            max_players=16,
            requires_power_of_two=False,
            config={
                "point_scheme": {
                    1: 5,  # Custom: 1st place = 5 points
                    2: 3,  # 2nd place = 3 points
                    3: 2,  # 3rd place = 2 points
                    4: 1   # 4th place = 1 point
                }
            }
        )
        db_session.add(tournament_type)
        db_session.commit()
        db_session.refresh(tournament_type)
        return tournament_type

    @pytest.fixture
    def test_tournament(self, db_session: Session, test_instructor, test_tournament_type):
        """Create test tournament"""
        tournament = Semester(
            code="TEST/POINTS",
            name="Test Points Tournament",
            start_date=(datetime.now(timezone.utc) + timedelta(days=7)).date(),
            end_date=(datetime.now(timezone.utc) + timedelta(days=14)).date(),
            tournament_status="IN_PROGRESS",
            tournament_type_id=test_tournament_type.id,
            master_instructor_id=test_instructor.id
        )
        db_session.add(tournament)
        db_session.commit()
        db_session.refresh(tournament)
        return tournament

    # ========================================================================
    # TEST 1: Standard Ranking Points (ALL_PARTICIPANTS mode)
    # ========================================================================

    def test_standard_ranking_points(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Standard ranking points (1st=3pts, 2nd=2pts, 3rd=1pt)

        Expected:
        - 1st place: 3 points
        - 2nd place: 2 points
        - 3rd place: 1 point
        - 4th+ place: 0 points
        """
        # Create session with ALL_PARTICIPANTS mode
        session = SessionModel(
            title="League Round 1",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='ALL_PARTICIPANTS'
        )
        db_session.add(session)
        db_session.commit()

        # Test points calculation (using default point scheme)
        points_1st = points_calculator.calculate_points(
            session_id=session.id,
            user_id=1,
            rank=1
        )
        points_2nd = points_calculator.calculate_points(
            session_id=session.id,
            user_id=2,
            rank=2
        )
        points_3rd = points_calculator.calculate_points(
            session_id=session.id,
            user_id=3,
            rank=3
        )
        points_4th = points_calculator.calculate_points(
            session_id=session.id,
            user_id=4,
            rank=4
        )

        assert points_1st == 3.0
        assert points_2nd == 2.0
        assert points_3rd == 1.0
        assert points_4th == 0.0

    # ========================================================================
    # TEST 2: Custom Point Scheme from Tournament Type
    # ========================================================================

    def test_custom_point_scheme_from_config(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor,
        test_tournament_type
    ):
        """
        TEST: Custom point scheme from tournament type config

        Expected:
        - 1st place: 5 points (from config)
        - 2nd place: 3 points
        - 3rd place: 2 points
        - 4th place: 1 point
        """
        # Create session
        session = SessionModel(
            title="Custom Points Round",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='ALL_PARTICIPANTS'
        )
        db_session.add(session)
        db_session.commit()

        # Get tournament config
        tournament_config = points_calculator.get_tournament_type_config(test_tournament.id)

        # Calculate points with config
        points_1st = points_calculator.calculate_points(
            session_id=session.id,
            user_id=1,
            rank=1,
            tournament_type_config=tournament_config
        )
        points_2nd = points_calculator.calculate_points(
            session_id=session.id,
            user_id=2,
            rank=2,
            tournament_type_config=tournament_config
        )

        assert points_1st == 5.0  # Custom scheme
        assert points_2nd == 3.0

    # ========================================================================
    # TEST 3: Tier-Based Multipliers (TIERED mode - Knockout)
    # ========================================================================

    def test_tier_based_multipliers(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Tier-based multipliers for Knockout tournaments

        Expected:
        - Round 1 (tier=1): 1.0x multiplier → 1st=3pts
        - Round 2 (tier=2): 1.5x multiplier → 1st=4.5pts
        - Round 3 (tier=3): 2.0x multiplier → 1st=6pts
        """
        # Create sessions at different tiers
        session_r1 = SessionModel(
            title="Knockout R1",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='TIERED',
            pod_tier=1  # Tier 1
        )
        db_session.add(session_r1)

        session_r2 = SessionModel(
            title="Knockout R2",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc) + timedelta(days=1),
            date_end=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
            is_tournament_game=True,
            ranking_mode='TIERED',
            pod_tier=2  # Tier 2 (Semi-finals)
        )
        db_session.add(session_r2)

        session_r3 = SessionModel(
            title="Knockout R3",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc) + timedelta(days=2),
            date_end=datetime.now(timezone.utc) + timedelta(days=2, hours=2),
            is_tournament_game=True,
            ranking_mode='TIERED',
            pod_tier=3  # Tier 3 (Finals)
        )
        db_session.add(session_r3)

        db_session.commit()

        # Calculate points at different tiers
        points_r1 = points_calculator.calculate_points(
            session_id=session_r1.id,
            user_id=1,
            rank=1
        )
        points_r2 = points_calculator.calculate_points(
            session_id=session_r2.id,
            user_id=1,
            rank=1
        )
        points_r3 = points_calculator.calculate_points(
            session_id=session_r3.id,
            user_id=1,
            rank=1
        )

        assert points_r1 == 3.0    # 3 * 1.0
        assert points_r2 == 4.5    # 3 * 1.5
        assert points_r3 == 6.0    # 3 * 2.0

    # ========================================================================
    # TEST 4: Pod-Based Modifiers (PERFORMANCE_POD mode - Swiss)
    # ========================================================================

    def test_pod_based_modifiers(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Pod-based modifiers for Swiss System

        Expected:
        - Pod 1 (top): 1.2x modifier → 1st=3.6pts
        - Pod 2 (middle): 1.0x modifier → 1st=3.0pts
        - Pod 3 (bottom): 0.8x modifier → 1st=2.4pts
        """
        # Create sessions in different pods
        session_pod1 = SessionModel(
            title="Swiss R2 - Pod 1",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='PERFORMANCE_POD',
            pod_tier=1  # Top pod
        )
        db_session.add(session_pod1)

        session_pod2 = SessionModel(
            title="Swiss R2 - Pod 2",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='PERFORMANCE_POD',
            pod_tier=2  # Middle pod
        )
        db_session.add(session_pod2)

        session_pod3 = SessionModel(
            title="Swiss R2 - Pod 3",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='PERFORMANCE_POD',
            pod_tier=3  # Bottom pod
        )
        db_session.add(session_pod3)

        db_session.commit()

        # Calculate points in different pods
        points_pod1 = points_calculator.calculate_points(
            session_id=session_pod1.id,
            user_id=1,
            rank=1
        )
        points_pod2 = points_calculator.calculate_points(
            session_id=session_pod2.id,
            user_id=2,
            rank=1
        )
        points_pod3 = points_calculator.calculate_points(
            session_id=session_pod3.id,
            user_id=3,
            rank=1
        )

        assert abs(points_pod1 - 3.6) < 0.001  # 3 * 1.2 (tolerance for floating point)
        assert points_pod2 == 3.0  # 3 * 1.0
        assert abs(points_pod3 - 2.4) < 0.001  # 3 * 0.8 (tolerance for floating point)

    # ========================================================================
    # TEST 5: Batch Points Calculation
    # ========================================================================

    def test_batch_points_calculation(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Batch calculation for multiple players

        Expected:
        - Returns dict with all user_ids mapped to points
        - Efficient single-pass calculation
        """
        # Create session
        session = SessionModel(
            title="Batch Test",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='ALL_PARTICIPANTS'
        )
        db_session.add(session)
        db_session.commit()

        # Calculate points for 4 players
        rankings = [(101, 1), (102, 2), (103, 3), (104, 4)]
        points_map = points_calculator.calculate_points_batch(
            session_id=session.id,
            rankings=rankings
        )

        assert len(points_map) == 4
        assert points_map[101] == 3.0
        assert points_map[102] == 2.0
        assert points_map[103] == 1.0
        assert points_map[104] == 0.0

    # ========================================================================
    # TEST 6: Points Validation
    # ========================================================================

    def test_ranking_validation_duplicate_ranks(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Validation rejects duplicate ranks

        Expected:
        - validate_ranking returns (False, error_message)
        """
        session = SessionModel(
            title="Validation Test",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='ALL_PARTICIPANTS'
        )
        db_session.add(session)
        db_session.commit()

        # Duplicate rank 1
        rankings = [(101, 1), (102, 1), (103, 2)]

        is_valid, error_msg = points_calculator.validate_ranking(
            session_id=session.id,
            rankings=rankings
        )

        assert is_valid is False
        assert "duplicate" in error_msg.lower()

    def test_ranking_validation_missing_first_rank(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Validation requires ranks to start from 1

        Expected:
        - validate_ranking returns (False, error_message)
        """
        session = SessionModel(
            title="Validation Test 2",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='ALL_PARTICIPANTS'
        )
        db_session.add(session)
        db_session.commit()

        # Ranks start from 2 (missing 1)
        rankings = [(101, 2), (102, 3), (103, 4)]

        is_valid, error_msg = points_calculator.validate_ranking(
            session_id=session.id,
            rankings=rankings
        )

        assert is_valid is False
        assert "start from 1" in error_msg.lower()

    # ========================================================================
    # TEST 7: Points Summary
    # ========================================================================

    def test_points_summary(
        self,
        db_session: Session,
        points_calculator,
        test_tournament,
        test_instructor
    ):
        """
        TEST: Get points summary for a session

        Expected:
        - Returns dict with session info and point distribution
        - Includes total points awarded
        """
        session = SessionModel(
            title="Summary Test",
            semester_id=test_tournament.id,
            instructor_id=test_instructor.id,
            date_start=datetime.now(timezone.utc),
            date_end=datetime.now(timezone.utc) + timedelta(hours=2),
            is_tournament_game=True,
            ranking_mode='ALL_PARTICIPANTS',
            tournament_phase='League',
            tournament_round=1
        )
        db_session.add(session)
        db_session.commit()

        rankings = [(101, 1), (102, 2), (103, 3)]
        summary = points_calculator.get_points_summary(
            session_id=session.id,
            rankings=rankings
        )

        assert summary["session_id"] == session.id
        assert summary["session_title"] == "Summary Test"
        assert summary["ranking_mode"] == 'ALL_PARTICIPANTS'
        assert summary["tournament_phase"] == 'League'
        assert summary["tournament_round"] == 1
        assert len(summary["points_distribution"]) == 3
        # Note: Uses test_tournament which has custom point scheme (1st=5, 2nd=3, 3rd=2)
        assert abs(summary["total_points_awarded"] - 10.0) < 0.001  # 5 + 3 + 2 = 10
