"""
Sprint 28 — services/sandbox_verdict_calculator.py
====================================================
Target: ≥90% statement, ≥70% branch

Covers:
  SandboxVerdictCalculator.calculate_verdict —
    NOT_WORKING: tournament not found / wrong status / participation mismatch /
                 zero skill change
    WORKING: full happy path with skill progression + top/bottom performers
  _build_not_working_verdict  — covered via calculate_verdict
  _calculate_skill_progression — direct + via calculate_verdict
  _get_top_performers         — coverage via calculate_verdict happy path
  _get_bottom_performers      — count ≤ requested → [] / normal path

Mock strategy
-------------
* ``_db(*)``  — sequential db.query() mock
* ``_q(...)`` — fluent chain mock
* Patch ``skill_progression_service.get_skill_profile`` at source
"""

import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from app.services.sandbox_verdict_calculator import SandboxVerdictCalculator

_PATCH_SKILL = "app.services.sandbox_verdict_calculator.skill_progression_service"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _q(*, first=None, all_=None, count=0):
    q = MagicMock()
    for m in ("filter", "order_by", "limit", "join"):
        getattr(q, m).return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count
    return q


def _seq_db(*qs):
    calls = [0]
    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return qs[idx] if idx < len(qs) else _q()
    db = MagicMock()
    db.query.side_effect = _side
    return db


def _tournament(status="REWARDS_DISTRIBUTED", tid=1):
    t = MagicMock()
    t.id = tid
    t.tournament_status = status
    return t


def _ranking(user_id=42, rank=1, points=100):
    r = MagicMock()
    r.user_id = user_id
    r.rank = rank
    r.points = points
    return r


def _user_mock(uid=42, email="player@test.com"):
    u = MagicMock()
    u.id = uid
    u.email = email
    return u


def _skill_profile(skill_name="passing", current_level=77.0):
    """Return value for get_skill_profile: {'skills': {skill_name: {'current_level': val}}}"""
    return {"skills": {skill_name: {"current_level": current_level}}}


# ── SandboxVerdictCalculator.calculate_verdict ────────────────────────────────

