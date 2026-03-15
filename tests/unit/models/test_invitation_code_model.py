"""
Unit tests for app/models/invitation_code.py

Branch coverage targets:

can_be_used_by_email():
  - invited_email is None (no restriction)   → True
  - invited_email matches exactly            → True
  - invited_email matches case-insensitively → True (both sides lowercased)
  - invited_email does not match             → False

is_valid():
  - is_used=True                             → False
  - expires_at set and expired               → False
  - all checks pass                          → True
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.invitation_code import InvitationCode


# ── Helpers ───────────────────────────────────────────────────────────────────

def _code(**kwargs) -> InvitationCode:
    """Build an InvitationCode without hitting the DB."""
    defaults = dict(
        code="INV-20260101-TESTXX",
        invited_name="Test Partner",
        bonus_credits=100,
        is_used=False,
    )
    defaults.update(kwargs)
    c = InvitationCode()
    for k, v in defaults.items():
        setattr(c, k, v)
    return c


# ── can_be_used_by_email() ────────────────────────────────────────────────────

class TestCanBeUsedByEmail:

    def test_no_email_restriction_always_true(self):
        """IC-MOD-01: invited_email=None → any email is accepted."""
        code = _code(invited_email=None)
        assert code.can_be_used_by_email("anyone@example.com") is True

    def test_exact_match_returns_true(self):
        """IC-MOD-02: invited_email matches the provided email exactly."""
        code = _code(invited_email="partner@lfa.com")
        assert code.can_be_used_by_email("partner@lfa.com") is True

    def test_case_insensitive_invited_email_uppercase(self):
        """IC-MOD-03: invited_email stored in uppercase → still matches lowercase input."""
        code = _code(invited_email="PARTNER@LFA.COM")
        assert code.can_be_used_by_email("partner@lfa.com") is True

    def test_case_insensitive_input_uppercase(self):
        """IC-MOD-04: input email uppercase → still matches lowercase stored email."""
        code = _code(invited_email="partner@lfa.com")
        assert code.can_be_used_by_email("PARTNER@LFA.COM") is True

    def test_case_insensitive_mixed_case(self):
        """IC-MOD-05: mixed-case on both sides → still matches."""
        code = _code(invited_email="Partner@Lfa.Com")
        assert code.can_be_used_by_email("pArTnEr@lFa.cOm") is True

    def test_different_email_returns_false(self):
        """IC-MOD-06: invited_email set but input is a different address → False."""
        code = _code(invited_email="partner@lfa.com")
        assert code.can_be_used_by_email("other@lfa.com") is False

    def test_subdomain_difference_returns_false(self):
        """IC-MOD-07: subdomain mismatch → False (not a prefix match)."""
        code = _code(invited_email="partner@lfa.com")
        assert code.can_be_used_by_email("partner@sub.lfa.com") is False


# ── is_valid() ────────────────────────────────────────────────────────────────

class TestIsValid:

    def test_used_code_is_invalid(self):
        """IC-MOD-08: is_used=True → is_valid() returns False."""
        code = _code(is_used=True, invited_email=None, expires_at=None)
        assert code.is_valid() is False

    def test_expired_code_is_invalid(self):
        """IC-MOD-09: expires_at in the past → is_valid() returns False."""
        code = _code(
            is_used=False,
            invited_email=None,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert code.is_valid() is False

    def test_future_expiry_is_valid(self):
        """IC-MOD-10: expires_at in the future → is_valid() returns True."""
        code = _code(
            is_used=False,
            invited_email=None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert code.is_valid() is True

    def test_no_expiry_is_valid(self):
        """IC-MOD-11: expires_at=None, not used → is_valid() returns True."""
        code = _code(is_used=False, invited_email=None, expires_at=None)
        assert code.is_valid() is True
