"""
Unit tests for app/api/api_v1/endpoints/instructor_management/positions.py

Coverage targets (105 stmts, ~14% → ≥95%):
  create_position()       — POST /
    - 403: not master instructor for location
    - 404: location not found
    - 422: no matching semester
    - happy path: position created, from_orm called, attributes set

  list_my_positions()     — GET /my-positions
    - empty list
    - positions returned with from_orm
    - location_id filter applied (no crash)
    - status_filter applied (no crash)
    - pos.location/master None → location_name/master_name None

  get_job_board()         — GET /job-board
    - empty board
    - user_has_applied=True when application found
    - user_has_applied=False when no application
    - location_id + specialization filters
    - pos.location/master None → "Unknown" fallbacks

  get_position()          — GET /{position_id}
    - 404: not found
    - happy path: from_orm called, attributes set

  update_position()       — PATCH /{position_id}
    - 404: not found
    - 403: not owner (posted_by != current_user.id)
    - happy path: no fields updated (all None)
    - happy path: all fields updated including status
    - partial update: only description

  delete_position()       — DELETE /{position_id}
    - 404: not found
    - 403: not owner and not admin
    - 400: has applications and not admin
    - admin override: can delete with applications (different owner)
    - happy path: no applications → deleted

NOTE: delete_position uses UserRole enum comparison (fixed in Issue #11).
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.models.user import UserRole
from app.api.api_v1.endpoints.instructor_management.positions import (
    create_position,
    list_my_positions,
    get_job_board,
    get_position,
    update_position,
    delete_position,
)

_POS   = "app.api.api_v1.endpoints.instructor_management.positions"
_PRESP = f"{_POS}.PositionResponse"
_PLR   = f"{_POS}.PositionListResponse"
_JBPOS = f"{_POS}.JobBoardPosition"
_JBR   = f"{_POS}.JobBoardResponse"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(user_id=42, role="INSTRUCTOR", name="Coach"):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.name = name
    return u


def _q(first=None, all_=None, count_=0):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.first.return_value = first
    q.count.return_value = count_
    q.all.return_value = all_ or []
    return q


def _db_seq(*qs):
    db = MagicMock()
    db.query.side_effect = list(qs) + [MagicMock()] * 4
    return db


def _pos_data(location_id=10):
    d = MagicMock()
    d.location_id = location_id
    d.specialization_type = "LFA_PLAYER"
    d.age_group = "U18"
    d.year = 2026
    d.time_period_start = "January"
    d.time_period_end = "June"
    d.description = "Looking for assistant"
    d.priority = 1
    d.application_deadline = MagicMock()
    return d


def _position_mock(position_id=1, posted_by=42):
    p = MagicMock()
    p.id = position_id
    p.posted_by = posted_by
    p.location = MagicMock()
    p.location.name = "Test Location"
    p.master = MagicMock()
    p.master.name = "Master Coach"
    p.applications = []
    p.specialization_type = "LFA_PLAYER"
    p.age_group = "U18"
    p.year = 2026
    p.time_period_start = "January"
    p.time_period_end = "June"
    p.description = "Test description"
    p.priority = 1
    p.application_deadline = MagicMock()
    p.created_at = MagicMock()
    return p


# ── create_position ─────────────────────────────────────────────────────────────

class TestCreatePosition:

    def test_403_not_master_instructor(self):
        db = _db_seq(_q(first=None))    # no master record for location
        with pytest.raises(HTTPException) as exc:
            create_position(_pos_data(), db=db, current_user=_user())
        assert exc.value.status_code == 403
        assert "master instructor" in exc.value.detail.lower()

    def test_404_location_not_found(self):
        db = _db_seq(
            _q(first=MagicMock()),   # master found
            _q(first=None),          # location not found
        )
        with pytest.raises(HTTPException) as exc:
            create_position(_pos_data(), db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_422_no_matching_semester(self):
        db = _db_seq(
            _q(first=MagicMock()),   # master found
            _q(first=MagicMock()),   # location found
            _q(first=None),          # no matching semester
        )
        with pytest.raises(HTTPException) as exc:
            create_position(_pos_data(), db=db, current_user=_user())
        assert exc.value.status_code == 422
        assert "semester" in exc.value.detail.lower()

    def test_happy_path_creates_position_and_returns_response(self):
        location = MagicMock()
        location.name = "Main Campus"
        db = _db_seq(
            _q(first=MagicMock()),   # master found
            _q(first=location),      # location found
            _q(first=MagicMock()),   # semester found
        )
        with patch(_PRESP) as MockPR, \
             patch(f"{_POS}.InstructorPosition") as MockIP:
            mock_response = MagicMock()
            MockPR.from_orm.return_value = mock_response
            MockIP.return_value = MagicMock()
            create_position(_pos_data(), db=db, current_user=_user(name="Head Coach"))
        db.add.assert_called()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        MockPR.from_orm.assert_called_once()
        assert mock_response.location_name == "Main Campus"
        assert mock_response.master_name == "Head Coach"
        assert mock_response.application_count == 0


# ── list_my_positions ─────────────────────────────────────────────────────────

class TestListMyPositions:

    def test_empty_returns_total_zero(self):
        db = MagicMock()
        db.query.return_value = _q(all_=[])
        with patch(_PRESP), patch(_PLR) as MockPLR:
            MockPLR.return_value = MagicMock()
            # Pass None explicitly — FastAPI Query(None) default is a truthy FieldInfo
            list_my_positions(location_id=None, status_filter=None, db=db, current_user=_user())
        MockPLR.assert_called_once_with(total=0, positions=[])

    def test_returns_positions_with_from_orm(self):
        pos = _position_mock()
        db = MagicMock()
        db.query.return_value = _q(all_=[pos])
        mock_response = MagicMock()
        with patch(_PRESP) as MockPR, patch(_PLR) as MockPLR:
            MockPR.from_orm.return_value = mock_response
            MockPLR.return_value = MagicMock()
            list_my_positions(location_id=None, status_filter=None, db=db, current_user=_user())
        MockPR.from_orm.assert_called_once_with(pos)
        MockPLR.assert_called_once_with(total=1, positions=[mock_response])

    def test_location_id_filter_does_not_crash(self):
        db = MagicMock()
        db.query.return_value = _q(all_=[])
        with patch(_PRESP), patch(_PLR) as MockPLR:
            MockPLR.return_value = MagicMock()
            list_my_positions(location_id=5, status_filter=None, db=db, current_user=_user())
        MockPLR.assert_called_once_with(total=0, positions=[])

    def test_status_filter_applied(self):
        db = MagicMock()
        db.query.return_value = _q(all_=[])
        status_filter = MagicMock()
        status_filter.value = "OPEN"
        with patch(_PRESP), patch(_PLR) as MockPLR, \
             patch(f"{_POS}.PositionStatus"):
            MockPLR.return_value = MagicMock()
            list_my_positions(location_id=None, status_filter=status_filter, db=db, current_user=_user())
        MockPLR.assert_called_once_with(total=0, positions=[])

    def test_position_with_no_location_or_master(self):
        pos = _position_mock()
        pos.location = None
        pos.master = None
        db = MagicMock()
        db.query.return_value = _q(all_=[pos])
        mock_response = MagicMock()
        with patch(_PRESP) as MockPR, patch(_PLR) as MockPLR:
            MockPR.from_orm.return_value = mock_response
            MockPLR.return_value = MagicMock()
            list_my_positions(location_id=None, status_filter=None, db=db, current_user=_user())
        assert mock_response.location_name is None
        assert mock_response.master_name is None


# ── get_job_board ─────────────────────────────────────────────────────────────

class TestGetJobBoard:

    def test_empty_board(self):
        db = MagicMock()
        db.query.return_value = _q(all_=[])
        with patch(_JBR) as MockJBR:
            MockJBR.return_value = MagicMock()
            get_job_board(location_id=None, specialization=None, db=db, current_user=_user())
        MockJBR.assert_called_once_with(total=0, positions=[])

    def test_position_user_has_applied(self):
        pos = _position_mock()
        app = MagicMock()
        app.status = "PENDING"
        db = _db_seq(
            _q(all_=[pos]),    # main OPEN positions query
            _q(first=app),     # PositionApplication check for pos
        )
        with patch(_JBPOS) as MockJBP, patch(_JBR) as MockJBR:
            MockJBP.return_value = MagicMock()
            MockJBR.return_value = MagicMock()
            get_job_board(location_id=None, specialization=None, db=db, current_user=_user())
        call_kwargs = MockJBP.call_args[1]
        assert call_kwargs["user_has_applied"] is True
        assert call_kwargs["user_application_status"] == "PENDING"

    def test_position_user_has_not_applied(self):
        pos = _position_mock()
        db = _db_seq(
            _q(all_=[pos]),    # main query
            _q(first=None),    # no application found
        )
        with patch(_JBPOS) as MockJBP, patch(_JBR) as MockJBR:
            MockJBP.return_value = MagicMock()
            MockJBR.return_value = MagicMock()
            get_job_board(location_id=None, specialization=None, db=db, current_user=_user())
        call_kwargs = MockJBP.call_args[1]
        assert call_kwargs["user_has_applied"] is False
        assert call_kwargs["user_application_status"] is None

    def test_location_and_specialization_filters(self):
        db = MagicMock()
        db.query.return_value = _q(all_=[])
        with patch(_JBR) as MockJBR:
            MockJBR.return_value = MagicMock()
            get_job_board(
                location_id=5, specialization="LFA_PLAYER",
                db=db, current_user=_user()
            )
        MockJBR.assert_called_once_with(total=0, positions=[])

    def test_position_with_no_location_or_master(self):
        """None location/master falls back to 'Unknown' strings."""
        pos = _position_mock()
        pos.location = None
        pos.master = None
        db = _db_seq(
            _q(all_=[pos]),
            _q(first=None),
        )
        with patch(_JBPOS) as MockJBP, patch(_JBR) as MockJBR:
            MockJBP.return_value = MagicMock()
            MockJBR.return_value = MagicMock()
            get_job_board(location_id=None, specialization=None, db=db, current_user=_user())
        call_kwargs = MockJBP.call_args[1]
        assert call_kwargs["location_name"] == "Unknown"
        assert call_kwargs["posted_by_name"] == "Unknown"


# ── get_position ─────────────────────────────────────────────────────────────

class TestGetPosition:

    def test_404_not_found(self):
        db = MagicMock()
        db.query.return_value = _q(first=None)
        with pytest.raises(HTTPException) as exc:
            get_position(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_happy_path_returns_response(self):
        pos = _position_mock()
        db = MagicMock()
        db.query.return_value = _q(first=pos)
        mock_response = MagicMock()
        with patch(_PRESP) as MockPR:
            MockPR.from_orm.return_value = mock_response
            result = get_position(1, db=db, current_user=_user())
        MockPR.from_orm.assert_called_once_with(pos)
        assert result is mock_response
        assert mock_response.location_name == pos.location.name
        assert mock_response.master_name == pos.master.name


# ── update_position ─────────────────────────────────────────────────────────────

class TestUpdatePosition:

    def test_404_not_found(self):
        db = MagicMock()
        db.query.return_value = _q(first=None)
        with pytest.raises(HTTPException) as exc:
            update_position(1, MagicMock(), db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_owner(self):
        pos = _position_mock(posted_by=99)   # different from current_user.id=42
        db = MagicMock()
        db.query.return_value = _q(first=pos)
        with pytest.raises(HTTPException) as exc:
            update_position(1, MagicMock(), db=db, current_user=_user(user_id=42))
        assert exc.value.status_code == 403
        assert "own positions" in exc.value.detail.lower()

    def test_happy_path_no_fields_updated(self):
        """All data fields None → skip all if-branches, still commits."""
        pos = _position_mock(posted_by=42)
        db = MagicMock()
        db.query.return_value = _q(first=pos)
        data = MagicMock()
        data.description = None
        data.priority = None
        data.application_deadline = None
        data.status = None
        with patch(_PRESP) as MockPR:
            MockPR.from_orm.return_value = MagicMock()
            update_position(1, data, db=db, current_user=_user(user_id=42))
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_all_fields_updated(self):
        pos = _position_mock(posted_by=42)
        db = MagicMock()
        db.query.return_value = _q(first=pos)
        data = MagicMock()
        data.description = "New description"
        data.priority = 3
        data.application_deadline = MagicMock()
        data.status = MagicMock()
        data.status.value = "CLOSED"
        with patch(_PRESP) as MockPR, \
             patch(f"{_POS}.PositionStatus") as MockPS:
            MockPR.from_orm.return_value = MagicMock()
            MockPS.__getitem__.return_value = MagicMock()
            update_position(1, data, db=db, current_user=_user(user_id=42))
        assert pos.description == "New description"
        assert pos.priority == 3
        assert pos.application_deadline is data.application_deadline
        db.commit.assert_called_once()

    def test_partial_update_description_only(self):
        pos = _position_mock(posted_by=42)
        db = MagicMock()
        db.query.return_value = _q(first=pos)
        data = MagicMock()
        data.description = "Partial update"
        data.priority = None
        data.application_deadline = None
        data.status = None
        with patch(_PRESP) as MockPR:
            MockPR.from_orm.return_value = MagicMock()
            update_position(1, data, db=db, current_user=_user(user_id=42))
        assert pos.description == "Partial update"
        db.commit.assert_called_once()


# ── delete_position ─────────────────────────────────────────────────────────────

class TestDeletePosition:

    def test_404_not_found(self):
        db = _db_seq(_q(first=None))
        with pytest.raises(HTTPException) as exc:
            delete_position(1, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_owner_not_admin(self):
        """Non-admin user trying to delete someone else's position."""
        pos = _position_mock(posted_by=99)   # not owned by current_user (id=42)
        db = _db_seq(_q(first=pos))
        with pytest.raises(HTTPException) as exc:
            delete_position(1, db=db, current_user=_user(user_id=42, role="INSTRUCTOR"))
        assert exc.value.status_code == 403
        assert "own positions" in exc.value.detail.lower()

    def test_400_has_applications_non_admin(self):
        """Owner cannot delete position that already has applications."""
        pos = _position_mock(posted_by=42)
        db = _db_seq(
            _q(first=pos),
            _q(count_=3),   # 3 existing applications
        )
        with pytest.raises(HTTPException) as exc:
            delete_position(1, db=db, current_user=_user(user_id=42, role="INSTRUCTOR"))
        assert exc.value.status_code == 400
        assert "application" in exc.value.detail.lower()

    def test_admin_can_delete_with_applications(self):
        """Admin bypasses both owner check and application guard."""
        pos = _position_mock(posted_by=99)   # different owner — admin overrides
        db = _db_seq(
            _q(first=pos),
            _q(count_=5),   # has applications — admin still allowed
        )
        result = delete_position(1, db=db, current_user=_user(role=UserRole.ADMIN))
        db.delete.assert_called_once_with(pos)
        db.commit.assert_called_once()
        assert result is None

    def test_happy_path_no_applications(self):
        """Owner with no applications can delete."""
        pos = _position_mock(posted_by=42)
        db = _db_seq(
            _q(first=pos),
            _q(count_=0),
        )
        result = delete_position(1, db=db, current_user=_user(user_id=42, role="INSTRUCTOR"))
        db.delete.assert_called_once_with(pos)
        db.commit.assert_called_once()
        assert result is None