class TestCalculateVerdict:

    def test_tournament_not_found_returns_not_working(self):
        """CV-01: tournament not found → NOT_WORKING with error insight."""
        db = _seq_db(_q(first=None))  # Semester query returns None
        calc = SandboxVerdictCalculator(db)

        result = calc.calculate_verdict(
            tournament_id=1,
            expected_participant_count=3,
            skills_to_test=["passing"],
            distribution_result=MagicMock(),
            skills_before_snapshot={},
        )

        assert result["verdict"] == "NOT_WORKING"
        assert result["skill_progression"] == {}
        assert result["top_performers"] == []
        assert result["bottom_performers"] == []
        assert any("not found" in i["message"] for i in result["insights"])

    def test_wrong_status_returns_not_working(self):
        """CV-02: status != REWARDS_DISTRIBUTED → NOT_WORKING."""
        db = _seq_db(_q(first=_tournament(status="IN_PROGRESS")))
        calc = SandboxVerdictCalculator(db)

        result = calc.calculate_verdict(
            tournament_id=1,
            expected_participant_count=3,
            skills_to_test=["passing"],
            distribution_result=MagicMock(),
            skills_before_snapshot={},
        )

        assert result["verdict"] == "NOT_WORKING"
        assert any("IN_PROGRESS" in i["message"] for i in result["insights"])

    def test_participation_count_mismatch_returns_not_working(self):
        """CV-03: participation count != expected → NOT_WORKING."""
        # q0: Semester → tournament
        # q1: TournamentParticipation.count() → 2 (expected 3)
        db = _seq_db(
            _q(first=_tournament()),
            _q(count=2),  # participation count = 2
        )
        calc = SandboxVerdictCalculator(db)

        result = calc.calculate_verdict(
            tournament_id=1,
            expected_participant_count=3,
            skills_to_test=["passing"],
            distribution_result=MagicMock(),
            skills_before_snapshot={},
        )

        assert result["verdict"] == "NOT_WORKING"
        assert any("Expected 3 participants" in i["message"] for i in result["insights"])

    def test_zero_skill_change_returns_not_working(self):
        """CV-04: total_skill_change == 0 → NOT_WORKING (skills_before == skills_after)."""
        skills_before = {42: {"passing": 75.0}}

        # q0: Semester, q1: TournamentParticipation count=1
        db = _seq_db(
            _q(first=_tournament()),
            _q(count=1),
        )
        calc = SandboxVerdictCalculator(db)

        # After = 75.0 same as before → no change
        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 75.0)
            result = calc.calculate_verdict(
                tournament_id=1,
                expected_participant_count=1,
                skills_to_test=["passing"],
                distribution_result=MagicMock(),
                skills_before_snapshot=skills_before,
            )

        assert result["verdict"] == "NOT_WORKING"
        assert any("No skill changes detected" in i["message"] for i in result["insights"])

    def test_working_verdict_with_skill_progression(self):
        """CV-05: full happy path → WORKING verdict with non-zero skill progression."""
        skills_before = {42: {"passing": 70.0}}

        # q0: Semester, q1: TournamentParticipation count=1,
        # q2: TournamentRanking top3 (for _get_top_performers),
        # q3: User lookup for ranking user,
        # q4: TournamentRanking total count (for _get_bottom_performers),
        # q5: TournamentRanking bottom2
        ranking = _ranking(user_id=42, rank=1, points=100)
        user = _user_mock(uid=42)

        db = _seq_db(
            _q(first=_tournament()),   # Semester
            _q(count=1),               # participation count
            _q(all_=[ranking]),        # top performers rankings
            _q(first=user),            # User for ranking
            _q(count=1),               # total count for bottom performers check
            _q(all_=[]),               # bottom performers (count <= requested → empty)
        )
        calc = SandboxVerdictCalculator(db)

        with patch(_PATCH_SKILL) as mock_svc:
            # After > before → non-zero skill change
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 77.0)
            result = calc.calculate_verdict(
                tournament_id=1,
                expected_participant_count=1,
                skills_to_test=["passing"],
                distribution_result=MagicMock(),
                skills_before_snapshot=skills_before,
            )

        assert result["verdict"] == "WORKING"
        assert "passing" in result["skill_progression"]
        sp = result["skill_progression"]["passing"]
        assert sp["before"]["average"] == 70.0
        assert sp["after"]["average"] == 77.0
        assert sp["change"] == "+7.0 avg"
        # Insights include status transition + participant success + skill info + idempotency
        categories = [i["category"] for i in result["insights"]]
        assert "STATUS_TRANSITION" in categories
        assert "IDEMPOTENCY" in categories
        assert "SKILL_PROGRESSION" in categories

    def test_working_verdict_multiple_participants(self):
        """CV-06: multiple users in snapshot → per-user skill progression aggregated."""
        skills_before = {10: {"dribbling": 60.0}, 20: {"dribbling": 80.0}}

        rank1 = _ranking(user_id=10, rank=1, points=150)
        rank2 = _ranking(user_id=20, rank=2, points=120)
        user10 = _user_mock(uid=10, email="u10@test.com")
        user20 = _user_mock(uid=20, email="u20@test.com")

        db = _seq_db(
            _q(first=_tournament()),          # Semester
            _q(count=2),                       # participation count
            _q(all_=[rank1, rank2]),           # top 3 rankings
            _q(first=user10),                  # User for rank1
            _q(first=user20),                  # User for rank2
            _q(count=5),                       # total for bottom performers (> count=2 → not empty)
            _q(all_=[rank2]),                  # bottom 2 performers
            _q(first=user20),                  # User for bottom rank
        )
        calc = SandboxVerdictCalculator(db)

        def _profile(db_arg, user_id):
            if user_id == 10:
                return _skill_profile("dribbling", 65.0)
            return _skill_profile("dribbling", 85.0)

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.side_effect = _profile
            result = calc.calculate_verdict(
                tournament_id=1,
                expected_participant_count=2,
                skills_to_test=["dribbling"],
                distribution_result=MagicMock(),
                skills_before_snapshot=skills_before,
            )

        assert result["verdict"] == "WORKING"
        sp = result["skill_progression"]["dribbling"]
        # before avg = (60+80)/2 = 70, after avg = (65+85)/2 = 75
        assert sp["before"]["average"] == 70.0
        assert sp["after"]["average"] == 75.0
        assert sp["before"]["min"] == 60.0
        assert sp["before"]["max"] == 80.0
        assert len(result["top_performers"]) == 2
        assert result["top_performers"][0]["rank"] == 1
        assert result["top_performers"][0]["username"] == "u10"
        assert len(result["bottom_performers"]) == 1


