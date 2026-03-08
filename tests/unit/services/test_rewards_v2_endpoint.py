"""
Unit tests for tournaments/rewards_v2.py
Sprint 23 — coverage: 22% → ≥90%

7 endpoints:
1. distribute_tournament_rewards_v2
2. get_user_tournament_rewards
3. add_tournament_skill_mapping
4. get_tournament_skill_mappings
5. delete_tournament_skill_mapping
6. get_user_tournament_badges
7. get_user_badge_showcase
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.tournaments.rewards_v2 import (
    distribute_tournament_rewards_v2,
    get_user_tournament_rewards,
    add_tournament_skill_mapping,
    get_tournament_skill_mappings,
    delete_tournament_skill_mapping,
    get_user_tournament_badges,
    get_user_badge_showcase,
    DistributeRewardsRequest,
    AddSkillMappingRequest,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.tournaments.rewards_v2"
_ORCH = "app.services.tournament.tournament_reward_orchestrator"
_LIFECYCLE = "app.api.api_v1.endpoints.tournaments.lifecycle"
_SKILL_MAPPING = "app.models.tournament_achievement.TournamentSkillMapping"
_BADGE_SVC = "app.services.tournament.tournament_badge_service"


# ============================================================================
# Helpers
# ============================================================================

def _user(user_id=42, role=UserRole.ADMIN):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.name = "Test User"
    return u


def _admin(uid=42):
    return _user(uid, UserRole.ADMIN)


def _instructor(uid=42):
    return _user(uid, UserRole.INSTRUCTOR)


def _student(uid=42):
    return _user(uid, UserRole.STUDENT)


def _tournament(tid=1, status="COMPLETED"):
    t = MagicMock()
    t.id = tid
    t.name = "Test Tournament"
    t.tournament_status = status
    return t


def _q(first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    return q


def _db(tournament=None, mapping=None, mappings=None):
    db = MagicMock()
    call_count = [0]

    def _side(_model):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return _q(first=tournament)
        elif idx == 1:
            if mappings is not None:
                return _q(all_=mappings)
            return _q(first=mapping)
        return MagicMock()

    db.query.side_effect = _side
    return db


# ============================================================================
# 1. distribute_tournament_rewards_v2
# ============================================================================

class TestDistributeTournamentRewardsV2:

    def _req(self, force=False):
        return DistributeRewardsRequest(tournament_id=1, reward_policy=None, force_redistribution=force)

    def test_student_raises_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards_v2(1, self._req(), db=db, current_user=_student())
        assert exc.value.status_code == 403

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards_v2(1, self._req(), db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_tournament_not_completed_raises_400(self):
        t = _tournament(status="ONGOING")
        db = _db(tournament=t)
        with pytest.raises(HTTPException) as exc:
            distribute_tournament_rewards_v2(1, self._req(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "COMPLETED" in exc.value.detail

    def test_orchestrator_value_error_raises_400(self):
        t = _tournament(status="COMPLETED")
        db = _db(tournament=t)
        with patch(f"{_ORCH}.distribute_rewards_for_tournament",
                   side_effect=ValueError("no rankings")):
            with pytest.raises(HTTPException) as exc:
                distribute_tournament_rewards_v2(1, self._req(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "no rankings" in exc.value.detail

    def test_orchestrator_exception_raises_500(self):
        t = _tournament(status="COMPLETED")
        db = _db(tournament=t)
        with patch(f"{_ORCH}.distribute_rewards_for_tournament",
                   side_effect=Exception("db crash")):
            with pytest.raises(HTTPException) as exc:
                distribute_tournament_rewards_v2(1, self._req(), db=db, current_user=_admin())
        assert exc.value.status_code == 500
        assert "db crash" in exc.value.detail

    def test_success_admin(self):
        t = _tournament(status="COMPLETED")
        db = _db(tournament=t)
        result_mock = MagicMock()
        result_mock.tournament_id = 1
        result_mock.tournament_name = "Test Tournament"
        result_mock.total_participants = 5
        result_mock.rewards_distributed = [MagicMock(), MagicMock()]
        result_mock.distribution_summary = {"total_badges_awarded": 3, "total_xp_awarded": 100}
        from datetime import datetime
        result_mock.distributed_at = datetime(2026, 3, 6)

        with patch(f"{_ORCH}.distribute_rewards_for_tournament", return_value=result_mock):
            with patch(f"{_LIFECYCLE}.record_status_change"):
                result = distribute_tournament_rewards_v2(1, self._req(), db=db, current_user=_admin())
        assert result["success"] is True
        assert result["total_participants"] == 5
        assert result["rewards_distributed_count"] == 2
        assert t.tournament_status == "REWARDS_DISTRIBUTED"

    def test_success_instructor_also_allowed(self):
        t = _tournament(status="COMPLETED")
        db = _db(tournament=t)
        result_mock = MagicMock()
        result_mock.tournament_id = 1
        result_mock.tournament_name = "Test"
        result_mock.total_participants = 2
        result_mock.rewards_distributed = []
        result_mock.distribution_summary = {}
        from datetime import datetime
        result_mock.distributed_at = datetime(2026, 3, 6)

        with patch(f"{_ORCH}.distribute_rewards_for_tournament", return_value=result_mock):
            with patch(f"{_LIFECYCLE}.record_status_change"):
                result = distribute_tournament_rewards_v2(
                    1, self._req(), db=db, current_user=_instructor()
                )
        assert result["success"] is True


# ============================================================================
# 2. get_user_tournament_rewards
# ============================================================================

class TestGetUserTournamentRewards:

    def test_other_user_student_raises_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            get_user_tournament_rewards(1, user_id=99, db=db, current_user=_student(42))
        assert exc.value.status_code == 403

    def test_own_rewards_allowed_for_student(self):
        """User viewing their own rewards → allowed."""
        summary = MagicMock()
        summary.to_dict.return_value = {"user_id": 42, "xp": 100}
        with patch(f"{_ORCH}.get_user_reward_summary", return_value=summary):
            db = MagicMock()
            result = get_user_tournament_rewards(1, user_id=42, db=db, current_user=_student(42))
        assert result["user_id"] == 42

    def test_no_rewards_raises_404(self):
        with patch(f"{_ORCH}.get_user_reward_summary", return_value=None):
            db = MagicMock()
            with pytest.raises(HTTPException) as exc:
                get_user_tournament_rewards(1, user_id=99, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_admin_can_view_any_user(self):
        summary = MagicMock()
        summary.to_dict.return_value = {"user_id": 99, "credits": 50}
        with patch(f"{_ORCH}.get_user_reward_summary", return_value=summary):
            db = MagicMock()
            result = get_user_tournament_rewards(1, user_id=99, db=db, current_user=_admin(42))
        assert result["user_id"] == 99


# ============================================================================
# 3. add_tournament_skill_mapping
# ============================================================================

class TestAddTournamentSkillMapping:

    def _req(self):
        return AddSkillMappingRequest(
            tournament_id=1,
            skill_name="agility",
            skill_category="Physical",
            weight=1.0,
        )

    def test_non_admin_raises_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            add_tournament_skill_mapping(1, self._req(), db=db, current_user=_instructor())
        assert exc.value.status_code == 403

    def test_tournament_not_found_raises_404(self):
        db = _db(tournament=None)
        with pytest.raises(HTTPException) as exc:
            add_tournament_skill_mapping(1, self._req(), db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_success_creates_mapping(self):
        t = _tournament()
        db = _db(tournament=t)
        mock_mapping = MagicMock()
        mock_mapping.id = 5
        mock_mapping.skill_name = "agility"
        mock_mapping.skill_category = "Physical"
        mock_mapping.weight = "1.0"

        with patch(_SKILL_MAPPING, return_value=mock_mapping):
            result = add_tournament_skill_mapping(1, self._req(), db=db, current_user=_admin())
        assert result["success"] is True
        assert result["skill_name"] == "agility"
        assert result["tournament_id"] == 1
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ============================================================================
# 4. get_tournament_skill_mappings
# ============================================================================

class TestGetTournamentSkillMappings:

    def test_returns_empty_list(self):
        db = MagicMock()
        with patch(_SKILL_MAPPING) as MockSM:
            q = MagicMock()
            q.filter.return_value = q
            q.all.return_value = []
            db.query.return_value = q
            result = get_tournament_skill_mappings(1, db=db, current_user=_admin())
        assert result == []

    def test_returns_mappings(self):
        m1 = MagicMock()
        m1.id = 1
        m1.skill_name = "speed"
        m1.skill_category = "Physical"
        m1.weight = "0.8"
        m1.created_at = None

        db = MagicMock()
        with patch(_SKILL_MAPPING):
            q = MagicMock()
            q.filter.return_value = q
            q.all.return_value = [m1]
            db.query.return_value = q
            result = get_tournament_skill_mappings(1, db=db, current_user=_instructor())
        assert len(result) == 1
        assert result[0]["skill_name"] == "speed"
        assert result[0]["weight"] == 0.8

    def test_created_at_isoformat_when_set(self):
        from datetime import datetime
        m1 = MagicMock()
        m1.id = 1
        m1.skill_name = "dribbling"
        m1.skill_category = "Technical"
        m1.weight = "1.0"
        m1.created_at = datetime(2026, 3, 1)

        db = MagicMock()
        with patch(_SKILL_MAPPING):
            q = MagicMock()
            q.filter.return_value = q
            q.all.return_value = [m1]
            db.query.return_value = q
            result = get_tournament_skill_mappings(1, db=db, current_user=_admin())
        assert result[0]["created_at"] == "2026-03-01T00:00:00"


# ============================================================================
# 5. delete_tournament_skill_mapping
# ============================================================================

class TestDeleteTournamentSkillMapping:

    def test_non_admin_raises_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            delete_tournament_skill_mapping(1, 5, db=db, current_user=_instructor())
        assert exc.value.status_code == 403

    def test_mapping_not_found_raises_404(self):
        db = MagicMock()
        with patch(_SKILL_MAPPING):
            q = MagicMock()
            q.filter.return_value = q
            q.first.return_value = None
            db.query.return_value = q
            with pytest.raises(HTTPException) as exc:
                delete_tournament_skill_mapping(1, 5, db=db, current_user=_admin())
        assert exc.value.status_code == 404

    def test_success_deletes_mapping(self):
        mapping = MagicMock()
        mapping.skill_name = "agility"
        db = MagicMock()
        with patch(_SKILL_MAPPING):
            q = MagicMock()
            q.filter.return_value = q
            q.first.return_value = mapping
            db.query.return_value = q
            result = delete_tournament_skill_mapping(1, 5, db=db, current_user=_admin())
        assert result["success"] is True
        assert result["message"] == "Skill mapping deleted: agility"
        db.delete.assert_called_once_with(mapping)
        db.commit.assert_called_once()


# ============================================================================
# 6. get_user_tournament_badges
# ============================================================================

class TestGetUserTournamentBadges:

    def test_other_student_raises_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            get_user_tournament_badges(user_id=99, tournament_id=None, limit=100, db=db, current_user=_student(42))
        assert exc.value.status_code == 403

    def test_own_badges_allowed(self):
        badges = [{"badge": "Gold"}, {"badge": "Silver"}]
        with patch(_BADGE_SVC) as mock_bs:
            mock_bs.get_player_badges.return_value = badges
            db = MagicMock()
            result = get_user_tournament_badges(
                user_id=42, tournament_id=None, limit=100, db=db, current_user=_student(42)
            )
        assert result["total_badges"] == 2
        assert result["user_id"] == 42

    def test_admin_can_view_any_user_badges(self):
        with patch(_BADGE_SVC) as mock_bs:
            mock_bs.get_player_badges.return_value = []
            db = MagicMock()
            result = get_user_tournament_badges(
                user_id=99, tournament_id=1, limit=50, db=db, current_user=_admin()
            )
        assert result["total_badges"] == 0

    def test_instructor_can_view_any_user_badges(self):
        with patch(_BADGE_SVC) as mock_bs:
            mock_bs.get_player_badges.return_value = [{"badge": "Bronze"}]
            db = MagicMock()
            result = get_user_tournament_badges(
                user_id=99, tournament_id=None, limit=100, db=db, current_user=_instructor()
            )
        assert result["total_badges"] == 1


# ============================================================================
# 7. get_user_badge_showcase
# ============================================================================

class TestGetUserBadgeShowcase:

    def test_other_student_raises_403(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            get_user_badge_showcase(user_id=99, db=db, current_user=_student(42))
        assert exc.value.status_code == 403

    def test_own_showcase_allowed(self):
        showcase = {"gold": 1, "silver": 2}
        with patch(_BADGE_SVC) as mock_bs:
            mock_bs.get_player_badge_showcase.return_value = showcase
            db = MagicMock()
            result = get_user_badge_showcase(user_id=42, db=db, current_user=_student(42))
        assert result["user_id"] == 42
        assert result["showcase"] == showcase

    def test_admin_views_any_showcase(self):
        showcase = {"platinum": 1}
        with patch(_BADGE_SVC) as mock_bs:
            mock_bs.get_player_badge_showcase.return_value = showcase
            db = MagicMock()
            result = get_user_badge_showcase(user_id=99, db=db, current_user=_admin())
        assert result["showcase"] == showcase

    def test_instructor_views_any_showcase(self):
        with patch(_BADGE_SVC) as mock_bs:
            mock_bs.get_player_badge_showcase.return_value = {}
            db = MagicMock()
            result = get_user_badge_showcase(user_id=99, db=db, current_user=_instructor())
        assert result["user_id"] == 99
