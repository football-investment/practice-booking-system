"""
Unit tests for app/services/location_validation_service.py
Covers: can_create_semester_at_location, get_allowed_semester_types,
        get_location_type_display, get_location_capabilities
All 16 branches exercised.
"""
import pytest
from unittest.mock import MagicMock

from app.services.location_validation_service import LocationValidationService
from app.models.location import LocationType
from app.models.specialization import SpecializationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db(location=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = location
    return db


def _location(location_type: LocationType, city: str = "Budapest"):
    loc = MagicMock()
    loc.location_type = location_type
    loc.city = city
    return loc


# ---------------------------------------------------------------------------
# can_create_semester_at_location
# ---------------------------------------------------------------------------

class TestCanCreateSemesterAtLocation:

    def test_csl01_location_not_found(self):
        """CSL-01: location not in DB → allowed=False, reason='Location not found'."""
        result = LocationValidationService.can_create_semester_at_location(
            location_id=99, specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            db=_db(location=None)
        )
        assert result["allowed"] is False
        assert result["location_type"] is None
        assert "not found" in result["reason"].lower()

    def test_csl02_center_allows_any_type(self):
        """CSL-02: CENTER location → always allowed regardless of spec type."""
        loc = _location(LocationType.CENTER)
        result = LocationValidationService.can_create_semester_at_location(
            location_id=1, specialization_type=SpecializationType.LFA_PLAYER_PRE_ACADEMY,
            db=_db(location=loc)
        )
        assert result["allowed"] is True
        assert result["location_type"] == "CENTER"
        assert result["reason"] is None

    def test_csl03_center_allows_partner_only_type(self):
        """CSL-03: CENTER allows types that PARTNER would block."""
        loc = _location(LocationType.CENTER)
        result = LocationValidationService.can_create_semester_at_location(
            location_id=1, specialization_type=SpecializationType.LFA_PLAYER_YOUTH_ACADEMY,
            db=_db(location=loc)
        )
        assert result["allowed"] is True

    def test_csl04_partner_blocks_academy_types(self):
        """CSL-04: PARTNER + CENTER_ONLY_TYPE → allowed=False."""
        loc = _location(LocationType.PARTNER, city="Miskolc")
        result = LocationValidationService.can_create_semester_at_location(
            location_id=2, specialization_type=SpecializationType.LFA_PLAYER_PRE_ACADEMY,
            db=_db(location=loc)
        )
        assert result["allowed"] is False
        assert result["location_type"] == "PARTNER"
        assert "Miskolc" in result["reason"]

    def test_csl05_partner_allows_mini_season(self):
        """CSL-05: PARTNER + allowed type → allowed=True."""
        loc = _location(LocationType.PARTNER)
        result = LocationValidationService.can_create_semester_at_location(
            location_id=2, specialization_type=SpecializationType.LFA_PLAYER_PRE,
            db=_db(location=loc)
        )
        assert result["allowed"] is True
        assert result["location_type"] == "PARTNER"
        assert result["reason"] is None

    def test_csl06_partner_allows_tournament_type(self):
        """CSL-06: PARTNER + LFA_FOOTBALL_PLAYER (tournament) → allowed."""
        loc = _location(LocationType.PARTNER)
        result = LocationValidationService.can_create_semester_at_location(
            location_id=2, specialization_type=SpecializationType.LFA_FOOTBALL_PLAYER,
            db=_db(location=loc)
        )
        assert result["allowed"] is True

    def test_csl07_partner_blocks_amateur_academy(self):
        """CSL-07: PARTNER + LFA_PLAYER_AMATEUR_ACADEMY → blocked."""
        loc = _location(LocationType.PARTNER)
        result = LocationValidationService.can_create_semester_at_location(
            location_id=2, specialization_type=SpecializationType.LFA_PLAYER_AMATEUR_ACADEMY,
            db=_db(location=loc)
        )
        assert result["allowed"] is False

    def test_csl08_partner_blocks_pro_academy(self):
        """CSL-08: PARTNER + LFA_PLAYER_PRO_ACADEMY → blocked."""
        loc = _location(LocationType.PARTNER)
        result = LocationValidationService.can_create_semester_at_location(
            location_id=2, specialization_type=SpecializationType.LFA_PLAYER_PRO_ACADEMY,
            db=_db(location=loc)
        )
        assert result["allowed"] is False


# ---------------------------------------------------------------------------
# get_allowed_semester_types
# ---------------------------------------------------------------------------

class TestGetAllowedSemesterTypes:

    def test_gast01_location_not_found_returns_empty(self):
        """GAST-01: location not found → empty list."""
        result = LocationValidationService.get_allowed_semester_types(
            location_id=99, db=_db(location=None)
        )
        assert result == []

    def test_gast02_center_returns_all_three(self):
        """GAST-02: CENTER → 3 categories including Academy."""
        loc = _location(LocationType.CENTER)
        result = LocationValidationService.get_allowed_semester_types(
            location_id=1, db=_db(location=loc)
        )
        assert len(result) == 3
        assert any("Academy" in r for r in result)

    def test_gast03_partner_returns_two(self):
        """GAST-03: PARTNER → 2 categories, no Academy."""
        loc = _location(LocationType.PARTNER)
        result = LocationValidationService.get_allowed_semester_types(
            location_id=2, db=_db(location=loc)
        )
        assert len(result) == 2
        assert not any("Academy" in r for r in result)


# ---------------------------------------------------------------------------
# get_location_type_display
# ---------------------------------------------------------------------------

class TestGetLocationTypeDisplay:

    def test_gltd01_center_display(self):
        """GLTD-01: CENTER → human-readable CENTER label."""
        result = LocationValidationService.get_location_type_display(LocationType.CENTER)
        assert "CENTER" in result

    def test_gltd02_partner_display(self):
        """GLTD-02: PARTNER → human-readable PARTNER label."""
        result = LocationValidationService.get_location_type_display(LocationType.PARTNER)
        assert "PARTNER" in result


# ---------------------------------------------------------------------------
# get_location_capabilities
# ---------------------------------------------------------------------------

class TestGetLocationCapabilities:

    def test_glc01_center_capabilities(self):
        """GLC-01: CENTER → all capabilities listed."""
        result = LocationValidationService.get_location_capabilities(LocationType.CENTER)
        assert "Academy" in result

    def test_glc02_partner_capabilities(self):
        """GLC-02: PARTNER → limited capabilities."""
        result = LocationValidationService.get_location_capabilities(LocationType.PARTNER)
        assert "Academy" not in result
        assert "Tornák" in result or "Mini" in result
