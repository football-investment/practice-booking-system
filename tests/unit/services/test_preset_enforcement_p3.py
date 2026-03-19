"""
Phase 3 — Preset Enforcement tests.

ENF-01  Preset overrides explicit skill_areas (override rejected log + metric)
ENF-02  Preset with empty skills_tested → ValueError in award_session_completion
ENF-03  _allow_skill_areas_override=True → override accepted, preset does NOT reject
ENF-04  skill_calc_preset metric incremented on preset path
ENF-05  skill_calc_fallback_reward_config metric + warning logged on legacy path
ENF-06  skill_calc_fallback_skill_mapping_table metric + warning logged on oldest path
"""
from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch, call


# ── Stubs (shared with p2 tests, redefined here for isolation) ─────────────

@dataclass
class _GamePresetStub:
    code: str
    id: int
    _skills_tested: list
    _skill_weights: dict

    @property
    def skills_tested(self):
        return self._skills_tested

    @property
    def skill_weights(self):
        return self._skill_weights


@dataclass
class _GameConfigStub:
    game_preset: Optional[_GamePresetStub]


@dataclass
class _SemesterStub:
    id: int
    game_config_obj: Optional[_GameConfigStub] = None
    reward_config: Optional[dict] = None


@dataclass
class _SessionStub:
    id: int = 1
    semester_id: Optional[int] = None
    session_reward_config: Optional[dict] = None
    event_category: object = None
    base_xp: Optional[int] = None


def _make_db_with_semester(semester: Optional[_SemesterStub]):
    db = MagicMock()
    (
        db.query.return_value
        .filter.return_value
        .options.return_value
        .first.return_value
    ) = semester
    db.query.return_value.filter.return_value.all.return_value = []
    reward_log = MagicMock()
    reward_log.xp_earned = 100
    db.query.return_value.filter.return_value.one.return_value = reward_log
    return db


# ── award_session_completion enforcement tests ────────────────────────────────

class TestENF01PresetOverridesExplicitSkillAreas:
    """ENF-01: preset is authoritative — explicit caller skill_areas is rejected."""

    def test_override_rejected_and_preset_used(self):
        from app.services import reward_service

        preset = _GamePresetStub(
            code="outfield_default", id=90,
            _skills_tested=["ball_control", "dribbling"],
            _skill_weights={"ball_control": 1.2, "dribbling": 1.5},
        )
        sem = _SemesterStub(id=20, game_config_obj=_GameConfigStub(game_preset=preset))
        db = _make_db_with_semester(sem)
        session = _SessionStub(id=50, semester_id=20, session_reward_config={"base_xp": 100})
        session.event_category = None

        mock_metrics = MagicMock()
        with patch("app.services.reward_service.metrics", mock_metrics):
            with patch("app.services.reward_service.log_debug"):
                with patch("app.services.reward_service.log_info") as mock_log_info:
                    with patch("app.services.reward_service.log_error"):
                        try:
                            reward_service.award_session_completion(
                                db=db,
                                user_id=1,
                                session=session,
                                skill_areas=["shooting", "long_shots"],  # ← override attempt
                            )
                        except Exception:
                            pass

        logged = str(mock_log_info.call_args_list)
        assert "skill_areas_override_rejected" in logged, (
            f"Expected override_rejected log. Got: {logged}"
        )
        assert "skill_areas_from_preset" in logged, (
            f"Expected skill_areas_from_preset log. Got: {logged}"
        )
        mock_metrics.increment.assert_any_call("skill_areas_override_rejected")
        mock_metrics.increment.assert_any_call("skill_areas_from_preset")


class TestENF02EmptyPresetRaisesValueError:
    """ENF-02: preset with empty skills_tested → ValueError (fail loud)."""

    def test_empty_skills_tested_raises_value_error(self):
        from app.services import reward_service

        empty_preset = _GamePresetStub(
            code="broken_preset", id=999,
            _skills_tested=[],
            _skill_weights={},
        )
        sem = _SemesterStub(id=21, game_config_obj=_GameConfigStub(game_preset=empty_preset))
        db = _make_db_with_semester(sem)
        session = _SessionStub(id=51, semester_id=21, session_reward_config={"base_xp": 100})
        session.event_category = None

        with patch("app.services.reward_service.metrics"):
            with patch("app.services.reward_service.log_debug"):
                with patch("app.services.reward_service.log_info"):
                    with patch("app.services.reward_service.log_error"):
                        with pytest.raises(ValueError, match="broken_preset"):
                            reward_service.award_session_completion(
                                db=db,
                                user_id=2,
                                session=session,
                            )


