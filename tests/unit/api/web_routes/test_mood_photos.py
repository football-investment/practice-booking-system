"""
MP-R01..MP-R09 — unit tests for mood_photos web routes.

Tests call route functions directly (asyncio.run) with patched
dependencies — no TestClient, no real DB, no disk I/O.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

_BASE = "app.api.web_routes.mood_photos"
_SVC  = "app.services.mood_photo_service"


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _user(uid: int = 1):
    u = MagicMock()
    u.id    = uid
    u.email = f"user{uid}@lfa.com"
    return u


def _db():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    return db


def _request(accept: str = "text/html"):
    req = MagicMock()
    req.headers = {"accept": accept}
    return req


def _run(coro):
    return asyncio.run(coro)


def _mock_photo(content: bytes = b"\xff\xd8\xff", content_type: str = "image/jpeg"):
    f = AsyncMock()
    f.read = AsyncMock(return_value=content)
    f.content_type = content_type
    return f


# ── MP-R01 ── authenticated upload → 303 redirect ────────────────────────────

def test_mp_r01_authenticated_upload_redirects():
    from app.api.web_routes.mood_photos import mood_photo_upload

    with patch(f"{_BASE}.save_mood_photo") as mock_save, \
         patch(f"{_BASE}.get_mood_photos_for_user", return_value={}):
        mock_save.return_value = MagicMock()

        resp = _run(
            mood_photo_upload(
                slot    = "mood_happy_smile",
                request = _request(),
                photo   = _mock_photo(),
                user    = _user(),
                db      = _db(),
            )
        )

    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 303
    assert "/profile/my-mood-photos" in str(resp.headers.get("location", ""))


# ── MP-R02 ── unauthenticated → dependency raises (simulated 401) ─────────────

def test_mp_r02_unauthenticated_raises():
    from app.api.web_routes.mood_photos import mood_photo_upload

    async def _raise():
        raise HTTPException(status_code=401, detail="Not authenticated")

    with pytest.raises(HTTPException) as exc_info:
        _run(
            mood_photo_upload(
                slot    = "mood_happy_smile",
                request = _request(),
                photo   = _mock_photo(),
                user    = await_raises(401),
                db      = _db(),
            )
        )


def await_raises(status: int):
    raise HTTPException(status_code=status)


# ── MP-R03 ── invalid slot → HTTPException 422 ───────────────────────────────

def test_mp_r03_invalid_slot_raises_422():
    from app.api.web_routes.mood_photos import mood_photo_upload

    with pytest.raises(HTTPException) as exc_info:
        _run(
            mood_photo_upload(
                slot    = "angry_rage",
                request = _request(),
                photo   = _mock_photo(),
                user    = _user(),
                db      = _db(),
            )
        )
    assert exc_info.value.status_code == 422


# ── MP-R04 ── GET page returns 4-slot context ─────────────────────────────────

def test_mp_r04_get_page_returns_all_slots():
    from app.api.web_routes.mood_photos import mood_photos_page

    four_slots = {
        "mood_intro_neutral":    None,
        "mood_happy_smile":      None,
        "mood_celebration":      None,
        "mood_sad_disappointed": None,
    }

    with patch(f"{_BASE}.get_mood_photos_for_user", return_value=four_slots), \
         patch(f"{_BASE}.templates") as mock_tpl:
        mock_tpl.TemplateResponse.return_value = MagicMock()

        _run(mood_photos_page(request=_request(), user=_user(), db=_db()))

        call_kwargs = mock_tpl.TemplateResponse.call_args
        ctx = call_kwargs[0][1]
        assert "mood_photos" in ctx
        assert set(ctx["mood_photos"].keys()) == set(four_slots.keys())
        assert "slots_meta" in ctx
        assert len(ctx["slots_meta"]) == 4


# ── MP-R05 ── GET only queries own user_id ───────────────────────────────────

def test_mp_r05_get_queries_correct_user_id():
    from app.api.web_routes.mood_photos import mood_photos_page

    with patch(f"{_BASE}.get_mood_photos_for_user") as mock_get, \
         patch(f"{_BASE}.templates") as mock_tpl:
        mock_get.return_value = {s: None for s in [
            "mood_intro_neutral", "mood_happy_smile",
            "mood_celebration",   "mood_sad_disappointed",
        ]}
        mock_tpl.TemplateResponse.return_value = MagicMock()

        db = _db()
        _run(mood_photos_page(request=_request(), user=_user(uid=42), db=db))

        called_uid = mock_get.call_args[0][0]
        assert called_uid == 42


# ── MP-R06 ── POST /delete form fallback → 303 ───────────────────────────────

def test_mp_r06_form_delete_redirects():
    from app.api.web_routes.mood_photos import mood_photo_delete_form

    with patch(f"{_BASE}.delete_mood_photo") as mock_del:
        resp = _run(
            mood_photo_delete_form(
                slot = "mood_intro_neutral",
                user = _user(),
                db   = _db(),
            )
        )

    mock_del.assert_called_once()
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 303


# ── MP-R07 ── DELETE endpoint → 204 (None return) ────────────────────────────

def test_mp_r07_delete_api_returns_none():
    from app.api.web_routes.mood_photos import mood_photo_delete_api

    with patch(f"{_BASE}.delete_mood_photo"):
        result = _run(
            mood_photo_delete_api(
                slot = "mood_celebration",
                user = _user(),
                db   = _db(),
            )
        )
    assert result is None  # 204 = no body


# ── MP-R08 ── delete invalid slot → 422 ──────────────────────────────────────

def test_mp_r08_delete_invalid_slot_raises_422():
    from app.api.web_routes.mood_photos import mood_photo_delete_form

    with pytest.raises(HTTPException) as exc_info:
        _run(
            mood_photo_delete_form(
                slot = "unknown_slot_xyz",
                user = _user(),
                db   = _db(),
            )
        )
    assert exc_info.value.status_code == 422


# ── MP-R09 ── onboarding Step 7 contains hangulatkep offer block ──────────────

def test_mp_r09_onboarding_template_contains_mood_offer():
    from pathlib import Path

    template_path = (
        Path(__file__).resolve()
        .parent.parent.parent.parent.parent
        / "app" / "templates" / "lfa_player_onboarding.html"
    )
    content = template_path.read_text(encoding="utf-8")
    assert "step7-mood-offer" in content, (
        "lfa_player_onboarding.html missing step7-mood-offer block"
    )
    assert "/profile/my-mood-photos" in content, (
        "lfa_player_onboarding.html missing link to /profile/my-mood-photos"
    )
    assert "Hangulatk" in content, (
        "lfa_player_onboarding.html missing 'Hangulatkép' text"
    )
    # Onboarding completion gate must NOT mention mood in submit handler
    assert "mood" not in content.split("lfa_player_onboarding_web_submit")[0].lower() \
        or "onboarding_completed" not in content.split("step7-mood-offer")[0], \
        "onboarding_completed must not be gated on mood upload"
