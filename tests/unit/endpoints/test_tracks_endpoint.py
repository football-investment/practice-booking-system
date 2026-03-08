"""
Unit tests for app/api/api_v1/endpoints/tracks.py

Branch coverage targets:
  enroll_in_track():
    - TrackEnrollmentError raised → 400
    - success path
  start_track():
    - track_progress not found → 404
    - ValueError raised → 400
    - success path
  start_module():
    - track_progress not found → 404
    - success path
  complete_module():
    - track_progress not found → 404
    - ValueError raised → 400
    - success path
  get_track_analytics():
    - role not in [instructor, admin] → 403
    - success path (instructor role)
  get_track_progress_detail():
    - track_progress not found → 404
    - success path (empty module_progresses)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.tracks import (
    enroll_in_track,
    start_track,
    start_module,
    complete_module,
    get_track_analytics,
    get_track_progress_detail,
)
from app.models.user_progress import TrackProgressStatus
from app.api.api_v1.endpoints.tracks import TrackEnrollmentError

_BASE = "app.api.api_v1.endpoints.tracks"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(role_value="student"):
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = role_value
    return u


def _db_chain(first_result=None):
    """DB mock where query().filter().filter().first() returns first_result."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.first.return_value = first_result
    db.query.return_value = q
    return db


def _progress_mock(status_value="active"):
    p = MagicMock()
    p.status = MagicMock()
    p.status.value = status_value
    p.track = MagicMock()
    p.track.id = "track-uuid"
    p.track.name = "Test Track"
    p.track.code = "TRK"
    p.track.description = "A test track"
    p.module_progresses = []  # empty = no iteration
    p.completion_percentage = 50.0
    p.enrollment_date = None
    p.started_at = None
    p.completed_at = None
    p.certificate_id = None
    return p


# ============================================================================
# enroll_in_track()
# ============================================================================

class TestEnrollInTrack:

    def test_success_returns_enrollment_response(self):
        import uuid as _uuid
        mock_progress = MagicMock()
        mock_progress.id = str(_uuid.uuid4())

        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.enroll_user_in_track.return_value = mock_progress
            req = MagicMock()
            req.track_id = "track-1"
            req.semester_id = 1
            result = enroll_in_track(req, current_user=_user(), db=MagicMock())

        assert result.success is True
        assert "enrolled" in result.message.lower()

    def test_enrollment_error_raises_400(self):
        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.enroll_user_in_track.side_effect = TrackEnrollmentError("max parallel tracks reached")
            req = MagicMock()
            req.track_id = "track-1"
            req.semester_id = 1
            with pytest.raises(HTTPException) as exc:
                enroll_in_track(req, current_user=_user(), db=MagicMock())

        assert exc.value.status_code == 400
        assert "max parallel" in exc.value.detail


# ============================================================================
# start_track()
# ============================================================================

class TestStartTrack:

    def test_not_found_raises_404(self):
        db = _db_chain(first_result=None)
        with pytest.raises(HTTPException) as exc:
            start_track("missing-id", current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_value_error_raises_400(self):
        p = _progress_mock()
        db = _db_chain(first_result=p)

        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.start_track.side_effect = ValueError("already active")
            with pytest.raises(HTTPException) as exc:
                start_track("progress-id", current_user=_user(), db=db)

        assert exc.value.status_code == 400

    def test_success_returns_dict_with_status(self):
        p = _progress_mock(status_value="active")
        db = _db_chain(first_result=p)
        updated = MagicMock()
        updated.status = MagicMock()
        updated.status.value = "active"

        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.start_track.return_value = updated
            result = start_track("progress-id", current_user=_user(), db=db)

        assert result["status"] == "active"


# ============================================================================
# start_module()
# ============================================================================

class TestStartModule:

    def test_not_found_raises_404(self):
        db = _db_chain(first_result=None)
        with pytest.raises(HTTPException) as exc:
            start_module("missing-id", "mod-id", current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_success_returns_module_info(self):
        p = _progress_mock()
        db = _db_chain(first_result=p)
        mod_progress = MagicMock()
        mod_progress.id = "mp-uuid"
        mod_progress.status = MagicMock()
        mod_progress.status.value = "in_progress"

        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.start_module.return_value = mod_progress
            result = start_module("progress-id", "mod-id", current_user=_user(), db=db)

        assert result["status"] == "in_progress"


# ============================================================================
# complete_module()
# ============================================================================

class TestCompleteModule:

    def test_not_found_raises_404(self):
        db = _db_chain(first_result=None)
        with pytest.raises(HTTPException) as exc:
            complete_module("missing", "mod", grade=None, current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_value_error_raises_400(self):
        p = _progress_mock()
        db = _db_chain(first_result=p)
        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.complete_module.side_effect = ValueError("not started")
            with pytest.raises(HTTPException) as exc:
                complete_module("prog-id", "mod-id", grade=None, current_user=_user(), db=db)
        assert exc.value.status_code == 400

    def test_success_returns_module_info(self):
        p = _progress_mock()
        db = _db_chain(first_result=p)
        mod_progress = MagicMock()
        mod_progress.id = "mp-uuid"
        mod_progress.status = MagicMock()
        mod_progress.status.value = "completed"
        mod_progress.grade = 88.0

        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.complete_module.return_value = mod_progress
            result = complete_module("prog-id", "mod-id", grade=88.0, current_user=_user(), db=db)

        assert result["grade"] == 88.0


# ============================================================================
# get_track_analytics()
# ============================================================================

class TestGetTrackAnalytics:

    def test_student_role_raises_403(self):
        with pytest.raises(HTTPException) as exc:
            get_track_analytics("track-id", current_user=_user(role_value="student"), db=MagicMock())
        assert exc.value.status_code == 403

    def test_instructor_role_returns_analytics(self):
        analytics = MagicMock()
        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.get_track_analytics.return_value = analytics
            result = get_track_analytics("track-id", current_user=_user(role_value="instructor"), db=MagicMock())
        assert result is analytics

    def test_admin_role_returns_analytics(self):
        analytics = MagicMock()
        with patch(f"{_BASE}.TrackService") as MockSvc:
            MockSvc.return_value.get_track_analytics.return_value = analytics
            result = get_track_analytics("track-id", current_user=_user(role_value="admin"), db=MagicMock())
        assert result is analytics


# ============================================================================
# get_track_progress_detail()
# ============================================================================

class TestGetTrackProgressDetail:

    def test_not_found_raises_404(self):
        db = _db_chain(first_result=None)
        with pytest.raises(HTTPException) as exc:
            get_track_progress_detail("missing-id", current_user=_user(), db=db)
        assert exc.value.status_code == 404

    def test_success_with_empty_module_progresses(self):
        p = _progress_mock()
        p.id = "tp-uuid"
        p.certificate_id = None
        db = _db_chain(first_result=p)

        result = get_track_progress_detail("tp-uuid", current_user=_user(), db=db)

        assert result["track_progress_id"] == "tp-uuid"
        assert result["module_progresses"] == []

    def test_certificate_id_none_gives_null_in_response(self):
        p = _progress_mock()
        p.id = "tp-uuid"
        p.certificate_id = None
        db = _db_chain(first_result=p)

        result = get_track_progress_detail("tp-uuid", current_user=_user(), db=db)
        assert result["certificate_id"] is None
