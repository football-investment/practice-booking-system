"""
Unit tests for MatchDurationConfig.normalize_to_utc field_validator.

Covers the Pydantic-level UTC normalisation of checkin_opens_at:
  CHDT-01  naive datetime string  → UTC-aware datetime (value preserved)
  CHDT-02  +02:00 offset string   → UTC equivalent (value shifted)
  CHDT-03  +00:00 (already UTC)   → unchanged
  CHDT-04  None                   → None (null allowed)
"""

import pytest
from datetime import timezone

from app.api.api_v1.endpoints.tournaments.schedule_config import MatchDurationConfig


class TestCheckinOpensAtValidator:

    def test_CHDT_01_naive_string_becomes_utc(self):
        """CHDT-01: naive ISO string has no tzinfo → gets UTC tzinfo, value preserved."""
        m = MatchDurationConfig(checkin_opens_at="2026-06-01T10:00:00")

        assert m.checkin_opens_at is not None
        assert m.checkin_opens_at.tzinfo is not None
        assert m.checkin_opens_at.tzinfo == timezone.utc
        assert m.checkin_opens_at.hour == 10
        assert m.checkin_opens_at.minute == 0

    def test_CHDT_02_offset_converted_to_utc(self):
        """CHDT-02: Budapest CEST (+02:00) shifted to UTC equivalent."""
        m = MatchDurationConfig(checkin_opens_at="2026-06-01T12:00:00+02:00")

        assert m.checkin_opens_at is not None
        assert m.checkin_opens_at.tzinfo == timezone.utc
        assert m.checkin_opens_at.hour == 10   # 12:00+02 → 10:00 UTC
        assert m.checkin_opens_at.minute == 0

    def test_CHDT_03_utc_string_unchanged(self):
        """CHDT-03: already-UTC +00:00 string — value and timezone unchanged."""
        m = MatchDurationConfig(checkin_opens_at="2026-06-01T10:00:00+00:00")

        assert m.checkin_opens_at is not None
        assert m.checkin_opens_at.tzinfo == timezone.utc
        assert m.checkin_opens_at.hour == 10

    def test_CHDT_04_null_allowed(self):
        """CHDT-04: None is valid (manual-only mode)."""
        m = MatchDurationConfig(checkin_opens_at=None)

        assert m.checkin_opens_at is None
