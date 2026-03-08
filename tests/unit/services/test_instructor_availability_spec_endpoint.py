"""
Unit tests for app/api/api_v1/endpoints/instructor_availability.py
Covers: get_instructor_availability_matrix, create_instructor_availability,
        update_instructor_availability, bulk_upsert_instructor_availability,
        delete_instructor_availability, get_instructor_availabilities
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.api_v1.endpoints.instructor_availability import (
    get_instructor_availability_matrix,
    create_instructor_availability,
    update_instructor_availability,
    bulk_upsert_instructor_availability,
    delete_instructor_availability,
    get_instructor_availabilities,
)
from app.models.user import UserRole

_BASE = "app.api.api_v1.endpoints.instructor_availability"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q():
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.all.return_value = []
    q.first.return_value = None
    return q


def _seq_db(*vals):
    db = MagicMock()
    counter = [0]
    def _side(model):
        idx = counter[0]; counter[0] += 1
        return vals[idx] if idx < len(vals) else _q()
    db.query.side_effect = _side
    return db


def _user(uid=42, role=UserRole.INSTRUCTOR):
    u = MagicMock()
    u.id = uid
    u.role = role
    return u


def _admin():
    return _user(uid=42, role=UserRole.ADMIN)


def _avail(aid=1, instructor_id=42):
    a = MagicMock()
    a.id = aid
    a.instructor_id = instructor_id
    a.time_period_code = "Q1"
    a.specialization_type = "LFA_PLAYER_PRE"
    a.is_available = True
    a.notes = None
    return a


# ---------------------------------------------------------------------------
# get_instructor_availability_matrix
# ---------------------------------------------------------------------------

class TestGetInstructorAvailabilityMatrix:
    def test_gam01_non_admin_viewing_other_403(self):
        """GAM-01: non-admin viewing another instructor's matrix → 403."""
        current_user = _user(uid=99)
        with pytest.raises(HTTPException) as exc:
            get_instructor_availability_matrix(
                instructor_id=42, year=2025, location_city=None,
                db=MagicMock(), current_user=current_user,
            )
        assert exc.value.status_code == 403

    def test_gam02_instructor_not_found_404(self):
        """GAM-02: instructor not in DB → 404."""
        q_user = _q(); q_user.first.return_value = None
        db = _seq_db(q_user)
        with pytest.raises(HTTPException) as exc:
            get_instructor_availability_matrix(
                instructor_id=42, year=2025, location_city=None,
                db=db, current_user=_user(uid=42),
            )
        assert exc.value.status_code == 404

    def test_gam03_no_availability_default_matrix(self):
        """GAM-03: no availability records → default Q1-Q4 × 4 specs matrix."""
        q_user = _q(); q_user.first.return_value = MagicMock()
        q_avail = _q(); q_avail.all.return_value = []
        db = _seq_db(q_user, q_avail)
        with patch(f"{_BASE}.InstructorAvailabilityMatrix") as MockMatrix:
            MockMatrix.return_value = MagicMock()
            get_instructor_availability_matrix(
                instructor_id=42, year=2025, location_city=None,
                db=db, current_user=_user(uid=42),
            )
        call_kwargs = MockMatrix.call_args[1]
        matrix_arg = call_kwargs["matrix"]
        assert set(matrix_arg.keys()) == {"Q1", "Q2", "Q3", "Q4"}
        for period_dict in matrix_arg.values():
            assert len(period_dict) == 4
            for val in period_dict.values():
                assert val is True

    def test_gam04_with_availability_data_matrix_filled(self):
        """GAM-04: availability data present → matrix updated from records."""
        q_user = _q(); q_user.first.return_value = MagicMock()
        av = _avail(); av.time_period_code = "Q1"; av.specialization_type = "LFA_PLAYER_PRE"
        av.is_available = False; av.notes = "On leave"
        q_avail = _q(); q_avail.all.return_value = [av]
        db = _seq_db(q_user, q_avail)
        with patch(f"{_BASE}.InstructorAvailabilityMatrix") as MockMatrix:
            MockMatrix.return_value = MagicMock()
            get_instructor_availability_matrix(
                instructor_id=42, year=2025, location_city=None,
                db=db, current_user=_user(uid=42),
            )
        matrix_arg = MockMatrix.call_args[1]["matrix"]
        assert matrix_arg["Q1"]["LFA_PLAYER_PRE"] is False

    def test_gam05_location_city_filter_applied(self):
        """GAM-05: location_city provided → extra filter called."""
        q_user = _q(); q_user.first.return_value = MagicMock()
        q_avail = _q(); q_avail.all.return_value = []
        db = _seq_db(q_user, q_avail)
        with patch(f"{_BASE}.InstructorAvailabilityMatrix") as MockMatrix:
            MockMatrix.return_value = MagicMock()
            get_instructor_availability_matrix(
                instructor_id=42, year=2025, location_city="Budapest",
                db=db, current_user=_user(uid=42),
            )
        assert q_avail.filter.call_count >= 2  # base + location_city

    def test_gam06_admin_can_view_any(self):
        """GAM-06: admin viewing other instructor → success."""
        q_user = _q(); q_user.first.return_value = MagicMock()
        q_avail = _q(); q_avail.all.return_value = []
        db = _seq_db(q_user, q_avail)
        with patch(f"{_BASE}.InstructorAvailabilityMatrix") as MockMatrix:
            MockMatrix.return_value = MagicMock()
            result = get_instructor_availability_matrix(
                instructor_id=99, year=2025, location_city=None,
                db=db, current_user=_admin(),
            )
        MockMatrix.assert_called_once()


