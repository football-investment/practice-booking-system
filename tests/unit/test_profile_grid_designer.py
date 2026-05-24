"""
PG — Public Profile Grid Designer tests.

Covers profile_grid_service + CardDraftService grid extensions +
dashboard designer route + player_profile.html rendering.
All tests use MagicMock — no real DB or HTTP server required.

Test list:
  TestSlotRegistry       PG-02  9 slots across left/right/bottom zones
                         PG-03  empty slot state is_empty=True
  TestSlotYouTube        PG-04  YouTube URL → video_youtube module saved
  TestSlotTikTok         PG-05  TikTok canonical URL → video_tiktok module saved
  TestSlotValidation     PG-06  Invalid URL → ValueError, draft untouched
                         PG-07  TikTok short URL → ValueError
  TestDraftIsolation     PG-08  save draft slot → published_data not modified
                         PG-10  remove draft slot → published_data not modified
  TestPublishGrid        PG-09  publish_draft → profile_grid in published_data
                         PG-11  remove + publish → profile_grid cleared from public
  TestIsPublishedGrid    PG-15  is_published False when slot video_id differs
                         PG-16  is_published False when slot provider differs
  TestPubDataIntegrity   PG-17  publish preserves other published_data keys
  TestSlotIdGuards       PG-18  invalid slot_id → ValueError (route returns 404)
                         PG-19  MAX_SLOTS guard fires when grid already full
  TestDesignerRoute      PG-01  designer GET returns 9 draft_slots in context
  TestPublicTemplate     PG-12  player_profile.html references profile_grid_slots
                         PG-13  legacy highlight_video fallback block present
                         PG-14  right_grid_slots block precedes legacy video block
                         PG-20  TikTok grid slot uses CTA link, no iframe in macro
                         PG-21  YouTube grid slot renders youtube-nocookie iframe
                         PG-22  all iframes carry sandbox attribute
  TestRegressions        PG-23  lfa_public_profile_editor.html retains HVE elements
                         PG-24  psp-tiktok-cta present on public profile (PR #170)
                         PG-25  GL grid layout invariants preserved
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.card_draft import CardDraft
from app.services.card_draft_service import CardDraftService
from app.services.profile_grid_service import (
    MAX_SLOTS,
    SLOT_REGISTRY,
    build_draft_grid_state,
    build_published_grid_state,
    grid_fingerprint,
    set_slot,
)

# ── URL fixtures ───────────────────────────────────────────────────────────────

_YT_URL  = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
_YT_VID  = "dQw4w9WgXcQ"
_TT_URL  = "https://www.tiktok.com/@user/video/7123456789012345678"
_TT_VID  = "7123456789012345678"
_TEST_UID = 42

# ── Template fixtures (static text loaded once) ────────────────────────────────

_TMPL_DIR = Path(__file__).parent.parent.parent / "app" / "templates"
_PLAYER_HTML = (_TMPL_DIR / "public" / "player_profile.html").read_text(encoding="utf-8")
_EDITOR_HTML = (_TMPL_DIR / "dashboard" / "lfa_public_profile_editor.html").read_text(encoding="utf-8")
_CARD_EDITOR_HTML = (_TMPL_DIR / "dashboard_card_editor.html").read_text(encoding="utf-8")


# ── Draft builder helper ───────────────────────────────────────────────────────

def _draft(
    draft_theme: str = "default",
    draft_variant: str = "fifa",
    published_theme: str | None = "default",
    published_variant: str | None = "fifa",
    draft_data: dict | None = None,
    published_data: dict | None = None,
) -> CardDraft:
    d = CardDraft()
    d.id                 = 7
    d.user_id            = _TEST_UID
    d.card_type_id       = "player_card"
    d.instance_name      = "default"
    d.draft_theme        = draft_theme
    d.draft_variant      = draft_variant
    d.draft_platform     = None
    d.draft_data         = draft_data
    d.published_theme    = published_theme
    d.published_variant  = published_variant
    d.published_platform = None
    d.published_data     = published_data
    d.published_at       = datetime.now(timezone.utc) if published_theme else None
    d.created_at         = datetime.now(timezone.utc)
    d.updated_at         = datetime.now(timezone.utc)
    return d


# ── PG-02/03: Slot registry ────────────────────────────────────────────────────

class TestSlotRegistry:

    def test_pg_02_slot_registry_has_9_slots_across_three_zones(self):
        """PG-02: SLOT_REGISTRY has 9 slots: 3 left + 3 right + 3 bottom."""
        assert len(SLOT_REGISTRY) == 9
        assert MAX_SLOTS == 9
        zones = {s["zone"] for s in SLOT_REGISTRY}
        assert zones == {"left", "right", "bottom"}
        for zone in zones:
            assert len([s for s in SLOT_REGISTRY if s["zone"] == zone]) == 3

    def test_pg_03_empty_draft_grid_state_all_slots_empty(self):
        """PG-03: build_draft_grid_state on an empty draft returns 9 slots, all is_empty."""
        draft = _draft()
        slots = build_draft_grid_state(draft)
        assert len(slots) == 9
        for slot in slots:
            assert slot["is_empty"] is True
            assert slot["module"] is None


# ── PG-04/05: Slot save ────────────────────────────────────────────────────────

class TestSlotYouTube:

    def test_pg_04_youtube_url_saved_as_video_youtube_module(self):
        """PG-04: set_draft_slot writes a video_youtube module into draft_data.profile_grid."""
        draft = _draft()
        db = MagicMock()
        CardDraftService.set_draft_slot(db, draft, "right_1", _YT_URL, "My goal")
        pg = (draft.draft_data or {}).get("profile_grid")
        assert pg is not None
        slots = pg.get("slots", [])
        assert len(slots) == 1
        entry = slots[0]
        assert entry["slot_id"] == "right_1"
        assert entry["module"]["type"] == "video_youtube"
        assert entry["module"]["provider"] == "youtube"
        assert entry["module"]["video_id"] == _YT_VID
        assert entry["module"]["title"] == "My goal"
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(draft)


class TestSlotTikTok:

    def test_pg_05_tiktok_canonical_url_saved_as_video_tiktok_module(self):
        """PG-05: set_draft_slot writes a video_tiktok module for canonical TikTok URL."""
        draft = _draft()
        db = MagicMock()
        CardDraftService.set_draft_slot(db, draft, "left_1", _TT_URL, "Skill clip")
        pg = (draft.draft_data or {}).get("profile_grid")
        assert pg is not None
        entry = pg["slots"][0]
        assert entry["slot_id"] == "left_1"
        assert entry["module"]["type"] == "video_tiktok"
        assert entry["module"]["provider"] == "tiktok"
        assert entry["module"]["video_id"] == _TT_VID
        assert entry["module"]["source_url"] == _TT_URL


# ── PG-06/07: URL validation ──────────────────────────────────────────────────

class TestSlotValidation:

    def test_pg_06_invalid_url_raises_value_error_draft_untouched(self):
        """PG-06: Non-video URL raises ValueError; draft_data stays None, no commit."""
        draft = _draft(draft_data=None)
        db = MagicMock()
        with pytest.raises(ValueError):
            CardDraftService.set_draft_slot(db, draft, "right_1", "https://example.com/not-a-video")
        assert draft.draft_data is None
        db.commit.assert_not_called()

    def test_pg_07_tiktok_short_url_rejected_with_informative_error(self):
        """PG-07: TikTok short URL (vm.tiktok.com) raises ValueError with 'short' in message."""
        draft = _draft(draft_data=None)
        db = MagicMock()
        with pytest.raises(ValueError, match="full TikTok"):
            CardDraftService.set_draft_slot(db, draft, "right_1", "https://vm.tiktok.com/ZMeABCDEF/")
        assert draft.draft_data is None


# ── PG-08/10: Draft isolation ─────────────────────────────────────────────────

class TestDraftIsolation:

    def test_pg_08_set_draft_slot_does_not_touch_published_data(self):
        """PG-08: Saving a draft slot never modifies published_data."""
        original_pub = {"highlight_video": {"provider": "youtube", "video_id": "pub123"}}
        draft = _draft(published_data=original_pub)
        db = MagicMock()
        CardDraftService.set_draft_slot(db, draft, "right_1", _YT_URL)
        assert draft.published_data == original_pub

    def test_pg_10_remove_draft_slot_does_not_touch_published_data(self):
        """PG-10: Removing a draft slot never modifies published_data."""
        pg = {"version": 1, "slots": [{"slot_id": "right_1", "module": {
            "provider": "youtube", "video_id": "abc", "type": "video_youtube", "title": ""
        }}]}
        original_pub = {"profile_grid": pg}
        draft = _draft(draft_data={"profile_grid": pg}, published_data=original_pub)
        db = MagicMock()
        CardDraftService.remove_draft_slot(db, draft, "right_1")
        assert draft.published_data == original_pub


# ── PG-09/11: Publish grid ────────────────────────────────────────────────────

class TestPublishGrid:

    def test_pg_09_publish_draft_copies_profile_grid_into_published_data(self):
        """PG-09: publish_draft copies draft_data.profile_grid into published_data."""
        draft = _draft()
        db = MagicMock()
        CardDraftService.set_draft_slot(db, draft, "right_1", _YT_URL, commit=False)
        CardDraftService.publish_draft(db, draft)
        pub_pg = (draft.published_data or {}).get("profile_grid")
        assert pub_pg is not None
        assert pub_pg["slots"][0]["slot_id"] == "right_1"
        assert pub_pg["slots"][0]["module"]["provider"] == "youtube"

    def test_pg_11_remove_and_publish_clears_profile_grid_from_published_data(self):
        """PG-11: Removing a slot from draft and publishing clears it from published_data."""
        draft = _draft()
        db = MagicMock()
        CardDraftService.set_draft_slot(db, draft, "right_1", _YT_URL, commit=False)
        CardDraftService.publish_draft(db, draft, commit=False)
        assert (draft.published_data or {}).get("profile_grid") is not None

        CardDraftService.remove_draft_slot(db, draft, "right_1", commit=False)
        CardDraftService.publish_draft(db, draft)
        assert (draft.published_data or {}).get("profile_grid") is None


# ── PG-15/16: is_published with grid ─────────────────────────────────────────

class TestIsPublishedGrid:

    def _pg(self, slot_id: str, provider: str, video_id: str) -> dict:
        return {"version": 1, "slots": [
            {"slot_id": slot_id, "module": {"provider": provider, "video_id": video_id}}
        ]}

    def test_pg_15_is_published_false_when_slot_video_id_differs(self):
        """PG-15: is_published False when draft grid slot video_id != published slot video_id."""
        draft = _draft(
            draft_data=    {"profile_grid": self._pg("right_1", "youtube", "draft_vid")},
            published_data={"profile_grid": self._pg("right_1", "youtube", "pub_vid")},
        )
        assert CardDraftService.is_published(draft) is False

    def test_pg_16_is_published_false_when_slot_provider_differs(self):
        """PG-16: is_published False when draft provider != published provider (same video_id)."""
        draft = _draft(
            draft_data=    {"profile_grid": self._pg("right_1", "youtube", "abc123")},
            published_data={"profile_grid": self._pg("right_1", "tiktok",  "abc123")},
        )
        assert CardDraftService.is_published(draft) is False


# ── PG-17: Published data integrity ──────────────────────────────────────────

class TestPubDataIntegrity:

    def test_pg_17_publish_merges_profile_grid_preserving_other_keys(self):
        """PG-17: publish_draft merges profile_grid without wholesale published_data replacement.

        publish_draft only writes highlight_video and profile_grid; other keys survive.
        """
        draft = _draft(published_data={"some_future_key": "preserved_value"})
        draft.draft_data = {"profile_grid": {"version": 1, "slots": [
            {"slot_id": "left_1", "module": {"provider": "youtube", "video_id": "grid_vid"}}
        ]}}
        db = MagicMock()
        CardDraftService.publish_draft(db, draft)
        assert draft.published_data.get("some_future_key") == "preserved_value", (
            "publish_draft must not wipe keys outside the highlight_video/profile_grid merge set"
        )
        assert draft.published_data.get("profile_grid") is not None


# ── PG-18/19: Slot ID guards ──────────────────────────────────────────────────

class TestSlotIdGuards:

    def test_pg_18_invalid_slot_id_raises_value_error(self):
        """PG-18: Unknown slot_id raises ValueError (dashboard route returns 404)."""
        draft = _draft()
        db = MagicMock()
        with pytest.raises(ValueError, match="Unknown slot_id"):
            CardDraftService.set_draft_slot(db, draft, "not_a_real_slot", _YT_URL)

    def test_pg_19_max_slots_guard_fires_when_grid_is_full(self):
        """PG-19: set_slot raises ValueError when 9 existing non-overlapping entries are present."""
        # Craft a grid with 9 phantom entries (not in SLOT_IDS) so "right_1" is a new slot
        full_grid = {"version": 1, "slots": [
            {"slot_id": f"zone_phantom_{i}", "module": {}} for i in range(9)
        ]}
        with pytest.raises(ValueError, match="Maximum"):
            set_slot(full_grid, "right_1", {})


# ── PG-01: Designer GET route ─────────────────────────────────────────────────

class TestDesignerRoute:

    def test_pg_01_designer_get_returns_9_draft_slots_in_context(self):
        """PG-01: GET /dashboard/.../public-profile-editor renders with 9 draft_slots (all empty)."""
        from app.api.web_routes.dashboard import lfa_public_profile_editor

        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.id = _TEST_UID
        mock_license = MagicMock()
        mock_license.user_id = _TEST_UID
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_license

        draft = _draft()
        captured: dict = {}

        def fake_response(req, template_name, context):
            captured["context"] = context
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch("app.api.web_routes.dashboard._CardDraftService") as MockCDS, \
             patch("app.api.web_routes.dashboard.templates") as mock_tpl, \
             patch("app.api.web_routes.dashboard._get_lfa_license", return_value=mock_license):
            MockCDS.get_player_card_draft.return_value = draft
            MockCDS.is_published.return_value = False
            mock_tpl.TemplateResponse.side_effect = fake_response
            asyncio.run(lfa_public_profile_editor(
                request=mock_request, db=mock_db, user=mock_user,
            ))

        ctx = captured.get("context", {})
        draft_slots = ctx.get("draft_slots", [])
        assert len(draft_slots) == 9, f"Expected 9 draft_slots, got {len(draft_slots)}"
        assert all(s["is_empty"] is True for s in draft_slots)


# ── PG-12..14 / PG-20..22: Public profile template ───────────────────────────

class TestPublicTemplate:

    def test_pg_12_player_profile_references_profile_grid_slots(self):
        """PG-12: player_profile.html uses profile_grid_slots for grid slot rendering."""
        assert "profile_grid_slots" in _PLAYER_HTML, (
            "player_profile.html must reference the profile_grid_slots context variable"
        )
        assert "slot.zone" in _PLAYER_HTML, (
            "player_profile.html must iterate profile_grid_slots by zone"
        )

    def test_pg_13_legacy_highlight_video_fallback_block_present(self):
        """PG-13: Legacy highlight_video block is retained as fallback when no grid slots."""
        assert "right_grid_slots" in _PLAYER_HTML, (
            "player_profile.html must define right_grid_slots for the override check"
        )
        assert "highlight_video.provider" in _PLAYER_HTML, (
            "Legacy highlight_video rendering must remain in player_profile.html"
        )

    def test_pg_14_right_grid_slots_precedes_legacy_highlight_video(self):
        """PG-14: right_grid_slots override block appears before the legacy Highlight Video section."""
        grid_pos   = _PLAYER_HTML.index("right_grid_slots")
        legacy_pos = _PLAYER_HTML.index("Highlight Video")
        assert grid_pos < legacy_pos, (
            "right_grid_slots block must precede the legacy 'Highlight Video' section"
        )

    def test_pg_20_tiktok_grid_slot_macro_uses_cta_link_not_iframe(self):
        """PG-20: render_slot_module macro TikTok branch uses <a href>, never <iframe>."""
        macro_start = _PLAYER_HTML.index("{% macro render_slot_module")
        macro_end   = _PLAYER_HTML.index("{% endmacro %}", macro_start) + len("{% endmacro %}")
        macro_body  = _PLAYER_HTML[macro_start:macro_end]

        assert 'provider == "tiktok"' in macro_body
        tiktok_pos     = macro_body.index('provider == "tiktok"')
        tiktok_section = macro_body[tiktok_pos:]
        assert "<iframe" not in tiktok_section, (
            "TikTok grid slot must not use <iframe — link-only CTA required (no CSP expansion)"
        )
        assert "source_url" in tiktok_section, (
            "TikTok CTA must use module.source_url as the href"
        )

    def test_pg_21_youtube_grid_slot_macro_renders_nocookie_iframe(self):
        """PG-21: render_slot_module macro YouTube branch renders youtube-nocookie.com iframe."""
        macro_start = _PLAYER_HTML.index("{% macro render_slot_module")
        macro_end   = _PLAYER_HTML.index("{% endmacro %}", macro_start) + len("{% endmacro %}")
        macro_body  = _PLAYER_HTML[macro_start:macro_end]
        assert "youtube-nocookie.com/embed" in macro_body, (
            "YouTube grid slot must use youtube-nocookie.com/embed iframe"
        )
        assert "<iframe" in macro_body

    def test_pg_22_all_iframes_carry_sandbox_attribute(self):
        """PG-22: Every <iframe> in player_profile.html includes a sandbox= attribute."""
        import re
        iframes = re.findall(r'<iframe[^>]+>', _PLAYER_HTML)
        assert len(iframes) > 0, "No iframes found in player_profile.html"
        for iframe in iframes:
            assert "sandbox=" in iframe, (
                f"iframe missing sandbox attribute (XSS risk): {iframe[:120]!r}"
            )


# ── PG-23..25: Regressions ────────────────────────────────────────────────────

class TestRegressions:

    def test_pg_23_hve_card_editor_template_retains_highlight_video_elements(self):
        """PG-23: dashboard_card_editor.html (HVE home) still contains HVE elements (PR #169 regression)."""
        assert "Highlight Video" in _CARD_EDITOR_HTML, (
            "HVE: 'Highlight Video' section missing from dashboard_card_editor.html — regression"
        )
        assert "draft_highlight_video" in _CARD_EDITOR_HTML, (
            "HVE: draft_highlight_video context variable missing from dashboard_card_editor.html"
        )
        # Profile grid editor has its own template; verify it has draft_slots
        assert "draft_slots" in _EDITOR_HTML, (
            "Profile grid draft_slots reference missing from lfa_public_profile_editor.html"
        )

    def test_pg_24_tiktok_cta_class_present_on_public_profile(self):
        """PG-24: psp-tiktok-cta class present in player_profile.html (PR #170 regression)."""
        assert "psp-tiktok-cta" in _PLAYER_HTML, (
            "psp-tiktok-cta class missing — regression from PR #170 TikTok integration"
        )

    def test_pg_25_gl_grid_layout_invariants_preserved(self):
        """PG-25: Core GL grid layout invariants still hold (PR #171 regression)."""
        assert "36px" in _PLAYER_HTML, "GL-01: base laptop grid must use 36px slot columns"
        assert "56px" in _PLAYER_HTML, "GL-04: large desktop (≥1440px) must use 56px slot columns"
        assert "grid-area: l-slot" in _PLAYER_HTML, "GL-02: l-slot grid-area must be defined"
        assert "grid-area: r-slot" in _PLAYER_HTML, "GL-02: r-slot grid-area must be defined"
        assert 'class="psp-l-slot"' in _PLAYER_HTML, "GL-03: psp-l-slot placeholder div must be present"
        assert 'class="psp-r-slot"' in _PLAYER_HTML, "GL-03: psp-r-slot placeholder div must be present"