# ── _calculate_skill_progression ──────────────────────────────────────────────

class TestCalculateSkillProgression:

    def test_empty_snapshot_returns_empty_stats(self):
        """SP-01: empty skills_before_snapshot → no stats for any skill."""
        db = MagicMock()
        calc = SandboxVerdictCalculator(db)
        result = calc._calculate_skill_progression(
            tournament_id=1,
            skills_to_test=["passing", "dribbling"],
            skills_before_snapshot={},
        )
        assert result == {}

    def test_skill_not_in_snapshot_uses_default_50(self):
        """SP-02: skill missing from user's snapshot dict → defaults to 50.0."""
        db = MagicMock()
        calc = SandboxVerdictCalculator(db)

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 60.0)
            result = calc._calculate_skill_progression(
                tournament_id=1,
                skills_to_test=["passing"],
                skills_before_snapshot={42: {}},  # no "passing" key → default 50.0
            )

        assert result["passing"]["before"]["average"] == 50.0
        assert result["passing"]["after"]["average"] == 60.0

    def test_non_dict_skill_profile_uses_default_50(self):
        """SP-03: get_skill_profile returns non-dict → after defaults to 50.0."""
        db = MagicMock()
        calc = SandboxVerdictCalculator(db)

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = None  # non-dict
            result = calc._calculate_skill_progression(
                tournament_id=1,
                skills_to_test=["passing"],
                skills_before_snapshot={42: {"passing": 70.0}},
            )

        assert result["passing"]["after"]["average"] == 50.0
        assert result["passing"]["before"]["average"] == 70.0

    def test_skill_missing_from_profile_uses_default_50(self):
        """SP-04: get_skill_profile has 'skills' dict but skill key absent → after=50.0."""
        db = MagicMock()
        calc = SandboxVerdictCalculator(db)

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = {"skills": {}}  # "passing" missing
            result = calc._calculate_skill_progression(
                tournament_id=1,
                skills_to_test=["passing"],
                skills_before_snapshot={42: {"passing": 70.0}},
            )

        assert result["passing"]["after"]["average"] == 50.0


# ── _get_bottom_performers ────────────────────────────────────────────────────

class TestGetBottomPerformers:

    def test_total_count_le_requested_returns_empty(self):
        """BP-01: total_count <= count → [] to avoid overlap with top performers."""
        # total_count query returns 2, requested=2 → overlap risk → return []
        db = _seq_db(_q(count=2))
        calc = SandboxVerdictCalculator(db)

        result = calc._get_bottom_performers(
            tournament_id=1,
            skills_to_test=["passing"],
            skills_before_snapshot={},
            count=2,
        )
        assert result == []

    def test_bottom_performers_returned_when_enough_participants(self):
        """BP-02: total_count > count → bottom N performers returned."""
        ranking = _ranking(user_id=42, rank=5, points=20)
        user = _user_mock(uid=42, email="bottom@test.com")

        db = _seq_db(
            _q(count=5),          # total count
            _q(all_=[ranking]),   # bottom performers
            _q(first=user),       # User for ranking
        )
        calc = SandboxVerdictCalculator(db)

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 55.0)
            result = calc._get_bottom_performers(
                tournament_id=1,
                skills_to_test=["passing"],
                skills_before_snapshot={42: {"passing": 60.0}},
                count=2,
            )

        assert len(result) == 1
        assert result[0]["rank"] == 5
        assert result[0]["username"] == "bottom"
        assert result[0]["skills_changed"]["passing"]["before"] == 60.0
        assert result[0]["skills_changed"]["passing"]["after"] == 55.0
        assert result[0]["skills_changed"]["passing"]["change"] == "-5.0"

    def test_user_not_found_uses_fallback_username(self):
        """BP-03: User not found → username = 'user_{id}'."""
        ranking = _ranking(user_id=99, rank=5, points=10)

        db = _seq_db(
            _q(count=5),          # total count
            _q(all_=[ranking]),   # bottom performers
            _q(first=None),       # User not found
        )
        calc = SandboxVerdictCalculator(db)

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 50.0)
            result = calc._get_bottom_performers(
                tournament_id=1,
                skills_to_test=["passing"],
                skills_before_snapshot={},
                count=2,
            )

        assert result[0]["username"] == "user_99"


