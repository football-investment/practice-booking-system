"""
Unit tests — tournaments/generator.py

Covers:
  - TournamentGenerateRequest validators (5 validators)
  - list_tournaments_admin
  - generate_tournament
  - send_instructor_request
  - accept_instructor_request
  - decline_instructor_request
  - get_tournament_summary
  - get_instructor_tournament_requests
  - delete_tournament
  - get_reward_policies
  - get_reward_policy_details
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.api_v1.endpoints.tournaments.generator import (
    TournamentGenerateRequest,
    list_tournaments_admin,
    generate_tournament,
    send_instructor_request,
    accept_instructor_request,
    decline_instructor_request,
    get_tournament_summary,
    get_instructor_tournament_requests,
    delete_tournament,
    get_reward_policies,
    get_reward_policy_details,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.tournaments.generator"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _user(role=UserRole.ADMIN, uid=42):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.nickname = None
    return u


def _db():
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = []
    q.first.return_value = None
    q.group_by.return_value = q
    db.query.return_value = q
    return db


# ─── TournamentGenerateRequest Validators ────────────────────────────────────

# Base data that produces a valid HEAD_TO_HEAD request
_H2H_BASE = {
    "date": "2099-01-01",
    "name": "Test Cup",
    "specialization_type": "LFA_FOOTBALL_PLAYER",
    "assignment_type": "OPEN_ASSIGNMENT",
    "max_players": 8,
    "enrollment_cost": 0,
    "format": "HEAD_TO_HEAD",
    "scoring_type": "PLACEMENT",
    "tournament_type_id": 1,
}

# Base data for INDIVIDUAL_RANKING
_IND_BASE = {
    "date": "2099-01-01",
    "name": "Sprint Challenge",
    "specialization_type": "LFA_FOOTBALL_PLAYER",
    "assignment_type": "OPEN_ASSIGNMENT",
    "max_players": 8,
    "enrollment_cost": 0,
    "format": "INDIVIDUAL_RANKING",
    "scoring_type": "PLACEMENT",
    "tournament_type_id": None,
}


@pytest.mark.unit
@pytest.mark.tournament
class TestMeasurementUnitValidator:
    def test_head_to_head_measurement_unit_forced_to_none(self):
        req = TournamentGenerateRequest(**{**_H2H_BASE, "measurement_unit": "seconds"})
        assert req.measurement_unit is None

    def test_placement_measurement_unit_forced_to_none(self):
        req = TournamentGenerateRequest(**{**_IND_BASE, "measurement_unit": "meters"})
        assert req.measurement_unit is None

    def test_time_based_valid_unit_passes(self):
        req = TournamentGenerateRequest(**{**_IND_BASE,
            "scoring_type": "TIME_BASED",
            "measurement_unit": "seconds",
            "ranking_direction": "ASC",
        })
        assert req.measurement_unit == "seconds"

    def test_time_based_none_unit_raises(self):
        with pytest.raises(ValidationError, match="measurement_unit"):
            TournamentGenerateRequest(**{**_IND_BASE,
                "scoring_type": "TIME_BASED",
                "measurement_unit": None,
                "ranking_direction": "ASC",
            })

    def test_time_based_invalid_unit_raises(self):
        with pytest.raises(ValidationError):
            TournamentGenerateRequest(**{**_IND_BASE,
                "scoring_type": "TIME_BASED",
                "measurement_unit": "kilograms",
                "ranking_direction": "ASC",
            })

    def test_distance_based_valid_unit(self):
        req = TournamentGenerateRequest(**{**_IND_BASE,
            "scoring_type": "DISTANCE_BASED",
            "measurement_unit": "meters",
            "ranking_direction": "DESC",
        })
        assert req.measurement_unit == "meters"

    def test_score_based_valid_unit(self):
        req = TournamentGenerateRequest(**{**_IND_BASE,
            "scoring_type": "SCORE_BASED",
            "measurement_unit": "points",
            "ranking_direction": "DESC",
        })
        assert req.measurement_unit == "points"


@pytest.mark.unit
@pytest.mark.tournament
class TestRankingDirectionValidator:
    def test_head_to_head_always_desc(self):
        req = TournamentGenerateRequest(**{**_H2H_BASE, "ranking_direction": "ASC"})
        assert req.ranking_direction == "DESC"

    def test_placement_direction_is_none(self):
        req = TournamentGenerateRequest(**_IND_BASE)
        assert req.ranking_direction is None

    def test_individual_non_placement_requires_direction(self):
        with pytest.raises(ValidationError):
            TournamentGenerateRequest(**{**_IND_BASE,
                "scoring_type": "SCORE_BASED",
                "measurement_unit": "points",
                "ranking_direction": None,
            })

    def test_individual_invalid_direction_raises(self):
        with pytest.raises(ValidationError):
            TournamentGenerateRequest(**{**_IND_BASE,
                "scoring_type": "SCORE_BASED",
                "measurement_unit": "points",
                "ranking_direction": "SIDEWAYS",
            })

    def test_individual_asc_direction_passes(self):
        req = TournamentGenerateRequest(**{**_IND_BASE,
            "scoring_type": "TIME_BASED",
            "measurement_unit": "seconds",
            "ranking_direction": "ASC",
        })
        assert req.ranking_direction == "ASC"


@pytest.mark.unit
@pytest.mark.tournament
class TestFormatTypeConsistencyValidator:
    def test_individual_with_tournament_type_id_raises(self):
        with pytest.raises(ValidationError, match="tournament_type"):
            TournamentGenerateRequest(**{**_IND_BASE, "tournament_type_id": 1})

    def test_head_to_head_without_tournament_type_raises(self):
        with pytest.raises(ValidationError, match="tournament_type"):
            TournamentGenerateRequest(**{**_H2H_BASE, "tournament_type_id": None})

    def test_individual_with_none_type_passes(self):
        req = TournamentGenerateRequest(**_IND_BASE)
        assert req.tournament_type_id is None

    def test_head_to_head_with_type_passes(self):
        req = TournamentGenerateRequest(**_H2H_BASE)
        assert req.tournament_type_id == 1


@pytest.mark.unit
@pytest.mark.tournament
class TestInstructorAtCreationValidator:
    def test_instructor_id_non_none_raises(self):
        with pytest.raises(ValidationError, match="instructor_id"):
            TournamentGenerateRequest(**{**_H2H_BASE, "instructor_id": 5})

    def test_instructor_id_none_passes(self):
        req = TournamentGenerateRequest(**{**_H2H_BASE, "instructor_id": None})
        assert req.instructor_id is None


@pytest.mark.unit
@pytest.mark.tournament
class TestCapacityVsSessionsValidator:
    def test_no_sessions_passes(self):
        req = TournamentGenerateRequest(**{**_H2H_BASE, "sessions": []})
        assert req.max_players == 8

    def test_sessions_within_capacity_passes(self):
        sessions = [{"time": "09:00", "title": "A", "capacity": 5}]
        req = TournamentGenerateRequest(**{**_H2H_BASE, "sessions": sessions})
        assert req.max_players == 8

    def test_sessions_exceed_capacity_raises(self):
        sessions = [
            {"time": "09:00", "title": "A", "capacity": 6},
            {"time": "10:00", "title": "B", "capacity": 6},
        ]
        with pytest.raises(ValidationError, match="max_players"):
            TournamentGenerateRequest(**{**_H2H_BASE, "sessions": sessions})


# ─── list_tournaments_admin ──────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestListTournamentsAdmin:
    def test_non_admin_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            list_tournaments_admin(db=_db(), current_user=_user(UserRole.STUDENT))
        assert ei.value.status_code == 403

    def _make_db(self, tournaments=None):
        """Make a db mock that returns all() and handles batch queries."""
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.isnot.return_value = q
        q.order_by.return_value = q
        q.group_by.return_value = q
        q.in_.return_value = q
        q.all.return_value = tournaments or []
        db.query.return_value = q
        return db

    def test_admin_empty_list(self):
        db = self._make_db()
        result = list_tournaments_admin(db=db, current_user=_user())
        assert result == []

    def test_admin_with_status_filter_calls_filter(self):
        t = MagicMock()
        t.id = 1
        t.code = "TOURN-20260101"
        t.name = "Test"
        t.tournament_status = "IN_PROGRESS"
        t.status = MagicMock()
        t.start_date = None
        t.end_date = None
        t.specialization_type = None
        db = self._make_db(tournaments=[t])
        result = list_tournaments_admin(
            status_filter="IN_PROGRESS", db=db, current_user=_user()
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["status"] == "IN_PROGRESS"

    def test_admin_with_tournament_id_filter(self):
        db = self._make_db()
        result = list_tournaments_admin(
            tournament_id=7, db=db, current_user=_user()
        )
        assert result == []

    def test_admin_ops_code_has_ops_source(self):
        """Tournament with OPS- prefix → source='ops'"""
        t = MagicMock()
        t.id = 2
        t.code = "OPS-20260101-001"
        t.name = "Ops Cup"
        t.tournament_status = "DRAFT"
        t.status = MagicMock()
        t.start_date = None
        t.end_date = None
        t.specialization_type = None
        db = self._make_db(tournaments=[t])
        result = list_tournaments_admin(db=db, current_user=_user())
        assert result[0]["source"] == "ops"


# ─── generate_tournament ─────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGenerateTournament:
    def test_non_admin_raises_403(self):
        req = TournamentGenerateRequest(**_H2H_BASE)
        with pytest.raises(HTTPException) as ei:
            generate_tournament(request=req, db=_db(), current_user=_user(UserRole.STUDENT))
        assert ei.value.status_code == 403

    def test_past_date_raises_400(self):
        req = TournamentGenerateRequest(**{**_H2H_BASE, "date": "2020-01-01"})
        with pytest.raises(HTTPException) as ei:
            generate_tournament(request=req, db=_db(), current_user=_user())
        assert ei.value.status_code == 400
        assert "future" in ei.value.detail.lower()

    def test_success_no_auto_book(self):
        req = TournamentGenerateRequest(**_H2H_BASE)
        mock_semester = MagicMock()
        mock_semester.id = 42
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.create_tournament_semester.return_value = mock_semester
            MockSvc.create_tournament_sessions.return_value = []
            MockSvc.get_tournament_summary.return_value = {"name": "Test"}
            result = generate_tournament(request=req, db=_db(), current_user=_user())
        assert result.tournament_id == 42
        assert result.total_bookings == 0

    def test_success_with_auto_book_students(self):
        req = TournamentGenerateRequest(**{**_H2H_BASE, "auto_book_students": True})
        mock_semester = MagicMock()
        mock_semester.id = 42
        mock_session = MagicMock()
        mock_session.id = 99
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.create_tournament_semester.return_value = mock_semester
            MockSvc.create_tournament_sessions.return_value = [mock_session]
            MockSvc.auto_book_students.return_value = {99: [1, 2, 3]}
            MockSvc.get_tournament_summary.return_value = {"name": "Test"}
            result = generate_tournament(request=req, db=_db(), current_user=_user())
        assert result.total_bookings == 3
        MockSvc.auto_book_students.assert_called_once()

    def test_tournament_service_exception_reraises(self):
        req = TournamentGenerateRequest(**_H2H_BASE)
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.create_tournament_semester.side_effect = RuntimeError("DB error")
            with pytest.raises(RuntimeError, match="DB error"):
                generate_tournament(request=req, db=_db(), current_user=_user())


# ─── send_instructor_request ─────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestSendInstructorRequest:
    def _req(self):
        r = MagicMock()
        r.instructor_id = 99
        r.message = "Please lead"
        return r

    def test_non_admin_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            send_instructor_request(
                tournament_id=1, request=self._req(),
                db=_db(), current_user=_user(UserRole.INSTRUCTOR)
            )
        assert ei.value.status_code == 403

    def test_value_error_raises_400(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.send_instructor_request.side_effect = ValueError("not found")
            with pytest.raises(HTTPException) as ei:
                send_instructor_request(
                    tournament_id=1, request=self._req(),
                    db=_db(), current_user=_user()
                )
        assert ei.value.status_code == 400

    def test_success_returns_request_info(self):
        assignment = MagicMock()
        assignment.id = 5
        assignment.instructor_id = 99
        assignment.status.value = "PENDING"
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.send_instructor_request.return_value = assignment
            result = send_instructor_request(
                tournament_id=1, request=self._req(),
                db=_db(), current_user=_user()
            )
        assert result["request_id"] == 5
        assert result["tournament_id"] == 1
        assert result["instructor_id"] == 99


# ─── accept_instructor_request ───────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestAcceptInstructorRequest:
    def test_non_instructor_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            accept_instructor_request(
                request_id=1, db=_db(), current_user=_user(UserRole.ADMIN)
            )
        assert ei.value.status_code == 403

    def test_value_error_raises_400(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.accept_instructor_request.side_effect = ValueError("already accepted")
            with pytest.raises(HTTPException) as ei:
                accept_instructor_request(
                    request_id=1, db=_db(),
                    current_user=_user(UserRole.INSTRUCTOR)
                )
        assert ei.value.status_code == 400

    def test_success_returns_accepted(self):
        semester = MagicMock()
        semester.id = 7
        semester.status.value = "READY_FOR_ENROLLMENT"
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.accept_instructor_request.return_value = semester
            result = accept_instructor_request(
                request_id=1, db=_db(),
                current_user=_user(UserRole.INSTRUCTOR)
            )
        assert result["status"] == "ACCEPTED"
        assert result["tournament_id"] == 7


# ─── decline_instructor_request ──────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestDeclineInstructorRequest:
    def _action_req(self):
        r = MagicMock()
        r.reason = "Not available"
        return r

    def test_non_instructor_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            decline_instructor_request(
                request_id=1, request=self._action_req(),
                db=_db(), current_user=_user(UserRole.ADMIN)
            )
        assert ei.value.status_code == 403

    def test_value_error_raises_400(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.decline_instructor_request.side_effect = ValueError("not pending")
            with pytest.raises(HTTPException) as ei:
                decline_instructor_request(
                    request_id=1, request=self._action_req(),
                    db=_db(), current_user=_user(UserRole.INSTRUCTOR)
                )
        assert ei.value.status_code == 400

    def test_success_returns_declined(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.decline_instructor_request.return_value = MagicMock()
            result = decline_instructor_request(
                request_id=1, request=self._action_req(),
                db=_db(), current_user=_user(UserRole.INSTRUCTOR)
            )
        assert result["status"] == "DECLINED"


# ─── get_tournament_summary ──────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGetTournamentSummary:
    def test_not_found_raises_404(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.get_tournament_summary.return_value = None
            with pytest.raises(HTTPException) as ei:
                get_tournament_summary(
                    tournament_id=99, db=_db(), current_user=_user()
                )
        assert ei.value.status_code == 404

    def test_success_returns_summary_response(self):
        summary = {
            "id": 7, "tournament_id": 7, "semester_id": 7,
            "code": "TOURN-20260101", "name": "Test Cup",
            "start_date": "2099-01-01", "date": "2099-01-01",
            "status": "SEEKING_INSTRUCTOR",
            "specialization_type": "LFA_FOOTBALL_PLAYER",
            "age_group": None, "location_id": None, "campus_id": None,
            "reward_policy_name": "default", "reward_policy_snapshot": None,
            "session_count": 0, "sessions_count": 0, "sessions": [],
            "total_capacity": 0, "total_bookings": 0, "fill_percentage": 0.0,
        }
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.get_tournament_summary.return_value = summary
            result = get_tournament_summary(
                tournament_id=7, db=_db(), current_user=_user()
            )
        assert result.tournament_id == 7
        assert result.code == "TOURN-20260101"


# ─── get_instructor_tournament_requests ──────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGetInstructorTournamentRequests:
    def test_wrong_user_raises_403(self):
        u = _user(UserRole.INSTRUCTOR, uid=10)
        with pytest.raises(HTTPException) as ei:
            get_instructor_tournament_requests(
                instructor_id=99, db=_db(), current_user=u
            )
        assert ei.value.status_code == 403

    def test_admin_can_see_any_instructor(self):
        db = MagicMock()
        req = MagicMock()
        req.id = 1
        req.semester_id = 7
        req.request_message = "Lead?"
        req.created_at = None
        req.expires_at = None
        req.priority = "NORMAL"
        req.status.value = "PENDING"
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = [req]
        db.query.return_value = q
        # InstructorAssignmentRequest/AssignmentRequestStatus are lazy imports in function body
        result = get_instructor_tournament_requests(
            instructor_id=99, db=db,
            current_user=_user(UserRole.ADMIN, uid=42)
        )
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_instructor_sees_own_empty_requests(self):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = []
        db.query.return_value = q
        result = get_instructor_tournament_requests(
            instructor_id=42, db=db,
            current_user=_user(UserRole.INSTRUCTOR, uid=42)
        )
        assert result == []


# ─── delete_tournament ───────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestDeleteTournament:
    def test_non_admin_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            delete_tournament(
                tournament_id=7, db=_db(),
                current_user=_user(UserRole.INSTRUCTOR)
            )
        assert ei.value.status_code == 403

    def test_not_found_raises_404(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.delete_tournament.return_value = False
            with pytest.raises(HTTPException) as ei:
                delete_tournament(
                    tournament_id=99, db=_db(), current_user=_user()
                )
        assert ei.value.status_code == 404

    def test_success_returns_none(self):
        with patch(f"{_BASE}.TournamentService") as MockSvc:
            MockSvc.delete_tournament.return_value = True
            result = delete_tournament(
                tournament_id=7, db=_db(), current_user=_user()
            )
        assert result is None


# ─── get_reward_policies ─────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGetRewardPolicies:
    def test_non_admin_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            get_reward_policies(current_user=_user(UserRole.STUDENT))
        assert ei.value.status_code == 403

    def test_success_all_valid_policies(self):
        with patch(f"{_BASE}.get_available_policies", return_value=["default"]), \
             patch(f"{_BASE}.get_policy_info", return_value={"policy_name": "default"}):
            result = get_reward_policies(current_user=_user())
        assert result["count"] == 1
        assert result["policies"][0]["policy_name"] == "default"

    def test_invalid_policy_skipped(self):
        from app.services.tournament.reward_policy_loader import RewardPolicyError
        with patch(f"{_BASE}.get_available_policies", return_value=["good", "bad"]), \
             patch(f"{_BASE}.get_policy_info",
                   side_effect=[{"policy_name": "good"}, RewardPolicyError("bad")]):
            result = get_reward_policies(current_user=_user())
        assert result["count"] == 1
        assert result["policies"][0]["policy_name"] == "good"

    def test_outer_exception_raises_500(self):
        with patch(f"{_BASE}.get_available_policies",
                   side_effect=RuntimeError("disk error")):
            with pytest.raises(HTTPException) as ei:
                get_reward_policies(current_user=_user())
        assert ei.value.status_code == 500


# ─── get_reward_policy_details ────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestGetRewardPolicyDetails:
    def test_non_admin_raises_403(self):
        with pytest.raises(HTTPException) as ei:
            get_reward_policy_details(
                policy_name="default", current_user=_user(UserRole.STUDENT)
            )
        assert ei.value.status_code == 403

    def test_reward_policy_error_raises_404(self):
        from app.services.tournament.reward_policy_loader import RewardPolicyError
        with patch(f"{_BASE}.get_policy_info",
                   side_effect=RewardPolicyError("not found")):
            with pytest.raises(HTTPException) as ei:
                get_reward_policy_details(
                    policy_name="missing", current_user=_user()
                )
        assert ei.value.status_code == 404

    def test_success_returns_policy_dict(self):
        with patch(f"{_BASE}.get_policy_info",
                   return_value={"policy_name": "default", "version": "1.0"}):
            result = get_reward_policy_details(
                policy_name="default", current_user=_user()
            )
        assert result["policy_name"] == "default"
        assert result["version"] == "1.0"
