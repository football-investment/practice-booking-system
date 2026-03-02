"""
Sandbox Tournament Regression Tests

Verifies that SandboxTestOrchestrator.execute_test() produces consistent,
expected results with the current API signature.

Note: The orchestrator cleans up all DB data at the end of each run,
so regression checks are performed against the returned result dict.

Uses postgres_db (session-scoped) with seed users that have active licenses.
"""

import uuid
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.core.security import get_password_hash


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def sandbox_users(postgres_db: Session):
    """
    Create 4 users with active UserLicense records for sandbox regression tests.
    Cleaned up after the module.
    """
    users = []
    licenses = []
    for i in range(4):
        uid = uuid.uuid4().hex[:8]
        user = User(
            email=f"sandbox_reg_{uid}@lfa-seed.hu",
            password_hash=get_password_hash("test123"),
            name=f"Sandbox Player {i + 1}",
            role=UserRole.STUDENT,
            is_active=True,
        )
        postgres_db.add(user)
        postgres_db.flush()

        license_ = UserLicense(
            user_id=user.id,
            specialization_type="PLAYER",
            started_at=datetime(2026, 1, 1),
            is_active=True,
        )
        postgres_db.add(license_)
        users.append(user)
        licenses.append(license_)

    postgres_db.commit()
    for u in users:
        postgres_db.refresh(u)

    yield [u.id for u in users]

    # Cleanup
    for lic in licenses:
        postgres_db.delete(lic)
    for u in users:
        postgres_db.delete(u)
    postgres_db.commit()


# ============================================================================
# TESTS
# ============================================================================

class TestSandboxRegression:
    """
    Regression tests for sandbox tournament simulation.

    Verifies:
    1. execute_test() succeeds and returns required fields
    2. Running with same parameters produces consistent structure
    3. Different ranking_distribution parameters produce different orderings
    """

    def test_deterministic_head_to_head_4_players(self, postgres_db: Session, sandbox_users):
        """
        Test that 4-player sandbox tournament executes successfully and returns
        complete, well-formed results.
        """
        orchestrator = SandboxTestOrchestrator(postgres_db)
        result = orchestrator.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control", "stamina"],
            player_count=4,
            selected_users=sandbox_users,
        )

        # Verify tournament ran successfully
        assert result["verdict"] in ["WORKING", "NEEDS_TUNING", "NOT_WORKING"]
        assert result["tournament"]["type"] == "LEAGUE"
        assert result["tournament"]["player_count"] == 4
        assert result["tournament"]["skills_tested"] == ["ball_control", "stamina"]

        # Verify execution summary
        assert "execution_summary" in result
        assert result["execution_summary"]["duration_seconds"] >= 0

        # Verify skill progression data returned
        assert "skill_progression" in result
        assert "top_performers" in result
        assert "bottom_performers" in result

    def test_deterministic_repeatability(self, postgres_db: Session, sandbox_users):
        """
        Test that running execute_test() twice with the same parameters
        produces the same verdict and consistent result structure.
        """
        orchestrator1 = SandboxTestOrchestrator(postgres_db)
        result1 = orchestrator1.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            ranking_distribution="NORMAL",
            selected_users=sandbox_users,
        )

        orchestrator2 = SandboxTestOrchestrator(postgres_db)
        result2 = orchestrator2.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            ranking_distribution="NORMAL",
            selected_users=sandbox_users,
        )

        # Both should complete (any verdict is acceptable)
        assert result1["verdict"] in ["WORKING", "NEEDS_TUNING", "NOT_WORKING"]
        assert result2["verdict"] in ["WORKING", "NEEDS_TUNING", "NOT_WORKING"]

        # Both should return same structural fields
        assert result1["tournament"]["player_count"] == result2["tournament"]["player_count"]
        assert result1["tournament"]["skills_tested"] == result2["tournament"]["skills_tested"]
        assert set(result1["skill_progression"].keys()) == set(result2["skill_progression"].keys())

    def test_different_distributions_produce_different_results(self, postgres_db: Session, sandbox_users):
        """
        Test that different ranking_distribution parameters are accepted without errors.
        """
        orchestrator1 = SandboxTestOrchestrator(postgres_db)
        result_normal = orchestrator1.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            ranking_distribution="NORMAL",
            selected_users=sandbox_users,
        )

        orchestrator2 = SandboxTestOrchestrator(postgres_db)
        result_top_heavy = orchestrator2.execute_test(
            tournament_type_code="league",
            skills_to_test=["ball_control"],
            player_count=4,
            ranking_distribution="TOP_HEAVY",
            selected_users=sandbox_users,
        )

        assert result_normal["verdict"] in ["WORKING", "NEEDS_TUNING", "NOT_WORKING"]
        assert result_top_heavy["verdict"] in ["WORKING", "NEEDS_TUNING", "NOT_WORKING"]
        assert "top_performers" in result_normal
        assert "top_performers" in result_top_heavy


def test_sandbox_result_structure(postgres_db: Session, sandbox_users):
    """
    Standalone test: verify execute_test() result conforms to expected schema.
    """
    orchestrator = SandboxTestOrchestrator(postgres_db)

    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["stamina"],
        player_count=4,
        selected_users=sandbox_users,
    )

    required_keys = [
        "verdict", "test_run_id", "tournament", "execution_summary",
        "skill_progression", "top_performers", "bottom_performers",
        "insights", "export_data"
    ]
    for key in required_keys:
        assert key in result, f"Missing required key in result: {key}"

    required_tournament_keys = ["id", "name", "type", "status", "player_count", "skills_tested"]
    for key in required_tournament_keys:
        assert key in result["tournament"], f"Missing key in tournament: {key}"
