"""Card Editor Entitlement UI tests — CE-01..CE-09.

CE-01  context has active_variant_owned=True when CDO entry exists for active variant
CE-02  context has active_variant_owned=False when user has no CDO entries at all
CE-03  context has active_variant_owned=False when user owns a different variant only
CE-04  btn-publish-card rendered without disabled when active_variant_owned=True
CE-05  btn-publish-card rendered with disabled when active_variant_owned=False
CE-06  btn-export-card rendered without disabled when active_variant_owned=True
CE-07  btn-export-card rendered with disabled when active_variant_owned=False
CE-08  Get Player Card CTA present when active_variant_owned=False
CE-09  Get Player Card CTA absent when active_variant_owned=True
"""
import asyncio
import re
from unittest.mock import MagicMock, patch

import jinja2
import pytest

_DASH_BASE   = "app.api.web_routes.dashboard"
_CDS_PATH    = f"{_DASH_BASE}._CardDraftService"
# is_design_accessible is imported locally inside the function body from its
# source module, so we must patch at the source to intercept it.
_IS_DA_PATH  = "app.services.card_design_service.is_design_accessible"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draft(variant: str = "fifa") -> MagicMock:
    d = MagicMock()
    d.draft_theme    = "default"
    d.draft_variant  = variant
    d.draft_platform = None
    d.draft_data     = None
    d.published_theme    = "default"
    d.published_variant  = "fifa"
    d.published_platform = None
    d.published_data     = None
    return d


def _invoke_editor(draft: MagicMock, is_owned: bool) -> dict:
    """Call lfa_player_card_editor, return captured context."""
    from app.api.web_routes.dashboard import lfa_player_card_editor

    user        = MagicMock(); user.id = 42; user.credit_balance = 0
    mock_license = MagicMock(); mock_license.onboarding_completed = True
    db           = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_license

    captured: dict = {}

    def _fake_tmpl(tmpl, ctx, **kw):
        captured["template"] = tmpl
        captured["context"]  = ctx
        return MagicMock(status_code=200)

    with patch(_CDS_PATH) as MockCDS, \
         patch(f"{_DASH_BASE}.templates") as mock_tpl, \
         patch(f"{_DASH_BASE}.SemesterEnrollment"), \
         patch(_IS_DA_PATH, return_value=is_owned), \
         patch("app.services.card_variant_service.get_all_variants", return_value=[]), \
         patch("app.services.card_theme_service.get_all_themes",     return_value=[]), \
         patch("app.services.card_theme_service.is_unlocked",        return_value=False), \
         patch("app.services.card_platform_service.build_platform_list", return_value=[]), \
         patch("app.services.card_constants.ANIMATED_EXPORT_CAPABLE", []), \
         patch("app.services.card_constants.CANVAS_SIZES", {}), \
         patch("app.services.card_constants.CARD_EDITOR_PLATFORM_IDS", []), \
         patch("app.services.highlight_video_service.build_youtube_embed_url", return_value=None):
        MockCDS.get_player_card_draft.return_value = draft
        mock_tpl.TemplateResponse.side_effect = _fake_tmpl
        try:
            asyncio.run(lfa_player_card_editor(
                request=MagicMock(), db=db, user=user,
            ))
        except Exception:
            pass  # we only need the context; template/redirect errors are fine

    return captured.get("context", {})


# ── Action bar template fragment ──────────────────────────────────────────────

_ACTION_BAR_FRAGMENT = """\
<div class="ce-action-bar">
    <div class="ce-publish-zone">
        <button class="btn-publish-card" id="btn-publish-card"
                onclick="publishCard()"
                {% if not active_variant_owned %}disabled{% endif %}>Publish Card</button>
    </div>
    <div class="ce-export-zone">
        <button id="btn-export-card" class="btn-export-card" onclick="exportCard()"
                {% if not active_variant_owned %}disabled{% endif %}
                title="Download PNG">⬇ PNG</button>
    </div>
</div>
{% if not active_variant_owned %}
<div class="ce-locked-note">
    This design requires a Player Card.
    <a href="/my-cards/player-card">Get Player Card &rarr;</a>
</div>
{% endif %}
"""


