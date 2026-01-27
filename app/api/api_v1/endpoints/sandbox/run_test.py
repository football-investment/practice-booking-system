"""
Sandbox Test Endpoint

POST /api/v1/sandbox/run-test
Runs end-to-end sandbox tournament test
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response schemas
class TestConfig(BaseModel):
    """Optional test configuration"""
    performance_variation: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")
    ranking_distribution: str = Field(default="NORMAL", pattern="^(NORMAL|TOP_HEAVY|BOTTOM_HEAVY)$")


class RunTestRequest(BaseModel):
    """Request schema for sandbox test"""
    tournament_type: str = Field(..., description="Tournament type code (league, knockout, hybrid)")
    skills_to_test: list[str] = Field(..., min_items=1, max_items=4, description="Skills to test (1-4)")
    player_count: int = Field(..., ge=4, le=16, description="Number of synthetic players (4-16)")
    test_config: Optional[TestConfig] = Field(default_factory=TestConfig)


class RunTestResponse(BaseModel):
    """Response schema matching API contract"""
    verdict: str
    test_run_id: str
    tournament: dict
    execution_summary: dict
    skill_progression: dict
    top_performers: list[dict]
    bottom_performers: list[dict]
    insights: list[dict]
    export_data: dict


@router.post("/run-test", response_model=RunTestResponse, status_code=status.HTTP_200_OK)
def run_sandbox_test(
    request: RunTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Run sandbox tournament test

    Creates temporary tournament, enrolls synthetic participants,
    generates rankings, distributes rewards, and returns verdict.

    **Authorization**: Admin only

    **Parameters**:
    - tournament_type: Tournament format (league, knockout, hybrid)
    - skills_to_test: List of skills to validate (1-4 skills)
    - player_count: Number of synthetic players (4-16)
    - test_config: Optional configuration (performance variation, ranking distribution)

    **Returns**: Complete test results with verdict, skill progression, and performers
    """
    logger.info(
        f"🧪 Sandbox test requested by admin {current_user.email}: "
        f"type={request.tournament_type}, players={request.player_count}, "
        f"skills={request.skills_to_test}"
    )

    # Validate tournament type exists
    from app.models.tournament_type import TournamentType

    tournament_type = db.query(TournamentType).filter(
        TournamentType.code == request.tournament_type
    ).first()

    if not tournament_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tournament type: {request.tournament_type}. Must be one of: league, knockout, hybrid"
        )

    # Validate player count against tournament type constraints
    is_valid, error_msg = tournament_type.validate_player_count(request.player_count)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Validate skills (basic check - could be expanded)
    valid_skills = ["passing", "dribbling", "shooting", "defending", "physical", "pace"]
    for skill in request.skills_to_test:
        if skill not in valid_skills:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid skill name: {skill}. Must be one of: {', '.join(valid_skills)}"
            )

    # Execute test
    try:
        orchestrator = SandboxTestOrchestrator(db)

        result = orchestrator.execute_test(
            tournament_type_code=request.tournament_type,
            skills_to_test=request.skills_to_test,
            player_count=request.player_count,
            performance_variation=request.test_config.performance_variation,
            ranking_distribution=request.test_config.ranking_distribution
        )

        logger.info(
            f"✅ Sandbox test completed: verdict={result['verdict']}, "
            f"test_run_id={result['test_run_id']}"
        )

        return result

    except ValueError as e:
        # Business logic errors (invalid config, constraints, etc.)
        logger.error(f"❌ Sandbox test validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected errors - return NOT_WORKING verdict
        logger.error(f"❌ Sandbox test execution failed: {e}", exc_info=True)

        # If result is already a NOT_WORKING verdict dict, return it
        if isinstance(e, dict) and e.get("verdict") == "NOT_WORKING":
            return e

        # Otherwise, build error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "verdict": "NOT_WORKING",
                "error": {
                    "stage": "EXECUTION",
                    "message": str(e),
                    "details": repr(e)
                }
            }
        )
