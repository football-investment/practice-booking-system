"""
Tests for session_generation/formats/individual_ranking_generator.py

Missing coverage targets:
  Lines 86-87:  tournament has no 'scoring_type' attribute → warning logged,
                then AttributeError on scoring_descriptions.get() → caught → re-raise
  Lines 119-121: number_of_rounds > 1 → scoring_type_value = 'ROUNDS_BASED'
  Lines 122-124: number_of_rounds == 1 → scoring_type_value = tournament.scoring_type
  Lines 168-174: except block → logs + re-raise
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.tournament.session_generation.formats.individual_ranking_generator import (
    IndividualRankingGenerator,
)


# ──────────────────── helpers ────────────────────


def _tournament(scoring_type="SCORE_BASED", name="Test Tournament"):
    t = MagicMock()
    t.id = 1
    t.name = name
    t.start_date = datetime(2026, 3, 1, 10, 0)
    t.end_date = datetime(2026, 4, 1)
    t.format = "INDIVIDUAL_RANKING"
    t.scoring_type = scoring_type
    t.campus = None
    t.location = None
    return t


def _db_with_enrollments(n=0):
    """DB returning n enrollments for the SemesterEnrollment query."""
    db = MagicMock()
    enrollments = []
    for i in range(n):
        e = MagicMock()
        e.user_id = i + 100
        enrollments.append(e)
    q = MagicMock()
    q.filter.return_value = q
    q.all.return_value = enrollments
    db.query.return_value = q
    return db


# ──────────────────── tests ────────────────────


class TestIndividualRankingGenerator:

    def test_single_round_preserves_scoring_type(self):
        """Lines 122-124: number_of_rounds=1 → scoring_type=tournament.scoring_type."""
        t = _tournament(scoring_type="SCORE_BASED")
        db = _db_with_enrollments(4)
        gen = IndividualRankingGenerator(db)

        result = gen.generate(
            t,
            tournament_type=None,
            player_count=4,
            parallel_fields=1,
            session_duration=90,
            break_minutes=15,
            number_of_rounds=1,
        )

        assert len(result) == 1
        assert result[0]["scoring_type"] == "SCORE_BASED"
        # structure_config preserves original scoring_method
        assert result[0]["structure_config"]["scoring_method"] == "SCORE_BASED"

    def test_multi_round_uses_rounds_based_scoring(self):
        """Lines 119-121: number_of_rounds=3 → scoring_type='ROUNDS_BASED'."""
        t = _tournament(scoring_type="TIME_BASED")
        db = _db_with_enrollments(4)
        gen = IndividualRankingGenerator(db)

        result = gen.generate(
            t,
            tournament_type=None,
            player_count=4,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            number_of_rounds=3,
        )

        assert len(result) == 1
        assert result[0]["scoring_type"] == "ROUNDS_BASED"
        # Underlying measurement type still stored in structure_config
        assert result[0]["structure_config"]["scoring_method"] == "TIME_BASED"

    def test_multi_round_total_duration_calculated(self):
        """Duration = (n_rounds * session_duration) + ((n_rounds - 1) * break)."""
        t = _tournament(scoring_type="DISTANCE_BASED")
        db = _db_with_enrollments(3)
        gen = IndividualRankingGenerator(db)

        result = gen.generate(
            t,
            tournament_type=None,
            player_count=3,
            parallel_fields=1,
            session_duration=90,
            break_minutes=15,
            number_of_rounds=3,
        )

        # Expected: (3 * 90) + (2 * 15) = 270 + 30 = 300 minutes
        session = result[0]
        delta = session["date_end"] - session["date_start"]
        assert int(delta.total_seconds() / 60) == 300

    def test_no_scoring_type_attribute_raises(self):
        """Lines 86-87, 168-174: tournament without scoring_type raises AttributeError."""

        class TournamentNoScoringType:
            """Mimics Semester without scoring_type attr."""
            id = 1
            name = "No Scoring Type"
            format = "INDIVIDUAL_RANKING"
            start_date = datetime(2026, 3, 1, 10, 0)
            end_date = datetime(2026, 4, 1)
            campus = None
            location = None
            # deliberately NO scoring_type attribute

        t = TournamentNoScoringType()
        db = _db_with_enrollments(2)
        gen = IndividualRankingGenerator(db)

        # AttributeError on t.scoring_type → caught → re-raise (lines 168-174)
        with pytest.raises(AttributeError):
            gen.generate(
                t,
                tournament_type=None,
                player_count=2,
                parallel_fields=1,
                session_duration=60,
                break_minutes=10,
            )

    def test_exception_reraise_preserves_original(self):
        """Lines 168-174: exception in generate() is re-raised unchanged."""
        t = _tournament()
        db = MagicMock()
        # Make the DB query blow up
        db.query.side_effect = RuntimeError("DB connection lost")
        gen = IndividualRankingGenerator(db)

        with pytest.raises(RuntimeError, match="DB connection lost"):
            gen.generate(
                t,
                tournament_type=None,
                player_count=4,
                parallel_fields=1,
                session_duration=90,
                break_minutes=15,
            )

    def test_campus_ids_picked_round_robin(self):
        """Multi-campus: pick_campus(0, campus_ids) called for single session."""
        t = _tournament(scoring_type="PLACEMENT")
        db = _db_with_enrollments(2)
        gen = IndividualRankingGenerator(db)

        result = gen.generate(
            t,
            tournament_type=None,
            player_count=2,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
            campus_ids=[10, 20],
        )

        # pick_campus(0, [10, 20]) = 10
        assert result[0]["campus_id"] == 10

    def test_no_campus_ids_returns_none(self):
        """campus_ids=None → pick_campus returns None → campus_id=None."""
        t = _tournament()
        db = _db_with_enrollments(2)
        gen = IndividualRankingGenerator(db)

        result = gen.generate(
            t,
            tournament_type=None,
            player_count=2,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
        )

        assert result[0]["campus_id"] is None

    def test_enrolled_player_ids_in_session(self):
        """participant_user_ids set from enrolled players."""
        t = _tournament()
        db = _db_with_enrollments(3)
        gen = IndividualRankingGenerator(db)

        result = gen.generate(
            t,
            tournament_type=None,
            player_count=3,
            parallel_fields=1,
            session_duration=60,
            break_minutes=10,
        )

        assert result[0]["participant_user_ids"] == [100, 101, 102]