class TestENF03AdminOverrideFlag:
    """ENF-03: _allow_skill_areas_override=True → caller's list accepted, no rejection log."""

    def test_admin_flag_bypasses_override_check(self):
        from app.services import reward_service

        preset = _GamePresetStub(
            code="outfield_default", id=90,
            _skills_tested=["ball_control", "dribbling"],
            _skill_weights={"ball_control": 1.2, "dribbling": 1.5},
        )
        sem = _SemesterStub(id=22, game_config_obj=_GameConfigStub(game_preset=preset))
        db = _make_db_with_semester(sem)
        session = _SessionStub(id=52, semester_id=22, session_reward_config={"base_xp": 100})
        session.event_category = None

        mock_metrics = MagicMock()
        with patch("app.services.reward_service.metrics", mock_metrics):
            with patch("app.services.reward_service.log_debug"):
                with patch("app.services.reward_service.log_info") as mock_log_info:
                    with patch("app.services.reward_service.log_error"):
                        try:
                            reward_service.award_session_completion(
                                db=db,
                                user_id=3,
                                session=session,
                                skill_areas=["shooting"],
                                _allow_skill_areas_override=True,  # ← admin bypass
                            )
                        except Exception:
                            pass

        logged = str(mock_log_info.call_args_list)
        assert "skill_areas_override_rejected" not in logged, (
            "Should NOT log override_rejected when admin override flag is True"
        )
        # Override rejection metric must NOT be incremented
        increment_calls = [str(c) for c in mock_metrics.increment.call_args_list]
        assert not any("skill_areas_override_rejected" in c for c in increment_calls), (
            "skill_areas_override_rejected metric must not be incremented with admin flag"
        )


# ── calculate_skill_points_for_placement metric tests ────────────────────────

class TestENF04PresetMetric:
    """ENF-04: skill_calc_preset metric incremented when preset path used."""

    def test_preset_path_increments_metric(self):
        from app.services.tournament.tournament_participation_service import (
            calculate_skill_points_for_placement,
        )

        preset = _GamePresetStub(
            code="outfield_default", id=90,
            _skills_tested=["dribbling", "passing"],
            _skill_weights={"dribbling": 1.5, "passing": 1.0},
        )
        sem = _SemesterStub(id=30, game_config_obj=_GameConfigStub(game_preset=preset))

        db = MagicMock()
        (
            db.query.return_value
            .filter.return_value
            .options.return_value
            .first.return_value
        ) = sem
        db.query.return_value.filter.return_value.all.return_value = []

        mock_metrics = MagicMock()
        with patch(
            "app.services.tournament.tournament_participation_service.metrics",
            mock_metrics,
        ):
            result = calculate_skill_points_for_placement(db, tournament_id=30, placement=1)

        assert "dribbling" in result
        mock_metrics.increment.assert_any_call("skill_calc_preset")


class TestENF05FallbackRewardConfigMetric:
    """ENF-05: skill_calc_fallback_reward_config metric + warning on legacy reward_config path."""

    def test_legacy_reward_config_metric_and_warning(self):
        from app.services.tournament.tournament_participation_service import (
            calculate_skill_points_for_placement,
        )

        # No preset (game_config_obj=None) → legacy reward_config path
        sem = _SemesterStub(
            id=31,
            game_config_obj=None,
            reward_config={
                "skill_mappings": [
                    {"skill": "dribbling", "weight": 1.0, "enabled": True, "category": "TECHNICAL"},
                ]
            },
        )
        db = MagicMock()
        (
            db.query.return_value
            .filter.return_value
            .options.return_value
            .first.return_value
        ) = sem
        db.query.return_value.filter.return_value.all.return_value = []

        mock_metrics = MagicMock()
        import logging
        with patch(
            "app.services.tournament.tournament_participation_service.metrics",
            mock_metrics,
        ):
            with patch.object(
                logging.getLogger(
                    "app.services.tournament.tournament_participation_service"
                ), "warning"
            ) as mock_warn:
                calculate_skill_points_for_placement(db, tournament_id=31, placement=1)

        mock_metrics.increment.assert_any_call("skill_calc_fallback_reward_config")
        assert mock_warn.called, "Expected warning logged for legacy reward_config path"
        assert "LEGACY" in str(mock_warn.call_args_list)


class TestENF06FallbackSkillMappingTableMetric:
    """ENF-06: skill_calc_fallback_skill_mapping_table metric + warning on oldest legacy path."""

    def test_legacy_skill_mapping_table_metric_and_warning(self):
        from app.services.tournament.tournament_participation_service import (
            calculate_skill_points_for_placement,
        )

        # No preset, no reward_config → TournamentSkillMapping table fallback
        sem = _SemesterStub(id=32, game_config_obj=None, reward_config=None)

        mapping = MagicMock()
        mapping.skill_name = "passing"
        mapping.weight = 1.0

        db = MagicMock()
        (
            db.query.return_value
            .filter.return_value
            .options.return_value
            .first.return_value
        ) = sem
        # TournamentSkillMapping .all() returns one row
        db.query.return_value.filter.return_value.all.return_value = [mapping]

        mock_metrics = MagicMock()
        import logging
        with patch(
            "app.services.tournament.tournament_participation_service.metrics",
            mock_metrics,
        ):
            with patch.object(
                logging.getLogger(
                    "app.services.tournament.tournament_participation_service"
                ), "warning"
            ) as mock_warn:
                result = calculate_skill_points_for_placement(db, tournament_id=32, placement=None)

        assert "passing" in result
        mock_metrics.increment.assert_any_call("skill_calc_fallback_skill_mapping_table")
        assert mock_warn.called
        assert "LEGACY" in str(mock_warn.call_args_list)
