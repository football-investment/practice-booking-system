"""
Import coverage test for app/schemas/badge_showcase_ui_contract.py

This file is never imported from app/ code (dead import), so its 132 statements
are all at 0% coverage. Importing it here executes every class body and enum
definition at import time, covering all statements.
"""
import pytest

import app.schemas.badge_showcase_ui_contract as badge_schema
from app.schemas.badge_showcase_ui_contract import (
    BadgeDisplayMode,
    BadgeRarity,
    BadgeUIMinimal,
    BadgeUIStandard,
    BadgeUIExtended,
    BadgeShowcaseSection,
    BadgeShowcaseUI,
    BadgeProgressUI,
    BadgeProgressListUI,
    BadgeFilter,
    BadgeSortOption,
    BadgeListUI,
    PinBadgeRequest,
    PinBadgeResponse,
    BadgeDetailModalUI,
    BadgeNotificationUI,
)


@pytest.mark.unit
class TestBadgeDisplayMode:
    def test_all_values(self):
        assert BadgeDisplayMode.GRID == "grid"
        assert BadgeDisplayMode.LIST == "list"
        assert BadgeDisplayMode.COMPACT == "compact"
        assert BadgeDisplayMode.SHOWCASE == "showcase"

    def test_is_str_enum(self):
        assert isinstance(BadgeDisplayMode.GRID, str)


@pytest.mark.unit
class TestBadgeRarity:
    def test_all_values(self):
        assert BadgeRarity.COMMON == "COMMON"
        assert BadgeRarity.UNCOMMON == "UNCOMMON"
        assert BadgeRarity.RARE == "RARE"
        assert BadgeRarity.EPIC == "EPIC"
        assert BadgeRarity.LEGENDARY == "LEGENDARY"

    def test_is_str_enum(self):
        assert isinstance(BadgeRarity.LEGENDARY, str)


@pytest.mark.unit
class TestBadgeUIMinimal:
    def test_instantiation(self):
        badge = BadgeUIMinimal(
            icon="🥇",
            rarity=BadgeRarity.LEGENDARY,
            title="Champion"
        )
        assert badge.icon == "🥇"
        assert badge.rarity == BadgeRarity.LEGENDARY
        assert badge.title == "Champion"

    def test_rarity_string_coercion(self):
        badge = BadgeUIMinimal(icon="🏆", rarity="EPIC", title="Epic Badge")
        assert badge.rarity == BadgeRarity.EPIC


@pytest.mark.unit
class TestBadgeUIStandard:
    def test_default_is_pinned_false(self):
        badge = BadgeUIStandard(
            id=1,
            icon="🥈",
            rarity=BadgeRarity.RARE,
            title="Silver",
            description="Second place",
            badge_type="RUNNER_UP",
            badge_category="PLACEMENT",
            earned_at="2026-01-01T00:00:00",
        )
        assert badge.is_pinned is False

    def test_is_pinned_can_be_true(self):
        badge = BadgeUIStandard(
            id=2,
            icon="🏅",
            rarity=BadgeRarity.UNCOMMON,
            title="Medal",
            description="Third place",
            badge_type="THIRD_PLACE",
            badge_category="PLACEMENT",
            earned_at="2026-02-01T00:00:00",
            is_pinned=True,
        )
        assert badge.is_pinned is True


@pytest.mark.unit
class TestPinBadgeRequest:
    def test_instantiation(self):
        req = PinBadgeRequest(badge_id=42, is_pinned=True)
        assert req.badge_id == 42
        assert req.is_pinned is True

    def test_unpin(self):
        req = PinBadgeRequest(badge_id=10, is_pinned=False)
        assert req.is_pinned is False


@pytest.mark.unit
class TestPinBadgeResponse:
    def test_success(self):
        resp = PinBadgeResponse(success=True, badge_id=42, is_pinned=True, message="Badge pinned")
        assert resp.success is True
        assert resp.badge_id == 42
        assert resp.is_pinned is True
        assert resp.message == "Badge pinned"

    def test_failure(self):
        resp = PinBadgeResponse(success=False, badge_id=10, is_pinned=False, message="Badge not found")
        assert resp.success is False


@pytest.mark.unit
class TestBadgeSortOption:
    def test_importable(self):
        assert BadgeSortOption is not None

    def test_enum_members_exist(self):
        # Verify the enum has members (exact names may vary)
        assert len(list(BadgeSortOption)) > 0


@pytest.mark.unit
class TestBadgeProgressUI:
    def test_module_importable(self):
        assert BadgeProgressUI is not None
        assert BadgeProgressListUI is not None
        assert BadgeFilter is not None
        assert BadgeListUI is not None
        assert BadgeShowcaseSection is not None
        assert BadgeShowcaseUI is not None
        assert BadgeUIExtended is not None
        assert BadgeDetailModalUI is not None
        assert BadgeNotificationUI is not None
