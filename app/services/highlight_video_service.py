"""Highlight video helper — YouTube (Phase 1) + TikTok link-only (Phase 2).

Supported URL formats:
  YouTube:
    youtube.com/watch?v={11-char id}
    youtu.be/{11-char id}
    youtube.com/shorts/{11-char id}
  TikTok (canonical only — short URLs rejected):
    tiktok.com/@{username}/video/{numeric 15-25 digit id}
    (query parameters stripped automatically)

Security contract:
  - User-supplied URL is NEVER passed as iframe src.
  - YouTube: only the extracted video_id (regex [A-Za-z0-9_-]{11}) is used;
    embed URL is always constructed from youtube-nocookie.com.
  - TikTok: only the extracted video_id (regex \\d{15,25}) is stored;
    watch_url is reconstructed from source_url (query-stripped), never from
    raw user input passed to an iframe.
  - TikTok short URLs (vm./vt.tiktok.com, tiktok.com/t/) are rejected outright;
    no backend HTTP redirects are followed.
  - TikTok iframe embed and embed.js are NOT used (link-only mode).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

# ── YouTube ───────────────────────────────────────────────────────────────────

_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

_YT_PATTERNS = [
    re.compile(r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/))([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:youtu\.be/)([A-Za-z0-9_-]{11})"),
]

_YT_EMBED_BASE = "https://www.youtube-nocookie.com/embed/"

# ── TikTok ────────────────────────────────────────────────────────────────────

_TT_ID_RE = re.compile(r"^\d{15,25}$")
_TT_CANONICAL_RE = re.compile(r"tiktok\.com/@[^/?#]+/video/(\d{15,25})")
_TT_SHORT_RE = re.compile(r"(?:vm|vt)\.tiktok\.com|tiktok\.com/t/")


# ── YouTube helpers ───────────────────────────────────────────────────────────

def extract_youtube_id(url: str) -> str | None:
    """Return the 11-char YouTube video ID from a watch/short/youtu.be URL, or None."""
    if not isinstance(url, str):
        return None
    stripped = url.strip().lower()
    if not stripped.startswith(("http://", "https://")):
        return None
    for pattern in _YT_PATTERNS:
        m = pattern.search(url)
        if m:
            vid_id = m.group(1)
            if _YT_ID_RE.match(vid_id):
                return vid_id
    return None


def build_youtube_embed_url(video_id: str) -> str:
    """Construct the privacy-enhanced embed URL from a validated YouTube video ID."""
    return f"{_YT_EMBED_BASE}{video_id}"


# ── TikTok helpers ────────────────────────────────────────────────────────────

def extract_tiktok_video_id(url: str) -> str | None:
    """Return numeric TikTok video ID from a canonical URL, or None.

    Supports tiktok.com/@user/video/{id} with any query parameters.
    Short URLs (vm./vt.tiktok.com, tiktok.com/t/) return None — callers
    should raise ValueError with an informative message via extract_any_video().
    """
    if not isinstance(url, str):
        return None
    stripped = url.strip().lower()
    if not stripped.startswith(("http://", "https://")):
        return None
    if _TT_SHORT_RE.search(stripped):
        return None
    m = _TT_CANONICAL_RE.search(url)
    if m:
        vid_id = m.group(1)
        if _TT_ID_RE.match(vid_id):
            return vid_id
    return None


def build_tiktok_watch_url(source_url: str) -> str:
    """Strip query parameters from a canonical TikTok URL to get a clean watch URL."""
    return source_url.split("?")[0]


# ── Provider router ───────────────────────────────────────────────────────────

def extract_any_video(url: str) -> dict[str, str] | None:
    """Detect provider and extract video_id from a YouTube or TikTok URL.

    Returns {"provider": "youtube"|"tiktok", "video_id": "..."} or None.

    Raises ValueError for recognised-but-unsupported short TikTok URLs so
    that callers can surface a helpful message to the user instead of a
    generic "invalid URL" error.
    """
    if not isinstance(url, str):
        return None
    stripped = url.strip().lower()
    if not stripped.startswith(("http://", "https://")):
        return None

    yt_id = extract_youtube_id(url)
    if yt_id:
        return {"provider": "youtube", "video_id": yt_id}

    if _TT_SHORT_RE.search(stripped):
        raise ValueError(
            "Please paste the full TikTok video link: "
            "tiktok.com/@user/video/..."
        )

    tt_id = extract_tiktok_video_id(url)
    if tt_id:
        return {"provider": "tiktok", "video_id": tt_id}

    return None


# ── Published-data reader (used by public profile route) ─────────────────────

def get_published_highlight_video(card_draft: Any) -> dict | None:
    """Read highlight_video from CardDraft.published_data; return structured dict or None.

    YouTube:  returns {provider, video_id, embed_url, watch_url}
    TikTok:   returns {provider, video_id, embed_url=None, watch_url}
              embed_url is None — the template must use the CTA link path.
    """
    if card_draft is None:
        return None
    try:
        pub_data = card_draft.published_data
    except AttributeError:
        return None
    if not isinstance(pub_data, dict):
        return None
    hv = pub_data.get("highlight_video")
    if not isinstance(hv, dict):
        return None

    provider = hv.get("provider")
    video_id = hv.get("video_id")

    if provider == "youtube":
        if not isinstance(video_id, str) or not _YT_ID_RE.match(video_id):
            return None
        return {
            "provider":  "youtube",
            "video_id":  video_id,
            "embed_url": build_youtube_embed_url(video_id),
            "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        }

    if provider == "tiktok":
        if not isinstance(video_id, str) or not _TT_ID_RE.match(video_id):
            return None
        source_url = hv.get("source_url", "")
        watch_url = build_tiktok_watch_url(source_url) if source_url else None
        return {
            "provider":  "tiktok",
            "video_id":  video_id,
            "embed_url": None,
            "watch_url": watch_url,
        }

    return None


def make_highlight_video_published_data(video_url: str) -> dict | None:
    """Build the published_data payload from a user-supplied URL (for seeding/testing).

    Returns None if URL is invalid or not a supported format.
    """
    try:
        parsed = extract_any_video(video_url)
    except ValueError:
        return None
    if parsed is None:
        return None
    return {
        "highlight_video": {
            "provider":  parsed["provider"],
            "video_id":  parsed["video_id"],
            "added_at":  datetime.now(timezone.utc).isoformat(),
        }
    }
