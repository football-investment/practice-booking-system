"""
Unit tests — GET /players/{user_id}/card/export/video
======================================================

Coverage:
  VX-01  fifa + instagram_square → 200 video/webm + WebM magic bytes
  VX-02  fifa + instagram_portrait → 422 (not animated capable)
  VX-03  compact + instagram_square → 422 (variant not animated capable)
  VX-04  invalid platform → 422
  VX-05  platform="default" → 422 (no canvas size, not an export target)
  VX-06  student exports other player's card → 403
  VX-07  admin exports any player's card → 200
  VX-08  video rate limit: 3rd request within 60s → 429 (limit=2)
  VX-09  Playwright/recording timeout → 504
  VX-10  player not found → 404
  VX-11  no active LFA Player license → 404
  VX-12  WebM magic bytes (\\x1aE\\xdf\\xa3) present in response body
  VX-13  PNG render URL never contains animated=1 (isolation invariant)
  VX-14  unsupported format → 422
  VX-15  unsupported duration → 422
  VX-16  Content-Disposition filename + Cache-Control headers correct
  VX-17  is_animated_capable() returns True for all registered pairs (fifa + pulse)
  VX-18  ANIMATED_EXPORT_CAPABLE registry contains exactly fifa+square AND pulse+square
  VX-19  pulse + instagram_square → 200 video/webm (new animated-capable pair)
  VX-20  pulse + instagram_portrait → 422 (pulse not capable on portrait)
  VX-21  pulse + instagram_story → 422 (pulse not capable on story)

Mock strategy:
  - get_current_user_web → MagicMock user (no DB, no cookie)
  - get_db              → MagicMock session returning preset user/license mocks
  - _export_svc._sync_record_video → returns fixture WebM bytes (no Playwright)
  - video rate counters reset between tests via reset_video_rate_counters()
"""
from __future__ import annotations

import struct
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.user import UserRole
from app.services.card_export_service import (
    ANIMATED_EXPORT_CAPABLE,
    CardVideoRecordError,
    is_animated_capable,
    reset_rate_counters,
    reset_video_rate_counters,
)

# ── WebM fixture ──────────────────────────────────────────────────────────────
# Minimal valid WebM magic bytes (EBML header start).
_WEBM_MAGIC = b"\x1a\x45\xdf\xa3"
_WEBM_FIXTURE = _WEBM_MAGIC + b"\x00" * 64  # stub payload


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _make_user(user_id: int = 7, role: UserRole = UserRole.STUDENT) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.is_active = True
    return u


def _make_license(card_variant: str = "fifa") -> MagicMock:
    lic = MagicMock()
    lic.card_variant = card_variant
    lic.specialization_type = "LFA_FOOTBALL_PLAYER"
    lic.is_active = True
    return lic


def _mock_db(target_user=None, target_license=None):
    db = MagicMock()
    q_user = MagicMock()
    q_user.filter.return_value.first.return_value = target_user
    q_license = MagicMock()
    q_license.filter.return_value.first.return_value = target_license
    db.query.side_effect = [q_user, q_license]
    return db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_counters():
    reset_rate_counters()
    reset_video_rate_counters()
    yield
    reset_rate_counters()
    reset_video_rate_counters()


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _setup_overrides(app, current_user, db):
    from app.dependencies import get_current_user_web, get_db

    async def _auth():
        return current_user

    app.dependency_overrides[get_current_user_web] = _auth
    app.dependency_overrides[get_db] = lambda: db


def _clear_overrides(app):
    app.dependency_overrides.clear()


def _video_export(
    client,
    platform: str = "instagram_square",
    user_id: int = 7,
    current_user=None,
    db=None,
    card_variant: str = "fifa",
    webm_bytes: bytes = _WEBM_FIXTURE,
    format: str = "webm",
    duration: int = 5,
):
    from app.main import app

    if current_user is None:
        current_user = _make_user(user_id=user_id)
    if db is None:
        db = _mock_db(
            target_user=_make_user(user_id=user_id),
            target_license=_make_license(card_variant=card_variant),
        )

    _setup_overrides(app, current_user, db)
    try:
        with patch("app.services.card_export_service._sync_record_video",
                   return_value=webm_bytes):
            url = (
                f"/players/{user_id}/card/export/video"
                f"?platform={platform}&format={format}&duration={duration}"
            )
            return client.get(url)
    finally:
        _clear_overrides(app)


# ── Tests: happy path ─────────────────────────────────────────────────────────

