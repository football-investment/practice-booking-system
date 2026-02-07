"""
Unit Tests: FootballSkillService.award_skill_points()

Tests the centralized skill reward method in isolation.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.services.football_skill_service import FootballSkillService
from app.models.skill_reward import SkillReward


class TestFootballSkillServiceAwardSkillPoints:
    """Unit tests for FootballSkillService.award_skill_points()"""

    def test_award_skill_points_success(self, postgres_db: Session):
        """Test awarding skill points to a user"""
        service = FootballSkillService(postgres_db)

        (reward, created) = service.award_skill_points(
            user_id=1,
            source_type="TEST_TOURNAMENT",
            source_id=999,
            skill_name="passing",
            points_awarded=10
        )

        assert created is True, "Reward should be marked as created"
        assert reward.id is not None, "Reward should have an ID"
        assert reward.points_awarded == 10
        assert reward.skill_name == "passing"

        # Cleanup
        postgres_db.delete(reward)
        postgres_db.commit()

    def test_award_skill_points_duplicate_protection(self, postgres_db: Session):
        """Test that duplicate (user, source, skill) returns existing reward"""
        service = FootballSkillService(postgres_db)

        # First call - should create
        (reward1, created1) = service.award_skill_points(
            user_id=1,
            source_type="TEST_TOURNAMENT",
            source_id=998,
            skill_name="finishing",
            points_awarded=15
        )

        assert created1 is True
        reward1_id = reward1.id

        # Second call with same (user, source, skill) - should return existing
        (reward2, created2) = service.award_skill_points(
            user_id=1,
            source_type="TEST_TOURNAMENT",  # Same source
            source_id=998,  # Same ID
            skill_name="finishing",  # Same skill
            points_awarded=20  # Different points (doesn't matter)
        )

        assert created2 is False, "Second call should return existing reward"
        assert reward2.id == reward1_id, "Should return same reward"
        assert reward2.points_awarded == 15, "Should have original points, not new ones"

        # Verify only ONE reward in database
        count = postgres_db.query(SkillReward).filter(
            SkillReward.user_id == 1,
            SkillReward.source_type == "TEST_TOURNAMENT",
            SkillReward.source_id == 998,
            SkillReward.skill_name == "finishing"
        ).count()
        assert count == 1, f"Expected 1 reward, found {count}"

        # Cleanup
        postgres_db.delete(reward1)
        postgres_db.commit()

    def test_award_skill_points_different_skills_same_source(self, postgres_db: Session):
        """Test that same user can receive different skill rewards from same source"""
        service = FootballSkillService(postgres_db)

        # Award Passing
        (reward1, created1) = service.award_skill_points(
            user_id=1,
            source_type="TEST_TOURNAMENT",
            source_id=997,
            skill_name="passing",
            points_awarded=10
        )

        # Award Shooting (different skill, same source)
        (reward2, created2) = service.award_skill_points(
            user_id=1,
            source_type="TEST_TOURNAMENT",
            source_id=997,  # Same source
            skill_name="finishing",  # Different skill
            points_awarded=12
        )

        assert created1 is True
        assert created2 is True, "Different skill should create new reward"
        assert reward1.id != reward2.id

        # Cleanup
        postgres_db.delete(reward1)
        postgres_db.delete(reward2)
        postgres_db.commit()

    def test_award_skill_points_validation_invalid_skill(self, postgres_db: Session):
        """Test that invalid skill names are rejected"""
        service = FootballSkillService(postgres_db)

        with pytest.raises(ValueError) as exc_info:
            service.award_skill_points(
                user_id=1,
                source_type="TEST_TOURNAMENT",
                source_id=996,
                skill_name="InvalidSkill",  # Not in VALID_SKILLS
                points_awarded=10
            )

        assert "Invalid skill name" in str(exc_info.value)
        assert "InvalidSkill" in str(exc_info.value)

    def test_award_skill_points_allows_negative_points(self, postgres_db: Session):
        """Test that negative points are allowed (for skill decrease)"""
        service = FootballSkillService(postgres_db)

        # Negative points should work (skill decrease for bottom players)
        (reward, created) = service.award_skill_points(
            user_id=1,
            source_type="TEST_TOURNAMENT",
            source_id=995,
            skill_name="passing",
            points_awarded=-10  # Negative for penalty!
        )

        assert created is True, "Should create reward with negative points"
        assert reward.points_awarded == -10, "Should store negative points"

        # Cleanup
        postgres_db.delete(reward)
        postgres_db.commit()

    def test_award_skill_points_validation_zero_points(self, postgres_db: Session):
        """Test that zero points are rejected"""
        service = FootballSkillService(postgres_db)

        with pytest.raises(ValueError) as exc_info:
            service.award_skill_points(
                user_id=1,
                source_type="TEST_TOURNAMENT",
                source_id=994,
                skill_name="passing",
                points_awarded=0  # Zero!
            )

        assert "Points awarded must be positive" in str(exc_info.value)

    def test_award_skill_points_all_valid_skills(self, postgres_db: Session):
        """Test awarding points for all valid skills"""
        service = FootballSkillService(postgres_db)

        # Get all valid skills
        valid_skills = service.VALID_SKILLS

        assert len(valid_skills) > 0, "Should have at least one valid skill"

        # Try awarding first 3 skills (don't test all to avoid cluttering DB)
        for i, skill_name in enumerate(valid_skills[:3]):
            (reward, created) = service.award_skill_points(
                user_id=1,
                source_type="TEST_ALL_SKILLS",
                source_id=990 + i,
                skill_name=skill_name,
                points_awarded=5
            )

            assert created is True, f"Should create reward for {skill_name}"
            assert reward.skill_name == skill_name

            # Cleanup
            postgres_db.delete(reward)

        postgres_db.commit()

    def test_race_condition_handling(self, postgres_db: Session):
        """
        Test that race condition (concurrent creates) is handled gracefully.
        """
        service = FootballSkillService(postgres_db)

        # First request creates reward
        (reward1, created1) = service.award_skill_points(
            user_id=1,
            source_type="TEST_RACE_SKILL",
            source_id=989,
            skill_name="dribbling",
            points_awarded=8
        )

        assert created1 is True

        # Commit to database
        postgres_db.commit()

        # Second request (simulating race condition) - should get existing
        (reward2, created2) = service.award_skill_points(
            user_id=1,
            source_type="TEST_RACE_SKILL",
            source_id=989,
            skill_name="dribbling",
            points_awarded=10
        )

        assert created2 is False, "Second request should get existing reward"
        assert reward2.id == reward1.id

        # Cleanup
        postgres_db.delete(reward1)
        postgres_db.commit()

    def test_award_skill_points_different_users_same_source(self, postgres_db: Session):
        """Test that different users can receive rewards from same source"""
        service = FootballSkillService(postgres_db)

        # User 2 gets reward
        (reward1, created1) = service.award_skill_points(
            user_id=1,
            source_type="TEST_MULTI_USER",
            source_id=988,
            skill_name="passing",
            points_awarded=10
        )

        # User 3 gets reward (different user, same source+skill)
        (reward2, created2) = service.award_skill_points(
            user_id=4,  # Different user
            source_type="TEST_MULTI_USER",
            source_id=988,  # Same source
            skill_name="passing",  # Same skill
            points_awarded=12
        )

        assert created1 is True
        assert created2 is True, "Different user should create new reward"
        assert reward1.id != reward2.id

        # Cleanup
        postgres_db.delete(reward1)
        postgres_db.delete(reward2)
        postgres_db.commit()

    def test_award_skill_points_different_sources_same_user_skill(self, postgres_db: Session):
        """Test that same user+skill can receive rewards from different sources"""
        service = FootballSkillService(postgres_db)

        # Tournament 1
        (reward1, created1) = service.award_skill_points(
            user_id=1,
            source_type="TOURNAMENT",
            source_id=100,
            skill_name="finishing",
            points_awarded=10
        )

        # Tournament 2 (different source)
        (reward2, created2) = service.award_skill_points(
            user_id=1,
            source_type="TOURNAMENT",
            source_id=101,  # Different source_id
            skill_name="finishing",
            points_awarded=15
        )

        assert created1 is True
        assert created2 is True, "Different source should create new reward"
        assert reward1.id != reward2.id

        # Cleanup
        postgres_db.delete(reward1)
        postgres_db.delete(reward2)
        postgres_db.commit()
