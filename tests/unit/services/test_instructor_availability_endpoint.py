"""
Unit tests for app/api/api_v1/endpoints/instructor_assignments/availability.py
Covers: create_availability_window, get_instructor_availability_windows,
        update_availability_window, delete_availability_window
"""
import pytest
from unittest.mock import MagicMock, patch

from app.api.api_v1.endpoints.instructor_assignments.availability import (
    create_availability_window,
    get_instructor_availability_windows,
    update_availability_window,
    delete_availability_window,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.instructor_assignments.availability"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(first_val=None, all_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.all.return_value = all_val if all_val is not None else []
    q.first.return_value = first_val
    return q


def _seq_db(*vals):
    call_n = [0]
    db = MagicMock()

    def side(*args):
        n = call_n[0]
        call_n[0] += 1
        v = vals[n] if n < len(vals) else None
        q = _q()
        if isinstance(v, list):
            q.all.return_value = v
            q.first.return_value = v[0] if v else None
        else:
            q.first.return_value = v
        return q

    db.query.side_effect = side
    return db


def _admin():
    u = MagicMock()
    u.id = 42
    u.role = UserRole.ADMIN
    return u


def _instructor(uid=42):
    u = MagicMock()
    u.id = uid
    u.role = UserRole.INSTRUCTOR
    return u


def _student():
    u = MagicMock()
    u.id = 99
    u.role = UserRole.STUDENT
    return u


def _avail_input(instructor_id=42, year=2026, time_period="Q1"):
    a = MagicMock()
    a.instructor_id = instructor_id
    a.year = year
    a.time_period = time_period
    a.model_dump.return_value = {
        "instructor_id": instructor_id,
        "year": year,
        "time_period": time_period,
    }
    return a


def _window(wid=10, instructor_id=42):
    w = MagicMock()
    w.id = wid
    w.instructor_id = instructor_id
    return w


# ---------------------------------------------------------------------------
# create_availability_window
# ---------------------------------------------------------------------------

class TestCreateAvailabilityWindow:
    def _call(self, availability=None, db=None, current_user=None):
        return create_availability_window(
            availability=availability or _avail_input(),
            db=db or MagicMock(),
            current_user=current_user or _instructor(),
        )

    def test_non_admin_other_instructor_403(self):
        """CAW-01: instructor trying to create for other → 403."""
        from fastapi import HTTPException
        avail = _avail_input(instructor_id=99)  # not their id
        current = _instructor(uid=42)
        with pytest.raises(HTTPException) as exc:
            self._call(availability=avail, current_user=current, db=MagicMock())
        assert exc.value.status_code == 403

    def test_instructor_not_found_404(self):
        """CAW-02: instructor user record missing → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)  # instructor not found
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_duplicate_window_409(self):
        """CAW-03: existing window → 409."""
        from fastapi import HTTPException
        instructor_obj = MagicMock()
        existing = _window()
        db = _seq_db(instructor_obj, existing)  # n0=instructor found, n1=duplicate found
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 409

    def test_admin_can_create_for_any(self):
        """CAW-04: admin creates for other instructor → no 403."""
        from fastapi import HTTPException
        instructor_obj = MagicMock()
        avail = _avail_input(instructor_id=7)
        db = _seq_db(instructor_obj, None)  # instructor found, no duplicate
        mock_window = _window()

        with patch(f"{_BASE}.InstructorAvailabilityWindow", return_value=mock_window):
            result = self._call(availability=avail, db=db, current_user=_admin())
        db.add.assert_called_once_with(mock_window)

    def test_success_creates_window(self):
        """CAW-05: success → window added and returned."""
        instructor_obj = MagicMock()
        mock_window = _window()
        db = _seq_db(instructor_obj, None)

        with patch(f"{_BASE}.InstructorAvailabilityWindow", return_value=mock_window):
            result = self._call(db=db)
        db.add.assert_called_once_with(mock_window)
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# get_instructor_availability_windows
# ---------------------------------------------------------------------------

class TestGetInstructorAvailabilityWindows:
    def _call(self, instructor_id=42, year=None, db=None, current_user=None):
        return get_instructor_availability_windows(
            instructor_id=instructor_id,
            year=year,
            db=db or MagicMock(),
            current_user=current_user or _instructor(uid=42),
        )

    def test_instructor_viewing_other_403(self):
        """GAW-01: instructor viewing other's windows → 403."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            self._call(instructor_id=99, current_user=_instructor(uid=42))
        assert exc.value.status_code == 403

    def test_admin_can_view_any(self):
        """GAW-02: admin can view any instructor."""
        q = _q(all_val=[_window()])
        db = MagicMock()
        db.query.return_value = q
        result = self._call(instructor_id=7, current_user=_admin(), db=db)
        assert isinstance(result, list)

    def test_with_year_filter(self):
        """GAW-03: year filter → additional filter applied."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        self._call(year=2026, db=db)
        assert q.filter.call_count >= 1

    def test_no_year_filter(self):
        """GAW-04: no year → only instructor_id filter."""
        q = _q(all_val=[_window(), _window()])
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert len(result) == 2

    def test_instructor_own_windows(self):
        """GAW-05: instructor viewing own → success."""
        windows = [_window(wid=1), _window(wid=2)]
        q = _q(all_val=windows)
        db = MagicMock()
        db.query.return_value = q
        result = self._call(instructor_id=42, current_user=_instructor(uid=42), db=db)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update_availability_window
# ---------------------------------------------------------------------------

class TestUpdateAvailabilityWindow:
    def _call(self, window_id=10, db=None, current_user=None, update_data=None):
        if update_data is None:
            update_data = MagicMock()
            update_data.model_dump.return_value = {"year": 2027}
        return update_availability_window(
            window_id=window_id,
            update_data=update_data,
            db=db or MagicMock(),
            current_user=current_user or _instructor(uid=42),
        )

    def test_window_not_found_404(self):
        """UAW-01: window not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_instructor_updating_other_window_403(self):
        """UAW-02: instructor updating other's window → 403."""
        from fastapi import HTTPException
        window = _window(instructor_id=99)
        db = _seq_db(window)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db, current_user=_instructor(uid=42))
        assert exc.value.status_code == 403

    def test_admin_can_update_any(self):
        """UAW-03: admin can update any window."""
        window = _window(instructor_id=99)
        db = _seq_db(window)
        update_data = MagicMock()
        update_data.model_dump.return_value = {"year": 2027}
        with patch(f"{_BASE}.datetime") as mock_dt:
            mock_dt.utcnow.return_value = MagicMock()
            self._call(db=db, current_user=_admin(), update_data=update_data)
        db.commit.assert_called_once()

    def test_instructor_own_window_success(self):
        """UAW-04: instructor updating own window → success."""
        window = _window(instructor_id=42)
        db = _seq_db(window)
        update_data = MagicMock()
        update_data.model_dump.return_value = {"year": 2027}
        with patch(f"{_BASE}.datetime") as mock_dt:
            mock_dt.utcnow.return_value = MagicMock()
            self._call(db=db, current_user=_instructor(uid=42), update_data=update_data)
        assert window.year == 2027
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# delete_availability_window
# ---------------------------------------------------------------------------

class TestDeleteAvailabilityWindow:
    def _call(self, window_id=10, db=None, current_user=None):
        return delete_availability_window(
            window_id=window_id,
            db=db or MagicMock(),
            current_user=current_user or _instructor(uid=42),
        )

    def test_window_not_found_404(self):
        """DAW-01: window not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_instructor_delete_other_403(self):
        """DAW-02: instructor deleting other's window → 403."""
        from fastapi import HTTPException
        window = _window(instructor_id=99)
        db = _seq_db(window)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db, current_user=_instructor(uid=42))
        assert exc.value.status_code == 403

    def test_admin_can_delete_any(self):
        """DAW-03: admin deletes any window → success."""
        window = _window(instructor_id=99)
        db = _seq_db(window)
        result = self._call(db=db, current_user=_admin())
        db.delete.assert_called_once_with(window)
        db.commit.assert_called_once()

    def test_instructor_own_window_deleted(self):
        """DAW-04: instructor deletes own window → success."""
        window = _window(instructor_id=42)
        db = _seq_db(window)
        result = self._call(db=db, current_user=_instructor(uid=42))
        db.delete.assert_called_once_with(window)