# ── Sprint 43 additions — targeted mutation kill tests ─────────────────────

class TestInsightStringValues:
    """
    Sprint 43: Assert exact category/severity/message in every insight dict.

    The 13 existing tests only check result["verdict"] or use partial message
    substring checks.  String-literal mutants on category/severity values all
    survived.  Exact field assertions are the targeted fix.
    """

    # ── NOT_WORKING: tournament not found ─────────────────────────────────

    def test_tournament_not_found_insight_category(self):
        """Exact 'VERDICT' category — kills any string-literal replacement."""
        db = _seq_db(_q(first=None))
        result = SandboxVerdictCalculator(db).calculate_verdict(
            tournament_id=99, expected_participant_count=1,
            skills_to_test=["passing"], distribution_result=None,
            skills_before_snapshot={},
        )
        assert result["insights"][0]["category"] == "VERDICT"

    def test_tournament_not_found_insight_severity(self):
        """Exact 'ERROR' severity — kills severity string-literal mutant."""
        db = _seq_db(_q(first=None))
        result = SandboxVerdictCalculator(db).calculate_verdict(
            tournament_id=99, expected_participant_count=1,
            skills_to_test=["passing"], distribution_result=None,
            skills_before_snapshot={},
        )
        assert result["insights"][0]["severity"] == "ERROR"

    def test_tournament_not_found_message_contains_id_and_not_found(self):
        """Message includes the tournament ID and the phrase 'not found'."""
        db = _seq_db(_q(first=None))
        result = SandboxVerdictCalculator(db).calculate_verdict(
            tournament_id=99, expected_participant_count=1,
            skills_to_test=["passing"], distribution_result=None,
            skills_before_snapshot={},
        )
        msg = result["insights"][0]["message"]
        assert "99" in msg
        assert "not found" in msg

    # ── NOT_WORKING: wrong status ─────────────────────────────────────────

    def test_wrong_status_insight_category_severity_and_message(self):
        """Wrong-status insight: VERDICT/ERROR with both status names in message."""
        db = _seq_db(_q(first=_tournament(status="IN_PROGRESS")))
        result = SandboxVerdictCalculator(db).calculate_verdict(
            tournament_id=1, expected_participant_count=1,
            skills_to_test=[], distribution_result=None,
            skills_before_snapshot={},
        )
        insight = result["insights"][0]
        assert insight["category"] == "VERDICT"
        assert insight["severity"] == "ERROR"
        assert "IN_PROGRESS" in insight["message"]
        assert "REWARDS_DISTRIBUTED" in insight["message"]

    # ── NOT_WORKING: zero skill change ────────────────────────────────────

    def test_zero_skill_change_insight_category_and_severity(self):
        """Zero-skill-change insight: SKILL_PROGRESSION/ERROR + expected phrase."""
        skills_before = {42: {"passing": 75.0}}
        db = _seq_db(_q(first=_tournament()), _q(count=1))
        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 75.0)
            result = SandboxVerdictCalculator(db).calculate_verdict(
                tournament_id=1, expected_participant_count=1,
                skills_to_test=["passing"], distribution_result=None,
                skills_before_snapshot=skills_before,
            )
        sp_err = [i for i in result["insights"]
                  if i["category"] == "SKILL_PROGRESSION" and i["severity"] == "ERROR"]
        assert len(sp_err) == 1
        assert "No skill changes detected" in sp_err[0]["message"]

    # ── WORKING path insight fields ───────────────────────────────────────

    def _working_db(self):
        """DB sequence for a minimal full-WORKING path: 1 participant, 1 ranking."""
        ranking = _ranking(user_id=42, rank=1, points=100)
        user = _user_mock(uid=42, email="player@test.com")
        return _seq_db(
            _q(first=_tournament()),   # Semester
            _q(count=1),               # TournamentParticipation count
            _q(all_=[ranking]),        # top performers
            _q(first=user),            # User for ranking
            _q(count=1),               # bottom performers total (1 ≤ 2 → [])
            _q(all_=[]),               # bottom performers (not consumed; guard exits early)
        )

    def _working_result(self, skill_after=77.0):
        skills_before = {42: {"passing": 70.0}}
        db = self._working_db()
        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", skill_after)
            return SandboxVerdictCalculator(db).calculate_verdict(
                tournament_id=1, expected_participant_count=1,
                skills_to_test=["passing"], distribution_result=None,
                skills_before_snapshot=skills_before,
            )

    def test_working_path_status_transition_insight_fields(self):
        """STATUS_TRANSITION/SUCCESS insight exists and message mentions REWARDS_DISTRIBUTED."""
        result = self._working_result()
        st = [i for i in result["insights"] if i["category"] == "STATUS_TRANSITION"]
        assert len(st) == 1
        assert st[0]["severity"] == "SUCCESS"
        assert "REWARDS_DISTRIBUTED" in st[0]["message"]

    def test_working_path_idempotency_insight_fields(self):
        """IDEMPOTENCY/SUCCESS insight: exact category + severity, 'duplicate' in message."""
        result = self._working_result()
        idem = [i for i in result["insights"] if i["category"] == "IDEMPOTENCY"]
        assert len(idem) == 1
        assert idem[0]["severity"] == "SUCCESS"
        assert "duplicate" in idem[0]["message"].lower()

    def test_working_path_skill_progression_info_insight_fields(self):
        """SKILL_PROGRESSION/INFO insight: message includes '+7.0 points' format."""
        result = self._working_result()
        info = [i for i in result["insights"]
                if i["category"] == "SKILL_PROGRESSION" and i["severity"] == "INFO"]
        assert len(info) == 1
        assert "points" in info[0]["message"]
        assert "+7.0" in info[0]["message"]

    def test_participation_success_insight_fields(self):
        """VERDICT/SUCCESS insight: all participants rewarded successfully."""
        result = self._working_result()
        ok = [i for i in result["insights"]
              if i["category"] == "VERDICT" and i["severity"] == "SUCCESS"]
        assert len(ok) == 1
        assert "1" in ok[0]["message"]  # expected_participant_count

    def test_skill_progression_change_field_has_avg_suffix(self):
        """The 'change' key in skill_progression dict ends with ' avg' suffix."""
        result = self._working_result()
        change = result["skill_progression"]["passing"]["change"]
        assert change.endswith(" avg"), f"Expected ' avg' suffix, got: {change!r}"


