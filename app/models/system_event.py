"""
SystemEvent model — structured business/security event store.

Separate from audit_logs (auto-captured HTTP trail).
System events are deliberately emitted by application logic
and are queryable/resolvable by admins via the Rendszerüzenetek panel.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class SystemEventLevel(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    SECURITY = "SECURITY"


class SystemEventType(str, enum.Enum):
    """Well-known event types.  Add new constants here as features grow."""
    MULTI_CAMPUS_BLOCKED = "MULTI_CAMPUS_BLOCKED"
    MULTI_CAMPUS_OVERRIDE_BLOCKED = "MULTI_CAMPUS_OVERRIDE_BLOCKED"
    # Placeholders for future use:
    FAILED_LOGIN = "FAILED_LOGIN"
    SESSION_COLLISION = "SESSION_COLLISION"
    TOURNAMENT_GENERATION_ERROR = "TOURNAMENT_GENERATION_ERROR"
    DATA_INCONSISTENCY = "DATA_INCONSISTENCY"


class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    level = Column(
        Enum(SystemEventLevel, name="systemeventlevel"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role = Column(String(50), nullable=True)
    payload_json = Column(JSONB, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False, server_default="false")

    # Relationships
    user = relationship("User", backref="system_events", foreign_keys=[user_id])

    # Composite index for rate-limiting queries
    __table_args__ = (
        Index(
            "ix_system_events_user_event_type_created",
            "user_id",
            "event_type",
            "created_at",
        ),
    )
