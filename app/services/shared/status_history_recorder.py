"""
Status History Recording Utility

Provides centralized status change recording functionality.
Eliminates 2 duplicated implementations (instructor_assignment.py, lifecycle.py).

Usage:
    from app.services.shared.status_history_recorder import StatusHistoryRecorder

    recorder = StatusHistoryRecorder(db)
    recorder.record_status_change(
        tournament_id=123,
        old_status="DRAFT",
        new_status="IN_PROGRESS",
        changed_by=user_id,
        reason="Approved by admin"
    )
"""

import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any


class StatusHistoryRecorder:
    """
    Centralized status history recording.

    Eliminates duplicated implementations in:
    - instructor_assignment.py (record_status_change function)
    - lifecycle.py (record_status_change function)
    """

    def __init__(self, db: Session):
        """
        Initialize recorder with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def record_status_change(
        self,
        tournament_id: int,
        old_status: Optional[str],
        new_status: str,
        changed_by: int,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a status change in tournament_status_history table.

        Args:
            tournament_id: Tournament ID
            old_status: Previous status (None for creation)
            new_status: New status
            changed_by: User ID who made the change
            reason: Optional reason for change
            metadata: Optional metadata dict

        Note:
            This method does NOT commit the transaction.
            The calling code should handle transaction management.

        Example:
            >>> recorder = StatusHistoryRecorder(db)
            >>> recorder.record_status_change(
            ...     tournament_id=123,
            ...     old_status="DRAFT",
            ...     new_status="IN_PROGRESS",
            ...     changed_by=user_id,
            ...     reason="Tournament approved"
            ... )
            >>> db.commit()  # Calling code commits
        """
        # Convert metadata dict to JSON string if provided
        metadata_json = json.dumps(metadata) if metadata is not None else None

        self.db.execute(
            text("""
            INSERT INTO tournament_status_history
            (tournament_id, old_status, new_status, changed_by, reason, extra_metadata)
            VALUES (:tournament_id, :old_status, :new_status, :changed_by, :reason, :extra_metadata)
            """),
            {
                "tournament_id": tournament_id,
                "old_status": old_status,
                "new_status": new_status,
                "changed_by": changed_by,
                "reason": reason,
                "extra_metadata": metadata_json
            }
        )

    def record_creation(
        self,
        tournament_id: int,
        created_by: int,
        initial_status: str = "DRAFT",
        reason: Optional[str] = None
    ) -> None:
        """
        Record tournament creation (old_status = None).

        Args:
            tournament_id: Tournament ID
            created_by: User ID who created the tournament
            initial_status: Initial status (default: DRAFT)
            reason: Optional reason

        Example:
            >>> recorder.record_creation(
            ...     tournament_id=123,
            ...     created_by=user_id,
            ...     initial_status="DRAFT"
            ... )
        """
        self.record_status_change(
            tournament_id=tournament_id,
            old_status=None,
            new_status=initial_status,
            changed_by=created_by,
            reason=reason or "Tournament created"
        )

    def record_transition(
        self,
        tournament_id: int,
        old_status: str,
        new_status: str,
        changed_by: int,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record status transition (both old and new status specified).

        Alias for record_status_change with clearer semantics.

        Args:
            tournament_id: Tournament ID
            old_status: Previous status
            new_status: New status
            changed_by: User ID who made the change
            reason: Optional reason
            metadata: Optional metadata

        Example:
            >>> recorder.record_transition(
            ...     tournament_id=123,
            ...     old_status="IN_PROGRESS",
            ...     new_status="COMPLETED",
            ...     changed_by=user_id,
            ...     reason="All matches finished"
            ... )
        """
        self.record_status_change(
            tournament_id=tournament_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
            metadata=metadata
        )


# Export main class
__all__ = ["StatusHistoryRecorder"]
