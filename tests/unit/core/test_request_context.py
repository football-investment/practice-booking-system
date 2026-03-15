"""
Unit tests — app/core/request_context.py + log correlation
===========================================================

Tests
-----
  RC-01  get_request_id() returns empty string when no ID is set
  RC-02  request_id_var.set() makes get_request_id() return the new value
  RC-03  get_operation_id() returns empty string by default
  RC-04  set_operation_id() sets and returns the operation ID
  RC-05  set_operation_id(None) auto-generates a non-empty hex string
  RC-06  structured_log includes request_id in log output when set
  RC-07  structured_log omits request_id when empty (clean test output)
  RC-08  structured_log includes both request_id and operation_id when both set
  RC-09  request_id_var is the same object imported from middleware.logging
"""
from __future__ import annotations

import logging
import pytest

from app.core.request_context import (
    get_request_id,
    get_operation_id,
    set_operation_id,
    request_id_var,
    operation_id_var,
)
from app.core.structured_log import log_event


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRequestContext:

    def test_rc01_get_request_id_default_empty(self):
        """RC-01: get_request_id() returns empty string without set()."""
        token = request_id_var.set("")   # explicit reset for isolation
        try:
            assert get_request_id() == ""
        finally:
            request_id_var.reset(token)

    def test_rc02_set_request_id_propagates(self):
        """RC-02: setting request_id_var makes get_request_id() return it."""
        token = request_id_var.set("test-req-abc")
        try:
            assert get_request_id() == "test-req-abc"
        finally:
            request_id_var.reset(token)

    def test_rc03_get_operation_id_default_empty(self):
        """RC-03: get_operation_id() returns empty string without set()."""
        token = operation_id_var.set("")
        try:
            assert get_operation_id() == ""
        finally:
            operation_id_var.reset(token)

    def test_rc04_set_operation_id_explicit(self):
        """RC-04: set_operation_id('myop') stores and returns 'myop'."""
        token = operation_id_var.set("")
        try:
            result = set_operation_id("myop-123")
            assert result == "myop-123"
            assert get_operation_id() == "myop-123"
        finally:
            operation_id_var.reset(token)

    def test_rc05_set_operation_id_auto_generates(self):
        """RC-05: set_operation_id(None) generates a non-empty 12-char hex string."""
        token = operation_id_var.set("")
        try:
            oid = set_operation_id()
            assert len(oid) == 12
            assert oid == oid.lower()
            assert all(c in "0123456789abcdef" for c in oid)
        finally:
            operation_id_var.reset(token)

    def test_rc09_request_id_var_same_object_as_middleware(self):
        """RC-09: middleware.logging imports the same ContextVar from request_context."""
        from app.middleware.logging import request_id_var as mw_var
        assert mw_var is request_id_var


class TestLogCorrelation:
    """Verify that structured_log includes correlation IDs in the emitted string."""

    def _capture_log(self, logger_name: str) -> list[str]:
        """Return a list that will collect log messages from ``logger_name``."""
        messages: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                messages.append(self.format(record))

        handler = _Capture()
        handler.setFormatter(logging.Formatter("%(message)s"))
        log = logging.getLogger(logger_name)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)
        return messages, log, handler

    def test_rc06_structured_log_includes_request_id(self):
        """RC-06: log_event includes request_id= when request_id_var is set."""
        messages, logger, handler = self._capture_log("test.rc06")
        req_token = request_id_var.set("req-abc123")
        try:
            log_event(logger, "test_event", user_id=1)
            assert any("request_id=req-abc123" in m for m in messages), (
                f"request_id not found in: {messages}"
            )
        finally:
            request_id_var.reset(req_token)
            logger.removeHandler(handler)

    def test_rc07_structured_log_omits_request_id_when_empty(self):
        """RC-07: log_event omits request_id= when ContextVar is empty."""
        messages, logger, handler = self._capture_log("test.rc07")
        req_token = request_id_var.set("")
        try:
            log_event(logger, "test_event", user_id=1)
            assert not any("request_id" in m for m in messages), (
                f"request_id should not appear; got: {messages}"
            )
        finally:
            request_id_var.reset(req_token)
            logger.removeHandler(handler)

    def test_rc08_structured_log_includes_both_ids_when_set(self):
        """RC-08: log_event includes both request_id and operation_id when both set."""
        messages, logger, handler = self._capture_log("test.rc08")
        req_token = request_id_var.set("req-xyz")
        op_token = operation_id_var.set("op-12345")
        try:
            log_event(logger, "reward_awarded", xp=50)
            assert any(
                "request_id=req-xyz" in m and "operation_id=op-12345" in m
                for m in messages
            ), f"Both IDs not found in: {messages}"
        finally:
            request_id_var.reset(req_token)
            operation_id_var.reset(op_token)
            logger.removeHandler(handler)
