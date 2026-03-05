"""Unit tests for app/api/api_v1/endpoints/instructor_management/applications.py

Sprint P8 — Coverage target: ≥85% stmt, ≥75% branch

Covers:
- create_application   (POST /): 9 validation + success paths
- list_my_applications (GET /my-applications): empty + status_filter + with data
- list_applications_for_position (GET /for-position/{id}): 404/403/200
- review_application   (PATCH /{id}): 404/403/400/200 accept/decline
- get_application      (GET /{id}): 404/403/200 applicant/master
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.api.api_v1.endpoints.instructor_management.applications import (
    create_application,
    get_application,
    list_applications_for_position,
    list_my_applications,
    review_application,
)
from app.models.instructor_assignment import ApplicationStatus, PositionStatus
from app.schemas.instructor_management import (
    ApplicationCreate,
    ApplicationStatusEnum,
    ApplicationUpdate,
)

_BASE = "app.api.api_v1.endpoints.instructor_management.applications"

_LONG_MSG = "A" * 60  # ≥50 chars required by ApplicationCreate.application_message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(*, first=None, all_=None):
    q = MagicMock()
    for m in ("filter", "options", "order_by", "offset", "limit", "group_by", "join", "with_for_update"):
        getattr(q, m).return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    return q


def _seq_db(*qs):
    """n-th db.query() call returns qs[n]; safe fallback after exhaustion."""
    calls = [0]

    def _side(*args, **kw):
        idx = calls[0]
        calls[0] += 1
        return qs[idx] if idx < len(qs) else _q()

    db = MagicMock()
    db.query.side_effect = _side
    return db


def _user(uid=42, name="Alice", email="alice@test.com"):
    u = MagicMock()
    u.id = uid
    u.name = name
    u.email = email
    return u


def _position(
    *,
    status=PositionStatus.OPEN,
    deadline_past=False,
    location_id=1,
    posted_by=99,
):
    pos = MagicMock()
    pos.id = 1
    pos.status = status
    # Use a real datetime so tzinfo is None → datetime.now(None) is safe
    pos.application_deadline = (
        datetime(2020, 1, 1) if deadline_past else datetime(2099, 12, 31)
    )
    pos.location_id = location_id
    pos.specialization_type = "LFA_PLAYER_PRE"
    pos.year = 2024
    pos.time_period_start = "M01"
    pos.time_period_end = "M06"
    pos.age_group = "PRE"
    pos.posted_by = posted_by
    return pos


def _app_mock(
    *,
    app_id=1,
    applicant_id=42,
    position_posted_by=99,
    status=ApplicationStatus.PENDING,
):
    """Full PositionApplication mock with nested .position and .applicant."""
    app = MagicMock()
    app.id = app_id
    app.applicant_id = applicant_id
    app.status = status
    app.position = MagicMock()
    app.position.posted_by = position_posted_by
    app.position.specialization_type = "LFA_PLAYER_PRE"
    app.position.age_group = "PRE"
    app.position.time_period_start = "M01"
    app.position.time_period_end = "M06"
    app.applicant = MagicMock()
    app.applicant.name = "Bob"
    app.applicant.email = "bob@test.com"
    return app


def _create_data(position_id=1):
    return ApplicationCreate(position_id=position_id, application_message=_LONG_MSG)


def _update_data(status=ApplicationStatusEnum.ACCEPTED):
    return ApplicationUpdate(status=status)


# ===========================================================================
# TestCreateApplication
# ===========================================================================

class TestCreateApplication:
    def test_404_position_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_400_position_not_open(self):
        pos = _position(status=PositionStatus.CLOSED)
        db = _seq_db(_q(first=pos))
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "not accepting" in exc.value.detail.lower()

    def test_400_deadline_passed(self):
        pos = _position(deadline_past=True)
        db = _seq_db(_q(first=pos))
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "deadline" in exc.value.detail.lower()

    def test_400_duplicate_application(self):
        pos = _position()
        existing_app = MagicMock()
        db = _seq_db(_q(first=pos), _q(first=existing_app))
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 400
        assert "already applied" in exc.value.detail.lower()

    def test_403_no_availability(self):
        pos = _position()
        loc = MagicMock()
        db = _seq_db(
            _q(first=pos),   # position
            _q(first=None),  # no duplicate
            _q(first=loc),   # location found
            _q(first=None),  # no availability
        )
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 403
        assert "availability" in exc.value.detail.lower()

    def test_500_position_location_not_found(self):
        pos = _position()
        db = _seq_db(
            _q(first=pos),   # position
            _q(first=None),  # no duplicate
            _q(first=None),  # location NOT found → 500
        )
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 500

    def test_403_no_license(self):
        pos = _position()
        loc = MagicMock()
        avail = MagicMock()
        db = _seq_db(
            _q(first=pos),   # position
            _q(first=None),  # no duplicate
            _q(first=loc),   # location
            _q(first=avail), # availability ok
            _q(first=None),  # no license → 403
        )
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 403
        assert "license" in exc.value.detail.lower()

    def test_409_already_master_at_other_location(self):
        pos = _position()
        loc = MagicMock()
        avail = MagicMock()
        lic = MagicMock()
        existing_master = MagicMock()
        db = _seq_db(
            _q(first=pos),           # position
            _q(first=None),          # no duplicate
            _q(first=loc),           # location
            _q(first=avail),         # availability
            _q(first=lic),           # license
            _q(first=existing_master), # master elsewhere → 409
        )
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 409
        assert "master instructor" in exc.value.detail.lower()

    def test_409_time_conflict(self):
        pos = _position()
        loc = MagicMock()
        avail = MagicMock()
        lic = MagicMock()
        conflict = MagicMock()
        db = _seq_db(
            _q(first=pos),    # position
            _q(first=None),   # no duplicate
            _q(first=loc),    # location
            _q(first=avail),  # availability
            _q(first=lic),    # license
            _q(first=None),   # no master at other location
            _q(first=conflict), # time conflict → 409
        )
        with pytest.raises(Exception) as exc:
            create_application(_create_data(), db=db, current_user=_user())
        assert exc.value.status_code == 409
        assert "active assignment" in exc.value.detail.lower()

    def test_201_success_calls_db_add_commit(self):
        pos = _position()
        loc = MagicMock()
        avail = MagicMock()
        lic = MagicMock()
        db = _seq_db(
            _q(first=pos),   # position
            _q(first=None),  # no duplicate
            _q(first=loc),   # location
            _q(first=avail), # availability
            _q(first=lic),   # license
            _q(first=None),  # no master elsewhere
            _q(first=None),  # no time conflict
        )
        user = _user()
        mock_resp = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp:
            MockResp.from_orm.return_value = mock_resp
            result = create_application(_create_data(), db=db, current_user=user)
        assert db.add.called
        assert db.commit.called
        assert db.refresh.called
        assert result is mock_resp
        assert mock_resp.applicant_name == user.name
        assert mock_resp.applicant_email == user.email


# ===========================================================================
# TestListMyApplications
# ===========================================================================

class TestListMyApplications:
    def test_200_empty_list(self):
        db = _seq_db(_q(all_=[]))
        user = _user()
        result = list_my_applications(status_filter=None, db=db, current_user=user)
        assert result.total == 0
        assert result.applications == []

    def test_200_with_status_filter_queries_filter(self):
        db = _seq_db(_q(all_=[]))
        user = _user()
        result = list_my_applications(
            status_filter=ApplicationStatusEnum.PENDING,
            db=db,
            current_user=user,
        )
        assert result.total == 0

    def test_200_with_applications_calls_from_orm(self):
        app_obj = MagicMock()
        app_obj.position = MagicMock()
        app_obj.position.specialization_type = "LFA"
        app_obj.position.age_group = "PRE"
        app_obj.position.time_period_start = "M01"
        app_obj.position.time_period_end = "M06"
        db = _seq_db(_q(all_=[app_obj]))
        user = _user()
        mock_resp = MagicMock()
        mock_list = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp, \
             patch(f"{_BASE}.ApplicationListResponse") as MockList:
            MockResp.from_orm.return_value = mock_resp
            MockList.return_value = mock_list
            result = list_my_applications(status_filter=None, db=db, current_user=user)
        MockResp.from_orm.assert_called_once_with(app_obj)
        assert result is mock_list


# ===========================================================================
# TestListApplicationsForPosition
# ===========================================================================

class TestListApplicationsForPosition:
    def test_404_position_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(Exception) as exc:
            list_applications_for_position(42, status_filter=None, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_position_poster(self):
        pos = _position(posted_by=99)
        db = _seq_db(_q(first=pos))
        with pytest.raises(Exception) as exc:
            list_applications_for_position(1, status_filter=None, db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 403
        assert "own positions" in exc.value.detail.lower()

    def test_200_empty_list_as_poster(self):
        pos = _position(posted_by=42)
        db = _seq_db(_q(first=pos), _q(all_=[]))
        result = list_applications_for_position(1, status_filter=None, db=db, current_user=_user(uid=42))
        assert result.total == 0

    def test_200_with_status_filter(self):
        pos = _position(posted_by=42)
        db = _seq_db(_q(first=pos), _q(all_=[]))
        result = list_applications_for_position(
            1,
            status_filter=ApplicationStatusEnum.PENDING,
            db=db,
            current_user=_user(uid=42),
        )
        assert result.total == 0

    def test_200_with_applications_calls_from_orm(self):
        pos = _position(posted_by=42)
        app_obj = _app_mock()
        db = _seq_db(_q(first=pos), _q(all_=[app_obj]))
        mock_resp = MagicMock()
        mock_list = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp, \
             patch(f"{_BASE}.ApplicationListResponse") as MockList:
            MockResp.from_orm.return_value = mock_resp
            MockList.return_value = mock_list
            result = list_applications_for_position(
                1, status_filter=None, db=db, current_user=_user(uid=42)
            )
        MockResp.from_orm.assert_called_once_with(app_obj)
        assert result is mock_list


# ===========================================================================
# TestReviewApplication
# ===========================================================================

class TestReviewApplication:
    def test_404_application_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(Exception) as exc:
            review_application(99, _update_data(), db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_not_position_poster(self):
        app = _app_mock(position_posted_by=99)
        db = _seq_db(_q(first=app))
        with pytest.raises(Exception) as exc:
            review_application(1, _update_data(), db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 403

    def test_400_application_already_reviewed(self):
        app = _app_mock(position_posted_by=42, status=ApplicationStatus.ACCEPTED)
        db = _seq_db(_q(first=app))
        with pytest.raises(Exception) as exc:
            review_application(1, _update_data(), db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 400
        assert "already been" in exc.value.detail.lower()

    def test_200_accept_application(self):
        app = _app_mock(position_posted_by=42)
        db = _seq_db(_q(first=app))
        mock_resp = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp:
            MockResp.from_orm.return_value = mock_resp
            result = review_application(
                1, _update_data(ApplicationStatusEnum.ACCEPTED), db=db, current_user=_user(uid=42)
            )
        assert db.commit.called
        assert result is mock_resp

    def test_200_decline_application(self):
        app = _app_mock(position_posted_by=42)
        db = _seq_db(_q(first=app))
        mock_resp = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp:
            MockResp.from_orm.return_value = mock_resp
            result = review_application(
                1, _update_data(ApplicationStatusEnum.DECLINED), db=db, current_user=_user(uid=42)
            )
        assert db.commit.called
        assert result is mock_resp


# ===========================================================================
# TestGetApplication
# ===========================================================================

class TestGetApplication:
    def test_404_application_not_found(self):
        db = _seq_db(_q(first=None))
        with pytest.raises(Exception) as exc:
            get_application(99, db=db, current_user=_user())
        assert exc.value.status_code == 404

    def test_403_no_access_as_stranger(self):
        # uid=42 is neither applicant (applicant_id=10) nor poster (posted_by=99)
        app = _app_mock(applicant_id=10, position_posted_by=99)
        db = _seq_db(_q(first=app))
        with pytest.raises(Exception) as exc:
            get_application(1, db=db, current_user=_user(uid=42))
        assert exc.value.status_code == 403

    def test_200_as_applicant(self):
        app = _app_mock(applicant_id=42, position_posted_by=99)
        db = _seq_db(_q(first=app))
        mock_resp = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp:
            MockResp.from_orm.return_value = mock_resp
            result = get_application(1, db=db, current_user=_user(uid=42))
        assert result is mock_resp

    def test_200_as_master_poster(self):
        # uid=42 is NOT applicant but IS poster
        app = _app_mock(applicant_id=10, position_posted_by=42)
        db = _seq_db(_q(first=app))
        mock_resp = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp:
            MockResp.from_orm.return_value = mock_resp
            result = get_application(1, db=db, current_user=_user(uid=42))
        assert result is mock_resp

    def test_200_no_position_on_application(self):
        # application.position is None → is_master = False; access only via applicant_id
        app = _app_mock(applicant_id=42)
        app.position = None
        db = _seq_db(_q(first=app))
        mock_resp = MagicMock()
        with patch(f"{_BASE}.ApplicationResponse") as MockResp:
            MockResp.from_orm.return_value = mock_resp
            result = get_application(1, db=db, current_user=_user(uid=42))
        assert result is mock_resp
