"""
Unit tests for app/services/specialization/common.py

Patches: validate_specialization_exists, specialization_id_to_enum,
         get_config_loader, SpecializationValidator.
Covers: get_level_requirements, can_level_up, get_all_levels,
        enroll_user, get_student_progress, update_progress.

Sprint P6 additions: name_en field, get_student_progress,
  update_progress (create=True patches for GamificationService /
  ProgressLicenseSyncService which have no module-level import).
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.specialization.common import (
    get_level_requirements,
    get_student_progress,
    update_progress,
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


# ── Sprint P6 additions ───────────────────────────────────────────────────────
# Covers the previously-skipped get_student_progress and update_progress,
# plus the name_en branch in get_level_requirements (line 84).

# ── get_level_requirements — name_en field (line 84) ─────────────────────────

class TestGetLevelRequirementsNameEn:

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_name_en_included_if_present(self, _, __, mock_get_loader):
        config = {**_basic_level_config(), 'name_en': 'Pre Coach EN'}
        mock_get_loader.return_value = _mock_config_loader(level_config=config)
        result = get_level_requirements(_mock_db(), "LFA_COACH", level=1)
        assert result['name_en'] == 'Pre Coach EN'

    @patch(CONFIG_LOADER)
    @patch(ID_TO_ENUM, return_value=MagicMock())
    @patch(VALIDATE, return_value=True)
    def test_name_en_absent_key_not_in_response(self, _, __, mock_get_loader):
        mock_get_loader.return_value = _mock_config_loader(level_config=_basic_level_config())
        result = get_level_requirements(_mock_db(), "LFA_COACH", level=1)
        assert 'name_en' not in result


# ── get_student_progress ──────────────────────────────────────────────────────

PATCH_GLR = f"{PATCH_BASE}.get_level_requirements"
PATCH_CAN = f"{PATCH_BASE}.can_level_up"


def _prog(spec_id="LFA_COACH", level=2, total_xp=150, sessions=5, projects=2):
    p = MagicMock()
    p.specialization_id = spec_id
    p.current_level = level
    p.total_xp = total_xp
    p.completed_sessions = sessions
    p.completed_projects = projects
    p.last_activity = None
    return p


def _db_with_progress(progress):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = progress
    return db


class TestGetStudentProgress:

    @patch(VALIDATE, return_value=False)
    def test_invalid_spec_raises_value_error(self, _):
        with pytest.raises(ValueError, match="does not exist"):
            get_student_progress(_mock_db(), 42, "INVALID")

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_existing_progress_returns_full_dict(self, _, mock_glr, __):
        mock_glr.side_effect = [
            {'level': 2, 'name': 'L2', 'required_xp': 200, 'required_sessions': 5},
            {'level': 3, 'name': 'L3', 'required_xp': 400, 'required_sessions': 10},
        ]
        progress = _prog(level=2, total_xp=150, sessions=5)
        result = get_student_progress(_db_with_progress(progress), 42, "LFA_COACH")
        assert result['student_id'] == 42
        assert result['specialization_id'] == "LFA_COACH"
        assert result['total_xp'] == 150
        assert result['is_max_level'] is False
        assert result['progress_percentage'] == 37   # 150/400*100 = 37.5 → int → 37

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_no_progress_creates_new_and_returns(self, _, mock_glr, __):
        mock_glr.return_value = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = get_student_progress(db, 42, "LFA_COACH")
        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result['student_id'] == 42

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR, return_value=None)
    @patch(VALIDATE, return_value=True)
    def test_max_level_flags_correctly(self, _, __, ___):
        """next_level_req=None → is_max_level=True, xp_needed=0, sessions_needed=0."""
        progress = _prog(level=8)
        result = get_student_progress(_db_with_progress(progress), 42, "LFA_COACH")
        assert result['is_max_level'] is True
        assert result['xp_needed'] == 0
        assert result['sessions_needed'] == 0
        assert result['progress_percentage'] == 0

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_progress_percentage_capped_at_100(self, _, mock_glr, __):
        mock_glr.side_effect = [
            {'level': 1, 'name': 'L1', 'required_xp': 100, 'required_sessions': 5},
            {'level': 2, 'name': 'L2', 'required_xp': 100, 'required_sessions': 5},
        ]
        progress = _prog(total_xp=999)   # way beyond required_xp=100
        result = get_student_progress(_db_with_progress(progress), 42, "LFA_COACH")
        assert result['progress_percentage'] == 100

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_xp_needed_computed(self, _, mock_glr, __):
        mock_glr.side_effect = [
            {'level': 1, 'required_xp': 100, 'required_sessions': 5},
            {'level': 2, 'required_xp': 200, 'required_sessions': 10},
        ]
        progress = _prog(total_xp=50, sessions=3)
        result = get_student_progress(_db_with_progress(progress), 42, "LFA_COACH")
        assert result['xp_needed'] == 150       # 200 - 50
        assert result['sessions_needed'] == 7   # 10 - 3

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_xp_needed_zero_when_exceeded(self, _, mock_glr, __):
        mock_glr.side_effect = [
            {'level': 1, 'required_xp': 100, 'required_sessions': 5},
            {'level': 2, 'required_xp': 100, 'required_sessions': 5},
        ]
        progress = _prog(total_xp=200, sessions=10)
        result = get_student_progress(_db_with_progress(progress), 42, "LFA_COACH")
        assert result['xp_needed'] == 0
        assert result['sessions_needed'] == 0

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_coach_spec_adds_hours_fields(self, _, mock_glr, __):
        mock_glr.side_effect = [
            {'level': 1, 'required_xp': 100, 'required_sessions': 5},
            {'level': 2, 'required_xp': 200, 'required_sessions': 10,
             'theory_hours': 20, 'practice_hours': 40},
        ]
        progress = _prog(spec_id='COACH', level=1, total_xp=50, sessions=3)
        progress.theory_hours_completed = 10
        progress.practice_hours_completed = 20
        result = get_student_progress(_db_with_progress(progress), 42, 'COACH')
        assert 'theory_hours_completed' in result
        assert 'practice_hours_completed' in result
        assert result['theory_hours_needed'] == 10   # 20 - 10
        assert result['practice_hours_needed'] == 20  # 40 - 20

    @patch(PATCH_CAN, return_value=False)
    @patch(PATCH_GLR)
    @patch(VALIDATE, return_value=True)
    def test_coach_spec_no_next_level_no_hours_needed(self, _, mock_glr, __):
        """COACH at max level: no next_level_req → no theory/practice_hours_needed."""
        mock_glr.side_effect = [
            {'level': 8, 'required_xp': 5000, 'required_sessions': 50},
            None,  # no next level
        ]
        progress = _prog(spec_id='COACH', level=8)
        progress.theory_hours_completed = 100
        progress.practice_hours_completed = 200
        result = get_student_progress(_db_with_progress(progress), 42, 'COACH')
        assert 'theory_hours_completed' in result
        assert 'theory_hours_needed' not in result


# ── update_progress ───────────────────────────────────────────────────────────

PATCH_GAMI = f"{PATCH_BASE}.GamificationService"
PATCH_SYNC = f"{PATCH_BASE}.ProgressLicenseSyncService"


class TestUpdateProgress:
    """
    GamificationService and ProgressLicenseSyncService are NOT imported at
    module level in common.py — they are bare name references (NameError in
    production too).  Use create=True to inject them during tests.
    """

    def _db(self, progress):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = progress
        return db

    @patch(VALIDATE, return_value=False)
    def test_invalid_spec_raises_value_error(self, _):
        with pytest.raises(ValueError):
            update_progress(_mock_db(), 42, "INVALID")

    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN, return_value=False)
    @patch(VALIDATE, return_value=True)
    def test_no_level_up_returns_success(self, _, __, mock_sync, mock_gami):
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        progress = _prog()
        result = update_progress(self._db(progress), 42, "LFA_COACH", xp_gained=50)
        assert result['success'] is True
        assert result['leveled_up'] is False
        assert result['levels_gained'] == 0
        assert result['sync_result'] is None

    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN, return_value=False)
    @patch(VALIDATE, return_value=True)
    def test_xp_and_sessions_incremented(self, _, __, mock_sync, mock_gami):
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        progress = _prog(total_xp=100, sessions=3)
        update_progress(self._db(progress), 42, "LFA_COACH",
                        xp_gained=50, sessions_completed=2, projects_completed=1)
        assert progress.total_xp == 150
        assert progress.completed_sessions == 5
        assert progress.completed_projects == 3

    @patch(PATCH_GLR)
    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN)
    @patch(VALIDATE, return_value=True)
    def test_level_up_increments_level(self, _, mock_can, mock_sync, mock_gami, mock_glr):
        mock_can.side_effect = [True, False]   # level up once then stop
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        mock_sync.return_value.sync_progress_to_license.return_value = {'success': True}
        mock_glr.return_value = {'level': 2, 'name': 'Level 2'}
        progress = _prog(level=1)
        result = update_progress(self._db(progress), 42, "LFA_COACH")
        assert result['leveled_up'] is True
        assert result['levels_gained'] == 1
        assert progress.current_level == 2

    @patch(PATCH_GLR)
    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN)
    @patch(VALIDATE, return_value=True)
    def test_multiple_level_ups_in_one_call(self, _, mock_can, mock_sync, mock_gami, mock_glr):
        mock_can.side_effect = [True, True, False]  # level up twice
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        mock_sync.return_value.sync_progress_to_license.return_value = {'success': True}
        mock_glr.return_value = {'level': 3}
        progress = _prog(level=1)
        result = update_progress(self._db(progress), 42, "LFA_COACH")
        assert result['levels_gained'] == 2

    @patch(PATCH_GLR)
    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN)
    @patch(VALIDATE, return_value=True)
    def test_sync_exception_does_not_fail_update(self, _, mock_can, mock_sync, mock_gami, mock_glr):
        mock_can.side_effect = [True, False]
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        mock_sync.return_value.sync_progress_to_license.side_effect = RuntimeError("sync error")
        mock_glr.return_value = {'level': 2}
        progress = _prog()
        result = update_progress(self._db(progress), 42, "LFA_COACH")
        assert result['success'] is True   # exception swallowed

    @patch(PATCH_GLR)
    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN)
    @patch(VALIDATE, return_value=True)
    def test_sync_failure_logged_but_returns_success(self, _, mock_can, mock_sync, mock_gami, mock_glr):
        mock_can.side_effect = [True, False]
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        mock_sync.return_value.sync_progress_to_license.return_value = {
            'success': False, 'message': 'not synced'
        }
        mock_glr.return_value = {'level': 2}
        progress = _prog()
        result = update_progress(self._db(progress), 42, "LFA_COACH")
        assert result['success'] is True

    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN, return_value=False)
    @patch(VALIDATE, return_value=True)
    def test_no_progress_creates_new(self, _, __, mock_sync, mock_gami):
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        result = update_progress(db, 42, "LFA_COACH")
        db.add.assert_called_once()
        assert result['success'] is True

    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN, return_value=False)
    @patch(VALIDATE, return_value=True)
    def test_achievements_included_in_result(self, _, __, mock_sync, mock_gami):
        ach = MagicMock()
        ach.title = "Level Up!"
        ach.description = "Leveled up"
        ach.icon = "🏆"
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = [ach]
        progress = _prog()
        result = update_progress(self._db(progress), 42, "LFA_COACH")
        assert len(result['achievements_earned']) == 1
        assert result['achievements_earned'][0]['title'] == "Level Up!"

    @patch(PATCH_GAMI, create=True)
    @patch(PATCH_SYNC, create=True)
    @patch(PATCH_CAN, return_value=False)
    @patch(VALIDATE, return_value=True)
    def test_db_committed(self, _, __, mock_sync, mock_gami):
        mock_gami.return_value.check_and_award_specialization_achievements.return_value = []
        progress = _prog()
        db = self._db(progress)
        update_progress(db, 42, "LFA_COACH")
        db.commit.assert_called_once()
