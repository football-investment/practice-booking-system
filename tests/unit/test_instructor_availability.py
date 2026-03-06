"""
Unit tests for app/api/api_v1/endpoints/instructor_availability.py

Coverage targets:
  bulk_upsert_instructor_availability() — POST /bulk-upsert  (main coverage target)
    - 403: non-admin tries to set other instructor's availability
    - all-insert path: all records new → created_count == N
    - all-update path: all records exist → updated_count == N
    - mixed path: some new, some existing → correct created/updated counts
    - empty matrix: 0 created, 0 updated
    - commit called after all upserts

  create_instructor_availability() — POST /
    - 403: instructor sets other's availability
    - 409: duplicate record
    - happy path: db.add + commit + refresh called

  update_instructor_availability() — PATCH /{availability_id}
    - 404: record not found
    - 403: instructor updates other's record
    - happy path: fields updated, commit called

  delete_instructor_availability() — DELETE /{availability_id}
    - 404: record not found
    - 403: instructor deletes other's record
    - happy path: db.delete + commit called

  get_instructor_availability_matrix() — GET /matrix/{instructor_id}/{year}
    - 403: instructor views other's matrix
    - 404: instructor not found
    - empty data → default Q1-Q4 matrix returned
    - with data → matrix filled from records
"""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException

