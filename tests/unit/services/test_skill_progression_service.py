"""
Comprehensive Unit Tests for SkillProgressionService

Tests cover:
- Delta calculation (tournament vs assessment)
- Cap enforcement (tournament, assessment, overall 100.0)
- Migration from old to new format
- Decay mechanism (exponential curve)
- Configuration overrides
- Edge cases (negative values, zero deltas, cap exceeded)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.skill_progression_service import SkillProgressionService
from app.schemas.skill_progression_config import (
    SkillProgressionConfig,
    get_tournament_config
)
from app.models.license import UserLicense
from app.models.tournament_achievement import TournamentParticipation


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def default_service(mock_db):
    """Default SkillProgressionService with standard config"""
    return SkillProgressionService(mock_db)


@pytest.fixture
def custom_config_service(mock_db):
    """Service with custom configuration"""
    config = SkillProgressionConfig(
        tournament_delta_multiplier=0.15,
        tournament_max_contribution=20.0,
        assessment_delta_multiplier=0.25,
        assessment_max_contribution=12.0
    )
    return SkillProgressionService(mock_db, config=config)


@pytest.fixture
def mock_user_license():
    """Mock UserLicense with old format skills"""
    license = Mock(spec=UserLicense)
    license.id = 1
    license.user_id = 100
    license.football_skills = {
        "speed": 80.0,
        "agility": 75.0,
        "ball_control": 85.0
    }
    return license


@pytest.fixture
def mock_user_license_new_format():
    """Mock UserLicense with new format skills"""
    license = Mock(spec=UserLicense)
    license.id = 1
    license.user_id = 100
    license.football_skills = {
        "speed": {
            "current_level": 80.0,
            "baseline": 80.0,
            "total_delta": 0.0,
            "tournament_delta": 0.0,
            "assessment_delta": 0.0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "tournament_count": 0,
            "assessment_count": 0
        }
    }
    return license


# ============================================================================
# Test: Delta Calculation
# ============================================================================

class TestDeltaCalculation:
    """Test delta calculation with different multipliers"""

    def test_tournament_delta_default(self, default_service):
        """Test tournament delta with default multiplier (0.125)"""
        raw_points = 10.0
        delta = default_service._calculate_delta(raw_points, source="tournament")
        assert delta == 1.25  # 10.0 × 0.125 = 1.25

    def test_assessment_delta_default(self, default_service):
        """Test assessment delta with default multiplier (0.20)"""
        raw_points = 10.0
        delta = default_service._calculate_delta(raw_points, source="assessment")
        assert delta == 2.0  # 10.0 × 0.20 = 2.0

    def test_tournament_delta_custom(self, custom_config_service):
        """Test tournament delta with custom multiplier (0.15)"""
        raw_points = 10.0
        delta = custom_config_service._calculate_delta(raw_points, source="tournament")
        assert delta == 1.5  # 10.0 × 0.15 = 1.5

    def test_assessment_delta_custom(self, custom_config_service):
        """Test assessment delta with custom multiplier (0.25)"""
        raw_points = 10.0
        delta = custom_config_service._calculate_delta(raw_points, source="assessment")
        assert delta == 2.5  # 10.0 × 0.25 = 2.5

    def test_zero_raw_points(self, default_service):
        """Test with zero raw points"""
        delta = default_service._calculate_delta(0.0, source="tournament")
        assert delta == 0.0

    def test_negative_raw_points(self, default_service):
        """Test with negative raw points (edge case)"""
        raw_points = -5.0
        delta = default_service._calculate_delta(raw_points, source="tournament")
        assert delta == -0.62  # -5.0 × 0.125 = -0.625, rounded to -0.62


# ============================================================================
# Test: Migration (Old Format → New Format)
# ============================================================================

class TestMigration:
    """Test migration from old to new format"""

    def test_migrate_old_format(self, default_service):
        """Test migration from old static format to new dynamic format"""
        old_skills = {
            "speed": 80.0,
            "agility": 75.0,
            "ball_control": 85.0
        }

        new_skills = default_service._ensure_new_format(old_skills)

        # Check structure
        assert "speed" in new_skills
        assert isinstance(new_skills["speed"], dict)
        assert "current_level" in new_skills["speed"]
        assert "baseline" in new_skills["speed"]
        assert "tournament_delta" in new_skills["speed"]
        assert "assessment_delta" in new_skills["speed"]

        # Check values
        assert new_skills["speed"]["current_level"] == 80.0
        assert new_skills["speed"]["baseline"] == 80.0
        assert new_skills["speed"]["total_delta"] == 0.0
        assert new_skills["speed"]["tournament_delta"] == 0.0
        assert new_skills["speed"]["assessment_delta"] == 0.0

    def test_already_new_format(self, default_service):
        """Test that already migrated skills are not re-migrated"""
        new_skills = {
            "speed": {
                "current_level": 85.0,
                "baseline": 80.0,
                "total_delta": 5.0,
                "tournament_delta": 3.0,
                "assessment_delta": 2.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 2,
                "assessment_count": 1
            }
        }

        result = default_service._ensure_new_format(new_skills)

        # Should return unchanged
        assert result["speed"]["current_level"] == 85.0
        assert result["speed"]["tournament_delta"] == 3.0
        assert result["speed"]["assessment_delta"] == 2.0

    def test_empty_skills(self, default_service):
        """Test with empty skills dict"""
        result = default_service._ensure_new_format({})
        assert result == {}


# ============================================================================
# Test: Cap Enforcement
# ============================================================================

class TestCapEnforcement:
    """Test tournament, assessment, and overall caps"""

    def test_tournament_cap_not_reached(self, default_service):
        """Test tournament delta within cap"""
        skills = {
            "speed": {
                "current_level": 80.0,
                "baseline": 80.0,
                "total_delta": 0.0,
                "tournament_delta": 5.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        # Apply +2.0 delta (total: 7.0, under cap of 15.0)
        result = default_service._apply_skill_delta(
            skills, "speed", 2.0, source="tournament"
        )

        assert result["speed"]["tournament_delta"] == 7.0
        assert result["speed"]["current_level"] == 87.0  # 80 + 7.0

    def test_tournament_cap_reached(self, default_service):
        """Test tournament cap enforcement (max +15.0)"""
        skills = {
            "speed": {
                "current_level": 94.0,
                "baseline": 80.0,
                "total_delta": 14.0,
                "tournament_delta": 14.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        # Try to apply +5.0 delta (would be 19.0, but cap is 15.0)
        result = default_service._apply_skill_delta(
            skills, "speed", 5.0, source="tournament"
        )

        # Should be capped at 15.0
        assert result["speed"]["tournament_delta"] == 15.0
        assert result["speed"]["current_level"] == 95.0  # 80 + 15.0

    def test_assessment_cap_reached(self, default_service):
        """Test assessment cap enforcement (max +10.0)"""
        skills = {
            "ball_control": {
                "current_level": 89.0,
                "baseline": 80.0,
                "total_delta": 9.0,
                "tournament_delta": 0.0,
                "assessment_delta": 9.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        # Try to apply +3.0 delta (would be 12.0, but cap is 10.0)
        result = default_service._apply_skill_delta(
            skills, "ball_control", 3.0, source="assessment"
        )

        # Should be capped at 10.0
        assert result["ball_control"]["assessment_delta"] == 10.0
        assert result["ball_control"]["current_level"] == 90.0  # 80 + 10.0

    def test_overall_cap_100(self, default_service):
        """Test overall skill cap at 100.0"""
        skills = {
            "shooting": {
                "current_level": 98.0,
                "baseline": 85.0,
                "total_delta": 13.0,
                "tournament_delta": 10.0,
                "assessment_delta": 3.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        # Try to apply +5.0 delta (would be 103.0, but overall cap is 100.0)
        result = default_service._apply_skill_delta(
            skills, "shooting", 5.0, source="tournament"
        )

        # Current level should be capped at 100.0
        assert result["shooting"]["current_level"] == 100.0
        # Delta tracking continues normally
        assert result["shooting"]["tournament_delta"] == 15.0

    def test_combined_caps(self, default_service):
        """Test tournament + assessment with overall cap"""
        skills = {
            "passing": {
                "current_level": 95.0,
                "baseline": 75.0,
                "total_delta": 20.0,
                "tournament_delta": 12.0,
                "assessment_delta": 8.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        # Apply +2.0 assessment delta
        result = default_service._apply_skill_delta(
            skills, "passing", 2.0, source="assessment"
        )

        # Tournament: 12.0, Assessment: 10.0 (capped), Total: 22.0
        # 75 + 22 = 97, under 100 cap
        assert result["passing"]["assessment_delta"] == 10.0
        assert result["passing"]["tournament_delta"] == 12.0
        assert result["passing"]["current_level"] == 97.0


# ============================================================================
# Test: Decay Mechanism
# ============================================================================

class TestDecayMechanism:
    """Test exponential decay with simulated dates"""

    def test_decay_disabled(self, default_service, mock_db):
        """Test that decay does nothing when disabled"""
        # Ensure decay is disabled
        default_service.DECAY_ENABLED = False

        result = default_service.apply_skill_decay(user_license_id=1)

        assert result == {}

    def test_decay_within_threshold(self, default_service, mock_db):
        """Test no decay if within 30-day threshold"""
        # Enable decay for testing
        default_service.DECAY_ENABLED = True

        # Mock license with skills
        license = Mock(spec=UserLicense)
        license.football_skills = {
            "speed": {
                "current_level": 85.0,
                "baseline": 80.0,
                "total_delta": 5.0,
                "tournament_delta": 5.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 3,
                "assessment_count": 0
            }
        }

        # Mock last participation (20 days ago - under threshold)
        current_date = datetime(2026, 1, 25, tzinfo=timezone.utc)
        last_participation = Mock(spec=TournamentParticipation)
        last_participation.created_at = current_date - timedelta(days=20)

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            license,  # First call: get license
            last_participation  # Second call: get participation
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = last_participation

        result = default_service.apply_skill_decay(
            user_license_id=1,
            current_date=current_date
        )

        # No decay applied (under threshold)
        assert result["speed"]["current_level"] == 85.0

    def test_decay_exponential_curve(self, default_service, mock_db):
        """Test exponential decay formula"""
        import math

        # Enable decay
        default_service.DECAY_ENABLED = True

        # Mock license with skills
        license = Mock(spec=UserLicense)
        license.football_skills = {
            "speed": {
                "current_level": 90.0,
                "baseline": 80.0,
                "total_delta": 10.0,
                "tournament_delta": 10.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 5,
                "assessment_count": 0
            }
        }

        # Mock last participation (60 days ago = 30 threshold + 30 active = 1 month)
        current_date = datetime(2026, 1, 25, tzinfo=timezone.utc)
        last_participation = Mock(spec=TournamentParticipation)
        last_participation.created_at = current_date - timedelta(days=60)

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            license,
            None  # Will use order_by chain instead
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = last_participation

        result = default_service.apply_skill_decay(
            user_license_id=1,
            current_date=current_date
        )

        # Calculate expected decay
        # months_inactive = (60 - 30) / 30 = 1.0
        # decay_factor = 1 - e^(-0.5 × 1.0) ≈ 0.393
        # max_decay = 10.0 × 0.20 = 2.0
        # decay_amount = 2.0 × 0.393 ≈ 0.786
        # new_level = 90.0 - 0.786 ≈ 89.2

        decay_factor = 1 - math.exp(-0.5 * 1.0)
        expected_decay = 10.0 * 0.20 * decay_factor
        expected_level = round(90.0 - expected_decay, 1)

        assert result["speed"]["current_level"] == expected_level
        assert "total_decay_applied" in result["speed"]
        assert result["speed"]["total_decay_applied"] > 0

    def test_decay_never_below_baseline(self, default_service, mock_db):
        """Test that decay never goes below baseline"""
        # Enable decay
        default_service.DECAY_ENABLED = True

        # Mock license with small delta
        license = Mock(spec=UserLicense)
        license.football_skills = {
            "speed": {
                "current_level": 81.0,
                "baseline": 80.0,
                "total_delta": 1.0,
                "tournament_delta": 1.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 1,
                "assessment_count": 0
            }
        }

        # Mock last participation (very long ago - 180 days)
        current_date = datetime(2026, 1, 25, tzinfo=timezone.utc)
        last_participation = Mock(spec=TournamentParticipation)
        last_participation.created_at = current_date - timedelta(days=180)

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            license,
            None
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = last_participation

        result = default_service.apply_skill_decay(
            user_license_id=1,
            current_date=current_date
        )

        # Should not go below baseline (80.0)
        assert result["speed"]["current_level"] >= 80.0


# ============================================================================
# Test: Configuration System
# ============================================================================

class TestConfigurationSystem:
    """Test configuration overrides and templates"""

    def test_default_config_values(self, default_service):
        """Test default configuration values"""
        assert default_service.TOURNAMENT_DELTA_MULTIPLIER == 0.125
        assert default_service.TOURNAMENT_MAX_CONTRIBUTION == 15.0
        assert default_service.ASSESSMENT_DELTA_MULTIPLIER == 0.20
        assert default_service.ASSESSMENT_MAX_CONTRIBUTION == 10.0
        assert default_service.MAX_SKILL_LEVEL == 100.0

    def test_custom_config_override(self, custom_config_service):
        """Test custom configuration override"""
        assert custom_config_service.TOURNAMENT_DELTA_MULTIPLIER == 0.15
        assert custom_config_service.TOURNAMENT_MAX_CONTRIBUTION == 20.0
        assert custom_config_service.ASSESSMENT_DELTA_MULTIPLIER == 0.25
        assert custom_config_service.ASSESSMENT_MAX_CONTRIBUTION == 12.0

    def test_speed_focus_template(self, mock_db):
        """Test SPEED_FOCUS template configuration"""
        config = get_tournament_config(tournament_type="SPEED_FOCUS")
        service = SkillProgressionService(mock_db, config=config)

        assert service.TOURNAMENT_DELTA_MULTIPLIER == 0.15
        assert service.TOURNAMENT_MAX_CONTRIBUTION == 20.0

    def test_technical_focus_template(self, mock_db):
        """Test TECHNICAL_FOCUS template configuration"""
        config = get_tournament_config(tournament_type="TECHNICAL_FOCUS")
        service = SkillProgressionService(mock_db, config=config)

        assert service.TOURNAMENT_DELTA_MULTIPLIER == 0.10
        assert service.TOURNAMENT_MAX_CONTRIBUTION == 12.0
        assert service.ASSESSMENT_DELTA_MULTIPLIER == 0.25

    def test_custom_override_on_template(self, mock_db):
        """Test custom override on top of template"""
        config = get_tournament_config(
            tournament_type="SPEED_FOCUS",
            custom_config={"tournament_delta_multiplier": 0.18}
        )
        service = SkillProgressionService(mock_db, config=config)

        # Override applied
        assert service.TOURNAMENT_DELTA_MULTIPLIER == 0.18
        # Template value preserved
        assert service.TOURNAMENT_MAX_CONTRIBUTION == 20.0


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_delta_application(self, default_service):
        """Test applying zero delta"""
        skills = {
            "speed": {
                "current_level": 80.0,
                "baseline": 80.0,
                "total_delta": 0.0,
                "tournament_delta": 0.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        result = default_service._apply_skill_delta(
            skills, "speed", 0.0, source="tournament"
        )

        assert result["speed"]["current_level"] == 80.0
        assert result["speed"]["tournament_delta"] == 0.0

    def test_new_skill_initialization(self, default_service):
        """Test initializing a new skill that doesn't exist"""
        skills = {}

        result = default_service._apply_skill_delta(
            skills, "positioning", 2.0, source="tournament"
        )

        # Should initialize with default baseline (50.0)
        assert "positioning" in result
        assert result["positioning"]["baseline"] == 50.0
        assert result["positioning"]["tournament_delta"] == 2.0
        assert result["positioning"]["current_level"] == 52.0

    def test_multiple_deltas_same_skill(self, default_service):
        """Test applying multiple deltas to same skill"""
        skills = {
            "speed": {
                "current_level": 80.0,
                "baseline": 80.0,
                "total_delta": 0.0,
                "tournament_delta": 0.0,
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 0,
                "assessment_count": 0
            }
        }

        # Apply tournament delta
        skills = default_service._apply_skill_delta(
            skills, "speed", 2.0, source="tournament"
        )

        # Apply assessment delta
        skills = default_service._apply_skill_delta(
            skills, "speed", 1.5, source="assessment"
        )

        # Both should accumulate
        assert skills["speed"]["tournament_delta"] == 2.0
        assert skills["speed"]["assessment_delta"] == 1.5
        assert skills["speed"]["total_delta"] == 3.5
        assert skills["speed"]["current_level"] == 83.5  # 80 + 2.0 + 1.5

    def test_cap_already_exceeded(self, default_service):
        """Test applying delta when cap is already exceeded (no change)"""
        skills = {
            "speed": {
                "current_level": 95.0,
                "baseline": 80.0,
                "total_delta": 15.0,
                "tournament_delta": 15.0,  # Already at cap
                "assessment_delta": 0.0,
                "last_updated": "2026-01-25T10:00:00Z",
                "tournament_count": 10,
                "assessment_count": 0
            }
        }

        # Try to apply more tournament delta
        result = default_service._apply_skill_delta(
            skills, "speed", 5.0, source="tournament"
        )

        # Should remain at cap
        assert result["speed"]["tournament_delta"] == 15.0
        assert result["speed"]["current_level"] == 95.0
        # Count should still increment (tournament participated)
        assert result["speed"]["tournament_count"] == 11


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
