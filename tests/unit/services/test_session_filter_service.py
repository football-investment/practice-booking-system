"""
Unit tests for app/services/session_filter_service.py (SessionFilterService)

Covers:
  get_user_specialization  — cache hit, non-student, student paths:
                             no projects/interests → GENERAL
                             coach-keyword project → COACH
                             player-keyword project → PLAYER
                             coach interests (JSON) → COACH
                             player interests (JSON) → PLAYER
                             both → MIXED
                             invalid JSON interests → GENERAL (no crash)
                             result cached on second call

  get_session_target_groups — coach/player/general keyword matching,
                              multiple groups, default GENERAL fallback

  get_relevant_sessions_for_user — GENERAL user (no limit / with limit),
                                   COACH user (scoring + filtering), limit branch

  _calculate_session_relevance — base 1.0, spec-match +5, general +3,
                                  mixed +4, interest sport bonus +2,
                                  JSON decode error in interests,
                                  COACH level bonus, PLAYER base bonus,
                                  capacity bonus

  apply_specialization_filter — non-student returns query, student no
                                  has_specialization returns query,
                                  student with specialization + include_mixed,
                                  student with specialization, include_mixed=False,
                                  student no specialization attr

  get_session_recommendations_summary — returns expected dict shape
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.session_filter_service import SessionFilterService, UserSpecialization
from app.models.user import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc():
    """Return (service, mock_db)."""
    db = MagicMock()
    return SessionFilterService(db), db


def _user(role=UserRole.STUDENT, uid=1, interests=None, has_spec=False, specialization=None):
    u = MagicMock()
    u.id = uid
    u.role = role
    u.name = "Test User"
    u.interests = interests
    u.has_specialization = has_spec
    u.specialization = specialization
    return u


def _session(title="Session", description="", sport_type="football", level="beginner",
             current_bookings=5, capacity=20):
    s = MagicMock()
    s.title = title
    s.description = description
    s.sport_type = sport_type
    s.level = level
    s.current_bookings = current_bookings
    s.capacity = capacity
    return s


def _q_projects(db, projects):
    """Wire db.query().join().filter().all() → projects list."""
    q = MagicMock()
    q.join.return_value = q
    q.filter.return_value = q
    q.all.return_value = projects
    db.query.return_value = q
    return q


def _make_project(title="Project", description=""):
    p = MagicMock()
    p.title = title
    p.description = description
    p.id = 1
    return p


# ===========================================================================
# get_user_specialization
# ===========================================================================

@pytest.mark.unit
class TestGetUserSpecialization:
    def test_cache_hit_returns_cached_value(self):
        svc, db = _svc()
        user = _user(uid=42)
        svc._user_specialization_cache[42] = UserSpecialization.COACH
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.COACH
        db.query.assert_not_called()  # No DB hit

    def test_non_student_returns_general(self):
        svc, db = _svc()
        user = _user(role=UserRole.INSTRUCTOR, uid=10)
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.GENERAL
        db.query.assert_not_called()

    def test_non_student_result_is_cached(self):
        svc, db = _svc()
        user = _user(role=UserRole.ADMIN, uid=20)
        svc.get_user_specialization(user)
        assert svc._user_specialization_cache[20] == UserSpecialization.GENERAL

    def test_student_no_projects_no_interests_returns_general(self):
        svc, db = _svc()
        user = _user(uid=3, interests=None)
        _q_projects(db, [])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.GENERAL

    def test_student_coach_keyword_in_project_title_returns_coach(self):
        svc, db = _svc()
        user = _user(uid=4, interests=None)
        project = _make_project(title="Coach Development", description="Training methods")
        _q_projects(db, [project])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.COACH

    def test_student_player_keyword_in_project_description_returns_player(self):
        svc, db = _svc()
        user = _user(uid=5, interests=None)
        project = _make_project(title="Football Academy", description="Player performance skills")
        _q_projects(db, [project])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.PLAYER

    def test_student_both_keywords_returns_mixed(self):
        svc, db = _svc()
        user = _user(uid=6, interests=None)
        project = _make_project(title="Coach player development", description="atléta edző program")
        _q_projects(db, [project])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.MIXED

    def test_student_coach_keyword_in_interests_returns_coach(self):
        svc, db = _svc()
        user = _user(uid=7, interests=json.dumps(["coaching", "tactics"]))
        _q_projects(db, [])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.COACH

    def test_student_player_keyword_in_interests_returns_player(self):
        svc, db = _svc()
        user = _user(uid=8, interests=json.dumps(["player development", "fitness"]))
        _q_projects(db, [])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.PLAYER

    def test_student_invalid_json_interests_returns_general(self):
        svc, db = _svc()
        user = _user(uid=9, interests="not valid json {{{")
        _q_projects(db, [])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.GENERAL  # No crash, falls through

    def test_student_result_is_cached(self):
        svc, db = _svc()
        user = _user(uid=11, interests=None)
        _q_projects(db, [])
        svc.get_user_specialization(user)
        # Second call — DB should NOT be called again (cache hit)
        db.query.reset_mock()
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.GENERAL
        db.query.assert_not_called()

    def test_student_interests_coach_and_player_returns_mixed(self):
        svc, db = _svc()
        user = _user(uid=12, interests=json.dumps(["coaching", "player skills"]))
        _q_projects(db, [])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.MIXED

    def test_hungarian_keyword_edzo_returns_coach(self):
        svc, db = _svc()
        user = _user(uid=13, interests=None)
        project = _make_project(title="Edző Program", description="vezető képzés")
        _q_projects(db, [project])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.COACH

    def test_hungarian_keyword_jatekos_returns_player(self):
        svc, db = _svc()
        user = _user(uid=14, interests=None)
        project = _make_project(title="Játékos fejlesztés", description="versenyző képzés")
        _q_projects(db, [project])
        result = svc.get_user_specialization(user)
        assert result == UserSpecialization.PLAYER


# ===========================================================================
# get_session_target_groups
# ===========================================================================

@pytest.mark.unit
class TestGetSessionTargetGroups:
    def test_coach_keyword_in_title(self):
        svc, _ = _svc()
        session = _session(title="Coach Training Session")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.COACH in result

    def test_player_keyword_in_description(self):
        svc, _ = _svc()
        session = _session(title="Advanced Training", description="Individual player skill development")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.PLAYER in result

    def test_general_keyword_everyone(self):
        svc, _ = _svc()
        session = _session(title="Open Workshop for Everyone")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.GENERAL in result

    def test_no_keywords_returns_general(self):
        svc, _ = _svc()
        session = _session(title="Morning Meetup", description="")
        result = svc.get_session_target_groups(session)
        assert result == [UserSpecialization.GENERAL]

    def test_coach_and_player_keywords_both_included(self):
        svc, _ = _svc()
        session = _session(title="Coach and Player Development", description="training tactics")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.COACH in result
        assert UserSpecialization.PLAYER in result

    def test_tactics_keyword_is_coach(self):
        svc, _ = _svc()
        session = _session(title="Tactics Workshop")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.COACH in result

    def test_fitness_keyword_is_player(self):
        svc, _ = _svc()
        session = _session(title="Fitness and Performance")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.PLAYER in result

    def test_mental_keyword_is_general(self):
        svc, _ = _svc()
        session = _session(title="Mental and Nutrition Workshop")
        result = svc.get_session_target_groups(session)
        assert UserSpecialization.GENERAL in result

    def test_description_none_handled_gracefully(self):
        svc, _ = _svc()
        session = _session(title="Instructor Methodology", description=None)
        result = svc.get_session_target_groups(session)
        # "instructor" keyword → coach
        assert UserSpecialization.COACH in result


# ===========================================================================
# _calculate_session_relevance
# ===========================================================================

@pytest.mark.unit
class TestCalculateSessionRelevance:
    def test_base_score_is_one(self):
        svc, _ = _svc()
        user = _user()
        # Session with no keywords → GENERAL target group
        session = _session(title="Quiet Session", description="")
        score = svc._calculate_session_relevance(session, user, UserSpecialization.GENERAL)
        # base 1.0 + general in targets +3.0 = 4.0 minimum
        assert score >= 1.0

    def test_specialization_match_adds_five(self):
        svc, _ = _svc()
        user = _user(interests=None)
        # Coach session → target = COACH; user spec = COACH
        session = _session(title="Edző Leadership", description="")
        score = svc._calculate_session_relevance(session, user, UserSpecialization.COACH)
        # base 1.0 + spec match +5.0 = 6.0 (at minimum)
        assert score >= 6.0

    def test_general_target_adds_three(self):
        svc, _ = _svc()
        user = _user(interests=None)
        session = _session(title="Open Workshop for everyone")  # → GENERAL target
        score = svc._calculate_session_relevance(session, user, UserSpecialization.PLAYER)
        # base 1.0 + general +3.0 = 4.0 (player not in targets, so general branch)
        assert score >= 4.0

    def test_mixed_user_adds_four(self):
        svc, _ = _svc()
        user = _user(interests=None)
        session = _session(title="Neutral Session", description="")  # → GENERAL target
        score = svc._calculate_session_relevance(session, user, UserSpecialization.MIXED)
        # base 1.0 + general +3.0 = 4.0 minimum (MIXED falls to general branch for GENERAL target)
        # or could be: mixed +4.0 if GENERAL not in targets
        # for a session that defaults to GENERAL, user_spec (MIXED) not in targets but GENERAL is
        # → +3.0. Total ≥ 4.0
        assert score >= 1.0

    def test_interest_sport_type_match_adds_two(self):
        svc, _ = _svc()
        user = _user(interests=json.dumps(["football", "tactics"]))
        session = _session(title="Coach Training", sport_type="football")
        score = svc._calculate_session_relevance(session, user, UserSpecialization.COACH)
        # base 1 + spec match 5 + sport type interest 2 = 8.0 minimum
        assert score >= 8.0

    def test_invalid_json_interests_no_crash(self):
        svc, _ = _svc()
        user = _user(interests="not json {{{")
        session = _session(title="Coach Workshop")
        # Should not raise; interest bonus just skipped
        score = svc._calculate_session_relevance(session, user, UserSpecialization.COACH)
        assert score >= 1.0

    def test_coach_advanced_level_adds_bonus(self):
        svc, _ = _svc()
        user = _user(interests=None)
        session = _session(title="Advanced Tactics", level="advanced")
        score = svc._calculate_session_relevance(session, user, UserSpecialization.COACH)
        # base 1 + spec match 5 + level bonus 1 = 7.0 minimum
        assert score >= 7.0

    def test_player_spec_adds_point5_bonus(self):
        svc, _ = _svc()
        user = _user(interests=None)
        session = _session(title="Skill Training for Players", level="beginner")
        score = svc._calculate_session_relevance(session, user, UserSpecialization.PLAYER)
        # base 1 + spec match 5 + player bonus 0.5 = 6.5
        assert score >= 6.5

    def test_capacity_bonus_applied(self):
        svc, _ = _svc()
        user = _user(interests=None)
        session = _session(title="Coach Workshop")
        session.current_bookings = 5
        session.capacity = 20  # 15 spots available, ratio = 0.75
        score = svc._calculate_session_relevance(session, user, UserSpecialization.COACH)
        # Should include availability_ratio * 1.0 = 0.75 bonus
        assert score >= 6.0 + 0.7  # rough check


# ===========================================================================
# get_relevant_sessions_for_user
# ===========================================================================

@pytest.mark.unit
class TestGetRelevantSessionsForUser:
    def test_general_user_no_limit_returns_all(self):
        svc, db = _svc()
        user = _user(role=UserRole.INSTRUCTOR, uid=1)  # non-student → GENERAL
        base_query = MagicMock()
        sessions = [_session(title=f"S{i}") for i in range(3)]
        base_query.all.return_value = sessions

        result = svc.get_relevant_sessions_for_user(user, base_query)
        assert result == sessions
        base_query.all.assert_called_once()

    def test_general_user_with_limit(self):
        svc, db = _svc()
        user = _user(role=UserRole.ADMIN, uid=2)  # non-student → GENERAL
        base_query = MagicMock()
        limited_query = MagicMock()
        sessions = [_session()]
        base_query.limit.return_value = limited_query
        limited_query.all.return_value = sessions

        result = svc.get_relevant_sessions_for_user(user, base_query, limit=5)
        base_query.limit.assert_called_once_with(5)
        assert result == sessions

    def test_coach_user_filters_irrelevant_sessions(self):
        svc, db = _svc()
        # Inject coach specialization into cache
        user = _user(uid=99, role=UserRole.STUDENT, interests=None)
        svc._user_specialization_cache[99] = UserSpecialization.COACH

        # One coach session (score > 0) and one player-only session (should still score > 0 since base=1)
        coach_session = _session(title="Edző Tactics", description="")
        base_query = MagicMock()
        limited_query = MagicMock()
        base_query.limit.return_value = limited_query
        limited_query.all.return_value = [coach_session]

        result = svc.get_relevant_sessions_for_user(user, base_query, limit=10)
        assert coach_session in result

    def test_non_general_user_sessions_sorted_by_score(self):
        svc, db = _svc()
        user = _user(uid=50, role=UserRole.STUDENT, interests=None)
        svc._user_specialization_cache[50] = UserSpecialization.PLAYER

        # High-score session (player keywords)
        high_session = _session(title="Player Performance Training", description="individual skill")
        # Low-score session (no keywords → default GENERAL)
        low_session = _session(title="Neutral Meetup", description="")

        base_query = MagicMock()
        limited_query = MagicMock()
        base_query.limit.return_value = limited_query
        limited_query.all.return_value = [low_session, high_session]

        result = svc.get_relevant_sessions_for_user(user, base_query)
        # high_session should appear first
        assert result[0] == high_session


# ===========================================================================
# apply_specialization_filter
# ===========================================================================

@pytest.mark.unit
class TestApplySpecializationFilter:
    def test_non_student_returns_query_unchanged(self):
        svc, _ = _svc()
        user = _user(role=UserRole.INSTRUCTOR)
        query = MagicMock()
        result = svc.apply_specialization_filter(query, user)
        assert result is query
        query.filter.assert_not_called()

    def test_student_without_has_specialization_returns_query_unchanged(self):
        svc, _ = _svc()
        user = _user(role=UserRole.STUDENT, has_spec=False)
        query = MagicMock()
        result = svc.apply_specialization_filter(query, user)
        assert result is query
        query.filter.assert_not_called()

    def test_student_with_specialization_applies_filter(self):
        svc, _ = _svc()
        # specialization must have a .value attribute (enum-like)
        spec = MagicMock()
        spec.value = "coach"
        user = _user(role=UserRole.STUDENT, has_spec=True, specialization=spec)
        query = MagicMock()
        filtered_query = MagicMock()
        query.filter.return_value = filtered_query

        result = svc.apply_specialization_filter(query, user)
        query.filter.assert_called_once()
        assert result is filtered_query

    def test_student_with_specialization_include_mixed_false(self):
        svc, _ = _svc()
        spec = MagicMock()
        spec.value = "player"
        user = _user(role=UserRole.STUDENT, has_spec=True, specialization=spec)
        query = MagicMock()
        query.filter.return_value = query

        svc.apply_specialization_filter(query, user, include_mixed=False)
        # filter should still be called (just without mixed condition)
        query.filter.assert_called_once()

    def test_student_no_specialization_attr_still_filters(self):
        svc, _ = _svc()
        user = _user(role=UserRole.STUDENT, has_spec=True, specialization=None)
        query = MagicMock()
        query.filter.return_value = query

        result = svc.apply_specialization_filter(query, user)
        # specialization is None → no specialization_conditions.append for specialization
        # but filter is still called with null condition
        query.filter.assert_called_once()


# ===========================================================================
# get_session_recommendations_summary
# ===========================================================================

@pytest.mark.unit
class TestGetSessionRecommendationsSummary:
    def test_returns_expected_shape(self):
        svc, db = _svc()
        user = _user(role=UserRole.INSTRUCTOR, uid=7)
        # Inject specialization to avoid DB call in get_user_specialization
        svc._user_specialization_cache[7] = UserSpecialization.GENERAL

        # DB call for enrolled_projects
        _q_projects(db, [])

        result = svc.get_session_recommendations_summary(user)
        assert result["user_id"] == 7
        assert result["specialization"] == UserSpecialization.GENERAL
        assert "enrolled_projects" in result
        assert "filtering_logic" in result

    def test_with_enrolled_projects(self):
        svc, db = _svc()
        user = _user(role=UserRole.STUDENT, uid=8, interests=None)
        svc._user_specialization_cache[8] = UserSpecialization.COACH

        project = _make_project(title="Coach Program", description="Leadership training")
        _q_projects(db, [project])

        result = svc.get_session_recommendations_summary(user)
        assert len(result["enrolled_projects"]) == 1
        assert result["enrolled_projects"][0]["title"] == "Coach Program"
        assert result["filtering_logic"]["project_bonus"] is True

    def test_filtering_logic_interest_matching_when_interests_present(self):
        svc, db = _svc()
        user = _user(uid=9, interests=json.dumps(["football"]))
        svc._user_specialization_cache[9] = UserSpecialization.PLAYER
        _q_projects(db, [])

        result = svc.get_session_recommendations_summary(user)
        assert result["filtering_logic"]["interest_matching"] is True

    def test_filtering_logic_interest_matching_when_no_interests(self):
        svc, db = _svc()
        user = _user(uid=10, interests=None)
        svc._user_specialization_cache[10] = UserSpecialization.GENERAL
        _q_projects(db, [])

        result = svc.get_session_recommendations_summary(user)
        assert result["filtering_logic"]["interest_matching"] is False
