"""
Integration tests for ResultProcessor — Round 2A: INDIVIDUAL_RANKING path

Uses real PostgreSQL with SAVEPOINT isolation (test_db fixture).

What is tested:
  Full orchestration chain for INDIVIDUAL_RANKING:
    process_match_results
      → _process_individual_ranking_tournament
        → get_or_create_ranking  (creates TournamentRanking rows in DB)
        → db.flush               (points written)
        → calculate_ranks        (reads ranking rows, assigns .rank)
        → session.game_results   (JSONB updated on the Session row)

What is NOT tested:
  - Internal service call order (no mock assertions)
  - PointsCalculatorService (not invoked in IR path)
  - KnockoutProgressionService (not invoked in IR path)

Why INDIVIDUAL_RANKING is the easiest integration path:
  Semester.format property falls back to "INDIVIDUAL_RANKING" (Priority 3)
  when no TournamentConfiguration exists — zero extra DB rows required.

Fixture dependency tree (all function-scoped, SAVEPOINT-isolated):
  test_db
  ├── instructor_user          (from tests/integration/conftest.py)
  ├── ir_tournament            (local: plain Semester, no config)
  ├── ir_session               (local: Session linked to ir_tournament)
  └── two_ir_students          (local: 2 User rows, UUID-suffixed)
"""
import json
import uuid
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.semester import Semester, SemesterStatus
from app.models.session import Session as SessionModel, SessionType
from app.models.user import User, UserRole
from app.models.tournament_ranking import TournamentRanking
from app.services.tournament.result_processor import ResultProcessor
from app.core.security import get_password_hash


# ============================================================================
# Local fixtures — Round 2A only, no conftest changes
# ============================================================================

@pytest.fixture
def ir_tournament(test_db: Session) -> Semester:
    """
    Plain Semester with NO TournamentConfiguration.
    Semester.format → Priority 3 default → "INDIVIDUAL_RANKING".
    No master_instructor required (nullable FK).
    """
    sem = Semester(
        code=f"IR-{uuid.uuid4().hex[:8]}",
        name="IR Integration Test Tournament",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        status=SemesterStatus.ONGOING,
    )
    test_db.add(sem)
    test_db.commit()
    test_db.refresh(sem)
    return sem


@pytest.fixture
def ir_session(test_db: Session, ir_tournament: Semester, instructor_user: User) -> SessionModel:
    """
    Minimal tournament session linked to ir_tournament.
    is_tournament_game=True so that calculate_ranks can detect scoring_type.
    No match_format set — defaults to None → "INDIVIDUAL_RANKING" in the processor.
    """
    session_start = datetime.now() + timedelta(days=1)
    sess = SessionModel(
        title="IR Integration Test Session",
        date_start=session_start,
        date_end=session_start + timedelta(hours=2),
        session_type=SessionType.on_site,
        capacity=20,
        instructor_id=instructor_user.id,
        semester_id=ir_tournament.id,
        is_tournament_game=True,
    )
    test_db.add(sess)
    test_db.commit()
    test_db.refresh(sess)
    return sess


@pytest.fixture
def two_ir_students(test_db: Session):
    """Two STUDENT users for use as participants in IR tests."""
    users = []
    for i in range(2):
        u = User(
            email=f"ir-student-{i}-{uuid.uuid4().hex[:6]}@test.com",
            name=f"IR Student {i}",
            password_hash=get_password_hash("test"),
            role=UserRole.STUDENT,
            is_active=True,
        )
        test_db.add(u)
        users.append(u)
    test_db.commit()
    for u in users:
        test_db.refresh(u)
    return users


# ============================================================================
# TestProcessMatchResultsIR — INDIVIDUAL_RANKING orchestration
# ============================================================================

