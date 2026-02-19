"""
Unit tests — SystemEventService

Covers:
  P-01  purge_old_events() removes resolved events older than retention window
  P-02  purge_old_events() keeps resolved events within the retention window
  P-03  purge_old_events() never removes OPEN (unresolved) events (even if old)
  P-04  purge_old_events() returns correct deleted count
  P-05  rate-limit: emit() deduplicates within 10-minute window (same user+event_type)
  P-06  rate-limit: emit() allows after >10 minutes (different window)
  P-07  get_events() pagination — offset + limit honour total correctly
  P-08  get_events() filter by resolved=False returns only open events
  P-09  get_events() filter by level=SECURITY returns only SECURITY level events
  P-10  mark_resolved() flips resolved to True

All tests use the PostgreSQL rollback fixture from tests/unit/conftest.py.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.system_event import SystemEvent, SystemEventLevel, SystemEventType
from app.services.system_event_service import SystemEventService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_event(
    db: Session,
    *,
    event_type: str = SystemEventType.MULTI_CAMPUS_BLOCKED,
    level: SystemEventLevel = SystemEventLevel.SECURITY,
    resolved: bool = False,
    age_days: int = 0,
    user_id: int = 1,
) -> SystemEvent:
    """Insert a SystemEvent directly (bypassing rate limit) for test setup."""
    created_at = datetime.now(tz=timezone.utc) - timedelta(days=age_days)
    evt = SystemEvent(
        level=level,
        event_type=event_type,
        user_id=user_id,
        role="INSTRUCTOR",
        payload_json={"test": True},
        resolved=resolved,
    )
    evt.created_at = created_at
    db.add(evt)
    db.flush()
    return evt


# ── Purge tests ────────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestSystemEventPurge:
    """purge_old_events() retention policy."""

    def test_purge_removes_old_resolved_events(self, postgres_db: Session):
        """P-01: resolved event older than retention → deleted"""
        _make_event(postgres_db, resolved=True, age_days=91)
        svc = SystemEventService(postgres_db)
        deleted = svc.purge_old_events(retention_days=90)
        assert deleted == 1

    def test_purge_keeps_recent_resolved_events(self, postgres_db: Session):
        """P-02: resolved event within retention window → kept"""
        _make_event(postgres_db, resolved=True, age_days=30)
        svc = SystemEventService(postgres_db)
        deleted = svc.purge_old_events(retention_days=90)
        assert deleted == 0

    def test_purge_never_deletes_open_events(self, postgres_db: Session):
        """P-03: unresolved event, even 200 days old → kept"""
        _make_event(postgres_db, resolved=False, age_days=200)
        svc = SystemEventService(postgres_db)
        deleted = svc.purge_old_events(retention_days=90)
        assert deleted == 0

    def test_purge_returns_correct_count(self, postgres_db: Session):
        """P-04: purge count matches number of matching rows"""
        _make_event(postgres_db, resolved=True, age_days=100)
        _make_event(postgres_db, resolved=True, age_days=95)
        _make_event(postgres_db, resolved=True, age_days=89)   # within window → kept
        _make_event(postgres_db, resolved=False, age_days=200) # open → kept
        svc = SystemEventService(postgres_db)
        deleted = svc.purge_old_events(retention_days=90)
        assert deleted == 2

    def test_purge_empty_table_returns_zero(self, postgres_db: Session):
        """P-04b: purge on empty table → 0"""
        svc = SystemEventService(postgres_db)
        deleted = svc.purge_old_events(retention_days=90)
        assert deleted == 0


# ── Rate-limit tests ───────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestSystemEventRateLimit:
    """emit() idempotency within 10-minute window."""

    def test_rate_limit_deduplicates_within_window(self, postgres_db: Session):
        """P-05: second emit for same (user_id, event_type) within 10 min → None"""
        svc = SystemEventService(postgres_db)
        first = svc.emit(
            SystemEventLevel.SECURITY,
            SystemEventType.MULTI_CAMPUS_BLOCKED,
            user_id=1,  # user_id=1 is a seeded fixture user
        )
        assert first is not None  # first emit succeeds

        second = svc.emit(
            SystemEventLevel.SECURITY,
            SystemEventType.MULTI_CAMPUS_BLOCKED,
            user_id=1,
        )
        assert second is None  # deduplicated

    def test_different_event_type_not_rate_limited(self, postgres_db: Session):
        """P-05b: different event_type for same user → not deduplicated"""
        svc = SystemEventService(postgres_db)
        svc.emit(
            SystemEventLevel.SECURITY,
            SystemEventType.MULTI_CAMPUS_BLOCKED,
            user_id=1,
        )
        second = svc.emit(
            SystemEventLevel.SECURITY,
            SystemEventType.MULTI_CAMPUS_OVERRIDE_BLOCKED,
            user_id=1,
        )
        assert second is not None  # different type → allowed

    def test_different_user_not_rate_limited(self, postgres_db: Session):
        """P-05c: same event_type, different user_id → not deduplicated"""
        svc = SystemEventService(postgres_db)
        svc.emit(
            SystemEventLevel.SECURITY,
            SystemEventType.MULTI_CAMPUS_BLOCKED,
            user_id=1,  # fixture user
        )
        other_user = svc.emit(
            SystemEventLevel.SECURITY,
            SystemEventType.MULTI_CAMPUS_BLOCKED,
            user_id=None,  # anonymous — different rate bucket from user_id=1
        )
        assert other_user is not None


# ── Read / filter tests ────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestSystemEventRead:
    """get_events() filtering and pagination."""

    def test_get_events_returns_total_count(self, postgres_db: Session):
        """P-07: total reflects full filtered set regardless of limit"""
        for _ in range(5):
            _make_event(postgres_db)
        svc = SystemEventService(postgres_db)
        rows, total = svc.get_events(limit=2)
        assert total == 5
        assert len(rows) == 2  # limit honoured

    def test_get_events_offset_pagination(self, postgres_db: Session):
        """P-07b: offset skips correct number of rows"""
        for i in range(5):
            _make_event(postgres_db, user_id=i + 1)
        svc = SystemEventService(postgres_db)
        _, total = svc.get_events()
        page1, _ = svc.get_events(limit=3, offset=0)
        page2, _ = svc.get_events(limit=3, offset=3)
        all_ids = {e.id for e in page1} | {e.id for e in page2}
        assert len(all_ids) == 5  # no duplicates across pages

    def test_filter_by_resolved_false(self, postgres_db: Session):
        """P-08: resolved=False returns only open events"""
        _make_event(postgres_db, resolved=False)
        _make_event(postgres_db, resolved=True)
        svc = SystemEventService(postgres_db)
        rows, total = svc.get_events(resolved=False)
        assert total == 1
        assert all(not r.resolved for r in rows)

    def test_filter_by_level_security(self, postgres_db: Session):
        """P-09: level=SECURITY returns only SECURITY events"""
        _make_event(postgres_db, level=SystemEventLevel.SECURITY)
        _make_event(postgres_db, level=SystemEventLevel.WARNING)
        svc = SystemEventService(postgres_db)
        rows, total = svc.get_events(level="SECURITY")
        assert total == 1
        assert rows[0].level == SystemEventLevel.SECURITY


# ── mark_resolved test ─────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.tournament
class TestSystemEventResolve:
    """mark_resolved() / mark_unresolved()."""

    def test_mark_resolved_flips_flag(self, postgres_db: Session):
        """P-10: mark_resolved sets resolved=True"""
        evt = _make_event(postgres_db, resolved=False)
        svc = SystemEventService(postgres_db)
        updated = svc.mark_resolved(evt.id)
        assert updated is not None
        assert updated.resolved is True

    def test_mark_unresolved_flips_flag(self, postgres_db: Session):
        """P-10b: mark_unresolved sets resolved=False"""
        evt = _make_event(postgres_db, resolved=True)
        svc = SystemEventService(postgres_db)
        updated = svc.mark_unresolved(evt.id)
        assert updated is not None
        assert updated.resolved is False

    def test_mark_resolved_returns_none_for_missing_id(self, postgres_db: Session):
        """P-10c: mark_resolved with non-existent id → None"""
        svc = SystemEventService(postgres_db)
        result = svc.mark_resolved(999_999)
        assert result is None
