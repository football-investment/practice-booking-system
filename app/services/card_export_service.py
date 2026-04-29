"""Player card headless screenshot export service.

Security contract:
  render_url is ALWAYS constructed server-side from a validated int user_id
  and a whitelisted platform preset id — raw user input never reaches Playwright.
"""
import logging
import time
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)

# Social canvas sizes — keyed by platform preset id.
# "default" is intentionally absent (not an export target).
# Dimensions match each platform's recommended export resolution.
CANVAS_SIZES: dict[str, tuple[int, int]] = {
    "instagram_square":   (1080, 1080),
    "instagram_portrait": (1080, 1350),
    "instagram_story":    (1080, 1920),
    "tiktok":             (1080, 1920),
    "facebook_square":    (1080, 1080),
    "facebook_landscape": (1200,  630),
    "og":                 (1200,  630),
    "banner_custom":      (1500,  500),
}

# ── Animated video export capability registry ─────────────────────────────────
# Central source of truth: (variant_id, platform_id) pairs that have a
# dedicated animated export template.  All other combinations are unsupported
# and the video endpoint returns 422 — no fallback, no silent degradation.
ANIMATED_EXPORT_CAPABLE: frozenset[tuple[str, str]] = frozenset({
    ("fifa",  "instagram_square"),
    ("pulse", "instagram_square"),
})


def is_animated_capable(variant_id: str, platform_id: str) -> bool:
    """Return True if (variant_id, platform_id) supports animated video export."""
    return (variant_id, platform_id) in ANIMATED_EXPORT_CAPABLE


_GOTO_TIMEOUT_MS  = 10_000  # 10 s — generous vs. measured 0.6 s
_VIDEO_TIMEOUT_MS = 30_000  # 30 s — covers 10 s recording + Chromium launch overhead

# Pre-roll: ms to wait after networkidle + document.fonts.ready before the main
# recording duration begins.  Allows DOMContentLoaded JS callbacks (OVR ring
# requestAnimationFrame, radar fade-in) to fire and the first CSS animation
# frame to commit, so the recording never starts in a half-initialized state.
# To change: update this constant only — do not touch duration_s.
_PRE_ROLL_MS = 400

# Video recording frame rate note:
# Playwright records via Chrome DevTools Protocol screencast at ~25 fps.
# This is not configurable through Playwright's public API without dropping
# to CDP level (Page.startScreencast with everyNthFrame).
# To change fps: replace record_video_dir approach with CDP screencast directly.
_VIDEO_FPS_NOTE = "~25 fps (CDP screencast default, not user-configurable via Playwright API)"


class CardExportTimeoutError(Exception):
    """Raised when Playwright page load exceeds _GOTO_TIMEOUT_MS."""


class CardVideoRecordError(Exception):
    """Raised when Playwright video recording fails or produces no output."""


# ── PNG rate limiter: 5 exports / 60 s per rate_key ──────────────────────────
_EXPORT_LIMIT  = 5
_EXPORT_WINDOW = 60  # seconds
_rate_counters: dict[str, deque] = {}
_rate_lock = Lock()


def check_export_rate_limit(rate_key: str) -> bool:
    """Return True if the caller is within the PNG rate limit, False if exceeded."""
    now = time.monotonic()
    with _rate_lock:
        if rate_key not in _rate_counters:
            _rate_counters[rate_key] = deque()
        dq = _rate_counters[rate_key]
        cutoff = now - _EXPORT_WINDOW
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= _EXPORT_LIMIT:
            return False
        dq.append(now)
        return True


def reset_rate_counters() -> None:
    """Test helper — clears all in-memory PNG rate counters."""
    with _rate_lock:
        _rate_counters.clear()


# ── Video rate limiter: 2 exports / 60 s per rate_key ────────────────────────
# Video recording is ~10× heavier than PNG — separate, tighter limit.
_VIDEO_LIMIT  = 2
_VIDEO_WINDOW = 60  # seconds
_video_rate_counters: dict[str, deque] = {}
_video_rate_lock = Lock()


def check_video_rate_limit(rate_key: str) -> bool:
    """Return True if the caller is within the video rate limit, False if exceeded."""
    now = time.monotonic()
    with _video_rate_lock:
        if rate_key not in _video_rate_counters:
            _video_rate_counters[rate_key] = deque()
        dq = _video_rate_counters[rate_key]
        cutoff = now - _VIDEO_WINDOW
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= _VIDEO_LIMIT:
            return False
        dq.append(now)
        return True


def reset_video_rate_counters() -> None:
    """Test helper — clears all in-memory video rate counters."""
    with _video_rate_lock:
        _video_rate_counters.clear()


def _sync_take_screenshot(render_url: str, platform: str) -> bytes:  # pragma: no cover
    """Launch headless Chromium, navigate to render_url, return PNG bytes.

    Called via asyncio.to_thread from the async export endpoint so it does
    not block the event loop.

    Raises:
        CardExportTimeoutError: if page.goto exceeds _GOTO_TIMEOUT_MS
        ValueError: if platform has no registered canvas size
    """
    canvas = CANVAS_SIZES.get(platform)
    if canvas is None:
        raise ValueError(f"No canvas size for platform: {platform!r}")
    w, h = canvas

    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as _PWTimeout

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": w, "height": h})
                page.goto(render_url, wait_until="networkidle", timeout=_GOTO_TIMEOUT_MS)
                png = page.screenshot(
                    clip={"x": 0, "y": 0, "width": w, "height": h},
                    type="png",
                )
            finally:
                browser.close()
    except _PWTimeout as exc:
        raise CardExportTimeoutError(str(exc)) from exc

    return png


def _sync_record_video(  # pragma: no cover
    render_url: str,
    platform: str,
    duration_s: int = 5,
) -> bytes:
    """Launch headless Chromium, record the animated card for duration_s, return WebM bytes.

    Called via asyncio.to_thread from the async video export endpoint so it does
    not block the event loop.

    Playwright writes a .webm file to a temp dir when context.close() is called.
    The render_url must include ?animated=1 so the template activates its CSS
    animation block — this function does not add that param itself.

    Raises:
        CardVideoRecordError: if recording times out or produces no WebM file
        ValueError: if platform has no registered canvas size
    """
    import pathlib
    import tempfile

    canvas = CANVAS_SIZES.get(platform)
    if canvas is None:
        raise ValueError(f"No canvas size for platform: {platform!r}")
    w, h = canvas

    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as _PWTimeout

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": w, "height": h},
                    record_video_dir=tmp_dir,
                    record_video_size={"width": w, "height": h},
                )
                page = context.new_page()
                page.goto(render_url, wait_until="networkidle", timeout=_VIDEO_TIMEOUT_MS)
                # Font readiness: await document.fonts.ready so DM Mono (Google
                # Fonts CDN) is fully loaded before recording begins.
                # page.evaluate() awaits the returned Promise in Playwright sync API.
                page.evaluate("() => document.fonts.ready")
                # Pre-roll: let DOMContentLoaded JS callbacks (OVR ring
                # requestAnimationFrame, radar fade-in) fire and the first
                # CSS animation frame commit before starting the timed recording.
                page.wait_for_timeout(_PRE_ROLL_MS)
                page.wait_for_timeout(duration_s * 1000)
                context.close()   # triggers WebM finalization
                browser.close()

            webm_files = list(pathlib.Path(tmp_dir).glob("*.webm"))
            if not webm_files:
                raise CardVideoRecordError("No WebM file produced by Playwright")
            return webm_files[0].read_bytes()
    except _PWTimeout as exc:
        raise CardVideoRecordError(str(exc)) from exc