@pytest.mark.integration
class TestProcessMatchResultsIR:
    """
    Validates the full DB-writing pipeline for INDIVIDUAL_RANKING tournaments.

    Assertions target final DB state, not implementation internals.
    """

    def test_happy_path_two_users_creates_ranking_rows(
        self,
        test_db: Session,
        ir_tournament: Semester,
        ir_session: SessionModel,
        two_ir_students: list,
    ):
        """
        Two users with distinct measured_value:
          - TournamentRanking rows created for both
          - points stored as Decimal(measured_value)
          - higher measured_value gets rank 1 (default DESC ranking_direction)
        """
        user_a, user_b = two_ir_students
        raw_results = [
            {"user_id": user_a.id, "measured_value": 100},
            {"user_id": user_b.id, "measured_value": 50},
        ]

        proc = ResultProcessor(db=test_db)
        proc.process_match_results(
            db=test_db,
            session=ir_session,
            tournament=ir_tournament,
            raw_results=raw_results,
        )

        # ── DB state assertions ──────────────────────────────────────────────
        rankings = (
            test_db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == ir_tournament.id)
            .all()
        )
        assert len(rankings) == 2, "Expected exactly 2 TournamentRanking rows"

        by_user = {r.user_id: r for r in rankings}
        assert user_a.id in by_user
        assert user_b.id in by_user

        # Points stored exactly as measured_value
        assert by_user[user_a.id].points == Decimal("100")
        assert by_user[user_b.id].points == Decimal("50")

        # Ranks assigned: higher points → better rank (lower number) with DESC direction
        assert by_user[user_a.id].rank == 1
        assert by_user[user_b.id].rank == 2

    def test_single_participant_gets_rank_1(
        self,
        test_db: Session,
        ir_tournament: Semester,
        ir_session: SessionModel,
        two_ir_students: list,
    ):
        """
        Single result entry: exactly one TournamentRanking row, rank=1.
        calculate_ranks must not crash with a single-row tournament.
        """
        solo_user = two_ir_students[0]
        raw_results = [{"user_id": solo_user.id, "measured_value": 42.5}]

        proc = ResultProcessor(db=test_db)
        proc.process_match_results(
            db=test_db,
            session=ir_session,
            tournament=ir_tournament,
            raw_results=raw_results,
        )

        rankings = (
            test_db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == ir_tournament.id)
            .all()
        )
        assert len(rankings) == 1
        assert rankings[0].rank == 1
        assert rankings[0].points == Decimal("42.5")

    def test_game_results_json_structure(
        self,
        test_db: Session,
        ir_tournament: Semester,
        ir_session: SessionModel,
        two_ir_students: list,
    ):
        """
        session.game_results is updated with valid JSON containing the
        documented keys: recorded_at, tournament_format, raw_results,
        derived_rankings.
        tournament_format must be "INDIVIDUAL_RANKING".
        derived_rankings must contain one entry per participant.
        """
        user_a, user_b = two_ir_students
        raw_results = [
            {"user_id": user_a.id, "measured_value": 75},
            {"user_id": user_b.id, "measured_value": 25},
        ]

        proc = ResultProcessor(db=test_db)
        proc.process_match_results(
            db=test_db,
            session=ir_session,
            tournament=ir_tournament,
            raw_results=raw_results,
        )

        # game_results must be set on the session
        test_db.refresh(ir_session)
        assert ir_session.game_results is not None, "session.game_results must be set"

        data = json.loads(ir_session.game_results)

        # Required top-level keys
        for key in ("recorded_at", "tournament_format", "raw_results", "derived_rankings"):
            assert key in data, f"Missing key in game_results: {key!r}"

        # Format marker
        assert data["tournament_format"] == "INDIVIDUAL_RANKING"

        # derived_rankings: one entry per participant
        assert isinstance(data["derived_rankings"], list)
        assert len(data["derived_rankings"]) == 2

        # Each derived ranking entry has user_id, rank, measured_value
        for entry in data["derived_rankings"]:
            assert "user_id" in entry
            assert "rank" in entry
            assert "measured_value" in entry

    def test_idempotent_reprocessing_updates_points(
        self,
        test_db: Session,
        ir_tournament: Semester,
        ir_session: SessionModel,
        two_ir_students: list,
    ):
        """
        Calling process_match_results twice for the same user:
        get_or_create_ranking returns the existing row on the second call,
        and points are overwritten (not accumulated).
        Final state: 2 rows (not 4), updated points.
        """
        user_a, user_b = two_ir_students
        proc = ResultProcessor(db=test_db)

        # First submission
        proc.process_match_results(
            db=test_db,
            session=ir_session,
            tournament=ir_tournament,
            raw_results=[
                {"user_id": user_a.id, "measured_value": 10},
                {"user_id": user_b.id, "measured_value": 5},
            ],
        )

        # Second submission with updated values
        proc.process_match_results(
            db=test_db,
            session=ir_session,
            tournament=ir_tournament,
            raw_results=[
                {"user_id": user_a.id, "measured_value": 90},
                {"user_id": user_b.id, "measured_value": 80},
            ],
        )

        rankings = (
            test_db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == ir_tournament.id)
            .all()
        )
        # Still 2 rows — no duplicates created
        assert len(rankings) == 2

        by_user = {r.user_id: r for r in rankings}
        # Points reflect the second submission
        assert by_user[user_a.id].points == Decimal("90")
        assert by_user[user_b.id].points == Decimal("80")

    def test_missing_required_field_raises_before_db_write(
        self,
        test_db: Session,
        ir_tournament: Semester,
        ir_session: SessionModel,
        two_ir_students: list,
    ):
        """
        Raw result missing 'measured_value' → ValueError raised,
        no TournamentRanking rows written.
        """
        user_a = two_ir_students[0]
        proc = ResultProcessor(db=test_db)

        with pytest.raises(ValueError, match="measured_value"):
            proc.process_match_results(
                db=test_db,
                session=ir_session,
                tournament=ir_tournament,
                raw_results=[{"user_id": user_a.id}],  # missing measured_value
            )

        count = (
            test_db.query(TournamentRanking)
            .filter(TournamentRanking.tournament_id == ir_tournament.id)
            .count()
        )
        assert count == 0, "No DB rows should be written on validation failure"
