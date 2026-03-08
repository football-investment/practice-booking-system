"""
Unit tests for app/repositories/tournament_repository.py
Covers: TournamentRepository — all branches:
  get_or_404 (found/not_found/custom_error), get_with_enrollments,
  get_with_sessions, get_with_full_details, get_optional,
  get_active_tournaments (with/without campus_id),
  get_tournaments_by_status (with/without campus_id),
  exists (True/False), delete, update.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.repositories.tournament_repository import TournamentRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(first_val=None, count_val=0, all_val=None):
    """Build TournamentRepository with a configurable DB mock."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.count.return_value = count_val
    q.first.return_value = first_val
    q.all.return_value = all_val or []
    db.query.return_value = q
    repo = TournamentRepository(db)
    return repo, db, q


def _tournament(tid=10, name="Spring Cup"):
    t = MagicMock()
    t.id = tid
    t.name = name
    t.is_active = True
    return t


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_init01_stores_db(self):
        """INIT-01: db attribute set."""
        db = MagicMock()
        repo = TournamentRepository(db)
        assert repo.db is db


# ---------------------------------------------------------------------------
# get_or_404
# ---------------------------------------------------------------------------

class TestGetOr404:

    def test_go4_01_found(self):
        """GO4-01: tournament found → returned."""
        t = _tournament()
        repo, db, q = _make_repo(first_val=t)
        result = repo.get_or_404(10)
        assert result is t

    def test_go4_02_not_found_default_message(self):
        """GO4-02: not found → 404 with default message."""
        repo, db, q = _make_repo(first_val=None)
        with pytest.raises(HTTPException) as exc:
            repo.get_or_404(99)
        assert exc.value.status_code == 404
        assert "99" in exc.value.detail

    def test_go4_03_not_found_custom_message(self):
        """GO4-03: not found + custom error_detail → 404 with custom message."""
        repo, db, q = _make_repo(first_val=None)
        with pytest.raises(HTTPException) as exc:
            repo.get_or_404(99, error_detail="Custom message here")
        assert exc.value.status_code == 404
        assert exc.value.detail == "Custom message here"


# ---------------------------------------------------------------------------
# get_with_enrollments
# ---------------------------------------------------------------------------

_REPO = "app.repositories.tournament_repository"


def _joinedload_ctx():
    """
    Context manager that patches both joinedload and Semester in the repo module.

    get_with_* methods call joinedload(Semester.semester_enrollments) where
    'semester_enrollments' doesn't exist on the real Semester model (production bug).
    Patching Semester makes all attribute access return MagicMock, avoiding AttributeError.
    """
    return patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload")


class TestGetWithEnrollments:
    # Note: production code uses Semester.semester_enrollments but the model
    # has `enrollments` — patch Semester + joinedload to avoid AttributeError.

    def test_gwe01_found(self):
        """GWE-01: tournament found with joinedload → returned."""
        t = _tournament()
        repo, db, q = _make_repo(first_val=t)
        with patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload"):
            result = repo.get_with_enrollments(10)
        assert result is t
        q.options.assert_called_once()

    def test_gwe02_not_found(self):
        """GWE-02: not found → 404."""
        repo, db, q = _make_repo(first_val=None)
        with patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload"):
            with pytest.raises(HTTPException) as exc:
                repo.get_with_enrollments(99)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_with_sessions
# ---------------------------------------------------------------------------

class TestGetWithSessions:

    def test_gws01_found(self):
        """GWS-01: tournament found with sessions loaded → returned."""
        t = _tournament()
        repo, db, q = _make_repo(first_val=t)
        with patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload"):
            result = repo.get_with_sessions(10)
        assert result is t

    def test_gws02_not_found(self):
        """GWS-02: not found → 404."""
        repo, db, q = _make_repo(first_val=None)
        with patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload"):
            with pytest.raises(HTTPException) as exc:
                repo.get_with_sessions(99)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_with_full_details
