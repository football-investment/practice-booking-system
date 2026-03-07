"""
Unit tests for app/api/api_v1/endpoints/instructor_management/masters/applications.py
Covers: hire_from_application — all 10 branches:
  404 (application not found), 400 (not PENDING), 400 (not master position),
  400 (existing master), success with no other applications,
  success with other applications declining loop.
All endpoints are sync.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.instructor_management.masters.applications import (
    hire_from_application,
)
from app.models.instructor_assignment import ApplicationStatus

_BASE = "app.api.api_v1.endpoints.instructor_management.masters.applications"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin(uid=42):
    u = MagicMock()
    u.id = uid
    return u


def _data(application_id=1, offer_deadline_days=7):
    d = MagicMock()
    d.application_id = application_id
    d.offer_deadline_days = offer_deadline_days
    d.contract_start = MagicMock()
    d.contract_end = MagicMock()
    return d


def _application(status=ApplicationStatus.PENDING, is_master=True):
    """Build a realistic application mock."""
    app = MagicMock()
    app.status = status
    app.applicant_id = 99
    position = MagicMock()
    position.is_master_position = is_master
    position.id = 10
    position.status = MagicMock()
    location = MagicMock()
    location.id = 5
    location.name = "Budapest"
    position.location = location
    app.position = position
    app.applicant = MagicMock()
    app.applicant.name = "Coach Bob"
    app.applicant.email = "bob@example.com"
    return app


def _make_db(app_result, existing_master_result=None, other_apps_result=None):
    """
    Sequential db.query mock:
    - query 0 (PositionApplication.first) → app_result
    - query 1 (LocationMasterInstructor.first) → existing_master_result
    - query 2 (PositionApplication.all) → other_apps_result
    """
    call_n = [0]

    def side_effect(model):
        idx = call_n[0]
        call_n[0] += 1
        q = MagicMock()
        q.filter.return_value = q
        if idx == 0:
            q.first.return_value = app_result
        elif idx == 1:
            q.first.return_value = existing_master_result
        else:
            q.all.return_value = other_apps_result or []
        return q

    db = MagicMock()
    db.query.side_effect = side_effect
    return db


# ---------------------------------------------------------------------------
# hire_from_application
# ---------------------------------------------------------------------------

class TestHireFromApplication:

    def test_hfa01_application_not_found_404(self):
        """HFA-01: application not in DB → 404."""
        db = _make_db(app_result=None)
        with pytest.raises(HTTPException) as exc:
            hire_from_application(data=_data(), db=db, current_user=_admin())
        assert exc.value.status_code == 404
        assert "not found" in exc.value.detail.lower()

    def test_hfa02_application_not_pending_400(self):
        """HFA-02: application already DECLINED → 400 (cannot hire)."""
        app = _application(status=ApplicationStatus.DECLINED)
        db = _make_db(app_result=app)
        with pytest.raises(HTTPException) as exc:
            hire_from_application(data=_data(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "cannot hire" in exc.value.detail.lower()

    def test_hfa03_not_master_position_400(self):
        """HFA-03: position.is_master_position=False → 400."""
        app = _application(status=ApplicationStatus.PENDING, is_master=False)
        db = _make_db(app_result=app)
        with pytest.raises(HTTPException) as exc:
            hire_from_application(data=_data(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "master position" in exc.value.detail.lower()

    def test_hfa04_existing_active_master_400(self):
        """HFA-04: location already has active master → 400."""
        app = _application(status=ApplicationStatus.PENDING, is_master=True)
        existing = MagicMock()
        db = _make_db(app_result=app, existing_master_result=existing)
        with pytest.raises(HTTPException) as exc:
            hire_from_application(data=_data(), db=db, current_user=_admin())
        assert exc.value.status_code == 400
        assert "already has an active master" in exc.value.detail

    def test_hfa05_success_no_other_applications(self):
        """HFA-05: success path, no other PENDING applications to decline."""
        app = _application(status=ApplicationStatus.PENDING, is_master=True)
        db = _make_db(
            app_result=app,
            existing_master_result=None,
            other_apps_result=[],
        )
        with patch(f"{_BASE}.LocationMasterInstructor") as MockLMI, \
             patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            mock_master = MagicMock()
            MockLMI.return_value = mock_master
            MockResp.return_value = MagicMock()
            result = hire_from_application(data=_data(), db=db, current_user=_admin())

        assert app.status == ApplicationStatus.ACCEPTED
        db.add.assert_called_once_with(mock_master)
        db.commit.assert_called_once()

    def test_hfa06_success_declines_other_pending_applications(self):
        """HFA-06: other PENDING applications auto-declined."""
        app = _application(status=ApplicationStatus.PENDING, is_master=True)
        other1 = MagicMock()
        other2 = MagicMock()
        db = _make_db(
            app_result=app,
            existing_master_result=None,
            other_apps_result=[other1, other2],
        )
        with patch(f"{_BASE}.LocationMasterInstructor") as MockLMI, \
             patch(f"{_BASE}.MasterOfferResponse") as MockResp:
            MockLMI.return_value = MagicMock()
            MockResp.return_value = MagicMock()
            hire_from_application(data=_data(), db=db, current_user=_admin())

        assert other1.status == ApplicationStatus.DECLINED
        assert other2.status == ApplicationStatus.DECLINED
        db.commit.assert_called_once()
