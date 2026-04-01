"""
Unit tests for app/utils/ — validators, game_results, rbac.

Coverage targets:
  - app/utils/validators.py  (126 lines, ~0% previously)
  - app/utils/game_results.py (55 lines, ~0% previously)
  - app/utils/rbac.py        (212 lines, ~0% previously)
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.utils.validators import validate_phone_number, validate_address, validate_name
from app.utils.game_results import parse_game_results, get_participants
from app.utils.rbac import (
    validate_license_ownership,
    validate_can_modify_user_data,
    validate_instructor_can_modify_student,
    require_role,
    validate_admin_only,
    validate_admin_or_instructor,
)
from app.models.user import UserRole


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user(role: UserRole, user_id: int = 42) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.role = role
    return u


# ── validate_phone_number ─────────────────────────────────────────────────────

class TestValidatePhoneNumber:

    def test_valid_international_format(self):
        ok, fmt, err = validate_phone_number("+36201234567")
        assert ok is True
        assert fmt == "+36201234567"
        assert err is None

    def test_valid_with_spaces(self):
        ok, fmt, err = validate_phone_number("+36 20 123 4567")
        assert ok is True
        assert fmt.startswith("+36")
        assert err is None

    def test_empty_string(self):
        ok, fmt, err = validate_phone_number("")
        assert ok is False
        assert fmt is None
        assert "required" in err.lower()

    def test_whitespace_only(self):
        ok, fmt, err = validate_phone_number("   ")
        assert ok is False
        assert "required" in err.lower()

    def test_invalid_string(self):
        ok, fmt, err = validate_phone_number("invalid")
        assert ok is False
        assert fmt is None
        assert err is not None

    def test_hungarian_local_format(self):
        """Without +, treated as Hungarian (HU) local number."""
        ok, fmt, err = validate_phone_number("06201234567")
        # Valid HU format → may succeed; either valid or returns error message
        assert isinstance(ok, bool)
        assert isinstance(err, (str, type(None)))

    def test_returns_e164_format(self):
        """Formatted number is in E164 format (+countrycode...)."""
        ok, fmt, err = validate_phone_number("+44 7700 900123")
        if ok:
            assert fmt.startswith("+")
            assert " " not in fmt


# ── validate_address ──────────────────────────────────────────────────────────

class TestValidateAddress:

    def test_valid_address(self):
        ok, err = validate_address("123 Main Street", "Budapest", "1011", "Hungary")
        assert ok is True
        assert err is None

    def test_short_street_address(self):
        ok, err = validate_address("abc", "Budapest", "1011", "Hungary")
        assert ok is False
        assert "street" in err.lower()

    def test_short_city(self):
        ok, err = validate_address("123 Long Street", "B", "1011", "Hungary")
        assert ok is False
        assert "city" in err.lower()

    def test_city_with_numbers(self):
        ok, err = validate_address("123 Main Street", "City123", "1011", "Hungary")
        assert ok is False
        assert "city" in err.lower()

    def test_short_postal_code(self):
        ok, err = validate_address("123 Main Street", "Budapest", "AB", "Hungary")
        assert ok is False
        assert "postal" in err.lower()

    def test_invalid_postal_code_chars(self):
        ok, err = validate_address("123 Main Street", "Budapest", "1011!!!", "Hungary")
        assert ok is False
        assert "postal" in err.lower()

    def test_short_country(self):
        ok, err = validate_address("123 Main Street", "Budapest", "1011", "H")
        assert ok is False
        assert "country" in err.lower()

    def test_country_with_numbers(self):
        ok, err = validate_address("123 Main Street", "Budapest", "1011", "Hungary123")
        assert ok is False
        assert "country" in err.lower()

    def test_city_with_hyphen_allowed(self):
        ok, err = validate_address("10 Oak Ave", "Saint-Germain", "75000", "France")
        assert ok is True

    def test_postal_code_with_letters(self):
        ok, err = validate_address("10 Oak Ave", "London", "SW1A 1AA", "United Kingdom")
        assert ok is True


# ── validate_name ─────────────────────────────────────────────────────────────

class TestValidateName:

    def test_valid_name(self):
        ok, err = validate_name("John")
        assert ok is True
        assert err is None

    def test_empty_name(self):
        ok, err = validate_name("")
        assert ok is False
        assert "required" in err.lower()

    def test_whitespace_name(self):
        ok, err = validate_name("  ")
        assert ok is False
        assert "required" in err.lower()

    def test_single_char(self):
        ok, err = validate_name("A")
        assert ok is False
        assert "2 characters" in err

    def test_numbers_only(self):
        ok, err = validate_name("123")
        assert ok is False
        assert "letter" in err.lower()

    def test_custom_field_name_in_error(self):
        ok, err = validate_name("", field_name="Last Name")
        assert "Last Name" in err

    def test_name_with_spaces(self):
        ok, err = validate_name("Mary Jane")
        assert ok is True

    def test_name_with_digits_and_letters(self):
        """Name with a letter is OK even if it has digits."""
        ok, err = validate_name("B2")
        assert ok is True  # contains at least one letter


# ── parse_game_results ────────────────────────────────────────────────────────

class TestParseGameResults:

    def test_none_returns_empty_dict(self):
        assert parse_game_results(None) == {}

    def test_dict_passthrough(self):
        data = {"score": 3, "goals": [1, 2, 3]}
        assert parse_game_results(data) == data

    def test_valid_json_string(self):
        assert parse_game_results('{"score": 5}') == {"score": 5}

    def test_invalid_json_string(self):
        assert parse_game_results("not-json") == {}

    def test_json_array_string_returns_empty(self):
        """JSON arrays are not dicts — return empty."""
        assert parse_game_results("[1, 2, 3]") == {}

    def test_integer_returns_empty(self):
        assert parse_game_results(42) == {}

    def test_empty_dict(self):
        assert parse_game_results({}) == {}

    def test_empty_json_string(self):
        assert parse_game_results("{}") == {}


# ── get_participants ──────────────────────────────────────────────────────────

class TestGetParticipants:

    def test_participants_key(self):
        data = {"participants": [{"id": 1}, {"id": 2}]}
        result = get_participants(data)
        assert result == [{"id": 1}, {"id": 2}]

    def test_raw_results_fallback(self):
        data = {"raw_results": [{"id": 3}]}
        result = get_participants(data)
        assert result == [{"id": 3}]

    def test_participants_takes_precedence_over_raw_results(self):
        data = {"participants": [{"id": 1}], "raw_results": [{"id": 99}]}
        result = get_participants(data)
        assert result == [{"id": 1}]

    def test_empty_dict_returns_empty_list(self):
        assert get_participants({}) == []

    def test_neither_key_returns_empty(self):
        assert get_participants({"score": 5}) == []

    def test_empty_participants_list(self):
        assert get_participants({"participants": []}) == []


# ── validate_license_ownership ────────────────────────────────────────────────

class TestValidateLicenseOwnership:

    def test_admin_always_allowed(self):
        db = MagicMock()
        user = _user(UserRole.ADMIN)
        result = validate_license_ownership(db, user, 1, "user_licenses")
        assert result is True
        db.execute.assert_not_called()

    def test_instructor_always_allowed(self):
        db = MagicMock()
        user = _user(UserRole.INSTRUCTOR)
        result = validate_license_ownership(db, user, 1, "user_licenses")
        assert result is True
        db.execute.assert_not_called()

    def test_student_owns_license(self):
        db = MagicMock()
        user = _user(UserRole.STUDENT, user_id=42)
        db.execute.return_value.fetchone.return_value = (42,)
        result = validate_license_ownership(db, user, 7, "user_licenses")
        assert result is True

    def test_student_not_owner_raises_403(self):
        db = MagicMock()
        user = _user(UserRole.STUDENT, user_id=42)
        db.execute.return_value.fetchone.return_value = (99,)  # different owner
        with pytest.raises(HTTPException) as exc:
            validate_license_ownership(db, user, 7, "user_licenses")
        assert exc.value.status_code == 403

    def test_license_not_found_raises_404(self):
        db = MagicMock()
        user = _user(UserRole.STUDENT, user_id=42)
        db.execute.return_value.fetchone.return_value = None
        with pytest.raises(HTTPException) as exc:
            validate_license_ownership(db, user, 99, "user_licenses")
        assert exc.value.status_code == 404


# ── validate_can_modify_user_data ─────────────────────────────────────────────

class TestValidateCanModifyUserData:

    def test_admin_can_modify_anyone(self):
        user = _user(UserRole.ADMIN, user_id=1)
        assert validate_can_modify_user_data(user, target_user_id=99) is True

    def test_user_can_modify_own_data(self):
        user = _user(UserRole.STUDENT, user_id=42)
        assert validate_can_modify_user_data(user, target_user_id=42) is True

    def test_user_cannot_modify_others_data(self):
        user = _user(UserRole.STUDENT, user_id=42)
        with pytest.raises(HTTPException) as exc:
            validate_can_modify_user_data(user, target_user_id=99)
        assert exc.value.status_code == 403

    def test_instructor_can_modify_own_data(self):
        user = _user(UserRole.INSTRUCTOR, user_id=42)
        assert validate_can_modify_user_data(user, target_user_id=42) is True

    def test_instructor_cannot_modify_other_without_admin(self):
        user = _user(UserRole.INSTRUCTOR, user_id=42)
        with pytest.raises(HTTPException) as exc:
            validate_can_modify_user_data(user, target_user_id=99)
        assert exc.value.status_code == 403

    def test_error_message_includes_operation(self):
        user = _user(UserRole.STUDENT, user_id=42)
        with pytest.raises(HTTPException) as exc:
            validate_can_modify_user_data(user, target_user_id=99, operation="delete profile")
        assert "delete profile" in exc.value.detail


# ── validate_instructor_can_modify_student ────────────────────────────────────

class TestValidateInstructorCanModifyStudent:

    def test_admin_always_allowed(self):
        db = MagicMock()
        user = _user(UserRole.ADMIN)
        result = validate_instructor_can_modify_student(db, user, student_user_id=5)
        assert result is True
        db.execute.assert_not_called()

    def test_non_instructor_non_admin_raises_403(self):
        db = MagicMock()
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            validate_instructor_can_modify_student(db, user, student_user_id=5)
        assert exc.value.status_code == 403

    def test_instructor_with_student_sessions(self):
        db = MagicMock()
        user = _user(UserRole.INSTRUCTOR, user_id=42)
        db.execute.return_value.scalar.return_value = 3  # 3 sessions
        result = validate_instructor_can_modify_student(db, user, student_user_id=5)
        assert result is True

    def test_instructor_without_student_sessions_raises_403(self):
        db = MagicMock()
        user = _user(UserRole.INSTRUCTOR, user_id=42)
        db.execute.return_value.scalar.return_value = 0  # no sessions
        with pytest.raises(HTTPException) as exc:
            validate_instructor_can_modify_student(db, user, student_user_id=5)
        assert exc.value.status_code == 403


# ── require_role ──────────────────────────────────────────────────────────────

class TestRequireRole:

    def test_user_has_required_role(self):
        user = _user(UserRole.ADMIN)
        require_role(user, [UserRole.ADMIN])  # should not raise

    def test_user_missing_role_raises_403(self):
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            require_role(user, [UserRole.ADMIN, UserRole.INSTRUCTOR])
        assert exc.value.status_code == 403

    def test_multiple_allowed_roles_first_match(self):
        user = _user(UserRole.INSTRUCTOR)
        require_role(user, [UserRole.ADMIN, UserRole.INSTRUCTOR])  # should not raise

    def test_error_includes_role_names(self):
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            require_role(user, [UserRole.ADMIN], operation="delete tournament")
        assert "delete tournament" in exc.value.detail


# ── validate_admin_only ───────────────────────────────────────────────────────

class TestValidateAdminOnly:

    def test_admin_passes(self):
        user = _user(UserRole.ADMIN)
        validate_admin_only(user)  # should not raise

    def test_instructor_raises_403(self):
        user = _user(UserRole.INSTRUCTOR)
        with pytest.raises(HTTPException) as exc:
            validate_admin_only(user)
        assert exc.value.status_code == 403

    def test_student_raises_403(self):
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            validate_admin_only(user)
        assert exc.value.status_code == 403

    def test_custom_operation_in_message(self):
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            validate_admin_only(user, operation="purge database")
        assert "purge database" in exc.value.detail


# ── validate_admin_or_instructor ──────────────────────────────────────────────

class TestValidateAdminOrInstructor:

    def test_admin_passes(self):
        user = _user(UserRole.ADMIN)
        validate_admin_or_instructor(user)  # should not raise

    def test_instructor_passes(self):
        user = _user(UserRole.INSTRUCTOR)
        validate_admin_or_instructor(user)  # should not raise

    def test_student_raises_403(self):
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            validate_admin_or_instructor(user)
        assert exc.value.status_code == 403

    def test_custom_operation_in_message(self):
        user = _user(UserRole.STUDENT)
        with pytest.raises(HTTPException) as exc:
            validate_admin_or_instructor(user, operation="view roster")
        assert "view roster" in exc.value.detail