@pytest.mark.unit
class TestVideoExportHappyPath:

    def test_vx01_fifa_square_returns_200_webm(self, client):
        """fifa + instagram_square is the only supported animated combo — must return 200."""
        r = _video_export(client, platform="instagram_square", card_variant="fifa")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("video/webm")

    def test_vx07_admin_exports_any_player(self, client):
        """Admin may export any user's card regardless of ownership."""
        admin = _make_user(user_id=1, role=UserRole.ADMIN)
        r = _video_export(client, user_id=7, current_user=admin,
                          platform="instagram_square", card_variant="fifa")
        assert r.status_code == 200

    def test_vx12_webm_magic_bytes_in_response(self, client):
        """Response body must start with WebM EBML magic bytes \\x1aE\\xdf\\xa3."""
        r = _video_export(client, platform="instagram_square", card_variant="fifa")
        assert r.status_code == 200
        assert r.content[:4] == _WEBM_MAGIC

    def test_vx16_response_headers_correct(self, client):
        """Content-Disposition filename and Cache-Control must be set correctly."""
        r = _video_export(client, user_id=7, platform="instagram_square",
                          card_variant="fifa")
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "")
        assert "lfa_card_7_instagram_square_animated.webm" in cd
        assert r.headers.get("cache-control") == "no-store"
        assert r.headers.get("x-export-platform") == "instagram_square"
        assert r.headers.get("x-export-format") == "webm"
        assert r.headers.get("x-export-duration") == "5"


# ── Tests: capability gating ──────────────────────────────────────────────────

@pytest.mark.unit
class TestVideoExportCapabilityGating:

    def test_vx02_fifa_portrait_returns_422(self, client):
        """fifa + instagram_portrait is not animated-capable → 422, no video."""
        r = _video_export(client, platform="instagram_portrait", card_variant="fifa")
        assert r.status_code == 422

    def test_vx03_compact_square_returns_422(self, client):
        """compact + instagram_square is not animated-capable → 422."""
        r = _video_export(client, platform="instagram_square", card_variant="compact")
        assert r.status_code == 422

    def test_vx04_invalid_platform_returns_422(self, client):
        """Unknown platform string → 422 before capability check."""
        r = _video_export(client, platform="foobar", card_variant="fifa")
        assert r.status_code == 422

    def test_vx05_default_platform_returns_422(self, client):
        """'default' is not an export target (no canvas size) → 422."""
        r = _video_export(client, platform="default", card_variant="fifa")
        assert r.status_code == 422

    def test_vx14_unsupported_format_returns_422(self, client):
        """format=mp4 is not supported in MVP → 422."""
        r = _video_export(client, platform="instagram_square", card_variant="fifa",
                          format="mp4")
        assert r.status_code == 422

    def test_vx15_unsupported_duration_returns_422(self, client):
        """duration=10 is not supported in MVP → 422."""
        r = _video_export(client, platform="instagram_square", card_variant="fifa",
                          duration=10)
        assert r.status_code == 422


# ── Tests: auth and ownership ─────────────────────────────────────────────────

@pytest.mark.unit
class TestVideoExportAuth:

    def test_vx06_student_exports_other_player_returns_403(self, client):
        """Student (id=99) requesting export for user_id=7 → 403."""
        attacker = _make_user(user_id=99, role=UserRole.STUDENT)
        db = _mock_db(
            target_user=_make_user(user_id=7),
            target_license=_make_license(card_variant="fifa"),
        )
        r = _video_export(client, user_id=7, current_user=attacker, db=db,
                          platform="instagram_square", card_variant="fifa")
        assert r.status_code == 403


# ── Tests: resource not found ─────────────────────────────────────────────────

@pytest.mark.unit
class TestVideoExportNotFound:

    def test_vx10_player_not_found_returns_404(self, client):
        """User not in DB → 404."""
        db = _mock_db(target_user=None, target_license=None)
        r = _video_export(client, user_id=7, db=db,
                          platform="instagram_square", card_variant="fifa")
        assert r.status_code == 404

    def test_vx11_no_active_license_returns_404(self, client):
        """User exists but has no active LFA Player license → 404."""
        db = _mock_db(
            target_user=_make_user(user_id=7),
            target_license=None,
        )
        r = _video_export(client, user_id=7, db=db,
                          platform="instagram_square", card_variant="fifa")
        assert r.status_code == 404


# ── Tests: rate limiting and errors ──────────────────────────────────────────

