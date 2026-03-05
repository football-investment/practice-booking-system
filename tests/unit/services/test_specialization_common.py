"""
Unit tests for app/services/specialization/common.py

Patches: validate_specialization_exists, specialization_id_to_enum,
         get_config_loader, SpecializationValidator.
Covers: get_level_requirements, can_level_up, get_all_levels,
        enroll_user (get_student_progress skipped — depends on update_progress NameErrors).
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.specialization.common import (
    get_level_requirements,
    can_level_up,
    get_all_levels,
    enroll_user,
)


# ── patch helpers ─────────────────────────────────────────────────────────────

PATCH_BASE = "app.services.specialization.common"
VALIDATE = f"{PATCH_BASE}.validate_specialization_exists"
ID_TO_ENUM = f"{PATCH_BASE}.specialization_id_to_enum"
CONFIG_LOADER = f"{PATCH_BASE}.get_config_loader"
VALIDATOR = f"{PATCH_BASE}.SpecializationValidator"


def _mock_db():
    return MagicMock()


def _mock_config_loader(level_config=None, max_level=3):
    loader = MagicMock()
    loader.get_level_config.return_value = level_config
    loader.get_max_level.return_value = max_level
    return loader


def _basic_level_config():
    return {
        'name': 'Pre Coach',
        'xp_required': 100,
        'xp_max': 500,
        'required_sessions': 5,
        'required_projects': 2,
        'description': 'Basic level',
    }


# ── get_level_requirements ────────────────────────────────────────────────────

class TestGetLevelRequirements:

    @patch(VALIDATE, return_value=False)
    def test_invalid_specialization_returns_none(self, _):
        db = _mock_db()
        result = get_level_requirements(db, "INVALID_SPEC", level=1)
        assert result is None

    @patch(ID_TO_ENUM, return_value=None)
    @patch(VALIDATE, return_value=True)
    def test_invalid_enum_returns_none(self, _, __):
        db = _mock_db()
        result = get_level_requirements(db, "LFA_COACH", level=1)
        assert result is None

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_no_level_config_returns_none(self, _, __, mock_get_loader):
        mock_get_loader.return_value = _mock_config_loader(level_config=None)
        result = get_level_requirements(_mock_db(), "LFA_COACH", level=99)
        assert result is None

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_returns_formatted_dict(self, _, __, mock_get_loader):
        mock_get_loader.return_value = _mock_config_loader(level_config=_basic_level_config())
        result = get_level_requirements(_mock_db(), "LFA_COACH", level=1)
        assert result is not None
        assert result['level'] == 1
        assert result['name'] == 'Pre Coach'
        assert result['required_xp'] == 100
        assert result['required_sessions'] == 5
        assert result['required_projects'] == 2
        assert result['license_title'] == 'Pre Coach'

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_belt_fields_included_if_present(self, _, __, mock_get_loader):
        config = {**_basic_level_config(), 'belt_color': 'yellow', 'belt_name': 'Yellow Belt'}
        mock_get_loader.return_value = _mock_config_loader(level_config=config)
        result = get_level_requirements(_mock_db(), "GANCUJU_PLAYER", level=1)
        assert result['color'] == 'yellow'
        assert result['belt_color'] == 'yellow'
        assert result['belt_name'] == 'Yellow Belt'

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_requirements_fields_added_if_present(self, _, __, mock_get_loader):
        config = {
            **_basic_level_config(),
            'requirements': {
                'theory_hours': 20,
                'practice_hours': 40,
                'skills': ['dribbling', 'passing'],
            }
        }
        mock_get_loader.return_value = _mock_config_loader(level_config=config)
        result = get_level_requirements(_mock_db(), "LFA_COACH", level=2)
        assert result['theory_hours'] == 20
        assert result['practice_hours'] == 40
        assert result['skills'] == ['dribbling', 'passing']

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_exception_in_config_returns_none(self, _, __, mock_get_loader):
        loader = MagicMock()
        loader.get_level_config.side_effect = RuntimeError("config broken")
        mock_get_loader.return_value = loader
        result = get_level_requirements(_mock_db(), "LFA_COACH", level=1)
        assert result is None


# ── can_level_up ──────────────────────────────────────────────────────────────

class TestCanLevelUp:

    def _progress(self, spec_id="LFA_COACH", current_level=1, total_xp=200, completed_sessions=6):
        p = MagicMock()
        p.specialization_id = spec_id
        p.current_level = current_level
        p.total_xp = total_xp
        p.completed_sessions = completed_sessions
        return p

    @patch(f"{PATCH_BASE}.get_level_requirements", return_value=None)
    def test_no_next_level_returns_false(self, _):
        progress = self._progress(current_level=8)
        result = can_level_up(_mock_db(), progress)
        assert result is False

    @patch(f"{PATCH_BASE}.get_level_requirements")
    def test_insufficient_xp_returns_false(self, mock_req):
        mock_req.return_value = {'required_xp': 500, 'required_sessions': 0}
        progress = self._progress(total_xp=100, completed_sessions=10)
        result = can_level_up(_mock_db(), progress)
        assert result is False

    @patch(f"{PATCH_BASE}.get_level_requirements")
    def test_insufficient_sessions_returns_false(self, mock_req):
        mock_req.return_value = {'required_xp': 100, 'required_sessions': 10}
        progress = self._progress(total_xp=500, completed_sessions=3)
        result = can_level_up(_mock_db(), progress)
        assert result is False

    @patch(f"{PATCH_BASE}.get_level_requirements")
    def test_meets_all_requirements_returns_true(self, mock_req):
        mock_req.return_value = {'required_xp': 100, 'required_sessions': 5}
        progress = self._progress(total_xp=200, completed_sessions=6)
        result = can_level_up(_mock_db(), progress)
        assert result is True

    @patch(f"{PATCH_BASE}.get_level_requirements")
    def test_coach_spec_also_checks_hours(self, mock_req):
        mock_req.return_value = {
            'required_xp': 100,
            'required_sessions': 5,
            'theory_hours': 20,
            'practice_hours': 40,
        }
        progress = self._progress(spec_id='COACH', total_xp=200, completed_sessions=10)
        progress.theory_hours_completed = 10  # Not enough
        progress.practice_hours_completed = 50
        result = can_level_up(_mock_db(), progress)
        assert result is False

    @patch(f"{PATCH_BASE}.get_level_requirements")
    def test_coach_spec_hours_met_returns_true(self, mock_req):
        mock_req.return_value = {
            'required_xp': 100,
            'required_sessions': 5,
            'theory_hours': 20,
            'practice_hours': 40,
        }
        progress = self._progress(spec_id='COACH', total_xp=200, completed_sessions=10)
        progress.theory_hours_completed = 25
        progress.practice_hours_completed = 50
        result = can_level_up(_mock_db(), progress)
        assert result is True


# ── get_all_levels ────────────────────────────────────────────────────────────

class TestGetAllLevels:

    @patch(VALIDATE, return_value=False)
    def test_invalid_specialization_returns_empty(self, _):
        result = get_all_levels(_mock_db(), "INVALID")
        assert result == []

    @patch(ID_TO_ENUM, return_value=None)
    @patch(VALIDATE, return_value=True)
    def test_invalid_enum_returns_empty(self, _, __):
        result = get_all_levels(_mock_db(), "INVALID")
        assert result == []

    @patch(CONFIG_LOADER)
    @patch(f"{PATCH_BASE}.get_level_requirements")
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_returns_levels_list(self, _, __, mock_level_req, mock_get_loader):
        mock_get_loader.return_value = _mock_config_loader(max_level=3)
        mock_level_req.return_value = {'level': 1, 'name': 'Level 1'}
        result = get_all_levels(_mock_db(), "LFA_COACH")
        assert len(result) == 3

    @patch(CONFIG_LOADER)
    @patch(f"{PATCH_BASE}.get_level_requirements")
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_skips_none_levels(self, _, __, mock_level_req, mock_get_loader):
        mock_get_loader.return_value = _mock_config_loader(max_level=3)
        # First level returns data, second and third return None
        mock_level_req.side_effect = [{'level': 1}, None, None]
        result = get_all_levels(_mock_db(), "LFA_COACH")
        assert len(result) == 1

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_exception_returns_empty(self, _, __, mock_get_loader):
        loader = MagicMock()
        loader.get_max_level.side_effect = RuntimeError("broken")
        mock_get_loader.return_value = loader
        result = get_all_levels(_mock_db(), "LFA_COACH")
        assert result == []


# ── enroll_user ───────────────────────────────────────────────────────────────

class TestEnrollUser:

    @patch(VALIDATE, return_value=False)
    def test_invalid_specialization_raises(self, _):
        with pytest.raises(ValueError, match="does not exist"):
            enroll_user(_mock_db(), user_id=42, specialization_id="INVALID")

    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_user_not_found_raises(self, _, __):
        db = _mock_db()
        db.query.return_value.filter_by.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            enroll_user(db, user_id=999, specialization_id="LFA_COACH")

    @patch(VALIDATOR)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_already_enrolled_returns_false_success(self, _, __, mock_validator_cls):
        mock_validator_cls.return_value.validate_user_for_specialization.return_value = True
        db = _mock_db()
        mock_user = MagicMock()
        mock_progress = MagicMock()
        # filter_by called twice: first for user, second for existing progress
        db.query.return_value.filter_by.return_value.first.side_effect = [
            mock_user, mock_progress
        ]
        result = enroll_user(db, user_id=42, specialization_id="LFA_COACH")
        assert result['success'] is False
        assert 'already enrolled' in result['message']

    @patch(VALIDATOR)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_successful_enrollment(self, _, __, mock_validator_cls):
        mock_validator_cls.return_value.validate_user_for_specialization.return_value = True
        db = _mock_db()
        mock_user = MagicMock()
        # filter_by: user found, then no existing progress
        db.query.return_value.filter_by.return_value.first.side_effect = [mock_user, None]
        result = enroll_user(db, user_id=42, specialization_id="LFA_COACH")
        assert result['success'] is True
        db.add.assert_called_once()
        db.commit.assert_called_once()
