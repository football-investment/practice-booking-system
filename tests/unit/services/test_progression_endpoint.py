"""
Sprint 29 — api/api_v1/endpoints/progression.py
=================================================
Target: ≥85% statement, ≥70% branch

Covers:
  validate_prerequisite   — all tracks + edge cases
  calculate_completed_semesters — all three tracks + specializations
  get_user_progress       — success path
  update_user_progress    — success (all tracks) + 400 prerequisite failures
  get_progression_systems — no-dep return
  get_skill_profile       — 404 (no license) + success
  get_skill_timeline      — 404 (no license) + 404 (skill not found) + success
  get_skill_audit         — 404 (no license) + success
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.progression import (
    validate_prerequisite,
    calculate_completed_semesters,
    get_user_progress,
    update_user_progress,
    get_progression_systems,
    get_skill_profile,
    get_skill_timeline,
    get_skill_audit,
    UpdateProgressRequest,
    PROGRESSION_SYSTEMS,
)

_PATCH_SPS = "app.api.api_v1.endpoints.progression.skill_progression_service"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _user(uid=42):
    u = MagicMock()
    u.id = uid
    return u


def _license_db(lic):
    """db.query(UserLicense).filter(...).first() → lic"""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = lic
    db.query.return_value = q
    return db


def _license(lic_id=10, spec="LFA_FOOTBALL_PLAYER"):
    lic = MagicMock()
    lic.id = lic_id
    lic.specialization_type = spec
    return lic


# ============================================================================
# validate_prerequisite
# ============================================================================

class TestValidatePrerequisite:

    def test_unknown_track_returns_false(self):
        """VP-01: unknown track → False."""
        assert validate_prerequisite("unknown", "junior", {}) is False

    def test_no_prerequisite_returns_true(self):
        """VP-02: level with no prerequisite (first level) → True."""
        # 'junior' has no prerequisite in internship
        assert validate_prerequisite("internship", "junior", {}) is True

    # ── internship ──────────────────────────────────────────────────────────

    def test_internship_current_not_in_levels_returns_false(self):
        """VP-03: current_level not in levels → index=-1 < required_index → False."""
        progress = {"internship_level": "nonexistent"}
        assert validate_prerequisite("internship", "senior", progress) is False

    def test_internship_no_current_level_returns_false(self):
        """VP-04: no current_level → index=-1 → False for level needing prerequisite."""
        assert validate_prerequisite("internship", "medior", {}) is False

    def test_internship_meets_prerequisite(self):
        """VP-05: current_level >= required → True."""
        progress = {"internship_level": "junior"}
        assert validate_prerequisite("internship", "medior", progress) is True

    def test_internship_senior_needs_medior(self):
        """VP-06: senior needs medior — junior not enough → False."""
        progress = {"internship_level": "junior"}
        assert validate_prerequisite("internship", "senior", progress) is False

    # ── coach ───────────────────────────────────────────────────────────────

    def test_coach_specialization_no_prerequisite_entry(self):
        """VP-07: coach specialization has no entry in prerequisites dict → True (always allowed)."""
        # goalkeeper is not in PROGRESSION_SYSTEMS["coach"]["prerequisites"]
        assert validate_prerequisite("coach", "goalkeeper", {}) is True

    def test_coach_foundation_no_current_level_returns_false(self):
        """VP-08: coach foundation needing prerequisite but no current level → False."""
        # youth_assistant requires pre_lead, but no current level set
        assert validate_prerequisite("coach", "youth_assistant", {}) is False

    def test_coach_foundation_below_required_returns_false(self):
        """VP-09: coach foundation below required → False."""
        # youth_assistant requires pre_lead; pre_assistant < pre_lead
        progress = {"coach_foundation_level": "pre_assistant"}
        assert validate_prerequisite("coach", "youth_assistant", progress) is False

    def test_coach_foundation_not_in_levels_returns_false(self):
        """VP-10: coach foundation current not in levels → -1 → False."""
        progress = {"coach_foundation_level": "bogus"}
        assert validate_prerequisite("coach", "youth_assistant", progress) is False

    def test_coach_foundation_meets_prerequisite(self):
        """VP-11: coach foundation pre_lead → youth_assistant allowed."""
        progress = {"coach_foundation_level": "pre_lead"}
        assert validate_prerequisite("coach", "youth_assistant", progress) is True

    # ── gancuju ─────────────────────────────────────────────────────────────

    def test_gancuju_no_current_returns_false(self):
        """VP-12: gancuju with no current level → -1 → False."""
        assert validate_prerequisite("gancuju", "dawn", {}) is False

    def test_gancuju_meets_prerequisite(self):
        """VP-13: gancuju bamboo → dawn allowed."""
        progress = {"gancuju_level": "bamboo"}
        assert validate_prerequisite("gancuju", "dawn", progress) is True

    def test_gancuju_skipping_levels_returns_false(self):
        """VP-14: gancuju skip two levels → False."""
        progress = {"gancuju_level": "bamboo"}
        assert validate_prerequisite("gancuju", "reed", progress) is False


# ============================================================================
# calculate_completed_semesters
# ============================================================================

class TestCalculateCompletedSemesters:

    def test_empty_progress_returns_zeros(self):
        """CS-01: no levels → all 0."""
        result = calculate_completed_semesters({})
        assert result == {"internship": 0, "coach": 0, "gancuju": 0}

    def test_internship_junior(self):
        """CS-02: internship junior (1 semester)."""
        result = calculate_completed_semesters({"internship_level": "junior"})
        assert result["internship"] == 1
        assert result["coach"] == 0

    def test_internship_medior(self):
        """CS-03: internship medior = junior(1) + medior(1) = 2."""
        result = calculate_completed_semesters({"internship_level": "medior"})
        assert result["internship"] == 2

    def test_internship_level_not_in_list(self):
        """CS-04: invalid level not in list → -1 index → empty range → 0."""
        result = calculate_completed_semesters({"internship_level": "bogus"})
        assert result["internship"] == 0

    def test_coach_foundation_pre_assistant(self):
        """CS-05: coach pre_assistant → 1 semester."""
        result = calculate_completed_semesters({"coach_foundation_level": "pre_assistant"})
        assert result["coach"] == 1

    def test_coach_foundation_pre_lead(self):
        """CS-06: coach pre_lead = pre_assistant(1) + pre_lead(2) = 3."""
        result = calculate_completed_semesters({"coach_foundation_level": "pre_lead"})
        assert result["coach"] == 3

    def test_coach_specializations_add_to_count(self):
        """CS-07: specializations add semester counts."""
        progress = {
            "coach_foundation_level": "pre_lead",
            "coach_specializations": ["goalkeeper", "fitness"]
        }
        result = calculate_completed_semesters(progress)
        # pre_assistant(1) + pre_lead(2) + goalkeeper(2) + fitness(2) = 7
        assert result["coach"] == 7

    def test_coach_unknown_specialization_not_counted(self):
        """CS-08: unknown specialization not in SEMESTER_COUNTS → skipped."""
        progress = {
            "coach_foundation_level": "pre_assistant",
            "coach_specializations": ["unknown_spec"]
        }
        result = calculate_completed_semesters(progress)
        assert result["coach"] == 1  # only pre_assistant

    def test_gancuju_bamboo(self):
        """CS-09: gancuju bamboo → 1 semester."""
        result = calculate_completed_semesters({"gancuju_level": "bamboo"})
        assert result["gancuju"] == 1

    def test_gancuju_reed(self):
        """CS-10: gancuju reed = bamboo(1) + dawn(1) + reed(1) = 3."""
        result = calculate_completed_semesters({"gancuju_level": "reed"})
        assert result["gancuju"] == 3

    def test_all_tracks_combined(self):
        """CS-11: all three tracks populated simultaneously."""
        progress = {
            "internship_level": "junior",
            "coach_foundation_level": "pre_assistant",
            "gancuju_level": "bamboo"
        }
        result = calculate_completed_semesters(progress)
        assert result["internship"] == 1
        assert result["coach"] == 1
        assert result["gancuju"] == 1


# ============================================================================
# get_user_progress endpoint
# ============================================================================

class TestGetUserProgress:

    def test_returns_user_progress_response(self):
        """GUP-01: success path returns UserProgressResponse structure."""
        db = MagicMock()
        result = get_user_progress(current_user=_user(), db=db)
        assert result.internship_level == "junior"
        assert result.coach_foundation_level == "pre_assistant"
        assert result.gancuju_level == "bamboo"
        assert isinstance(result.completed_semesters, dict)
        assert "internship" in result.completed_semesters


# ============================================================================
# update_user_progress endpoint
# ============================================================================

class TestUpdateUserProgress:

    def _req(self, track, level, specializations=None):
        return UpdateProgressRequest(track=track, level=level, specializations=specializations)

    def test_internship_medior_no_prerequisite_met_returns_400(self):
        """UUP-01: internship medior fails — current is junior (already junior, medior allowed)."""
        # Actually junior → medior: prerequisite is junior, current is "junior" → met
        # Let's pick senior: prerequisite is medior, current is junior → fails
        req = self._req("internship", "senior")
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            update_user_progress(request=req, current_user=_user(), db=db)
        assert exc.value.status_code == 400

    def test_internship_medior_prerequisite_met_returns_success(self):
        """UUP-02: internship medior — prerequisite met (current=junior) → success."""
        req = self._req("internship", "medior")
        db = MagicMock()
        result = update_user_progress(request=req, current_user=_user(), db=db)
        assert result["message"] == "Progress updated successfully"
        assert result["new_progress"]["internship_level"] == "medior"

    def test_internship_junior_no_prerequisite_needed(self):
        """UUP-03: internship junior has no prerequisite → always succeeds."""
        req = self._req("internship", "junior")
        db = MagicMock()
        result = update_user_progress(request=req, current_user=_user(), db=db)
        assert result["new_progress"]["internship_level"] == "junior"

    def test_coach_specialization_adds_to_list(self):
        """UUP-04: coach specialization (pre_lead in current) → added to specializations."""
        req = self._req("coach", "goalkeeper")
        db = MagicMock()
        # current mock progress has pre_lead foundation → goalkeeper allowed
        result = update_user_progress(request=req, current_user=_user(), db=db)
        assert "goalkeeper" in result["new_progress"]["coach_specializations"]

    def test_coach_foundation_level_update(self):
        """UUP-05: coach foundation level (pre_lead) → coach_foundation_level updated."""
        req = self._req("coach", "pre_lead")
        db = MagicMock()
        result = update_user_progress(request=req, current_user=_user(), db=db)
        assert result["new_progress"]["coach_foundation_level"] == "pre_lead"

    def test_gancuju_level_update(self):
        """UUP-06: gancuju bamboo (no prerequisite) → gancuju_level updated."""
        req = self._req("gancuju", "bamboo")
        db = MagicMock()
        result = update_user_progress(request=req, current_user=_user(), db=db)
        assert result["new_progress"]["gancuju_level"] == "bamboo"

    def test_gancuju_skip_levels_returns_400(self):
        """UUP-07: gancuju skip level (bamboo → reed) → 400."""
        req = self._req("gancuju", "reed")
        db = MagicMock()
        with pytest.raises(HTTPException) as exc:
            update_user_progress(request=req, current_user=_user(), db=db)
        assert exc.value.status_code == 400

    def test_returns_completed_semesters_in_response(self):
        """UUP-08: response includes completed_semesters."""
        req = self._req("gancuju", "bamboo")
        db = MagicMock()
        result = update_user_progress(request=req, current_user=_user(), db=db)
        assert "completed_semesters" in result


# ============================================================================
# get_progression_systems endpoint
# ============================================================================

class TestGetProgressionSystems:

    def test_returns_all_three_systems(self):
        """GPS-01: returns systems dict with all three tracks."""
        result = get_progression_systems()
        assert "systems" in result
        assert set(result["systems"].keys()) == {"internship", "coach", "gancuju"}

    def test_systems_have_ui_metadata(self):
        """GPS-02: each system has id, title, emoji."""
        result = get_progression_systems()
        for key, sys in result["systems"].items():
            assert "id" in sys
            assert "title" in sys
            assert "emoji" in sys

    def test_returns_semester_counts(self):
        """GPS-03: returns semester_counts dict."""
        result = get_progression_systems()
        assert "semester_counts" in result
        assert "junior" in result["semester_counts"]


# ============================================================================
# get_skill_profile endpoint
# ============================================================================

class TestGetSkillProfile:

    def test_no_license_raises_404(self):
        """GSP-01: no active license → 404."""
        db = _license_db(None)
        with pytest.raises(HTTPException) as exc:
            get_skill_profile(current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_success_with_skills(self):
        """GSP-02: license found → returns SkillProfileResponse."""
        lic = _license()
        db = _license_db(lic)

        profile_data = {
            "skills": {
                "passing": {
                    "current_level": 75.0,
                    "baseline": 50.0,
                    "total_delta": 25.0,
                    "tournament_delta": 20.0,
                    "assessment_delta": 5.0,
                    "assessment_count": 3,
                    "tournament_count": 2,
                    "tier": "INTERMEDIATE",
                    "tier_emoji": "⚽",
                }
            },
            "average_level": 75.0,
            "total_tournaments": 2,
            "total_assessments": 3,
        }

        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_profile.return_value = profile_data
            result = get_skill_profile(current_user=_user(), db=db)

        assert result.user_license_id == 10
        assert result.average_level == 75.0
        assert "passing" in result.skills
        assert result.skills["passing"].current_level == 75.0
        assert result.skills["passing"].tier == "INTERMEDIATE"

    def test_empty_skills_returns_empty_dict(self):
        """GSP-03: license found but no skills → empty skills dict."""
        lic = _license()
        db = _license_db(lic)

        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_profile.return_value = {
                "skills": {},
                "average_level": 0.0,
                "total_tournaments": 0,
                "total_assessments": 0,
            }
            result = get_skill_profile(current_user=_user(), db=db)

        assert result.skills == {}
        assert result.total_assessments == 0


# ============================================================================
# get_skill_timeline endpoint
# ============================================================================

class TestGetSkillTimeline:

    def test_no_license_raises_404(self):
        """GST-01: no license → 404."""
        db = _license_db(None)
        with pytest.raises(HTTPException) as exc:
            get_skill_timeline(skill="passing", current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_skill_not_found_raises_404(self):
        """GST-02: get_skill_timeline returns None → 404."""
        lic = _license()
        db = _license_db(lic)
        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_timeline.return_value = None
            with pytest.raises(HTTPException) as exc:
                get_skill_timeline(skill="unknown_skill", current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_success_returns_timeline(self):
        """GST-03: success path returns SkillTimelineResponse."""
        lic = _license()
        db = _license_db(lic)

        timeline_data = {
            "skill": "passing",
            "baseline": 50.0,
            "current_level": 75.0,
            "total_delta": 25.0,
            "timeline": [
                {
                    "tournament_id": 1,
                    "tournament_name": "Test Cup",
                    "achieved_at": "2026-01-01T00:00:00",
                    "placement": 1,
                    "total_players": 8,
                    "placement_skill": 95.0,
                    "skill_weight": 1.0,
                    "skill_value_after": 75.0,
                    "delta_from_baseline": 25.0,
                    "delta_from_previous": 25.0,
                }
            ],
        }

        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_timeline.return_value = timeline_data
            result = get_skill_timeline(skill="passing", current_user=_user(), db=db)

        assert result.skill == "passing"
        assert result.baseline == 50.0
        assert len(result.timeline) == 1
        assert result.timeline[0].tournament_name == "Test Cup"

    def test_empty_timeline_returns_empty_list(self):
        """GST-04: success with empty timeline list."""
        lic = _license()
        db = _license_db(lic)

        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_timeline.return_value = {
                "skill": "dribbling",
                "baseline": 50.0,
                "current_level": 50.0,
                "total_delta": 0.0,
                "timeline": [],
            }
            result = get_skill_timeline(skill="dribbling", current_user=_user(), db=db)

        assert result.timeline == []


# ============================================================================
# get_skill_audit endpoint
# ============================================================================

class TestGetSkillAudit:

    def test_no_license_raises_404(self):
        """GSA-01: no license → 404."""
        db = _license_db(None)
        with pytest.raises(HTTPException) as exc:
            get_skill_audit(current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_success_empty_audit(self):
        """GSA-02: empty audit rows → total=0, unfair=0."""
        lic = _license()
        db = _license_db(lic)
        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_audit.return_value = []
            result = get_skill_audit(current_user=_user(), db=db)
        assert result.total_entries == 0
        assert result.unfair_entries == 0
        assert result.audit == []

    def test_unfair_entries_counted_only_when_ema_path(self):
        """GSA-03: unfair_entries = rows with fairness_ok=False AND ema_path=True."""
        lic = _license()
        db = _license_db(lic)

        rows = [
            {  # unfair + ema_path → counted
                "tournament_id": 1, "tournament_name": "T1",
                "achieved_at": "2026-01-01", "placement": 3, "total_players": 8,
                "skill": "passing", "skill_weight": 1.0, "avg_weight": 1.0,
                "is_dominant": True, "expected_change": True,
                "placement_skill": 70.0, "delta_this_tournament": -5.0,
                "norm_delta": -5.0, "actual_changed": True,
                "fairness_ok": False, "opponent_factor": 1.0, "ema_path": True,
            },
            {  # unfair but ema_path=False → NOT counted
                "tournament_id": 2, "tournament_name": "T2",
                "achieved_at": "2026-01-02", "placement": 2, "total_players": 8,
                "skill": "dribbling", "skill_weight": 1.0, "avg_weight": 1.0,
                "is_dominant": False, "expected_change": True,
                "placement_skill": 75.0, "delta_this_tournament": 2.0,
                "norm_delta": 2.0, "actual_changed": True,
                "fairness_ok": False, "opponent_factor": 1.0, "ema_path": False,
            },
            {  # fairness_ok=True → not unfair
                "tournament_id": 3, "tournament_name": "T3",
                "achieved_at": "2026-01-03", "placement": 1, "total_players": 8,
                "skill": "finishing", "skill_weight": 1.2, "avg_weight": 1.0,
                "is_dominant": True, "expected_change": True,
                "placement_skill": 95.0, "delta_this_tournament": 10.0,
                "norm_delta": 10.0, "actual_changed": True,
                "fairness_ok": True, "opponent_factor": 1.0, "ema_path": True,
            },
        ]

        with patch(_PATCH_SPS) as mock_sps:
            mock_sps.get_skill_audit.return_value = rows
            result = get_skill_audit(current_user=_user(), db=db)

        assert result.total_entries == 3
        assert result.unfair_entries == 1
        assert len(result.audit) == 3
