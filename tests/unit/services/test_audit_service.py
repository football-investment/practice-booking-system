"""
Sprint P5 — audit_service.py
==============================
Target: ≥85% stmt, ≥75% branch

Uses a self-referential fluent-interface mock so that every chained
.filter() / .order_by() / .offset() / .limit() / .group_by() call
returns the same mock object.  This means any number of conditional
filter appends is handled transparently.

Covers:
  log                  — add/commit/refresh, all fields, minimal fields
  get_user_logs        — no filters / start_date / end_date / action / combined
  get_logs_by_action   — no filters / start_date / end_date / both
  get_resource_logs    — basic call + custom pagination
  get_recent_logs      — default hours / custom hours
  get_failed_logins    — basic / custom params
  get_logs_by_ip       — basic / custom hours
  get_security_events  — basic / custom params
  get_statistics       — no filters / start_date / end_date / both + return shape
  search_logs          — no filters / each optional filter / all combined
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog, AuditAction


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fluent_db(
    *,
    all_result=None,
    count_result=0,
    scalar_result=None,
    action_counts=None,
) -> MagicMock:
    """
    Build a fluent-interface DB mock.

    Every query-chain method (filter, order_by, offset, limit, group_by)
    returns the same mock `q`, so any chain depth is handled without
    manual chaining setup.
    """
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.group_by.return_value = q
    q.whereclause = None           # used in get_statistics date-filter branch
    q.all.return_value = all_result or []
    q.count.return_value = count_result
    q.scalar.return_value = scalar_result

    db = MagicMock()
    db.query.return_value = q
    return db


def _svc(db=None) -> AuditService:
    return AuditService(db or MagicMock())


# ── log ───────────────────────────────────────────────────────────────────────

class TestLog:
    def test_log_adds_commits_and_refreshes(self):
        db = _fluent_db()
        svc = _svc(db)
        entry = svc.log(action="LOGIN", user_id=42)
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_log_returns_audit_log_instance(self):
        db = _fluent_db()
        svc = _svc(db)
        entry = svc.log(action="LOGIN")
        assert isinstance(entry, AuditLog)

    def test_log_stores_action(self):
        db = _fluent_db()
        entry = _svc(db).log(action="USER_CREATED", user_id=42)
        assert entry.action == "USER_CREATED"
        assert entry.user_id == 42

    def test_log_with_all_optional_fields(self):
        db = _fluent_db()
        entry = _svc(db).log(
            action="ADMIN_ACCESS",
            user_id=7,
            resource_type="user",
            resource_id=99,
            details={"note": "test"},
            ip_address="10.0.0.1",
            user_agent="pytest/1.0",
            request_method="POST",
            request_path="/api/v1/admin",
            status_code=200,
        )
        assert entry.resource_type == "user"
        assert entry.resource_id == 99
        assert entry.ip_address == "10.0.0.1"
        assert entry.status_code == 200

    def test_log_with_minimal_fields_no_error(self):
        db = _fluent_db()
        entry = _svc(db).log(action="LOGOUT")
        assert entry.action == "LOGOUT"
        assert entry.user_id is None


# ── get_user_logs ─────────────────────────────────────────────────────────────

class TestGetUserLogs:
    """Covers all optional filter branches (start_date / end_date / action)."""

    def _log(self):
        return MagicMock(spec=AuditLog)

    def test_no_filters_returns_results(self):
        expected = [self._log()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_user_logs(user_id=42)
        assert result == expected

    def test_with_start_date_still_returns_results(self):
        expected = [self._log()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_user_logs(
            user_id=42, start_date=datetime(2026, 1, 1)
        )
        assert result == expected

    def test_with_end_date_still_returns_results(self):
        expected = [self._log()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_user_logs(
            user_id=42, end_date=datetime(2026, 12, 31)
        )
        assert result == expected

    def test_with_action_filter(self):
        expected = [self._log()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_user_logs(user_id=42, action="LOGIN")
        assert result == expected

    def test_all_filters_combined(self):
        expected = [self._log(), self._log()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_user_logs(
            user_id=42,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
            action="LOGIN",
            limit=50,
            offset=10,
        )
        assert result == expected

    def test_empty_results_returns_empty_list(self):
        db = _fluent_db(all_result=[])
        assert _svc(db).get_user_logs(user_id=42) == []


# ── get_logs_by_action ────────────────────────────────────────────────────────

class TestGetLogsByAction:
    def test_no_date_filters(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_logs_by_action(action="LOGIN")
        assert result == expected

    def test_with_start_date(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).get_logs_by_action(
            action="LOGIN", start_date=datetime(2026, 1, 1)
        )
        assert result == []

    def test_with_end_date(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).get_logs_by_action(
            action="LOGOUT", end_date=datetime(2026, 12, 31)
        )
        assert result == []

    def test_both_dates_with_pagination(self):
        expected = [MagicMock(), MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_logs_by_action(
            action="LOGIN",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
            limit=10,
            offset=5,
        )
        assert result == expected


# ── get_resource_logs ─────────────────────────────────────────────────────────

class TestGetResourceLogs:
    def test_returns_results(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_resource_logs(resource_type="user", resource_id=99)
        assert result == expected

    def test_custom_limit_and_offset(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).get_resource_logs(
            resource_type="license", resource_id=5, limit=10, offset=20
        )
        assert result == []


# ── get_recent_logs ───────────────────────────────────────────────────────────

class TestGetRecentLogs:
    def test_default_24_hours(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_recent_logs()
        assert result == expected

    def test_custom_hours(self):
        expected = [MagicMock(), MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_recent_logs(hours=48, limit=50)
        assert result == expected


# ── get_failed_logins ─────────────────────────────────────────────────────────

class TestGetFailedLogins:
    def test_default_params(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_failed_logins()
        assert result == expected

    def test_custom_hours_and_limit(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).get_failed_logins(hours=1, limit=10)
        assert result == []


# ── get_logs_by_ip ────────────────────────────────────────────────────────────

class TestGetLogsByIP:
    def test_default_hours(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_logs_by_ip(ip_address="192.168.1.1")
        assert result == expected

    def test_custom_hours(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).get_logs_by_ip(ip_address="10.0.0.1", hours=1, limit=5)
        assert result == []


# ── get_security_events ───────────────────────────────────────────────────────

class TestGetSecurityEvents:
    def test_default_params(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).get_security_events()
        assert result == expected

    def test_custom_window(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).get_security_events(hours=72, limit=200)
        assert result == []


# ── get_statistics ────────────────────────────────────────────────────────────

class TestGetStatistics:
    def test_no_date_filters_returns_all_keys(self):
        action_counts_rows = [("LOGIN", 10), ("LOGOUT", 5)]
        db = _fluent_db(
            count_result=15,
            scalar_result=3,
            all_result=action_counts_rows,
        )
        result = _svc(db).get_statistics()
        assert "total_logs" in result
        assert "unique_users" in result
        assert "failed_logins" in result
        assert "action_counts" in result
        assert result["start_date"] is None
        assert result["end_date"] is None

    def test_action_counts_dict_shape(self):
        action_counts_rows = [("LOGIN", 8), ("LOGOUT", 2)]
        db = _fluent_db(count_result=10, all_result=action_counts_rows)
        result = _svc(db).get_statistics()
        assert result["action_counts"] == {"LOGIN": 8, "LOGOUT": 2}

    def test_with_start_date_propagated(self):
        db = _fluent_db(count_result=5, all_result=[])
        start = datetime(2026, 1, 1)
        result = _svc(db).get_statistics(start_date=start)
        assert result["start_date"] == start

    def test_with_end_date_propagated(self):
        db = _fluent_db(count_result=3, all_result=[])
        end = datetime(2026, 12, 31)
        result = _svc(db).get_statistics(end_date=end)
        assert result["end_date"] == end

    def test_both_dates_propagated(self):
        db = _fluent_db(count_result=7, all_result=[])
        start = datetime(2026, 1, 1)
        end = datetime(2026, 3, 31)
        result = _svc(db).get_statistics(start_date=start, end_date=end)
        assert result["start_date"] == start
        assert result["end_date"] == end

    def test_empty_action_counts(self):
        db = _fluent_db(count_result=0, all_result=[])
        result = _svc(db).get_statistics()
        assert result["action_counts"] == {}


# ── search_logs ───────────────────────────────────────────────────────────────

class TestSearchLogs:
    """Covers every optional filter branch in search_logs."""

    def test_no_filters_returns_all(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).search_logs()
        assert result == expected

    def test_filter_by_user_id(self):
        db = _fluent_db(all_result=[])
        result = _svc(db).search_logs(user_id=42)
        assert result == []

    def test_filter_by_action(self):
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(action="LOGIN")

    def test_filter_by_resource_type(self):
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(resource_type="license")

    def test_filter_by_resource_id(self):
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(resource_id=5)

    def test_filter_by_ip_address(self):
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(ip_address="10.0.0.1")

    def test_filter_by_start_date(self):
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(start_date=datetime(2026, 1, 1))

    def test_filter_by_end_date(self):
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(end_date=datetime(2026, 12, 31))

    def test_all_filters_combined(self):
        expected = [MagicMock()]
        db = _fluent_db(all_result=expected)
        result = _svc(db).search_logs(
            user_id=42,
            action="LOGIN",
            resource_type="user",
            resource_id=99,
            ip_address="10.0.0.1",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
            limit=25,
            offset=5,
        )
        assert result == expected

    def test_user_id_zero_still_filtered(self):
        """user_id=0 is not None → filter IS applied."""
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(user_id=0)
        # Verify .filter was called (user_id is not None branch taken)
        db.query.return_value.filter.assert_called()

    def test_resource_id_zero_still_filtered(self):
        """resource_id=0 is not None → filter IS applied."""
        db = _fluent_db(all_result=[])
        _svc(db).search_logs(resource_id=0)
        db.query.return_value.filter.assert_called()
