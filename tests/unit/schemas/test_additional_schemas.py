"""
Import-coverage tests for schema files at 0% combined coverage.

Each module's Pydantic class bodies execute at import time,
covering all field definitions, validators, and enum members.

Files covered (0% combined → ~100% after import):
  schemas/license.py            — 78 stmts
  schemas/belt_promotion.py     — 46 stmts
  schemas/location.py           — 33 stmts
  schemas/skill_progression_config.py — 26 stmts
"""
import pytest

# ---------------------------------------------------------------------------
# Import everything at module level → all class bodies execute here
# ---------------------------------------------------------------------------

import app.schemas.license as license_schema
from app.schemas.license import (
    FootballSkillsBase,
    FootballSkillsUpdate,
    FootballSkillsResponse,
)

import app.schemas.belt_promotion as belt_schema
from app.schemas.belt_promotion import (
    BeltPromotionCreate,
)

import app.schemas.location as location_schema
from app.schemas.location import (
    LocationBase,
)

import app.schemas.skill_progression_config as sp_config_schema
from app.schemas.skill_progression_config import (
    SkillProgressionConfig,
)


# ===========================================================================
# schemas/license.py
# ===========================================================================

@pytest.mark.unit
class TestLicenseSchemas:
    def test_module_importable(self):
        assert license_schema is not None

    def test_football_skills_base_instantiation(self):
        skills = FootballSkillsBase(
            heading=70.0,
            shooting=80.0,
            crossing=65.5,
            passing=75.0,
            dribbling=60.0,
            ball_control=72.5,
        )
        assert skills.heading == 70.0
        assert skills.shooting == 80.0

    def test_football_skills_base_rounding(self):
        # Field validator rounds to 1 decimal place
        skills = FootballSkillsBase(
            heading=70.123,
            shooting=80.0,
            crossing=65.0,
            passing=75.0,
            dribbling=60.0,
            ball_control=72.0,
        )
        assert skills.heading == 70.1

    def test_football_skills_update_with_notes(self):
        skills = FootballSkillsUpdate(
            heading=70.0,
            shooting=80.0,
            crossing=65.0,
            passing=75.0,
            dribbling=60.0,
            ball_control=72.0,
            instructor_notes="Good session",
        )
        assert skills.instructor_notes == "Good session"

    def test_other_license_schema_classes_importable(self):
        """Verify remaining schema classes are present in module."""
        assert hasattr(license_schema, "FootballSkillsBase")
        assert hasattr(license_schema, "FootballSkillsResponse")


# ===========================================================================
# schemas/belt_promotion.py
# ===========================================================================

@pytest.mark.unit
class TestBeltPromotionSchemas:
    def test_module_importable(self):
        assert belt_schema is not None

    def test_belt_promotion_create_minimal(self):
        promo = BeltPromotionCreate()
        assert promo.exam_score is None
        assert promo.notes is None

    def test_belt_promotion_create_with_score(self):
        promo = BeltPromotionCreate(exam_score=85, notes="Good form")
        assert promo.exam_score == 85
        assert promo.notes == "Good form"

    def test_invalid_exam_score_raises(self):
        with pytest.raises(Exception):
            BeltPromotionCreate(exam_score=150)  # > 100 — invalid

    def test_all_belt_classes_in_module(self):
        # Ensure the module has all expected names
        assert "BeltPromotionCreate" in dir(belt_schema)


# ===========================================================================
# schemas/location.py
# ===========================================================================

@pytest.mark.unit
class TestLocationSchemas:
    def test_module_importable(self):
        assert location_schema is not None

    def test_location_base_instantiation(self):
        loc = LocationBase(
            name="Budapest Sports Complex",
            city="Budapest",
            country="Hungary",
        )
        assert loc.name == "Budapest Sports Complex"
        assert loc.city == "Budapest"
        assert loc.country == "Hungary"
        assert loc.is_active is True  # default

    def test_location_base_with_optional_fields(self):
        loc = LocationBase(
            name="Vienna Arena",
            city="Vienna",
            country="Austria",
            country_code="AT",
            location_code="VIE",
            postal_code="1010",
        )
        assert loc.country_code == "AT"
        assert loc.location_code == "VIE"

    def test_all_location_classes_in_module(self):
        assert "LocationBase" in dir(location_schema)


# ===========================================================================
# schemas/skill_progression_config.py
# ===========================================================================

@pytest.mark.unit
class TestSkillProgressionConfigSchema:
    def test_module_importable(self):
        assert sp_config_schema is not None

    def test_skill_progression_config_defaults(self):
        config = SkillProgressionConfig()
        # Should instantiate with defaults
        assert config is not None

    def test_all_config_classes_in_module(self):
        assert "SkillProgressionConfig" in dir(sp_config_schema)
