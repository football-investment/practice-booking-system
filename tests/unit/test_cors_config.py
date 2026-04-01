"""
Unit tests for CORS_ALLOWED_ORIGINS config validation.

Locks down the _CORSSafeEnvSource / _CORSFormatError interception chain so
the friendly error message is guaranteed and the behaviour cannot silently
regress.  See app/config.py IMPORTANT comment for the full explanation of why
a @field_validator cannot be used here.

Each test uses a subprocess so module-level state (already-imported Settings,
loaded .env, cached os.environ) cannot leak between cases.
"""
import json
import os
import subprocess
import sys

import pytest


_RUNNER = """\
import os, json, sys

for k, v in {env!r}.items():
    os.environ[k] = v

try:
    from app.config import Settings
    s = Settings()
    print(json.dumps({{"ok": True, "cors": s.CORS_ALLOWED_ORIGINS}}))
except Exception as e:
    print(json.dumps({{"ok": False, "error": str(e), "exc_type": type(e).__qualname__}}))
"""

_BASE = {
    "ENVIRONMENT": "test",
    "SECRET_KEY": "test-secret-key-for-ci-health-check",
    "DATABASE_URL": "postgresql://x:x@localhost:5432/db",
    "ADMIN_EMAIL": "admin@test.com",
    "ADMIN_PASSWORD": "admin123",
    "ADMIN_NAME": "Test Admin",
}

_BASE_PROD = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "aG9wZXRoaXNpc3Ryb25nZW5vdWdoZm9ycHJvZA",
    "DATABASE_URL": "postgresql://x:x@localhost:5432/db",
    "ADMIN_EMAIL": "admin@lfa.com",
    "ADMIN_PASSWORD": "Str0ng!Pass#2026",
    "ADMIN_NAME": "LFA Admin",
    "COOKIE_SECURE": "true",
    # Required: production validator raises if DEBUG=True (app/config.py:330-335).
    # In CI there is no .env file and no DEBUG env var, so the class default
    # (True) fires the check.  Local runs pass because the developer's .env has
    # DEBUG=false.  Always include this key in _BASE_PROD to avoid CI flakiness.
    "DEBUG": "false",
}


def _run(env: dict) -> dict:
    code = _RUNNER.format(env=env)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    )
    output = result.stdout.strip()
    if not output:
        output = result.stderr.strip().split("\n")[-1]
    return json.loads(output)


class TestCORSConfigValidator:
    """CORS_ALLOWED_ORIGINS field_validator — friendly errors + correct parsing."""

    # ── Happy paths ────────────────────────────────────────────────────────────

    def test_no_cors_env_test_mode_returns_localhost_list(self):
        """CI / dev / test: omitting CORS_ALLOWED_ORIGINS auto-returns localhost list."""
        data = _run(_BASE)
        assert data["ok"] is True
        cors = data["cors"]
        assert isinstance(cors, list)
        assert any("localhost" in o for o in cors)

    def test_json_array_production_parsed_correctly(self):
        """Production canonical format: JSON array string is parsed to a list."""
        env = {**_BASE_PROD, "CORS_ALLOWED_ORIGINS": '["https://app.lfa.com","https://admin.lfa.com"]'}
        data = _run(env)
        assert data["ok"] is True
        assert data["cors"] == ["https://app.lfa.com", "https://admin.lfa.com"]

    # ── Error paths — must raise ValueError, not SettingsError ────────────────
    # Regression: previously raised pydantic_settings.sources.SettingsError
    # when CORS_ALLOWED_ORIGINS was a plain URL string in CI .env (2026-03-23).

    def test_cors_error_not_wrapped_in_settings_error(self):
        """CORS format error must surface as ValueError, never as SettingsError.

        Regression lock: the _CORSFormatError bypass ensures the opaque
        SettingsError from pydantic-settings does not reach the caller.
        """
        env = {**_BASE, "CORS_ALLOWED_ORIGINS": "http://localhost:3000"}
        data = _run(env)
        assert data["ok"] is False
        assert data["exc_type"] == "ValueError", (
            f"Expected ValueError but got {data['exc_type']}: {data['error']}"
        )

    def test_plain_url_raises_value_error_with_hint(self):
        """Plain URL (no brackets) must raise ValueError with clear instructions."""
        env = {**_BASE, "CORS_ALLOWED_ORIGINS": "http://localhost:3000"}
        data = _run(env)
        assert data["ok"] is False
        err = data["error"]
        assert "JSON array" in err, f"Expected 'JSON array' in error, got: {err}"
        assert "CORS_ALLOWED_ORIGINS" in err

    def test_comma_separated_raises_value_error_with_hint(self):
        """Comma-separated format (no brackets) must raise ValueError."""
        env = {**_BASE, "CORS_ALLOWED_ORIGINS": "https://a.com,https://b.com"}
        data = _run(env)
        assert data["ok"] is False
        assert "JSON array" in data["error"]

    def test_error_message_includes_correct_example(self):
        """Error message must show the correct JSON array example format."""
        env = {**_BASE, "CORS_ALLOWED_ORIGINS": "https://bad-format.com"}
        data = _run(env)
        assert data["ok"] is False
        err = data["error"]
        # Must show the correct format in the hint
        assert '["' in err or "JSON array" in err

    def test_error_message_mentions_dev_omit_hint(self):
        """Error message must explain that omitting is correct for dev/test."""
        env = {**_BASE, "CORS_ALLOWED_ORIGINS": "http://localhost:3000"}
        data = _run(env)
        assert data["ok"] is False
        # Should mention omitting the variable is the right approach for dev
        assert "omit" in data["error"].lower() or "dev" in data["error"].lower()

    # ── Non-masking guarantee ──────────────────────────────────────────────────

    def test_unrelated_settings_error_not_masked(self):
        """A SettingsError from a non-CORS field must NOT be silently converted to
        a CORS error message — the original error must propagate unchanged."""
        # SKILL_TIER_THRESHOLDS is dict[int, str]; invalid JSON triggers SettingsError
        # for that field, not for CORS_ALLOWED_ORIGINS.
        env = {**_BASE, "SKILL_TIER_THRESHOLDS": "not-valid-json"}
        data = _run(env)
        assert data["ok"] is False
        err = data["error"]
        # Must NOT have been silently rewritten to the CORS friendly message
        assert "CORS_ALLOWED_ORIGINS" not in err, (
            f"Unrelated SettingsError was incorrectly masked as CORS error: {err}"
        )
        # Must still reference the actual bad field
        assert "SKILL_TIER_THRESHOLDS" in err
