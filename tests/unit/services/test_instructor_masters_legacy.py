"""
Unit tests for app/api/api_v1/endpoints/instructor_management/masters/legacy.py
Covers: create_master_instructor_legacy, get_master_for_location, list_all_masters,
        update_master_instructor, terminate_master_instructor
"""
import pytest
from unittest.mock import MagicMock, patch

from app.api.api_v1.endpoints.instructor_management.masters.legacy import (
    create_master_instructor_legacy,
    get_master_for_location,
    list_all_masters,
    update_master_instructor,
    terminate_master_instructor,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.instructor_management.masters.legacy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(first_val=None, all_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
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


def _location(lid=1, name="Budapest"):
    loc = MagicMock()
    loc.id = lid
    loc.name = name
    return loc


def _instructor_user(uid=7):
    u = MagicMock()
    u.id = uid
    u.name = "Test Instructor"
    u.email = "instructor@example.com"
    return u


def _master(mid=10, location_id=1, instructor_id=7, is_active=True):
    m = MagicMock()
    m.id = mid
    m.location_id = location_id
    m.instructor_id = instructor_id
    m.is_active = is_active
    m.location = MagicMock()
    m.location.name = "Budapest"
    m.instructor = MagicMock()
    m.instructor.name = "Test Instructor"
    m.instructor.email = "instructor@example.com"
    return m


def _hire_data(location_id=1, instructor_id=7):
    d = MagicMock()
    d.location_id = location_id
    d.instructor_id = instructor_id
    d.contract_start = MagicMock()
    d.contract_end = MagicMock()
    return d


# ---------------------------------------------------------------------------
# create_master_instructor_legacy
# ---------------------------------------------------------------------------

class TestCreateMasterInstructorLegacy:
    def _call(self, data=None, db=None, current_user=None):
        return create_master_instructor_legacy(
            data=data or _hire_data(),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_location_not_found_404(self):
        """CML-01: location not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)  # location not found
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_instructor_not_found_404(self):
        """CML-02: instructor not found → 404."""
        from fastapi import HTTPException
        loc = _location()
        db = _seq_db(loc, None)  # location ok, instructor not found
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_existing_active_master_400(self):
        """CML-03: location already has active master → 400."""
        from fastapi import HTTPException
        loc = _location()
        instr = _instructor_user()
        existing = _master()
        db = _seq_db(loc, instr, existing)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_success_creates_master(self):
        """CML-04: success → master created, semester transition triggered."""
        loc = _location()
        instr = _instructor_user()
        mock_master = _master()
        db = _seq_db(loc, instr, None)  # no existing

        with patch(f"{_BASE}.LocationMasterInstructor", return_value=mock_master):
            with patch(f"{_BASE}.transition_to_instructor_assigned") as mock_trans:
                with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
                    MockResp.from_orm.return_value = MagicMock()
                    self._call(db=db)
        db.add.assert_called_once_with(mock_master)
        mock_trans.assert_called_once()


# ---------------------------------------------------------------------------
# get_master_for_location
# ---------------------------------------------------------------------------

class TestGetMasterForLocation:
    def _call(self, location_id=1, db=None, current_user=None):
        return get_master_for_location(
            location_id=location_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_no_active_master_404(self):
        """GMFL-01: no active master → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_active_master_found(self):
        """GMFL-02: master found → response built."""
        master = _master()
        db = _seq_db(master)
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            result = self._call(db=db)
        MockResp.from_orm.assert_called_once_with(master)


# ---------------------------------------------------------------------------
# list_all_masters
# ---------------------------------------------------------------------------

class TestListAllMasters:
    def _call(self, include_inactive=False, db=None, current_user=None):
        return list_all_masters(
            include_inactive=include_inactive,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_active_only_default(self):
        """LAM-01: include_inactive=False → filter applied."""
        masters = [_master(mid=1), _master(mid=2)]
        q = _q(all_val=masters)
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            with patch(f"{_BASE}.MasterInstructorListResponse") as MockList:
                MockList.return_value = MagicMock()
                result = self._call(db=db)
        q.filter.assert_called_once()  # is_active filter

    def test_include_inactive(self):
        """LAM-02: include_inactive=True → no is_active filter."""
        masters = [_master(mid=1), _master(mid=2, is_active=False)]
        q = _q(all_val=masters)
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            with patch(f"{_BASE}.MasterInstructorListResponse") as MockList:
                MockList.return_value = MagicMock()
                self._call(include_inactive=True, db=db)
        q.filter.assert_not_called()

    def test_empty_list(self):
        """LAM-03: no masters → empty list."""
        q = _q(all_val=[])
        db = MagicMock()
        db.query.return_value = q
        with patch(f"{_BASE}.MasterInstructorListResponse") as MockList:
            MockList.return_value = MagicMock()
            self._call(db=db)
        MockList.assert_called_once_with(total=0, masters=[])


# ---------------------------------------------------------------------------
# update_master_instructor
# ---------------------------------------------------------------------------

class TestUpdateMasterInstructor:
    def _update(self, contract_end=None, is_active=None):
        d = MagicMock()
        d.contract_end = contract_end
        d.is_active = is_active
        return d

    def _call(self, master_id=10, data=None, db=None, current_user=None):
        return update_master_instructor(
            master_id=master_id,
            data=data or self._update(),
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_master_not_found_404(self):
        """UMI-01: master not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_deactivate_active_master(self):
        """UMI-02: is_active=False on active master → terminated."""
        master = _master(is_active=True)
        db = _seq_db(master)
        data = self._update(is_active=False)
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            self._call(data=data, db=db)
        assert master.is_active is False

    def test_reactivate_with_conflict_400(self):
        """UMI-03: reactivate master but another already active → 400."""
        from fastapi import HTTPException
        master = _master(is_active=False)
        other_active = _master(mid=20, is_active=True)
        db = _seq_db(master, other_active)
        data = self._update(is_active=True)
        with pytest.raises(HTTPException) as exc:
            self._call(data=data, db=db)
        assert exc.value.status_code == 400

    def test_reactivate_no_conflict(self):
        """UMI-04: reactivate with no other active → success."""
        master = _master(is_active=False)
        db = _seq_db(master, None)  # no other active
        data = self._update(is_active=True)
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            self._call(data=data, db=db)
        assert master.is_active is True

    def test_update_contract_end(self):
        """UMI-05: contract_end updated → committed."""
        master = _master()
        db = _seq_db(master)
        new_end = MagicMock()
        data = self._update(contract_end=new_end, is_active=None)
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            self._call(data=data, db=db)
        assert master.contract_end == new_end
        db.commit.assert_called_once()

    def test_already_active_stays_active(self):
        """UMI-06: is_active=True on already active → no conflict query needed."""
        master = _master(is_active=True)
        db = _seq_db(master)
        data = self._update(is_active=True)
        with patch(f"{_BASE}.MasterInstructorResponse") as MockResp:
            MockResp.from_orm.return_value = MagicMock()
            self._call(data=data, db=db)
        # master stays active, no change needed


# ---------------------------------------------------------------------------
# terminate_master_instructor
# ---------------------------------------------------------------------------

class TestTerminateMasterInstructor:
    def _call(self, master_id=10, db=None, current_user=None):
        return terminate_master_instructor(
            master_id=master_id,
            db=db or MagicMock(),
            current_user=current_user or _admin(),
        )

    def test_master_not_found_404(self):
        """TMI-01: master not found → 404."""
        from fastapi import HTTPException
        db = _seq_db(None)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 404

    def test_already_terminated_400(self):
        """TMI-02: master already inactive → 400."""
        from fastapi import HTTPException
        master = _master(is_active=False)
        db = _seq_db(master)
        with pytest.raises(HTTPException) as exc:
            self._call(db=db)
        assert exc.value.status_code == 400

    def test_success_terminates(self):
        """TMI-03: active master → terminated (is_active=False)."""
        master = _master(is_active=True)
        db = _seq_db(master)
        result = self._call(db=db)
        assert master.is_active is False
        db.commit.assert_called_once()
