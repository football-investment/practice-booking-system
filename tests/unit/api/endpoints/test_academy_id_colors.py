"""
Academy ID Color System — Phase 1 unit tests.

AIC-01  GET /me/academy-id/colors — no licence → 404
AIC-02  GET /me/academy-id/colors — with licence → 3 free colours, all is_owned=True
AIC-03  GET /me/academy-id/colors — active_color_id reflects stored value
AIC-04  POST /me/academy-id/colors/select — unknown color_id → 400
AIC-05  POST /me/academy-id/colors/select — valid ivory → active_color_id updated
AIC-06  POST /me/academy-id/colors/select — no licence → 404
AIC-07  GET /me/academy-id — includes active_color_id (licence present)
AIC-08  GET /me/academy-id — active_color_id=None when no licence
AIC-09  academy_id_color_service is isolated from Player/Welcome card systems
AIC-10  get_active_color_id falls back to 'official' for unknown/NULL value
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.api_v1.endpoints.users.profile import (
    get_academy_id_colors,
    select_academy_id_color,
)
from app.services.academy_id_color_service import (
    ACADEMY_ID_COLORS,
    get_active_color_id,
    get_all_colors,
    is_valid_color,
    set_active_color,
)

_BASE = "app.api.api_v1.endpoints.users.profile"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _user(uid: int = 1):
    u = MagicMock()
    u.id  = uid
    u.lfa_academy_id = "LFA-2026-00001"
    u.public_token   = "test-token-uuid"
    return u


def _license(color: str = "official", spec: str = "LFA_FOOTBALL_PLAYER"):
    lic = MagicMock()
    lic.specialization_type = spec
    lic.academy_id_color    = color
    return lic


def _db_with_license(lic):
    """DB mock whose .query().filter().first() returns lic."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = lic
    return db


def _db_no_license():
    """DB mock with no licence row."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


class _SelectPayload:
    def __init__(self, color_id: str):
        self.color_id = color_id


# ── AIC-01 ────────────────────────────────────────────────────────────────────

def test_aic_01_colors_no_licence_raises_404():
    """GET /me/academy-id/colors with no LFA licence → 404."""
    with pytest.raises(HTTPException) as exc:
        get_academy_id_colors(db=_db_no_license(), current_user=_user())
    assert exc.value.status_code == 404


# ── AIC-02 ────────────────────────────────────────────────────────────────────

def test_aic_02_colors_returns_three_free_colors():
    """GET /me/academy-id/colors with licence → 3 colours, all is_owned=True, credit_cost=0."""
    db  = _db_with_license(_license())
    res = get_academy_id_colors(db=db, current_user=_user())

    assert res["active_color_id"] == "official"
    colors = res["colors"]
    assert len(colors) == 3
    ids = {c["id"] for c in colors}
    assert ids == {"official", "ivory", "charcoal"}
    for c in colors:
        assert c["is_owned"]    is True
        assert c["credit_cost"] == 0
        assert c["is_premium"]  is False
        assert "dot_color" in c
        assert "sort_order" in c


# ── AIC-03 ────────────────────────────────────────────────────────────────────

def test_aic_03_colors_reflects_stored_active_color():
    """active_color_id matches what is stored on the licence."""
    db  = _db_with_license(_license(color="charcoal"))
    res = get_academy_id_colors(db=db, current_user=_user())
    assert res["active_color_id"] == "charcoal"


# ── AIC-04 ────────────────────────────────────────────────────────────────────

def test_aic_04_select_unknown_color_raises_400():
    """POST select with unknown color_id → 400."""
    with pytest.raises(HTTPException) as exc:
        select_academy_id_color(
            payload=_SelectPayload("royal_navy"),   # Phase 2 colour — not valid yet
            db=_db_with_license(_license()),
            current_user=_user(),
        )
    assert exc.value.status_code == 400
    assert "royal_navy" in exc.value.detail


# ── AIC-05 ────────────────────────────────────────────────────────────────────

def test_aic_05_select_ivory_updates_color():
    """POST select ivory → active_color_id = 'ivory', DB committed."""
    lic = _license(color="official")
    db  = _db_with_license(lic)

    res = select_academy_id_color(
        payload=_SelectPayload("ivory"),
        db=db,
        current_user=_user(),
    )

    assert res["ok"] is True
    assert res["active_color_id"] == "ivory"
    assert lic.academy_id_color == "ivory"
    db.commit.assert_called_once()


# ── AIC-06 ────────────────────────────────────────────────────────────────────

def test_aic_06_select_no_licence_raises_404():
    """POST select with no licence → 404."""
    with pytest.raises(HTTPException) as exc:
        select_academy_id_color(
            payload=_SelectPayload("charcoal"),
            db=_db_no_license(),
            current_user=_user(),
        )
    assert exc.value.status_code == 404


# ── AIC-07 ────────────────────────────────────────────────────────────────────

def test_aic_07_get_academy_id_includes_active_color():
    """GET /me/academy-id response includes active_color_id when licence present."""
    from app.api.api_v1.endpoints.users.profile import get_academy_id

    user = _user()
    lic  = _license(color="ivory")
    db   = MagicMock()
    # Sequence: query().filter().first() called for licence
    db.query.return_value.filter.return_value.first.return_value = lic

    with patch(f"{_BASE}.assign_lfa_academy_id"), \
         patch(f"{_BASE}.ensure_public_token"):
        res = get_academy_id(db=db, current_user=user)

    assert "active_color_id" in res
    assert res["active_color_id"] == "ivory"


# ── AIC-08 ────────────────────────────────────────────────────────────────────

def test_aic_08_get_academy_id_active_color_none_without_licence():
    """GET /me/academy-id returns active_color_id=None when no licence exists."""
    from app.api.api_v1.endpoints.users.profile import get_academy_id

    user = _user()
    db   = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with patch(f"{_BASE}.assign_lfa_academy_id"), \
         patch(f"{_BASE}.ensure_public_token"):
        res = get_academy_id(db=db, current_user=user)

    assert res["active_color_id"] is None


# ── AIC-09 ────────────────────────────────────────────────────────────────────

def test_aic_09_color_service_is_isolated():
    """academy_id_color_service must not import Player/Welcome/Challenge services."""
    import importlib, ast, pathlib

    src = pathlib.Path(
        "app/services/academy_id_color_service.py"
    ).read_text()
    tree = ast.parse(src)

    forbidden = {
        "card_color_service",
        "card_theme_service",
        "shop_catalog_service",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if node.module else [])
            )
            for name in names:
                for f in forbidden:
                    if f in (name or ""):
                        imported.add(f)

    assert not imported, (
        f"academy_id_color_service must not import: {imported}"
    )


# ── AIC-10 ────────────────────────────────────────────────────────────────────

def test_aic_10_get_active_color_id_fallback():
    """get_active_color_id falls back to 'official' for NULL/unknown values."""
    lic_null    = _license(color=None)
    lic_unknown = _license(color="royal_navy")   # Phase 2, not valid in Phase 1
    lic_empty   = _license(color="")

    assert get_active_color_id(lic_null)    == "official"
    assert get_active_color_id(lic_unknown) == "official"
    assert get_active_color_id(lic_empty)   == "official"
    assert get_active_color_id(_license(color="ivory")) == "ivory"
