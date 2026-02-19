"""
SystemEventService — deliberate business/security event store.

Design rules:
  - emit() is idempotent within a 10-minute window:
    same (user_id, event_type) → at most 1 record per 10 minutes.
  - All writes run inside a SAVEPOINT; failure rolls back only the savepoint
    and emits a structured SYSTEM_EVENT_WRITE_FAILED WARNING — the calling
    code (e.g. a 403 guard) is never affected by a write failure.
  - Reads are admin-only and exposed via the /system-events API.
  - Retention: 90 days by default (SYSTEM_EVENT_RETENTION_DAYS env var).
    Call purge_old_events() from a maintenance cron or the admin endpoint.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, delete
from sqlalchemy.orm import Session

from app.models.system_event import SystemEvent, SystemEventLevel

logger = logging.getLogger(__name__)

_RATE_LIMIT_MINUTES = 10

# Retention: keep events for this many days before they can be purged.
# Override via environment variable in production.
_DEFAULT_RETENTION_DAYS = int(os.environ.get("SYSTEM_EVENT_RETENTION_DAYS", "90"))


class SystemEventService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Write ─────────────────────────────────────────────────────────────────

    def emit(
        self,
        level: SystemEventLevel,
        event_type: str,
        *,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[SystemEvent]:
        """
        Persist a system event, honouring the 10-minute rate limit.

        The entire body runs inside a SAVEPOINT so that any DB failure
        (e.g. table not yet migrated, constraint violation) rolls back only
        the savepoint and leaves the outer transaction intact.

        On failure a structured WARNING is emitted with key
        SYSTEM_EVENT_WRITE_FAILED for log-based alerting.

        Returns the newly created SystemEvent, or None if deduplicated/failed.
        """
        # begin_nested() issues SAVEPOINT; rollback() issues ROLLBACK TO SAVEPOINT.
        # This isolates any DB error from the caller's transaction.
        savepoint = self.db.begin_nested()
        try:
            if self._is_rate_limited(user_id, event_type):
                logger.debug(
                    "system_event deduplicated — user_id=%s event_type=%s",
                    user_id,
                    event_type,
                )
                savepoint.commit()
                return None

            event = SystemEvent(
                level=level,
                event_type=event_type,
                user_id=user_id,
                role=role,
                payload_json=payload,
                resolved=False,
            )
            self.db.add(event)
            self.db.flush()
            savepoint.commit()
            return event
        except Exception as exc:
            savepoint.rollback()
            # Structured key makes this grep-able / alertable in production logs.
            logger.warning(
                "SYSTEM_EVENT_WRITE_FAILED — user_id=%s event_type=%s error=%s",
                user_id,
                event_type,
                type(exc).__name__,
                exc_info=True,
            )
            return None

    def _is_rate_limited(self, user_id: Optional[int], event_type: str) -> bool:
        """Return True if a (user_id, event_type) event was written in the last 10 min."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=_RATE_LIMIT_MINUTES)
        exists = (
            self.db.query(SystemEvent.id)
            .filter(
                and_(
                    SystemEvent.user_id == user_id,
                    SystemEvent.event_type == event_type,
                    SystemEvent.created_at >= cutoff,
                )
            )
            .first()
        )
        return exists is not None

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_events(
        self,
        *,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        resolved: Optional[bool] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SystemEvent], int]:
        """
        Return (rows, total_count) with optional filtering.

        Ordered by created_at DESC (newest first).
        total_count reflects the full filtered set (before limit/offset)
        so the UI can calculate pages.
        """
        q = self.db.query(SystemEvent)

        if level is not None:
            q = q.filter(SystemEvent.level == level)
        if event_type is not None:
            q = q.filter(SystemEvent.event_type == event_type)
        if resolved is not None:
            q = q.filter(SystemEvent.resolved == resolved)
        if user_id is not None:
            q = q.filter(SystemEvent.user_id == user_id)

        total = q.count()
        rows = q.order_by(SystemEvent.created_at.desc()).offset(offset).limit(limit).all()
        return rows, total

    # ── Update ────────────────────────────────────────────────────────────────

    def mark_resolved(self, event_id: int) -> Optional[SystemEvent]:
        """Mark a single event as resolved.  Returns the event or None if not found."""
        event = self.db.get(SystemEvent, event_id)
        if event is None:
            return None
        event.resolved = True
        self.db.flush()
        return event

    def mark_unresolved(self, event_id: int) -> Optional[SystemEvent]:
        """Reopen a previously resolved event."""
        event = self.db.get(SystemEvent, event_id)
        if event is None:
            return None
        event.resolved = False
        self.db.flush()
        return event

    # ── Retention / Purge ─────────────────────────────────────────────────────

    def purge_old_events(self, retention_days: Optional[int] = None) -> int:
        """
        Delete events older than `retention_days` days.

        Retention policy: 90 days (default), configurable via
        SYSTEM_EVENT_RETENTION_DAYS environment variable or caller argument.

        Only RESOLVED events are purged — unresolved events are kept
        indefinitely until an admin acts on them.

        Returns the number of deleted rows.
        """
        days = retention_days if retention_days is not None else _DEFAULT_RETENTION_DAYS
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

        result = self.db.execute(
            delete(SystemEvent).where(
                and_(
                    SystemEvent.created_at < cutoff,
                    SystemEvent.resolved == True,  # noqa: E712 — SQLAlchemy needs ==
                )
            )
        )
        deleted = result.rowcount
        self.db.flush()

        logger.info(
            "system_events purged — retention_days=%s cutoff=%s deleted=%s",
            days,
            cutoff.date().isoformat(),
            deleted,
        )
        return deleted
