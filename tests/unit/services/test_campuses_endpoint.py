"""
Unit tests for app/api/api_v1/endpoints/campuses.py
Covers: get_campuses_by_location, get_all_campuses, get_campus,
        create_campus, update_campus, delete_campus, toggle_campus_status
"""
import pytest
from unittest.mock import MagicMock, patch

from app.api.api_v1.endpoints.campuses import (
    get_campuses_by_location, get_all_campuses, get_campus,
    create_campus, update_campus, delete_campus, toggle_campus_status
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.campuses"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(first_val=None, all_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
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


def _location(lid=1, city="Budapest"):
    loc = MagicMock()
    loc.id = lid
    loc.city = city
    loc.name = "Budapest Campus"
    return loc


def _campus(cid=10, name="Main Campus", is_active=True):
    c = MagicMock()
    c.id = cid
    c.name = name
    c.is_active = is_active
    c.location_id = 1
    return c


def _campus_data(name="New Campus"):
    d = MagicMock()
    d.name = name
    d.venue = "Sports Hall"
    d.address = "Andrássy út 1"
    d.notes = None
    d.is_active = True
    return d


def _campus_update(name=None):
    d = MagicMock()
    d.name = name
    d.dict.return_value = {"name": name} if name else {}
    return d


# ---------------------------------------------------------------------------
# get_campuses_by_location
# ---------------------------------------------------------------------------

class TestGetCampusesByLocation:
    def _call(self, location_id=1, include_inactive=False, db=None, current_user=None):
        return get_campuses_by_location(
            location_id=location_id,
            include_inactive=include_inactive,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_location_not_found_404(self):
        """GCBL-01: location not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_returns_active_campuses_only(self):
        """GCBL-02: include_inactive=False → active filter applied."""
        loc = _location()
        campuses = [_campus(cid=1), _campus(cid=2)]
        # n0: location, n1: campuses
        call_n = [0]
        db = MagicMock()
        def side(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = loc
            else:
                q.all.return_value = campuses
            return q
        db.query.side_effect = side
        result = self._call(db=db, include_inactive=False)
        assert len(result) == 2

    def test_include_inactive(self):
        """GCBL-03: include_inactive=True → no is_active filter."""
        loc = _location()
        campuses = [_campus(cid=1), _campus(cid=2, is_active=False)]
        call_n = [0]
        db = MagicMock()
        def side(*args):
            n = call_n[0]; call_n[0] += 1
            q = _q()
            if n == 0:
                q.first.return_value = loc
            else:
                q.all.return_value = campuses
            return q
        db.query.side_effect = side
        result = self._call(db=db, include_inactive=True)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_all_campuses
# ---------------------------------------------------------------------------

class TestGetAllCampuses:
    def _call(self, include_inactive=False, db=None, current_user=None):
        return get_all_campuses(
            include_inactive=include_inactive,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_active_only(self):
        """GAC-01: include_inactive=False → filter applied."""
        campuses = [_campus(cid=1)]
        q = _q(all_val=campuses)
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        q.filter.assert_called()

    def test_include_inactive(self):
        """GAC-02: include_inactive=True → no filter."""
        campuses = [_campus(cid=1), _campus(cid=2, is_active=False)]
        q = _q(all_val=campuses)
        db = MagicMock()
        db.query.return_value = q
        result = self._call(include_inactive=True, db=db)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_campus
# ---------------------------------------------------------------------------

class TestGetCampus:
    def _call(self, campus_id=10, db=None, current_user=None):
        return get_campus(
            campus_id=campus_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_not_found_404(self):
        """GC-01: campus not found → 404."""
        from fastapi import HTTPException
        q = _q(first_val=None)
        db = MagicMock()
        db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_found(self):
        """GC-02: campus found → returned."""
        campus = _campus()
        q = _q(first_val=campus)
        db = MagicMock()
        db.query.return_value = q
        result = self._call(db=db)
        assert result is campus


# ---------------------------------------------------------------------------
# create_campus
# ---------------------------------------------------------------------------

class TestCreateCampus:
    def _call(self, location_id=1, campus_data=None, db=None, current_user=None):
        return create_campus(
            location_id=location_id,
            campus_data=campus_data or _campus_data(),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_location_not_found_404(self):
        """CC-01: location not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_duplicate_name_400(self):
        """CC-02: campus name already exists → 400."""
        from fastapi import HTTPException
        loc = _location()
        existing = _campus(name="New Campus")
        db = _seq_db(loc, existing)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_success_creates_campus(self):
        """CC-03: unique name → campus created."""
        loc = _location()
        db = _seq_db(loc, None)
        mock_campus = _campus()
        with patch(f"{_BASE}.Campus", return_value=mock_campus):
            result = self._call(db=db)
        db.add.assert_called_once_with(mock_campus)
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# update_campus
# ---------------------------------------------------------------------------

class TestUpdateCampus:
    def _call(self, campus_id=10, campus_data=None, db=None, current_user=None):
        return update_campus(
            campus_id=campus_id,
            campus_data=campus_data or _campus_update(),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_not_found_404(self):
        """UC-01: campus not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_name_conflict_400(self):
        """UC-02: new name already taken → 400."""
        from fastapi import HTTPException
        campus = _campus(name="Old Name")
        existing = _campus(cid=20, name="New Name")
        db = _seq_db(campus, existing)
        data = _campus_update(name="New Name")
        with pytest.raises(HTTPException) as exc:
            self._call(campus_data=data, db=db)
        assert exc.value.status_code == 400

    def test_same_name_no_conflict_check(self):
        """UC-03: name unchanged → no duplicate check."""
        campus = _campus(name="Same Name")
        db = _seq_db(campus)
        data = _campus_update(name="Same Name")
        data.dict.return_value = {}
        result = self._call(campus_data=data, db=db)
        db.commit.assert_called_once()

    def test_no_name_update(self):
        """UC-04: name=None → no conflict check, updates other fields."""
        campus = _campus()
        db = _seq_db(campus)
        data = _campus_update(name=None)
        data.dict.return_value = {"venue": "New Venue"}
        result = self._call(campus_data=data, db=db)
        assert campus.venue == "New Venue"
        db.commit.assert_called_once()

    def test_name_conflict_none_no_error(self):
        """UC-05: new name, no existing campus → success."""
        campus = _campus(name="Old Name")
        db = _seq_db(campus, None)  # no duplicate
        data = _campus_update(name="Brand New")
        data.dict.return_value = {"name": "Brand New"}
        result = self._call(campus_data=data, db=db)
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# delete_campus
# ---------------------------------------------------------------------------

class TestDeleteCampus:
    def _call(self, campus_id=10, db=None, current_user=None):
        return delete_campus(
            campus_id=campus_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_not_found_404(self):
        """DC-01: campus not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_soft_delete(self):
        """DC-02: soft delete → is_active=False, committed."""
        campus = _campus(is_active=True)
        db = _seq_db(campus)
        self._call(db=db)
        assert campus.is_active is False
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# toggle_campus_status
# ---------------------------------------------------------------------------

class TestToggleCampusStatus:
    def _call(self, campus_id=10, is_active=True, db=None, current_user=None):
        return toggle_campus_status(
            campus_id=campus_id,
            is_active=is_active,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_not_found_404(self):
        """TCS-01: campus not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_activate(self):
        """TCS-02: is_active=True → campus activated."""
        campus = _campus(is_active=False)
        db = _seq_db(campus)
        self._call(is_active=True, db=db)
        assert campus.is_active is True
        db.commit.assert_called_once()

    def test_deactivate(self):
        """TCS-03: is_active=False → campus deactivated."""
        campus = _campus(is_active=True)
        db = _seq_db(campus)
        self._call(is_active=False, db=db)
        assert campus.is_active is False