@pytest.mark.unit
class TestVideoExportRateAndErrors:

    def test_vx08_rate_limit_third_request_returns_429(self, client):
        """Video rate limit is 2/60s; 3rd request must return 429."""
        for _ in range(2):
            r = _video_export(client, platform="instagram_square", card_variant="fifa")
            assert r.status_code == 200
        r = _video_export(client, platform="instagram_square", card_variant="fifa")
        assert r.status_code == 429

    def test_vx09_recording_timeout_returns_504(self, client):
        """CardVideoRecordError from _sync_record_video → 504."""
        from app.main import app
        current_user = _make_user(user_id=7)
        db = _mock_db(
            target_user=_make_user(user_id=7),
            target_license=_make_license(card_variant="fifa"),
        )
        _setup_overrides(app, current_user, db)
        try:
            with patch("app.services.card_export_service._sync_record_video",
                       side_effect=CardVideoRecordError("timed out")):
                r = client.get(
                    "/players/7/card/export/video"
                    "?platform=instagram_square&format=webm&duration=5"
                )
        finally:
            _clear_overrides(app)
        assert r.status_code == 504


# ── Tests: registry and isolation invariants ─────────────────────────────────

@pytest.mark.unit
class TestAnimatedCapabilityRegistry:

    def test_vx17_is_animated_capable_true_only_for_registered_pairs(self):
        """is_animated_capable must return True for all registered pairs and False for others."""
        assert is_animated_capable("fifa",  "instagram_square") is True
        assert is_animated_capable("pulse", "instagram_square") is True
        assert is_animated_capable("fifa",  "instagram_portrait") is False
        assert is_animated_capable("fifa",  "instagram_story") is False
        assert is_animated_capable("fifa",  "tiktok") is False
        assert is_animated_capable("pulse", "instagram_portrait") is False
        assert is_animated_capable("pulse", "instagram_story") is False
        assert is_animated_capable("compact",  "instagram_square") is False
        assert is_animated_capable("showcase", "instagram_square") is False
        assert is_animated_capable("atlas",    "instagram_square") is False
        assert is_animated_capable("", "") is False

    def test_vx18_registry_contains_exactly_fifa_and_pulse_square(self):
        """Registry must contain exactly two entries: fifa+square and pulse+square."""
        assert ANIMATED_EXPORT_CAPABLE == frozenset({
            ("fifa",  "instagram_square"),
            ("pulse", "instagram_square"),
        })

    def test_vx13_png_render_url_never_contains_animated_param(self):
        """The PNG export endpoint must never include animated=1 in render_url.

        This is the key isolation invariant: static exports cannot accidentally
        activate the animated CSS block in the template.
        """
        import inspect
        import app.api.web_routes.public_player as _mod
        src = inspect.getsource(_mod.export_player_card)
        # The PNG endpoint render_url construction must not contain animated=1
        assert "animated=1" not in src, (
            "PNG export endpoint must never include animated=1 in render_url — "
            "this would activate animation CSS in static export templates"
        )
        # Confirm the video endpoint DOES include animated=1 (positive check)
        video_src = inspect.getsource(_mod.export_player_card_video)
        assert "animated=1" in video_src, (
            "Video export endpoint must include animated=1 in render_url"
        )


# ── Tests: Pulse × Instagram Square animated export ──────────────────────────

@pytest.mark.unit
class TestPulseVideoExport:
    """Video export tests for the Pulse × Instagram Square animated pair.

    VX-19  pulse + instagram_square → 200 video/webm
    VX-20  pulse + instagram_portrait → 422 (pulse not animated-capable on portrait)
    VX-21  pulse + instagram_story → 422 (pulse not animated-capable on story)
    """

    def test_vx19_pulse_square_returns_200_webm(self, client):
        """pulse + instagram_square is registered in ANIMATED_EXPORT_CAPABLE → 200."""
        r = _video_export(client, platform="instagram_square", card_variant="pulse")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("video/webm")

    def test_vx20_pulse_portrait_returns_422(self, client):
        """pulse + instagram_portrait is not animated-capable → 422."""
        r = _video_export(client, platform="instagram_portrait", card_variant="pulse")
        assert r.status_code == 422

    def test_vx21_pulse_story_returns_422(self, client):
        """pulse + instagram_story is not animated-capable → 422."""
        r = _video_export(client, platform="instagram_story", card_variant="pulse")
        assert r.status_code == 422