class TestBoundaryConditions:
    """
    Sprint 43: Kill comparison and arithmetic mutants via boundary-specific tests.
    """

    def test_participation_count_greater_than_expected_not_working(self):
        """CV-08 (symmetric): count=4 > expected=3 → NOT_WORKING."""
        db = _seq_db(_q(first=_tournament()), _q(count=4))
        result = SandboxVerdictCalculator(db).calculate_verdict(
            tournament_id=1, expected_participant_count=3,
            skills_to_test=["passing"], distribution_result=None,
            skills_before_snapshot={},
        )
        assert result["verdict"] == "NOT_WORKING"
        assert any("Expected 3 participants" in i["message"] for i in result["insights"])

    def test_total_count_strictly_less_than_requested_returns_empty(self):
        """BP-04: total=1 < count=2 → [] (strict-less-than boundary)."""
        db = _seq_db(_q(count=1))  # total=1, requested count=2
        result = SandboxVerdictCalculator(db)._get_bottom_performers(
            tournament_id=1, skills_to_test=["passing"],
            skills_before_snapshot={}, count=2,
        )
        assert result == []

    def test_abs_skill_change_mixed_signs_yields_working(self):
        """
        Two skills with equal-and-opposite changes: shooting +10, passing −10.

        Without abs(): total_skill_change = 0 → NOT_WORKING (wrong).
        With abs():    total_skill_change = 20 → WORKING (correct).

        Directly kills the abs() arithmetic mutant at line 114.
        """
        skills_before = {42: {"shooting": 50.0, "passing": 60.0}}
        ranking = _ranking(user_id=42, rank=1, points=100)
        user = _user_mock(uid=42)
        db = _seq_db(
            _q(first=_tournament()), _q(count=1),
            _q(all_=[ranking]), _q(first=user),
            _q(count=1), _q(all_=[]),
        )

        def _profile(_db, _uid):
            return {"skills": {
                "shooting": {"current_level": 60.0},  # before=50 → +10
                "passing":  {"current_level": 50.0},  # before=60 → -10
            }}

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.side_effect = _profile
            result = SandboxVerdictCalculator(db).calculate_verdict(
                tournament_id=1, expected_participant_count=1,
                skills_to_test=["shooting", "passing"], distribution_result=None,
                skills_before_snapshot=skills_before,
            )
        assert result["verdict"] == "WORKING"

    def test_performer_skill_change_format_no_avg_suffix(self):
        """Performer 'change' field is '+X.X' with NO ' avg' suffix (kills format mutant)."""
        ranking = _ranking(user_id=42, rank=5, points=20)
        user = _user_mock(uid=42, email="bottom@test.com")
        db = _seq_db(_q(count=5), _q(all_=[ranking]), _q(first=user))
        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 55.0)
            result = SandboxVerdictCalculator(db)._get_bottom_performers(
                tournament_id=1, skills_to_test=["passing"],
                skills_before_snapshot={42: {"passing": 60.0}}, count=2,
            )
        change = result[0]["skills_changed"]["passing"]["change"]
        assert change == "-5.0"
        assert not change.endswith(" avg")