from app.api.api_v1.endpoints.instructor_availability import (
    bulk_upsert_instructor_availability,
    create_instructor_availability,
    update_instructor_availability,
    delete_instructor_availability,
    get_instructor_availability_matrix,
)
from app.models.user import UserRole
from app.models.instructor_availability import InstructorSpecializationAvailability
from app.schemas.instructor_availability import (
    InstructorAvailabilityCreate,
    InstructorAvailabilityUpdate,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _user(role: UserRole = UserRole.INSTRUCTOR, user_id: int = 42):
    u = MagicMock()
    u.id   = user_id
    u.role = role
    return u


def _avail_record(instructor_id=42, avail_id=1, is_available=True):
    r = MagicMock(spec=InstructorSpecializationAvailability)
    r.id             = avail_id
    r.instructor_id  = instructor_id
    r.is_available   = is_available
    r.time_period_code = "Q1"
    r.specialization_type = "LFA_PLAYER_PRE"
    r.year = 2026
    r.location_city = "Budapest"
    r.notes = None
    return r


def _db_avail(first_result=None):
    """db.query(InstructorSpecializationAvailability).filter().first() → first_result."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.all.return_value = []
    q.first.return_value = first_result
    db.query.return_value = q
    return db, q


def _db_user_avail(instructor_first=None, avail_first=None, avail_all=None):
    """Discriminating db: User queries → instructor, Availability queries → avail."""
    from app.models.user import User
    db = MagicMock()

    user_q = MagicMock()
    user_q.filter.return_value = user_q
    user_q.first.return_value  = instructor_first

    avail_q = MagicMock()
    avail_q.filter.return_value = avail_q
    avail_q.all.return_value    = avail_all or []
    avail_q.first.return_value  = avail_first

    db.query.side_effect = lambda model: user_q if model is User else avail_q
    return db


# ── bulk_upsert_instructor_availability ───────────────────────────────────────

class TestBulkUpsertAuthGuard:

    def test_instructor_cannot_upsert_for_other_instructor(self):
        db, _ = _db_avail()
        with pytest.raises(HTTPException) as exc:
            bulk_upsert_instructor_availability(
                instructor_id=99,   # ≠ current_user.id (42)
                year=2026,
                location_city=None,
                matrix={"Q1": {"LFA_PLAYER_PRE": True}},
                db=db,
                current_user=_user(UserRole.INSTRUCTOR, user_id=42),
            )
        assert exc.value.status_code == 403

    def test_admin_can_upsert_for_any_instructor(self):
        db, _ = _db_avail(first_result=None)
        result = bulk_upsert_instructor_availability(
            instructor_id=99,
            year=2026,
            location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": True}},
            db=db,
            current_user=_user(UserRole.ADMIN, user_id=1),
        )
        assert "created" in result

    def test_instructor_can_upsert_for_themselves(self):
        db, _ = _db_avail(first_result=None)
        result = bulk_upsert_instructor_availability(
            instructor_id=42,
            year=2026,
            location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": True}},
            db=db,
            current_user=_user(UserRole.INSTRUCTOR, user_id=42),
        )
        assert "created" in result


class TestBulkUpsertAllNew:
    """All records are new → created_count = matrix size, updated_count = 0."""

    def test_all_insert_created_count(self):
        db, _ = _db_avail(first_result=None)  # nothing exists
        matrix = {
            "Q1": {"LFA_PLAYER_PRE": True, "LFA_PLAYER_YOUTH": False},
            "Q2": {"LFA_PLAYER_PRE": True},
        }
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix=matrix, db=db, current_user=_user(UserRole.ADMIN),
        )
        assert result["created"] == 3
        assert result["updated"] == 0
        assert result["total"] == 3

    def test_all_insert_calls_db_add_for_each_record(self):
        db, _ = _db_avail(first_result=None)
        matrix = {"Q1": {"LFA_PLAYER_PRE": True, "LFA_PLAYER_YOUTH": True}}
        bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix=matrix, db=db, current_user=_user(UserRole.ADMIN),
        )
        assert db.add.call_count == 2

    def test_all_insert_commits(self):
        db, _ = _db_avail(first_result=None)
        bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": True}}, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        db.commit.assert_called_once()


class TestBulkUpsertAllExisting:
    """All records already exist → updated_count = N, created_count = 0."""

    def test_all_update_updated_count(self):
        existing = _avail_record()
        db, _ = _db_avail(first_result=existing)
        matrix = {"Q1": {"LFA_PLAYER_PRE": False, "LFA_PLAYER_YOUTH": True}}
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix=matrix, db=db, current_user=_user(UserRole.ADMIN),
        )
        assert result["updated"] == 2
        assert result["created"] == 0
        assert result["total"] == 2

    def test_all_update_does_not_call_db_add(self):
        existing = _avail_record()
        db, _ = _db_avail(first_result=existing)
        bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": False}}, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        db.add.assert_not_called()

    def test_update_sets_is_available_on_existing_record(self):
        existing = _avail_record(is_available=True)
        db, _ = _db_avail(first_result=existing)
        bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": False}}, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        assert existing.is_available is False


class TestBulkUpsertEmptyMatrix:

    def test_empty_matrix_returns_zero_counts(self):
        db, _ = _db_avail()
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix={}, db=db, current_user=_user(UserRole.ADMIN),
        )
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total"] == 0

    def test_empty_matrix_still_commits(self):
        db, _ = _db_avail()
        bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix={}, db=db, current_user=_user(UserRole.ADMIN),
        )
        db.commit.assert_called_once()


class TestBulkUpsertReturnFields:

    def test_response_has_message_field(self):
        db, _ = _db_avail(first_result=None)
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix={"Q1": {"LFA_PLAYER_PRE": True}}, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        assert "message" in result

    def test_total_equals_created_plus_updated(self):
        db, _ = _db_avail(first_result=None)
        matrix = {"Q1": {"A": True, "B": False}, "Q2": {"A": True}}
        result = bulk_upsert_instructor_availability(
            instructor_id=42, year=2026, location_city=None,
            matrix=matrix, db=db, current_user=_user(UserRole.ADMIN),
        )
        assert result["total"] == result["created"] + result["updated"]


# ── create_instructor_availability ────────────────────────────────────────────

class TestCreateInstructorAvailability:

    def _payload(self):
        return InstructorAvailabilityCreate(
            instructor_id=42,
            specialization_type="LFA_PLAYER_PRE",
            time_period_code="Q1",
            year=2026,
            location_city="Budapest",
            is_available=True,
        )

    def test_403_when_instructor_creates_for_other(self):
        db, _ = _db_avail()
        payload = self._payload()
        payload.instructor_id = 99
        with pytest.raises(HTTPException) as exc:
            create_instructor_availability(
                availability=payload, db=db,
                current_user=_user(UserRole.INSTRUCTOR, user_id=42),
            )
        assert exc.value.status_code == 403

    def test_409_when_record_already_exists(self):
        db, _ = _db_avail(first_result=_avail_record())
        with pytest.raises(HTTPException) as exc:
            create_instructor_availability(
                availability=self._payload(), db=db,
                current_user=_user(UserRole.INSTRUCTOR, user_id=42),
            )
        assert exc.value.status_code == 409

    def test_happy_path_calls_db_add_and_commit(self):
        db, _ = _db_avail(first_result=None)
        create_instructor_availability(
            availability=self._payload(), db=db,
            current_user=_user(UserRole.INSTRUCTOR, user_id=42),
        )
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ── update_instructor_availability ───────────────────────────────────────────

class TestUpdateInstructorAvailability:

    def test_404_when_record_not_found(self):
        db, _ = _db_avail(first_result=None)
        with pytest.raises(HTTPException) as exc:
            update_instructor_availability(
                availability_id=999,
                availability_update=InstructorAvailabilityUpdate(is_available=False),
                db=db,
                current_user=_user(UserRole.INSTRUCTOR),
            )
        assert exc.value.status_code == 404

    def test_403_when_instructor_updates_other_record(self):
        rec = _avail_record(instructor_id=99)  # owned by user 99
        db, _ = _db_avail(first_result=rec)
        with pytest.raises(HTTPException) as exc:
            update_instructor_availability(
                availability_id=1,
                availability_update=InstructorAvailabilityUpdate(is_available=False),
                db=db,
                current_user=_user(UserRole.INSTRUCTOR, user_id=42),  # user 42 ≠ 99
            )
        assert exc.value.status_code == 403

    def test_happy_path_updates_field_and_commits(self):
        rec = _avail_record(instructor_id=42, is_available=True)
        db, _ = _db_avail(first_result=rec)
        update_instructor_availability(
            availability_id=1,
            availability_update=InstructorAvailabilityUpdate(is_available=False),
            db=db,
            current_user=_user(UserRole.INSTRUCTOR, user_id=42),
        )
        assert rec.is_available is False
        db.commit.assert_called_once()


# ── delete_instructor_availability ────────────────────────────────────────────

class TestDeleteInstructorAvailability:

    def test_404_when_record_not_found(self):
        db, _ = _db_avail(first_result=None)
        with pytest.raises(HTTPException) as exc:
            delete_instructor_availability(
                availability_id=999, db=db,
                current_user=_user(UserRole.INSTRUCTOR),
            )
        assert exc.value.status_code == 404

    def test_403_when_instructor_deletes_other_record(self):
        rec = _avail_record(instructor_id=99)
        db, _ = _db_avail(first_result=rec)
        with pytest.raises(HTTPException) as exc:
            delete_instructor_availability(
                availability_id=1, db=db,
                current_user=_user(UserRole.INSTRUCTOR, user_id=42),
            )
        assert exc.value.status_code == 403

    def test_happy_path_deletes_and_commits(self):
        rec = _avail_record(instructor_id=42)
        db, _ = _db_avail(first_result=rec)
        result = delete_instructor_availability(
            availability_id=1, db=db,
            current_user=_user(UserRole.INSTRUCTOR, user_id=42),
        )
        db.delete.assert_called_once_with(rec)
        db.commit.assert_called_once()
        assert result is None


# ── get_instructor_availability_matrix ────────────────────────────────────────

class TestGetInstructorAvailabilityMatrix:

    def test_403_instructor_views_other_matrix(self):
        db = _db_user_avail(instructor_first=MagicMock())
        with pytest.raises(HTTPException) as exc:
            get_instructor_availability_matrix(
                instructor_id=99, year=2026, db=db,
                current_user=_user(UserRole.INSTRUCTOR, user_id=42),
            )
        assert exc.value.status_code == 403

    def test_404_instructor_not_found(self):
        db = _db_user_avail(instructor_first=None, avail_all=[])
        with pytest.raises(HTTPException) as exc:
            get_instructor_availability_matrix(
                instructor_id=99, year=2026, db=db,
                current_user=_user(UserRole.ADMIN),
            )
        assert exc.value.status_code == 404

    def test_empty_data_returns_default_quarterly_matrix(self):
        db = _db_user_avail(instructor_first=MagicMock(), avail_all=[])
        result = get_instructor_availability_matrix(
            instructor_id=42, year=2026, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        assert set(result.matrix.keys()) == {"Q1", "Q2", "Q3", "Q4"}

    def test_matrix_filled_from_records(self):
        rec = _avail_record(instructor_id=42, is_available=False)
        rec.time_period_code    = "Q1"
        rec.specialization_type = "LFA_PLAYER_PRE"
        rec.notes = None
        db = _db_user_avail(instructor_first=MagicMock(), avail_all=[rec])
        result = get_instructor_availability_matrix(
            instructor_id=42, year=2026, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        assert result.matrix["Q1"]["LFA_PLAYER_PRE"] is False

    def test_returns_instructor_id_and_year(self):
        db = _db_user_avail(instructor_first=MagicMock(), avail_all=[])
        result = get_instructor_availability_matrix(
            instructor_id=42, year=2026, db=db,
            current_user=_user(UserRole.ADMIN),
        )
        assert result.instructor_id == 42
        assert result.year == 2026