# ---------------------------------------------------------------------------
# create_instructor_availability
# ---------------------------------------------------------------------------

class TestCreateInstructorAvailability:
    def test_cia01_non_admin_for_other_403(self):
        """CIA-01: non-admin creating for other instructor → 403."""
        av = MagicMock(); av.instructor_id = 99
        with pytest.raises(HTTPException) as exc:
            create_instructor_availability(
                availability=av, db=MagicMock(), current_user=_user(uid=42),
            )
        assert exc.value.status_code == 403

    def test_cia02_duplicate_409(self):
        """CIA-02: record already exists → 409."""
        av = MagicMock(); av.instructor_id = 42
        q = _q(); q.first.return_value = _avail()
        db = MagicMock(); db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            create_instructor_availability(
                availability=av, db=db, current_user=_user(uid=42),
            )
        assert exc.value.status_code == 409

    def test_cia03_success(self):
        """CIA-03: valid request → db.add called, record returned."""
        av = MagicMock(); av.instructor_id = 42
        av.model_dump.return_value = {"instructor_id": 42}
        q = _q(); q.first.return_value = None
        db = MagicMock(); db.query.return_value = q
        with patch(f"{_BASE}.InstructorSpecializationAvailability") as MockModel:
            new_rec = MagicMock(); MockModel.return_value = new_rec
            result = create_instructor_availability(
                availability=av, db=db, current_user=_user(uid=42),
            )
        db.add.assert_called_once_with(new_rec)
        db.commit.assert_called_once()
        assert result is new_rec


# ---------------------------------------------------------------------------
# update_instructor_availability
# ---------------------------------------------------------------------------

class TestUpdateInstructorAvailability:
    def test_uia01_not_found_404(self):
        """UIA-01: record not found → 404."""
        q = _q(); q.first.return_value = None
        db = MagicMock(); db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            update_instructor_availability(
                availability_id=99, availability_update=MagicMock(),
                db=db, current_user=_user(uid=42),
            )
        assert exc.value.status_code == 404

    def test_uia02_non_admin_updating_other_403(self):
        """UIA-02: non-admin updating other's record → 403."""
        existing = _avail(instructor_id=99)
        q = _q(); q.first.return_value = existing
        db = MagicMock(); db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            update_instructor_availability(
                availability_id=1, availability_update=MagicMock(),
                db=db, current_user=_user(uid=42),
            )
        assert exc.value.status_code == 403

    def test_uia03_success_fields_updated(self):
        """UIA-03: own record → fields set, commit called."""
        existing = _avail(instructor_id=42)
        q = _q(); q.first.return_value = existing
        db = MagicMock(); db.query.return_value = q
        upd = MagicMock(); upd.model_dump.return_value = {"is_available": False, "notes": "Leave"}
        result = update_instructor_availability(
            availability_id=1, availability_update=upd,
            db=db, current_user=_user(uid=42),
        )
        assert existing.is_available is False
        assert existing.notes == "Leave"
        db.commit.assert_called_once()

    def test_uia04_admin_can_update_any(self):
        """UIA-04: admin updates any record → success."""
        existing = _avail(instructor_id=77)
        q = _q(); q.first.return_value = existing
        db = MagicMock(); db.query.return_value = q
        upd = MagicMock(); upd.model_dump.return_value = {"is_available": True}
        result = update_instructor_availability(
            availability_id=1, availability_update=upd,
            db=db, current_user=_admin(),
        )
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# bulk_upsert_instructor_availability
# ---------------------------------------------------------------------------