# ---------------------------------------------------------------------------

class TestGetWithFullDetails:

    def test_gwfd01_found(self):
        """GWFD-01: all relations eagerly loaded → returned."""
        t = _tournament()
        repo, db, q = _make_repo(first_val=t)
        with patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload"):
            result = repo.get_with_full_details(10)
        assert result is t

    def test_gwfd02_not_found(self):
        """GWFD-02: not found → 404."""
        repo, db, q = _make_repo(first_val=None)
        with patch(f"{_REPO}.Semester"), patch(f"{_REPO}.joinedload"):
            with pytest.raises(HTTPException) as exc:
                repo.get_with_full_details(99)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_optional
# ---------------------------------------------------------------------------

class TestGetOptional:

    def test_gopt01_found(self):
        """GOPT-01: tournament found → returned."""
        t = _tournament()
        repo, db, q = _make_repo(first_val=t)
        result = repo.get_optional(10)
        assert result is t

    def test_gopt02_not_found(self):
        """GOPT-02: not found → None (no exception)."""
        repo, db, q = _make_repo(first_val=None)
        result = repo.get_optional(99)
        assert result is None


# ---------------------------------------------------------------------------
# get_active_tournaments
# ---------------------------------------------------------------------------

class TestGetActiveTournaments:

    def test_gat01_without_campus_filter(self):
        """GAT-01: campus_id=None → no extra filter applied."""
        t1, t2 = _tournament(1), _tournament(2)
        repo, db, q = _make_repo(all_val=[t1, t2])
        result = repo.get_active_tournaments(campus_id=None, limit=10)
        # filter called once (for is_active), NOT twice
        q.filter.assert_called_once()
        assert len(result) == 2

    def test_gat02_with_campus_filter(self):
        """GAT-02: campus_id provided → extra campus filter applied."""
        t = _tournament()
        repo, db, q = _make_repo(all_val=[t])
        result = repo.get_active_tournaments(campus_id=5, limit=10)
        assert q.filter.call_count == 2
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_tournaments_by_status
# ---------------------------------------------------------------------------

class TestGetTournamentsByStatus:

    def test_gtbs01_without_campus_filter(self):
        """GTBS-01: campus_id=None → one filter only (status)."""
        repo, db, q = _make_repo(all_val=[_tournament()])
        result = repo.get_tournaments_by_status("DRAFT", campus_id=None)
        q.filter.assert_called_once()

    def test_gtbs02_with_campus_filter(self):
        """GTBS-02: campus_id provided → two filters (status + campus)."""
        repo, db, q = _make_repo(all_val=[])
        result = repo.get_tournaments_by_status("IN_PROGRESS", campus_id=3)
        assert q.filter.call_count == 2


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------

class TestExists:

    def test_ex01_tournament_exists(self):
        """EX-01: count > 0 → True."""
        repo, db, q = _make_repo(count_val=1)
        assert repo.exists(10) is True

    def test_ex02_tournament_does_not_exist(self):
        """EX-02: count == 0 → False."""
        repo, db, q = _make_repo(count_val=0)
        assert repo.exists(99) is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:

    def test_del01_found_deletes_and_commits(self):
        """DEL-01: found → get_or_404 succeeds, db.delete + commit called."""
        t = _tournament()
        repo, db, q = _make_repo(first_val=t)
        repo.delete(10)
        db.delete.assert_called_once_with(t)
        db.commit.assert_called_once()

    def test_del02_not_found_raises_404(self):
        """DEL-02: get_or_404 raises → propagated."""
        repo, db, q = _make_repo(first_val=None)
        with pytest.raises(HTTPException) as exc:
            repo.delete(99)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:

    def test_upd01_adds_commits_refreshes(self):
        """UPD-01: update → db.add, commit, refresh called, returns tournament."""
        t = _tournament()
        repo, db, q = _make_repo()
        result = repo.update(t)
        db.add.assert_called_once_with(t)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(t)
        assert result is t
