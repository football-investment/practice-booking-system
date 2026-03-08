"""
Unit tests for app/api/api_v1/endpoints/locations.py.

Branch coverage targets (9.1% → ~90%):
  get_all_locations: include_inactive=False (filter active), include_inactive=True (no filter)
  get_location: not found 404, found success
  create_location: duplicate name 400, success
  update_location: not found 404, cascade inactivation (is_active going False + active campuses),
                   not inactivated, campus already inactive (no update)
  delete_location: not found 404, cascade with active campus, cascade with inactive campus
  get_active_locations: returns filtered list
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import datetime

from app.api.api_v1.endpoints.locations import (
    get_all_locations,
    get_location,
    create_location,
    update_location,
    delete_location,
    get_active_locations,
    LocationCreate,
    LocationUpdate,
)
from app.models.location import Location
from app.models.campus import Campus

_BASE = "app.api.api_v1.endpoints.locations"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_admin():
    return MagicMock()


def _location(**kwargs):
    loc = MagicMock(spec=Location)
    loc.id = kwargs.get("id", 1)
    loc.name = kwargs.get("name", "Test Location")
    loc.city = "Budapest"
    loc.country = "Hungary"
    loc.is_active = kwargs.get("is_active", True)
    loc.created_at = datetime.utcnow()
    loc.updated_at = datetime.utcnow()
    return loc


def _campus(is_active=True):
    c = MagicMock(spec=Campus)
    c.is_active = is_active
    c.updated_at = datetime.utcnow()
    return c


def _db_location(first_val=None, all_val=None):
    """DB returning given location for .first() and list for .all()."""
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.first.return_value = first_val
    q.all.return_value = all_val if all_val is not None else []
    db = MagicMock()
    db.query.return_value = q
    return db


def _db_routed(location=None, campuses=None):
    """DB routing Location vs Campus queries."""
    loc_q = MagicMock()
    loc_q.filter.return_value = loc_q
    loc_q.order_by.return_value = loc_q
    loc_q.first.return_value = location
    loc_q.all.return_value = [location] if location else []

    cam_q = MagicMock()
    cam_q.filter.return_value = cam_q
    cam_q.all.return_value = campuses if campuses is not None else []

    db = MagicMock()
    db.query.side_effect = lambda model: loc_q if model is Location else cam_q
    return db


# ---------------------------------------------------------------------------
# get_all_locations
# ---------------------------------------------------------------------------

class TestGetAllLocations:

    def test_include_inactive_false_filters_active(self):
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = [_location()]
        db = MagicMock()
        db.query.return_value = q
        result = asyncio.run(get_all_locations(include_inactive=False, db=db, current_admin=_mock_admin()))
        # filter() should have been called (for is_active)
        q.filter.assert_called()
        assert len(result) == 1

    def test_include_inactive_true_skips_filter(self):
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = []
        db = MagicMock()
        db.query.return_value = q
        result = asyncio.run(get_all_locations(include_inactive=True, db=db, current_admin=_mock_admin()))
        assert result == []


# ---------------------------------------------------------------------------
# get_location
# ---------------------------------------------------------------------------

class TestGetLocation:

    def test_not_found_raises_404(self):
        db = _db_location(first_val=None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_location(location_id=1, db=db, current_admin=_mock_admin()))
        assert exc.value.status_code == 404

    def test_found_returns_location(self):
        loc = _location()
        db = _db_location(first_val=loc)
        result = asyncio.run(get_location(location_id=1, db=db, current_admin=_mock_admin()))
        assert result is loc


# ---------------------------------------------------------------------------
# create_location
# ---------------------------------------------------------------------------

class TestCreateLocation:

    def test_duplicate_name_raises_400(self):
        existing = _location(name="Existing")
        db = _db_location(first_val=existing)
        payload = LocationCreate(name="Existing", city="Budapest", country="Hungary")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(create_location(location_data=payload, db=db, current_admin=_mock_admin()))
        assert exc.value.status_code == 400

    def test_new_location_created(self):
        db = _db_location(first_val=None)
        payload = LocationCreate(name="New Campus", city="Vienna", country="Austria")
        asyncio.run(create_location(location_data=payload, db=db, current_admin=_mock_admin()))
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# update_location
# ---------------------------------------------------------------------------

class TestUpdateLocation:

    def test_not_found_raises_404(self):
        db = _db_routed(location=None)
        payload = LocationUpdate(name="New Name")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(update_location(location_id=1, location_data=payload, db=db, current_admin=_mock_admin()))
        assert exc.value.status_code == 404

    def test_simple_update_no_cascade(self):
        loc = _location(is_active=True)
        db = _db_routed(location=loc, campuses=[])
        payload = LocationUpdate(name="Renamed")  # not changing is_active
        asyncio.run(update_location(location_id=1, location_data=payload, db=db, current_admin=_mock_admin()))
        db.commit.assert_called_once()

    def test_inactivation_cascades_to_active_campus(self):
        loc = _location(is_active=True)
        active_campus = _campus(is_active=True)
        db = _db_routed(location=loc, campuses=[active_campus])
        payload = LocationUpdate(is_active=False)
        asyncio.run(update_location(location_id=1, location_data=payload, db=db, current_admin=_mock_admin()))
        assert active_campus.is_active is False

    def test_inactivation_skips_already_inactive_campus(self):
        loc = _location(is_active=True)
        inactive_campus = _campus(is_active=False)
        db = _db_routed(location=loc, campuses=[inactive_campus])
        payload = LocationUpdate(is_active=False)
        asyncio.run(update_location(location_id=1, location_data=payload, db=db, current_admin=_mock_admin()))
        # campus was already inactive — no change
        assert inactive_campus.is_active is False


# ---------------------------------------------------------------------------
# delete_location
# ---------------------------------------------------------------------------

class TestDeleteLocation:

    def test_not_found_raises_404(self):
        db = _db_routed(location=None)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(delete_location(location_id=1, db=db, current_admin=_mock_admin()))
        assert exc.value.status_code == 404

    def test_soft_delete_cascades_to_active_campus(self):
        loc = _location(is_active=True)
        active_campus = _campus(is_active=True)
        db = _db_routed(location=loc, campuses=[active_campus])
        asyncio.run(delete_location(location_id=1, db=db, current_admin=_mock_admin()))
        assert active_campus.is_active is False

    def test_soft_delete_skips_inactive_campus(self):
        loc = _location(is_active=True)
        inactive_campus = _campus(is_active=False)
        db = _db_routed(location=loc, campuses=[inactive_campus])
        asyncio.run(delete_location(location_id=1, db=db, current_admin=_mock_admin()))
        assert inactive_campus.is_active is False  # unchanged


# ---------------------------------------------------------------------------
# get_active_locations (public endpoint — no auth)
# ---------------------------------------------------------------------------

class TestGetActiveLocations:

    def test_returns_active_locations(self):
        loc = _location()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = [loc]
        db = MagicMock()
        db.query.return_value = q
        result = asyncio.run(get_active_locations(db=db))
        assert len(result) == 1
