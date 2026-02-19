"""
Tournament Service Protocols

Phase 2.2: Service Layer Isolation
Defines abstract protocols (interfaces) for tournament services to enforce
clear contracts and enable dependency injection.

Using Python Protocol (PEP 544) for structural subtyping instead of ABC
for maximum flexibility and easier testing.
"""

from typing import Protocol, Optional, Dict, Any, List
from app.models.session import Session as SessionModel
from app.models.semester import Semester


class TournamentProgressionService(Protocol):
    """
    Protocol for tournament progression services.

    Defines the contract for handling automatic tournament progression
    (e.g., knockout bracket advancement, group stage completion).

    Phase 2.2 Design: Separates progression into two phases:
    1. calculate_progression() - Read-only, deterministic planning
    2. execute_progression() - Write-only, database mutation

    This separation enables:
    - Pure function testing (calculate without database)
    - Clear side-effect boundaries
    - Transactional safety (plan before commit)
    """

    def can_progress(
        self,
        session: SessionModel,
        tournament: Semester
    ) -> bool:
        """
        Check if a completed session can trigger progression.

        This is a fast guard check before expensive operations.

        Args:
            session: Completed session
            tournament: Tournament context

        Returns:
            True if progression should be evaluated, False otherwise

        Example:
            >>> service.can_progress(session, tournament)
            True  # session is in knockout phase
        """
        ...

    def calculate_progression(
        self,
        session: SessionModel,
        tournament: Semester,
        game_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate what progression should occur (READ-ONLY operation).

        This method is PURE - no side effects, no database writes.
        It only queries existing state and returns a progression plan.

        Args:
            session: Completed session that triggered progression check
            tournament: Tournament context
            game_results: Match results with winner/loser info

        Returns:
            Progression plan dict with structure:
            {
                "action": "create_next_round" | "wait" | "complete",
                "message": "Human-readable status",
                "sessions_to_create": [
                    {
                        "title": "Final",
                        "participant_user_ids": [10, 12],
                        "tournament_round": 2,
                        "tournament_phase": TournamentPhase.KNOCKOUT,
                        ...
                    }
                ],
                "metadata": {...}  # Optional additional context
            }

            Returns None if no progression needed (e.g., non-knockout session)

        Example:
            >>> plan = service.calculate_progression(semi_final, tournament, results)
            >>> plan["action"]
            "create_next_round"
            >>> len(plan["sessions_to_create"])
            1  # Final match
        """
        ...

    def execute_progression(
        self,
        progression_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the progression plan (WRITE operation).

        This is the ONLY method that modifies database state.
        It takes the output of calculate_progression() and creates
        the planned sessions.

        Args:
            progression_plan: Output from calculate_progression()

        Returns:
            Execution result with structure:
            {
                "success": True,
                "message": "✅ Created 1 next-round matches",
                "created_sessions": [
                    {
                        "session_id": 123,
                        "title": "Final",
                        "participants": [10, 12]
                    }
                ]
            }

        Raises:
            ValueError: If progression_plan is invalid
            IntegrityError: If database constraints violated

        Example:
            >>> result = service.execute_progression(plan)
            >>> result["success"]
            True
            >>> result["created_sessions"][0]["session_id"]
            123
        """
        ...


class ProgressionPlanValidator(Protocol):
    """
    Protocol for validating progression plans before execution.

    Optional validation layer to ensure progression plans are well-formed
    before attempting database writes.
    """

    def validate_plan(
        self,
        plan: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a progression plan structure.

        Args:
            plan: Progression plan from calculate_progression()

        Returns:
            (is_valid, error_message) tuple
            - (True, None) if valid
            - (False, "error description") if invalid

        Example:
            >>> validator.validate_plan(plan)
            (True, None)
        """
        ...
