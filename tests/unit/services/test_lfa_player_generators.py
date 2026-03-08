"""
Unit tests for app/api/api_v1/endpoints/periods/lfa_player_generators.py
Covers: all 4 generators — PRE/YOUTH/AMATEUR/PRO
Branches: invalid param, location 404, already-exists 400, new create, force_overwrite update
Sync endpoints — no asyncio.run() needed.
"""
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.api_v1.endpoints.periods.lfa_player_generators import (
    generate_lfa_player_pre_season,
    generate_lfa_player_youth_season,
    generate_lfa_player_amateur_season,
    generate_lfa_player_pro_season,
    LFAPlayerPreRequest,
    LFAPlayerYouthRequest,
    LFAPlayerAmateurRequest,
    LFAPlayerProRequest,
)

_BASE = "app.api.api_v1.endpoints.periods.lfa_player_generators"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_location():
    loc = MagicMock()
    loc.id = 1
    return loc


def _db(location=None):
    """DB mock — db.query(Location).filter().first() returns location arg."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = location
    return db


def _existing_semester():
    s = MagicMock()
    s.code = "EXISTING/CODE"
    s.name = "Existing Season"
    s.start_date = MagicMock()
    s.end_date = MagicMock()
    s.theme = "Old Theme"
    s.focus_description = "Old Focus"
    return s


# ---------------------------------------------------------------------------
# LFA_PLAYER PRE (monthly)
# ---------------------------------------------------------------------------

class TestGenerateLFAPlayerPreSeason:

    def _call(self, year=2025, month=3, location_id=1, force_overwrite=False, db=None):
        req = LFAPlayerPreRequest(year=year, month=month, location_id=location_id, force_overwrite=force_overwrite)
        return generate_lfa_player_pre_season(
            request=req,
            db=db or _db(location=_mock_location()),
            current_user=MagicMock(),
        )

    def test_pre01_invalid_month_low_400(self):
        """month=0 → 400 bad request."""
        with pytest.raises(HTTPException) as exc:
            self._call(month=0)
        assert exc.value.status_code == 400
        assert "1-12" in exc.value.detail

    def test_pre02_invalid_month_high_400(self):
        """month=13 → 400."""
        with pytest.raises(HTTPException) as exc:
            self._call(month=13)
        assert exc.value.status_code == 400

    def test_pre03_location_not_found_404(self):
        """Location not in DB → 404."""
        with pytest.raises(HTTPException) as exc:
            self._call(db=_db(location=None))
        assert exc.value.status_code == 404
        assert "Location" in exc.value.detail

    def test_pre04_already_exists_no_force_400(self):
        """Existing season + no force_overwrite → 400."""
        existing = _existing_semester()
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            with pytest.raises(HTTPException) as exc:
                self._call(force_overwrite=False)
        assert exc.value.status_code == 400
        assert "force_overwrite" in exc.value.detail

    def test_pre05_new_season_created(self):
        """No existing → creates new Semester, commits, returns success."""
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(year=2025, month=3, db=db)
        assert result.success is True
        assert "M03" in result.period["code"]
        assert result.period["period_type"] == "season"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_pre06_force_overwrite_updates_existing(self):
        """Existing + force_overwrite → updates existing semester attributes."""
        existing = _existing_semester()
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            result = self._call(year=2025, month=3, force_overwrite=True, db=db)
        assert result.success is True
        # Should NOT add new object — updates existing
        db.add.assert_not_called()
        db.commit.assert_called_once()

    def test_pre07_response_includes_period_fields(self):
        """Response period dict has required keys."""
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(year=2025, month=6, db=db)
        assert "code" in result.period
        assert "name" in result.period
        assert "start_date" in result.period
        assert "end_date" in result.period
        assert "theme" in result.period


# ---------------------------------------------------------------------------
# LFA_PLAYER YOUTH (quarterly)
# ---------------------------------------------------------------------------

class TestGenerateLFAPlayerYouthSeason:

    def _call(self, year=2025, quarter=2, location_id=1, force_overwrite=False, db=None):
        req = LFAPlayerYouthRequest(year=year, quarter=quarter, location_id=location_id, force_overwrite=force_overwrite)
        return generate_lfa_player_youth_season(
            request=req,
            db=db or _db(location=_mock_location()),
            current_user=MagicMock(),
        )

    def test_youth01_invalid_quarter_low_400(self):
        """quarter=0 → 400."""
        with pytest.raises(HTTPException) as exc:
            self._call(quarter=0)
        assert exc.value.status_code == 400
        assert "1-4" in exc.value.detail

    def test_youth02_invalid_quarter_high_400(self):
        """quarter=5 → 400."""
        with pytest.raises(HTTPException) as exc:
            self._call(quarter=5)
        assert exc.value.status_code == 400

    def test_youth03_location_not_found_404(self):
        with pytest.raises(HTTPException) as exc:
            self._call(db=_db(location=None))
        assert exc.value.status_code == 404

    def test_youth04_already_exists_no_force_400(self):
        existing = _existing_semester()
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            with pytest.raises(HTTPException) as exc:
                self._call(force_overwrite=False)
        assert exc.value.status_code == 400

    def test_youth05_new_season_created(self):
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(quarter=1, db=db)
        assert result.success is True
        assert "Q1" in result.period["code"]
        assert result.period["period_type"] == "season"
        db.add.assert_called_once()

    def test_youth06_force_overwrite_updates(self):
        existing = _existing_semester()
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            result = self._call(quarter=2, force_overwrite=True, db=db)
        assert result.success is True
        db.add.assert_not_called()


# ---------------------------------------------------------------------------
# LFA_PLAYER AMATEUR (annual)
# ---------------------------------------------------------------------------

class TestGenerateLFAPlayerAmateurSeason:

    def _call(self, year=2025, location_id=1, force_overwrite=False, db=None):
        req = LFAPlayerAmateurRequest(year=year, location_id=location_id, force_overwrite=force_overwrite)
        return generate_lfa_player_amateur_season(
            request=req,
            db=db or _db(location=_mock_location()),
            current_user=MagicMock(),
        )

    def test_amateur01_location_not_found_404(self):
        with pytest.raises(HTTPException) as exc:
            self._call(db=_db(location=None))
        assert exc.value.status_code == 404

    def test_amateur02_already_exists_no_force_400(self):
        existing = _existing_semester()
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            with pytest.raises(HTTPException) as exc:
                self._call(force_overwrite=False)
        assert exc.value.status_code == 400

    def test_amateur03_new_season_created(self):
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(year=2025, db=db)
        assert result.success is True
        assert "LFA_PLAYER_AMATEUR" in result.period["code"]
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_amateur04_force_overwrite_updates(self):
        existing = _existing_semester()
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            result = self._call(force_overwrite=True, db=db)
        assert result.success is True
        db.add.assert_not_called()

    def test_amateur05_message_includes_year(self):
        """Success message includes the year."""
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(year=2026, db=db)
        assert "2026" in result.message


# ---------------------------------------------------------------------------
# LFA_PLAYER PRO (annual)
# ---------------------------------------------------------------------------

class TestGenerateLFAPlayerProSeason:

    def _call(self, year=2025, location_id=1, force_overwrite=False, db=None):
        req = LFAPlayerProRequest(year=year, location_id=location_id, force_overwrite=force_overwrite)
        return generate_lfa_player_pro_season(
            request=req,
            db=db or _db(location=_mock_location()),
            current_user=MagicMock(),
        )

    def test_pro01_location_not_found_404(self):
        with pytest.raises(HTTPException) as exc:
            self._call(db=_db(location=None))
        assert exc.value.status_code == 404

    def test_pro02_already_exists_no_force_400(self):
        existing = _existing_semester()
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            with pytest.raises(HTTPException) as exc:
                self._call(force_overwrite=False)
        assert exc.value.status_code == 400

    def test_pro03_new_season_created(self):
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(year=2025, db=db)
        assert result.success is True
        assert "LFA_PLAYER_PRO" in result.period["code"]
        db.add.assert_called_once()

    def test_pro04_force_overwrite_updates(self):
        existing = _existing_semester()
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(True, existing)):
            result = self._call(force_overwrite=True, db=db)
        assert result.success is True
        db.add.assert_not_called()
        db.commit.assert_called_once()

    def test_pro05_response_period_type_is_season(self):
        """LFA_PLAYER generators return period_type='season'."""
        db = _db(location=_mock_location())
        with patch(f"{_BASE}.check_existing_period", return_value=(False, None)):
            result = self._call(db=db)
        assert result.period["period_type"] == "season"


# ---------------------------------------------------------------------------
# Base helpers (via public import)
# ---------------------------------------------------------------------------

class TestBaseHelpers:
    """Verify get_first_monday / get_last_sunday produce valid dates."""

    def test_get_first_monday_is_monday(self):
        from app.api.api_v1.endpoints.periods.base import get_first_monday
        d = get_first_monday(2025, 3)  # March 2025
        assert d.weekday() == 0  # Monday

    def test_get_last_sunday_is_sunday(self):
        from app.api.api_v1.endpoints.periods.base import get_last_sunday
        d = get_last_sunday(2025, 3)
        assert d.weekday() == 6  # Sunday

    def test_get_last_sunday_december_crosses_year(self):
        """December last Sunday uses Jan of next year - 1 day logic."""
        from app.api.api_v1.endpoints.periods.base import get_last_sunday
        d = get_last_sunday(2025, 12)
        assert d.weekday() == 6
        assert d.year == 2025

    def test_check_existing_period(self):
        """check_existing_period wraps db.query().filter().first()."""
        from app.api.api_v1.endpoints.periods.base import check_existing_period
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        exists, existing = check_existing_period(db, "LFA_PLAYER_PRE", "2025/CODE")
        assert exists is False
        assert existing is None

    def test_check_existing_period_found(self):
        from app.api.api_v1.endpoints.periods.base import check_existing_period
        mock_sem = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_sem
        exists, existing = check_existing_period(db, "LFA_PLAYER_PRE", "2025/CODE")
        assert exists is True
        assert existing is mock_sem

    def test_get_period_label_lfa_player(self):
        from app.api.api_v1.endpoints.periods.base import get_period_label
        assert get_period_label("LFA_PLAYER") == "season"

    def test_get_period_label_other(self):
        from app.api.api_v1.endpoints.periods.base import get_period_label
        assert get_period_label("INTERNSHIP") == "semester"
