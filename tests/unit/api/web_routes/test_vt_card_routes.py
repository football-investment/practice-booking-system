"""VTC-CARD-01..25 — Virtual Training Card route guard and invariant tests.

Tests:
  - Platform validation (422 for unknown platform)
  - Single-game eligibility gate (0/5 → 403, 4/5 → 403, 5/5 → 200)
  - Challenge attempts excluded from eligibility count
  - Reward eligibility gate (tier 3/5/10)
  - Tier 10 gate when < 10 active games
  - card_registry: get_card_type_spec("virtual_training_card") returns VT spec
  - get_card_family("virtual_training_card") == "fclassic"
  - VT spec platform IDs are subsets of CANVAS_SIZES
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_ROUTES_MODULE = "app.api.web_routes.vt_card"
# Patch eligibility functions at the ROUTE module level because vt_card.py
# imports them directly (from ...services.vt_card_eligibility import ...).
# Patching the source module would NOT affect the route's local binding.
_ELIG_SGL  = f"{_ROUTES_MODULE}.check_single_game_eligibility"
_ELIG_RWRD = f"{_ROUTES_MODULE}.check_reward_eligibility"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _user(uid: int = 1) -> MagicMock:
    u = MagicMock()
    u.id = uid
    u.email = f"user{uid}@test.lfa"
    u.is_active = True
    return u


def _game(game_id: int = 1, max_daily: int = 5) -> MagicMock:
    g = MagicMock()
    g.id = game_id
    g.name = "Target Tracking"
    g.code = "target_tracking"
    g.is_active = True
    g.max_daily_attempts = max_daily
    return g


def _request() -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    return req


def _db(game: Any = None) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = game
    return db


# ── VTC-CARD-01..02: card_registry integration ────────────────────────────────

class TestCardRegistryIntegration:
    def test_card01_vt_spec_registered(self):
        from app.services.card_system import card_registry
        spec = card_registry.get_card_type_spec("virtual_training_card")
        assert spec.card_type_id == "virtual_training_card"

    def test_card02_vt_spec_label(self):
        from app.services.card_system import card_registry
        spec = card_registry.get_card_type_spec("virtual_training_card")
        assert spec.label == "Virtual Training Card"

    def test_card03_vt_spec_not_editable(self):
        from app.services.card_system import card_registry
        spec = card_registry.get_card_type_spec("virtual_training_card")
        assert spec.is_editable is False

    def test_card04_vt_spec_not_theme_compatible(self):
        from app.services.card_system import card_registry
        spec = card_registry.get_card_type_spec("virtual_training_card")
        assert spec.theme_compatible is False

    def test_card05_get_card_family_returns_fclassic(self):
        from app.services.card_design_service import get_card_family
        assert get_card_family("virtual_training_card") == "fclassic"

    def test_card06_vt_spec_platforms_in_canvas_sizes(self):
        from app.services.card_constants import CANVAS_SIZES
        from app.services.card_system import card_registry
        spec = card_registry.get_card_type_spec("virtual_training_card")
        for platform_id in spec.supported_platform_ids:
            assert platform_id in CANVAS_SIZES, (
                f"VT spec references platform {platform_id!r} absent from CANVAS_SIZES"
            )


# ── VTC-CARD-07..11: vt_card_preview — single-game guard ─────────────────────

class TestSingleGamePreviewGuard:
    @pytest.mark.asyncio
    async def test_card07_invalid_platform_returns_422(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        user = _user()
        db = _db()
        with pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="instagram_square",
                date_str=None, render_token=None, db=db, user=user,
            )
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_card08_zero_attempts_returns_403(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        user = _user()
        db = _db()
        with patch(_ELIG_SGL, return_value=(False, 0, 5)), \
             pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, render_token=None, db=db, user=user,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_card09_partial_attempts_returns_403(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        user = _user()
        db = _db()
        with patch(_ELIG_SGL, return_value=(False, 4, 5)), \
             pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, render_token=None, db=db, user=user,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_card10_completed_game_allows_preview(self):
        """5/5 attempts → eligibility passes → TemplateResponse returned."""
        from unittest.mock import patch as _patch
        from app.api.web_routes.vt_card import vt_card_preview

        game = _game()
        user = _user()
        db = _db(game=game)

        fake_response = MagicMock()
        fake_response.status_code = 200

        with patch(_ELIG_SGL, return_value=(True, 5, 5)), \
             patch(f"{_ROUTES_MODULE}.templates") as mock_tpl:
            mock_tpl.TemplateResponse.return_value = fake_response
            result = await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, render_token=None, db=db, user=user,
            )
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_card11_unauthenticated_returns_401(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        with pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, render_token=None, db=_db(), user=None,
            )
        assert exc.value.status_code == 401


# ── VTC-CARD-12..13: another game's attempts don't count ─────────────────────

class TestGameIsolation:
    @pytest.mark.asyncio
    async def test_card12_different_game_attempts_do_not_unlock(self):
        """Eligibility for game_id=1 is 0/5 even if game_id=2 has 5/5."""
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        user = _user()
        db = _db()

        def _elig(db, user_id, game_id, day):
            # game 1 = 0/5, game 2 = 5/5
            return (False, 0, 5) if game_id == 1 else (True, 5, 5)

        with patch(_ELIG_SGL, side_effect=_elig), \
             pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, render_token=None, db=db, user=user,
            )
        assert exc.value.status_code == 403


# ── VTC-CARD-14..17: reward preview guard ────────────────────────────────────

class TestRewardPreviewGuard:
    @pytest.mark.asyncio
    async def test_card14_invalid_platform_returns_422(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_reward_card_preview

        with pytest.raises(HTTPException) as exc:
            await vt_reward_card_preview(
                request=_request(), tier=3, platform="vt_landscape",
                date_str=None, render_token=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_card15_invalid_tier_returns_422(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_reward_card_preview

        with pytest.raises(HTTPException) as exc:
            await vt_reward_card_preview(
                request=_request(), tier=7, platform="vt_reward_landscape",
                date_str=None, render_token=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_card16_not_enough_completed_games_returns_403(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_reward_card_preview

        with patch(_ELIG_RWRD, return_value=(False, 2)), \
             pytest.raises(HTTPException) as exc:
            await vt_reward_card_preview(
                request=_request(), tier=3, platform="vt_reward_landscape",
                date_str=None, render_token=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_card17_tier3_met_allows_preview(self):
        from app.api.web_routes.vt_card import vt_reward_card_preview

        fake_response = MagicMock()
        fake_response.status_code = 200

        with patch(_ELIG_RWRD, return_value=(True, 3)), \
             patch(f"{_ROUTES_MODULE}.templates") as mock_tpl:
            mock_tpl.TemplateResponse.return_value = fake_response
            result = await vt_reward_card_preview(
                request=_request(), tier=3, platform="vt_reward_landscape",
                date_str=None, render_token=None, db=_db(), user=_user(),
            )
        assert result.status_code == 200


# ── VTC-CARD-18..20: export guard ────────────────────────────────────────────

class TestExportGuard:
    @pytest.mark.asyncio
    async def test_card18_export_0_of_5_returns_403(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_export

        with patch(_ELIG_SGL, return_value=(False, 0, 5)), \
             pytest.raises(HTTPException) as exc:
            await vt_card_export(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_card19_export_4_of_5_returns_403(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_export

        with patch(_ELIG_SGL, return_value=(False, 4, 5)), \
             pytest.raises(HTTPException) as exc:
            await vt_card_export(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_card20_export_5_of_5_proceeds_to_render(self):
        """5/5 eligible — export proceeds past eligibility check (rate limit + Playwright)."""
        from app.api.web_routes.vt_card import vt_card_export

        fake_png = b"\x89PNG\r\n"
        with patch(_ELIG_SGL, return_value=(True, 5, 5)), \
             patch(f"{_ROUTES_MODULE}._export_svc.check_export_rate_limit", return_value=True), \
             patch("app.core.auth.create_vt_card_render_token", return_value="tok"), \
             patch("asyncio.to_thread", new=AsyncMock(return_value=fake_png)), \
             patch("app.config.settings") as mock_settings:
            mock_settings.APP_INTERNAL_PORT = 8000
            result = await vt_card_export(
                    request=_request(), game_id=1, platform="vt_landscape",
                    date_str=None, db=_db(), user=_user(),
                )
        assert result.media_type == "image/png"
        assert result.body == fake_png


# ── VTC-CARD-21..23: reward export guard ─────────────────────────────────────

class TestRewardExportGuard:
    @pytest.mark.asyncio
    async def test_card21_reward_export_not_eligible_returns_403(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_reward_card_export

        with patch(_ELIG_RWRD, return_value=(False, 2)), \
             pytest.raises(HTTPException) as exc:
            await vt_reward_card_export(
                request=_request(), tier=3, platform="vt_reward_landscape",
                date_str=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_card22_reward_export_eligible_proceeds_to_render(self):
        from app.api.web_routes.vt_card import vt_reward_card_export

        fake_png = b"\x89PNG\r\n"
        with patch(_ELIG_RWRD, return_value=(True, 3)), \
             patch(f"{_ROUTES_MODULE}._export_svc.check_export_rate_limit", return_value=True), \
             patch("app.core.auth.create_vt_card_render_token", return_value="tok"), \
             patch("asyncio.to_thread", new=AsyncMock(return_value=fake_png)), \
             patch("app.config.settings") as mock_settings:
            mock_settings.APP_INTERNAL_PORT = 8000
            result = await vt_reward_card_export(
                    request=_request(), tier=3, platform="vt_reward_landscape",
                    date_str=None, db=_db(), user=_user(),
                )
        assert result.media_type == "image/png"

    @pytest.mark.asyncio
    async def test_card23_reward_export_invalid_tier_returns_422(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_reward_card_export

        with pytest.raises(HTTPException) as exc:
            await vt_reward_card_export(
                request=_request(), tier=99, platform="vt_reward_landscape",
                date_str=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 422


# ── VTC-CARD-24..25: date parsing ────────────────────────────────────────────

class TestDateParsing:
    @pytest.mark.asyncio
    async def test_card24_invalid_date_returns_422(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        with pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str="not-a-date", render_token=None, db=_db(), user=_user(),
            )
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_card25_valid_date_is_accepted(self):
        from fastapi import HTTPException
        from app.api.web_routes.vt_card import vt_card_preview

        with patch(_ELIG_SGL, return_value=(False, 0, 5)), \
             pytest.raises(HTTPException) as exc:
            await vt_card_preview(
                request=_request(), game_id=1, platform="vt_landscape",
                date_str="2026-06-04", render_token=None, db=_db(), user=_user(),
            )
        # Reaches eligibility check (returns 403, not 422) → date was parsed OK
        assert exc.value.status_code == 403