class TestGetTopPerformers:
    """
    Sprint 43: Direct tests of _get_top_performers — fills the gap where only
    _get_bottom_performers had isolation tests.  Kills mutants in lines 238-286
    including the null-user fallback and username/email derivation.
    """

    def test_top_performers_null_user_fallback_username(self):
        """User query returns None → username = 'user_{ranking.user_id}'."""
        ranking = _ranking(user_id=77, rank=1, points=200)
        db = _seq_db(_q(all_=[ranking]), _q(first=None))
        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 70.0)
            result = SandboxVerdictCalculator(db)._get_top_performers(
                tournament_id=1, skills_to_test=["passing"],
                skills_before_snapshot={}, count=3,
            )
        assert result[0]["username"] == "user_77"

    def test_top_performers_username_extracted_from_email(self):
        """Username is the local part of email (before '@')."""
        ranking = _ranking(user_id=42, rank=1, points=150)
        user = _user_mock(uid=42, email="alice@example.com")
        db = _seq_db(_q(all_=[ranking]), _q(first=user))
        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.return_value = _skill_profile("passing", 80.0)
            result = SandboxVerdictCalculator(db)._get_top_performers(
                tournament_id=1, skills_to_test=["passing"],
                skills_before_snapshot={42: {"passing": 70.0}}, count=3,
            )
        assert result[0]["username"] == "alice"

    def test_top_performers_total_skill_gain_and_change_format(self):
        """total_skill_gain = sum of per-skill changes; 'change' format is '+X.X'."""
        ranking = _ranking(user_id=42, rank=1, points=100)
        user = _user_mock(uid=42)
        db = _seq_db(_q(all_=[ranking]), _q(first=user))
        skills_before = {42: {"shooting": 50.0, "passing": 60.0}}

        def _profile(_db, _uid):
            return {"skills": {
                "shooting": {"current_level": 55.0},  # +5
                "passing":  {"current_level": 65.0},  # +5
            }}

        with patch(_PATCH_SKILL) as mock_svc:
            mock_svc.get_skill_profile.side_effect = _profile
            result = SandboxVerdictCalculator(db)._get_top_performers(
                tournament_id=1, skills_to_test=["shooting", "passing"],
                skills_before_snapshot=skills_before, count=3,
            )
        assert result[0]["total_skill_gain"] == 10.0
        assert result[0]["skills_changed"]["shooting"]["change"] == "+5.0"
        assert result[0]["skills_changed"]["passing"]["change"] == "+5.0"
