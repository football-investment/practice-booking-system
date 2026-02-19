"""
Tournament Status History Model
Audit log for tracking tournament status changes
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..database import Base


class TournamentStatusHistory(Base):
    """
    Audit log for tournament status transitions

    Tracks every status change with timestamp, reason, and metadata
    for compliance and debugging purposes.
    """
    __tablename__ = "tournament_status_history"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    old_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)  # Additional context (e.g., instructor_id, application_id)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("(NOW() AT TIME ZONE 'utc')")
    )

    # Relationships
    tournament = relationship("Semester", foreign_keys=[tournament_id])
    changed_by_user = relationship("User", foreign_keys=[changed_by])

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "tournament_id": self.tournament_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "reason": self.reason,
            "extra_metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
