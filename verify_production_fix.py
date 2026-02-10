#!/usr/bin/env python3
"""
Production Fix Verification Script
Tests the performance_card rendering with REAL production data from lfa_intern_system DB
"""
import sys
from unittest.mock import MagicMock, patch

# Mock streamlit before importing performance_card
streamlit_mock = MagicMock()

def _mock_columns(n, **kwargs):
    """Mock st.columns to return list of context managers"""
    col = MagicMock()
    col.__enter__ = lambda s: s
    col.__exit__ = MagicMock(return_value=False)
    return [col] * n

streamlit_mock.columns.side_effect = _mock_columns
streamlit_mock.markdown = MagicMock()
streamlit_mock.metric = MagicMock()
streamlit_mock.expander = MagicMock()
streamlit_mock.expander.return_value.__enter__ = MagicMock()
streamlit_mock.expander.return_value.__exit__ = MagicMock(return_value=False)

sys.modules['streamlit'] = streamlit_mock

# Now import the component
from streamlit_app.components.tournaments.performance_card import render_performance_card


def test_production_scenario_champion_at_index_0():
    """Scenario 1: CHAMPION badge at index 0 (current DB state for most tournaments)"""
    print("\n" + "="*80)
    print("TEST 1: CHAMPION badge at index 0 (badges order: CHAMPION, PODIUM, PARTICIPANT)")
    print("="*80)

    streamlit_mock.markdown.reset_mock()

    tournament_data = {
        "tournament_id": 123,
        "tournament_name": "SANDBOX-sandbox-2026-02-09-10-23-03-4221",
        "tournament_status": "COMPLETED",
        "metrics": {
            "rank": None,  # NULL in tournament_rankings
            "total_participants": None,  # NULL in tournament_rankings
            "points": 100,
            "avg_points": 50.0,
            "wins": 5,
            "draws": 1,
            "losses": 0,
            "goals_for": 10,
            "xp_earned": 500,
            "credits_earned": 3,
            "badges_earned": 3,
        },
        "badges": [
            {
                "badge_type": "CHAMPION",
                "badge_category": "PLACEMENT",
                "title": "Champion",
                "icon": "🏆",
                "rarity": "LEGENDARY",
                "badge_metadata": {"placement": 1, "total_participants": 8}
            },
            {
                "badge_type": "PODIUM_FINISH",
                "badge_category": "PLACEMENT",
                "title": "Podium Finish",
                "icon": "🥇",
                "rarity": "RARE",
                "badge_metadata": {"placement": 1, "total_participants": 8}
            },
            {
                "badge_type": "TOURNAMENT_PARTICIPANT",
                "badge_category": "PARTICIPATION",
                "title": "Tournament Participant",
                "icon": "🎫",
                "rarity": "COMMON",
                "badge_metadata": None
            }
        ]
    }

    render_performance_card(tournament_data, size="normal")

    # Check results
    rendered = " ".join(str(call) for call in streamlit_mock.markdown.call_args_list)

    if "No ranking data" in rendered:
        print("❌ FAILED: 'No ranking data' found in output!")
        print(f"   Rendered output: {rendered[:200]}...")
        return False
    elif "#1 of 8 players" in rendered or "#1" in rendered:
        print("✅ PASSED: Ranking data correctly shown (#1 of 8 players)")
        return True
    else:
        print("⚠️  UNCERTAIN: Neither 'No ranking data' nor '#1' found")
        print(f"   Rendered output: {rendered[:200]}...")
        return False


def test_production_scenario_champion_not_at_index_0():
    """Scenario 2: TOURNAMENT_PARTICIPANT at index 0 (regression scenario)"""
    print("\n" + "="*80)
    print("TEST 2: CHAMPION badge NOT at index 0 (PARTICIPANT, PODIUM, CHAMPION)")
    print("="*80)
    print("This is the EXACT scenario that caused the production bug.")

    streamlit_mock.markdown.reset_mock()

    tournament_data = {
        "tournament_id": 124,
        "tournament_name": "SANDBOX-TEST-LEAGUE-2026-02-09",
        "tournament_status": "COMPLETED",
        "metrics": {
            "rank": None,
            "total_participants": None,
            "points": 100,
            "avg_points": 50.0,
            "wins": 5,
            "draws": 1,
            "losses": 0,
            "goals_for": 10,
            "xp_earned": 500,
            "credits_earned": 3,
            "badges_earned": 3,
        },
        "badges": [
            {
                "badge_type": "TOURNAMENT_PARTICIPANT",
                "badge_category": "PARTICIPATION",
                "title": "Tournament Participant",
                "icon": "🎫",
                "rarity": "COMMON",
                "badge_metadata": None  # NULL - this would break old code
            },
            {
                "badge_type": "PODIUM_FINISH",
                "badge_category": "PLACEMENT",
                "title": "Podium Finish",
                "icon": "🥇",
                "rarity": "RARE",
                "badge_metadata": {"placement": 1, "total_participants": 8}
            },
            {
                "badge_type": "CHAMPION",
                "badge_category": "PLACEMENT",
                "title": "Champion",
                "icon": "🏆",
                "rarity": "LEGENDARY",
                "badge_metadata": {"placement": 1, "total_participants": 8}
            }
        ]
    }

    render_performance_card(tournament_data, size="normal")

    # Check results
    rendered = " ".join(str(call) for call in streamlit_mock.markdown.call_args_list)

    if "No ranking data" in rendered:
        print("❌ FAILED: 'No ranking data' found - REGRESSION DETECTED!")
        print("   OLD BUG: badges[0] read TOURNAMENT_PARTICIPANT (metadata=null)")
        print(f"   Rendered output: {rendered[:200]}...")
        return False
    elif "#1 of 8 players" in rendered or "#1" in rendered:
        print("✅ PASSED: Fix working! primary_badge used instead of badges[0]")
        return True
    else:
        print("⚠️  UNCERTAIN: Neither 'No ranking data' nor '#1' found")
        print(f"   Rendered output: {rendered[:200]}...")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PRODUCTION FIX VERIFICATION")
    print("Testing performance_card.py with real production data scenarios")
    print("="*80)

    results = []

    results.append(test_production_scenario_champion_at_index_0())
    results.append(test_production_scenario_champion_not_at_index_0())

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n✅ ALL TESTS PASSED - Production fix verified!")
        print("   The fix correctly uses primary_badge for metadata fallbacks.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Production fix may not be working!")
        sys.exit(1)