class TestBulkUpsertInstructorAvailability:
    def test_bui01_non_admin_for_other_403(self):
        """BUI-01: non-admin for other instructor → 403."""
        with pytest.raises(HTTPException) as exc:
            bulk_upsert_instructor_availability(
                instructor_id=99, year=2025, location_city=None, matrix={},
                db=MagicMock(), current_user=_user(uid=42),
            )
        assert exc.value.status_code == 403

    def test_bui02_empty_matrix_zero_counts(self):
        """BUI-02: empty matrix → 0 created, 0 updated."""
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2025, location_city=None, matrix={},
            db=MagicMock(), current_user=_user(uid=42),
        )
        assert result["created"] == 0
        assert result["updated"] == 0

    def test_bui03_new_entries_created(self):
        """BUI-03: no existing → entries created."""
        q = _q(); q.first.return_value = None
        db = MagicMock(); db.query.return_value = q
        with patch(f"{_BASE}.InstructorSpecializationAvailability") as MockModel:
            MockModel.return_value = MagicMock()
            result = bulk_upsert_instructor_availability(
                instructor_id=42, year=2025, location_city=None,
                matrix={"Q1": {"LFA_PLAYER_PRE": True, "LFA_PLAYER_YOUTH": False}},
                db=db, current_user=_user(uid=42),
            )
        assert result["created"] == 2
        assert result["updated"] == 0

    def test_bui04_existing_entries_updated(self):
        """BUI-04: existing records → updated (not created)."""
        existing1 = _avail(aid=10); existing2 = _avail(aid=11)
        call_n = [0]
        records = [existing1, existing2]
        q = _q()
        def first_side(): n = call_n[0]; call_n[0] += 1; return records[n] if n < 2 else None
        q.first.side_effect = first_side
        db = MagicMock(); db.query.return_value = q
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2025, location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": False, "LFA_PLAYER_YOUTH": True}},
            db=db, current_user=_user(uid=42),
        )
        assert result["updated"] == 2
        assert result["created"] == 0


# ---------------------------------------------------------------------------
# delete_instructor_availability
# ---------------------------------------------------------------------------

class TestDeleteInstructorAvailability:
    def test_dia01_not_found_404(self):
        """DIA-01: record not found → 404."""
        q = _q(); q.first.return_value = None
        db = MagicMock(); db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            delete_instructor_availability(
                availability_id=99, db=db, current_user=_user(uid=42),
            )
        assert exc.value.status_code == 404

    def test_dia02_non_admin_deleting_other_403(self):
        """DIA-02: non-admin deleting other's record → 403."""
        existing = _avail(instructor_id=99)
        q = _q(); q.first.return_value = existing
        db = MagicMock(); db.query.return_value = q
        with pytest.raises(HTTPException) as exc:
            delete_instructor_availability(
                availability_id=1, db=db, current_user=_user(uid=42),
            )
        assert exc.value.status_code == 403

    def test_dia03_success(self):
        """DIA-03: own record → db.delete + commit, returns None."""
        existing = _avail(instructor_id=42)
        q = _q(); q.first.return_value = existing
        db = MagicMock(); db.query.return_value = q
        result = delete_instructor_availability(
            availability_id=1, db=db, current_user=_user(uid=42),
        )
        db.delete.assert_called_once_with(existing)
        db.commit.assert_called_once()
        assert result is None


# ---------------------------------------------------------------------------
# get_instructor_availabilities
# ---------------------------------------------------------------------------

class TestGetInstructorAvailabilities:
    def test_gia01_non_admin_viewing_other_403(self):
        """GIA-01: non-admin viewing other's availabilities → 403."""
        with pytest.raises(HTTPException) as exc:
            get_instructor_availabilities(
                instructor_id=99, year=None, location_city=None,
                db=MagicMock(), current_user=_user(uid=42),
            )
        assert exc.value.status_code == 403

    def test_gia02_own_no_filters_all_returned(self):
        """GIA-02: own, no filters → all records returned."""
        avail_list = [_avail(aid=1), _avail(aid=2)]
        q = _q(); q.all.return_value = avail_list
        db = MagicMock(); db.query.return_value = q
        result = get_instructor_availabilities(
            instructor_id=42, year=None, location_city=None,
            db=db, current_user=_user(uid=42),
        )
        assert result == avail_list

    def test_gia03_with_year_filter(self):
        """GIA-03: year provided → extra filter applied."""
        q = _q(); q.all.return_value = []
        db = MagicMock(); db.query.return_value = q
        get_instructor_availabilities(
            instructor_id=42, year=2025, location_city=None,
            db=db, current_user=_user(uid=42),
        )
        assert q.filter.call_count >= 2

    def test_gia04_with_location_city_filter(self):
        """GIA-04: location_city provided → extra filter applied."""
        q = _q(); q.all.return_value = []
        db = MagicMock(); db.query.return_value = q
        get_instructor_availabilities(
            instructor_id=42, year=None, location_city="Budapest",
            db=db, current_user=_user(uid=42),
        )
        assert q.filter.call_count >= 2