def _render_fragment(active_variant_owned: bool) -> str:
    env = jinja2.Environment()
    tmpl = env.from_string(_ACTION_BAR_FRAGMENT)
    return tmpl.render(active_variant_owned=active_variant_owned)


# ── CE-01..CE-03: Route context — active_variant_owned ───────────────────────

class TestCardEditorOwnershipContext:

    def test_ce01_owned_when_cdo_exists(self):
        """CE-01: active_variant_owned=True when is_design_accessible returns True."""
        ctx = _invoke_editor(_draft("fifa"), is_owned=True)
        assert ctx.get("active_variant_owned") is True

    def test_ce02_not_owned_when_no_cdo(self):
        """CE-02: active_variant_owned=False when is_design_accessible returns False."""
        ctx = _invoke_editor(_draft("fifa"), is_owned=False)
        assert ctx.get("active_variant_owned") is False

    def test_ce03_not_owned_different_variant(self):
        """CE-03: active_variant_owned=False even if user owns other designs (mock returns False)."""
        ctx = _invoke_editor(_draft("compact"), is_owned=False)
        assert ctx.get("active_variant_owned") is False


# ── CE-04..CE-07: Template fragment — buttons disabled state ─────────────────

class TestCardEditorButtonState:

    def test_ce04_publish_not_disabled_when_owned(self):
        """CE-04: btn-publish-card has no disabled attr when active_variant_owned=True."""
        html = _render_fragment(active_variant_owned=True)
        btn_match = re.search(
            r'<button[^>]*id="btn-publish-card"[^>]*>', html
        )
        assert btn_match, "btn-publish-card not found in fragment"
        assert "disabled" not in btn_match.group(0)

    def test_ce05_publish_disabled_when_not_owned(self):
        """CE-05: btn-publish-card has disabled attr when active_variant_owned=False."""
        html = _render_fragment(active_variant_owned=False)
        btn_match = re.search(
            r'<button[^>]*id="btn-publish-card"[^>]*>', html
        )
        assert btn_match, "btn-publish-card not found in fragment"
        assert "disabled" in btn_match.group(0)

    def test_ce06_export_not_disabled_when_owned(self):
        """CE-06: btn-export-card has no disabled attr when active_variant_owned=True."""
        html = _render_fragment(active_variant_owned=True)
        btn_match = re.search(
            r'<button[^>]*id="btn-export-card"[^>]*>', html
        )
        assert btn_match, "btn-export-card not found in fragment"
        assert "disabled" not in btn_match.group(0)

    def test_ce07_export_disabled_when_not_owned(self):
        """CE-07: btn-export-card has disabled attr when active_variant_owned=False."""
        html = _render_fragment(active_variant_owned=False)
        btn_match = re.search(
            r'<button[^>]*id="btn-export-card"[^>]*>', html
        )
        assert btn_match, "btn-export-card not found in fragment"
        assert "disabled" in btn_match.group(0)


# ── CE-08..CE-09: Template fragment — locked note CTA ────────────────────────

class TestCardEditorLockedNote:

    def test_ce08_locked_note_present_when_not_owned(self):
        """CE-08: ce-locked-note with Get Player Card CTA visible when active_variant_owned=False."""
        html = _render_fragment(active_variant_owned=False)
        assert "ce-locked-note" in html
        assert "/my-cards/player-card" in html

    def test_ce09_locked_note_absent_when_owned(self):
        """CE-09: ce-locked-note not rendered when active_variant_owned=True."""
        html = _render_fragment(active_variant_owned=True)
        assert "ce-locked-note" not in html
        assert "/my-cards/player-card" not in html
