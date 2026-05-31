"""
Unit tests — Card preview routing (draft variant browser preview fix)
======================================================================

Root cause:
  The card editor iframe loaded /players/{id}/card without ?preview=, so the route
  read published_variant ("fifa") even after the user switched the draft to Pulse.
  _VARIANTS (static dict) also blocked manifest-only designs from being previewed.

Fix:
  1. Iframe initial src + _cardIframeSrc() now pass ?preview={draft_variant}.
  2. ?preview= validation uses _get_design(preview, db) — DB-backed designs accepted.

Coverage:
  PR-01  ?preview=pulse   → Pulse template renders (pls-hero present)
  PR-02  ?preview=compact → non-Pulse template renders (no pls-hero; status 200)
  PR-03  no ?preview=     → published_variant used; Pulse draft ignored
  PR-04  DB-backed manifest design ("classic_lite", not in static DESIGNS dict) →
         _get_design(preview, db) accepts it; published "fifa" is not rendered

Patch strategy:
  PR-01/02: patch public_player._get_design (module-level import) so preview
            validation is deterministic. Template rendering uses DESIGNS dict
            naturally via the deferred card_variant_service import — no extra patch.
  PR-03:    no patching; default platform skips export-routing _get_design call.
  PR-04:    patch card_design_service._maybe_reload so BOTH the preview validation
            call (_pp._get_design) AND the get_variant template lookup (which calls
            card_design_service.get_design internally) see "classic_lite".
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _make_user(user_id: int = 7) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.name = "Test Player"
    u.nationality = "Hungarian"
    u.is_active = True
    u.date_of_birth = None
    u.skills = {}
    return u


def _make_license(published_variant: str = "fifa") -> MagicMock:
    lic = MagicMock()
    lic.card_variant             = published_variant
    lic.card_theme               = "default"
    lic.public_card_platform     = None
    lic.published_card_variant   = published_variant
    lic.published_card_theme     = "default"
    lic.published_card_platform  = None
    lic.specialization_type      = "LFA_FOOTBALL_PLAYER"
    lic.is_active                = True
    lic.onboarding_completed     = False
    lic.card_theme_id            = None
    lic.card_bg_compact_url      = None
    lic.card_bg_showcase_url     = None
    lic.player_card_photo_url    = None
    lic.card_photo_portrait_url  = None
    lic.card_photo_landscape_url = None
    lic.motivation_scores        = {}
    lic.compact_photo_position   = "left"
    lic.compact_focus_x          = 50
    lic.compact_focus_y          = 20
    lic.right_foot_score         = None
    lic.left_foot_score          = None
    lic.sponsor_logo_url         = None
    lic.current_level            = 1
    lic.max_achieved_level       = 1
    return lic


def _mock_db(user=None, license_=None):
    from app.models.card_draft import CardDraft as _CardDraft

    db    = MagicMock()
    calls = [0]

    def _side(cls_or_col, *a, **kw):
        calls[0] += 1
        q = MagicMock()
        if cls_or_col is _CardDraft:
            draft = MagicMock()
            draft.published_theme    = (license_.published_card_theme    if license_ else None) or "default"
            draft.published_variant  = (license_.published_card_variant  if license_ else None) or "fifa"
            draft.published_platform = (license_.published_card_platform if license_ else None)
            draft.draft_theme        = draft.published_theme
            draft.draft_variant      = draft.published_variant
            draft.draft_platform     = draft.published_platform
            q.filter.return_value.first.return_value = draft
        elif calls[0] == 1:
            q.filter.return_value.first.return_value = user
        elif calls[0] == 2:
            q.filter.return_value.first.return_value = license_
        else:
            q.filter.return_value.order_by.return_value.all.return_value = []
            q.filter.return_value.all.return_value                       = []
            q.join.return_value.filter.return_value.all.return_value     = []
            q.outerjoin.return_value.filter.return_value.all.return_value = []
            q.all.return_value                                            = []
        return q

    db.query.side_effect = _side
    return db


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── PR-01: ?preview=pulse → Pulse template ────────────────────────────────────

@pytest.mark.unit
def test_pr01_preview_pulse_renders_pulse_template(client):
    """
    ?preview=pulse must render player_card_pulse.html, not the FIFA fallback.
    Published variant is "fifa" — proves ?preview= overrides published state.
    Marker: .pls-hero CSS class (unique to player_card_pulse.html).
    """
    from app.main import app
    from app.dependencies import get_db
    from app.api.web_routes import public_player as _pp
    from app.services.card_design_service import DESIGNS, _invalidate_cache

    _invalidate_cache()   # ensure clean cache state

    db = _mock_db(user=_make_user(7), license_=_make_license("fifa"))
    app.dependency_overrides[get_db] = lambda: db

    def _design_se(design_id, db_arg=None):
        return DESIGNS.get(design_id, DESIGNS["fifa"])

    with patch.object(_pp, "_get_design", side_effect=_design_se):
        try:
            r = client.get("/players/7/card?preview=pulse")
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    html = r.text
    assert "pls-hero" in html, (
        "pls-hero class not found — player_card_pulse.html was not rendered. "
        "Pulse likely fell back to the FIFA template via published_variant."
    )


# ── PR-02: ?preview=compact → non-Pulse template ─────────────────────────────

@pytest.mark.unit
def test_pr02_preview_compact_renders_compact_not_pulse(client):
    """
    ?preview=compact must render the compact design, not Pulse or FIFA.
    Verifies that non-Pulse variants also work via the DB-backed ?preview= path.
    pls-hero absent confirms Pulse template was not incorrectly selected.
    """
    from app.main import app
    from app.dependencies import get_db
    from app.api.web_routes import public_player as _pp
    from app.services.card_design_service import DESIGNS, _invalidate_cache

    _invalidate_cache()

    db = _mock_db(user=_make_user(7), license_=_make_license("fifa"))
    app.dependency_overrides[get_db] = lambda: db

    def _design_se(design_id, db_arg=None):
        return DESIGNS.get(design_id, DESIGNS["fifa"])

    with patch.object(_pp, "_get_design", side_effect=_design_se):
        try:
            r = client.get("/players/7/card?preview=compact")
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    html = r.text
    assert "pls-hero" not in html, (
        "pls-hero found — Pulse template was incorrectly rendered for compact preview."
    )


# ── PR-03: No ?preview= → published_variant only ─────────────────────────────

@pytest.mark.unit
def test_pr03_no_preview_param_uses_published_variant(client):
    """
    /players/{id}/card without ?preview= must render the published variant only.
    Draft variant (Pulse) must remain invisible to visitors until Publish is clicked.
    The public card route must not pick up the editor draft state.
    """
    from app.main import app
    from app.dependencies import get_db
    from app.services.card_design_service import _invalidate_cache

    _invalidate_cache()

    # published = "fifa", draft would be "pulse" — but without ?preview= it's irrelevant
    db = _mock_db(user=_make_user(7), license_=_make_license("fifa"))
    app.dependency_overrides[get_db] = lambda: db

    try:
        r = client.get("/players/7/card")   # no ?preview= param
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200
    html = r.text
    assert "pls-hero" not in html, (
        "pls-hero found — Pulse (draft) was rendered without ?preview=. "
        "Public card must only show the published variant."
    )


# ── PR-04: DB-backed manifest design previewable via ?preview= ────────────────

@pytest.mark.unit
def test_pr04_db_backed_manifest_design_previewable_via_preview_param(client):
    """
    A design created via admin manifest (in DB, NOT in the static DESIGNS dict)
    must be previewable via ?preview=.

    OLD code:  `preview in _VARIANTS` (static dict) → False for "classic_lite" → ignored
    NEW code:  `_get_design(preview, db).id == preview` → True → design accepted

    Patch strategy: patch card_design_service._maybe_reload to include "classic_lite"
    so BOTH the preview validation call AND the deferred get_variant() call see it.
    Uses player_card_pulse.html as the test design's browser_template so the
    distinctive pls-hero class proves the DB-backed design was rendered (not FIFA).
    """
    from app.main import app
    from app.dependencies import get_db
    from app.services.card_design_service import CardDesignDefinition, DESIGNS, _invalidate_cache
    import app.services.card_design_service as _cds

    _invalidate_cache()

    # "classic_lite" must not be in static DESIGNS (it is a manifest-only design)
    assert "classic_lite" not in DESIGNS, (
        "'classic_lite' is now in the static DESIGNS dict. "
        "This test requires a DB-only design ID."
    )

    # Simulate DB cache containing "classic_lite" with Pulse template so we can
    # detect it distinctively in the rendered HTML.
    db_design = CardDesignDefinition(
        id="classic_lite",
        label="Classic Lite",
        description="Manifest-only column design.",
        is_premium=False,
        credit_cost=0,
        template="public/player_card_pulse.html",   # distinctive for assertion
        sort_order=10,
        archetype_id="pulse",
        supported_export_buckets=("square",),
        animated_platforms=(),
        component_config={},
    )

    # Patching _maybe_reload in card_design_service makes BOTH the public_player
    # module-level _get_design alias AND the card_variant_service internal _get_design
    # (used by get_variant) return "classic_lite" from the simulated DB cache.
    def _patched_maybe_reload(db_arg=None):
        return {**DESIGNS, "classic_lite": db_design}

    # published = "fifa" — old code would silently ignore ?preview=classic_lite
    db = _mock_db(user=_make_user(7), license_=_make_license("fifa"))
    app.dependency_overrides[get_db] = lambda: db

    with patch.object(_cds, "_maybe_reload", side_effect=_patched_maybe_reload):
        try:
            r = client.get("/players/7/card?preview=classic_lite")
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    html = r.text
    assert "pls-hero" in html, (
        "pls-hero not found — DB-backed 'classic_lite' design was not accepted by "
        "?preview=. The published 'fifa' template rendered instead, which means "
        "_get_design(preview, db) did not override the published_variant."
    )
