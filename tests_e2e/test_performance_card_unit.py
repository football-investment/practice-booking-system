"""
Unit tests: Tournament Performance Card — CHAMPION badge logic
==============================================================

Root cause reference
--------------------
The "No ranking data" bug occurred because:

  1. `tournament_rankings` table had no rows for completed tournaments.
  2. The metrics query returned `rank=NULL, total_participants=NULL`.
  3. `render_performance_card` rendered the f-string fallback:
         f"#{rank} of {total_participants} players" if rank and total_participants
         else "No ranking data"
     which evaluates to "No ranking data" when either value is None/0.
  4. CHAMPION badges always have `badge_metadata.placement=1` and
     `badge_metadata.total_participants=N`, but this was never consulted.

The fix added two fallback blocks (performance_card.py:87-93 and :111-116):
  - Block A: if total_participants is missing → read from badge_metadata
  - Block B: if rank is missing AND badge_type == CHAMPION → read placement
             from badge_metadata (guaranteed by business rule)

These tests verify every data state that can reach the card,
including production-realistic "imperfect" states.

Coverage matrix
---------------
  T1  Happy path          rank + total_participants present in metrics
  T2  CHAMPION guard      rank=None in metrics → badge_metadata.placement used
  T3  total_participants  total_participants=None → badge_metadata fallback
  T4  Both fallbacks      rank=None AND total_participants=None → both fallbacks
  T5  No badge_metadata   CHAMPION + no badge_metadata → "No ranking data" (acceptable)
  T6  No badges list      metrics ok, badges=[] → normal render (no crash)
  T7  No metrics          metrics=None → early return with warning
  T8  Partial metrics     some fields None (points, wins, etc.) → no crash
  T9  RUNNER_UP badge     rank present → no CHAMPION guard triggered
  T10 Falsy rank=0        rank=0 treated as missing (falsy) → fallback applies
  T11 placement=0         badge_metadata.placement=0 (falsy) → guard not applied
  T12 Badge priority      CHAMPION > RUNNER_UP → CHAMPION selected as primary
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

# ── Streamlit mock (must be in place before importing the component) ──────────
# We mock the entire streamlit module so tests run without a Streamlit server.
streamlit_mock = MagicMock()

# st.columns(n) must return n context-manager mocks so tuple-unpacking works.
def _mock_columns(n, **kwargs):
    col = MagicMock()
    col.__enter__ = lambda s: s
    col.__exit__ = MagicMock(return_value=False)
    return [col] * n

streamlit_mock.columns.side_effect = _mock_columns

# st.expander must work as a context manager
_expander_ctx = MagicMock()
_expander_ctx.__enter__ = lambda s: s
_expander_ctx.__exit__ = MagicMock(return_value=False)
streamlit_mock.expander.return_value = _expander_ctx

sys.modules.setdefault("streamlit", streamlit_mock)

# Patch the specific st calls the component uses
_st_patch = patch.dict(sys.modules, {"streamlit": streamlit_mock})
_st_patch.start()

# ── Add project root to path ──────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
STREAMLIT_APP = os.path.join(PROJECT_ROOT, "streamlit_app")
if STREAMLIT_APP not in sys.path:
    sys.path.insert(0, STREAMLIT_APP)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Import the module under test ──────────────────────────────────────────────
from components.tournaments.performance_card import (  # noqa: E402
    render_performance_card,
    _get_primary_badge,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _champion_badge(placement=1, total_participants=24):
    return {
        "badge_type": "CHAMPION",
        "badge_category": "PLACEMENT",
        "title": "🥇 Champion",
        "icon": "🥇",
        "rarity": "LEGENDARY",
        "badge_metadata": {
            "placement": placement,
            "total_participants": total_participants,
            "tournament_name": "Test Championship",
        },
    }


def _runner_up_badge():
    return {
        "badge_type": "RUNNER_UP",
        "badge_category": "PLACEMENT",
        "title": "🥈 Runner Up",
        "icon": "🥈",
        "rarity": "EPIC",
        "badge_metadata": {"placement": 2, "total_participants": 24},
    }


def _minimal_metrics(**overrides):
    base = {
        "rank": 1,
        "total_participants": 24,
        "points": 30.0,
        "avg_points": 18.0,
        "wins": 10,
        "draws": 0,
        "losses": 2,
        "goals_for": 25,
        "xp_earned": 500,
        "credits_earned": 100,
        "badges_earned": 1,
        "rank_source": "current",
    }
    base.update(overrides)
    return base


def _capture_markdown_calls():
    """Reset and return the markdown mock so we can inspect what was rendered."""
    streamlit_mock.markdown.reset_mock()
    return streamlit_mock.markdown


# ──────────────────────────────────────────────────────────────────────────────
# T1 — Happy path: rank + total_participants present in metrics
# ──────────────────────────────────────────────────────────────────────────────
def test_T1_happy_path_rank_and_total_present():
    """Metrics contain rank=1 and total_participants=24; should render '#1 of 24 players'."""
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=1, total_participants=24),
        "badges": [_champion_badge()],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "#1 of 24 players" in rendered, (
        "T1 FAIL: Expected '#1 of 24 players' in rendered output.\n"
        f"Got: {rendered[:500]}"
    )
    assert "No ranking data" not in rendered, "T1 FAIL: 'No ranking data' must not appear"


# ──────────────────────────────────────────────────────────────────────────────
# T2 — CHAMPION guard: rank=None in metrics → badge_metadata.placement used
# ──────────────────────────────────────────────────────────────────────────────
def test_T2_champion_guard_rank_none_uses_badge_placement():
    """
    ROOT CAUSE SCENARIO.
    tournament_rankings has no row → rank=None.
    CHAMPION badge has placement=1 in badge_metadata.
    Must render '#1 of 24 players', never 'No ranking data'.
    """
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=None, total_participants=24),
        "badges": [_champion_badge(placement=1, total_participants=24)],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "No ranking data" not in rendered, (
        "T2 FAIL: REGRESSION — CHAMPION badge shows 'No ranking data' when rank=None.\n"
        "The CHAMPION guard (performance_card.py:111-116) is not working."
    )
    assert "#1 of 24 players" in rendered, (
        "T2 FAIL: Expected '#1 of 24 players' from badge_metadata fallback."
    )


# ──────────────────────────────────────────────────────────────────────────────
# T3 — total_participants fallback: None in metrics → badge_metadata
# ──────────────────────────────────────────────────────────────────────────────
def test_T3_total_participants_fallback_from_badge_metadata():
    """
    total_participants=None in metrics but present in badge_metadata.
    Should render the correct count, not a zero-participant card.
    """
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=1, total_participants=None),
        "badges": [_champion_badge(placement=1, total_participants=24)],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "No ranking data" not in rendered, (
        "T3 FAIL: total_participants fallback not working — 'No ranking data' shown."
    )
    assert "24" in rendered, "T3 FAIL: total_participants=24 from badge_metadata not in output."


# ──────────────────────────────────────────────────────────────────────────────
# T4 — Both fallbacks: rank=None AND total_participants=None
# ──────────────────────────────────────────────────────────────────────────────
def test_T4_both_rank_and_total_null_uses_badge_metadata():
    """
    Both rank and total_participants are NULL in metrics (full fallback path).
    badge_metadata has both placement and total_participants.
    Must render '#1 of 24 players'.
    """
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=None, total_participants=None),
        "badges": [_champion_badge(placement=1, total_participants=24)],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "No ranking data" not in rendered, (
        "T4 FAIL: Both fallbacks failed — 'No ranking data' shown despite badge_metadata."
    )
    assert "#1 of 24 players" in rendered, (
        "T4 FAIL: Expected '#1 of 24 players' when both fallbacks used."
    )


# ──────────────────────────────────────────────────────────────────────────────
# T5 — No badge_metadata: CHAMPION + empty metadata → "No ranking data" (acceptable)
# ──────────────────────────────────────────────────────────────────────────────
def test_T5_champion_no_badge_metadata_shows_no_ranking_data():
    """
    CHAMPION badge with no badge_metadata at all.
    This is a legitimate data gap — the UI correctly shows 'No ranking data'.
    Test documents and pins this ACCEPTABLE state (not a regression).
    """
    md = _capture_markdown_calls()

    badge_no_meta = {
        "badge_type": "CHAMPION",
        "badge_category": "PLACEMENT",
        "title": "🥇 Champion",
        "icon": "🥇",
        "rarity": "LEGENDARY",
        "badge_metadata": {},  # empty — no placement, no total_participants
    }

    render_performance_card({
        "metrics": _minimal_metrics(rank=None, total_participants=None),
        "badges": [badge_no_meta],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    # This state is acceptable — no crash, graceful degradation
    assert "No ranking data" in rendered, (
        "T5: Expected graceful 'No ranking data' when badge_metadata is empty."
    )


# ──────────────────────────────────────────────────────────────────────────────
# T6 — No badges list: metrics present, badges=[] → renders without crash
# ──────────────────────────────────────────────────────────────────────────────
def test_T6_no_badges_list_renders_without_crash():
    """Empty badges list — should not crash, no fallback needed."""
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=3, total_participants=15),
        "badges": [],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "#3 of 15 players" in rendered
    assert "No ranking data" not in rendered


# ──────────────────────────────────────────────────────────────────────────────
# T7 — No metrics: early return with warning, no crash
# ──────────────────────────────────────────────────────────────────────────────
def test_T7_no_metrics_early_return():
    """metrics=None must trigger st.warning and return early without rendering a card."""
    streamlit_mock.warning.reset_mock()

    render_performance_card({
        "metrics": None,
        "badges": [_champion_badge()],
    })

    streamlit_mock.warning.assert_called_once()
    warning_msg = str(streamlit_mock.warning.call_args)
    assert "No performance data" in warning_msg


# ──────────────────────────────────────────────────────────────────────────────
# T8 — Partial metrics: some fields None → no crash, no empty-string exception
# ──────────────────────────────────────────────────────────────────────────────
def test_T8_partial_metrics_no_crash():
    """
    Production-realistic: some metric fields may be NULL (no games played yet).
    Component must render without raising an exception.
    """
    partial = {
        "rank": 2,
        "total_participants": 12,
        "points": None,
        "avg_points": None,
        "wins": None,
        "draws": None,
        "losses": None,
        "goals_for": None,
        "xp_earned": None,
        "credits_earned": None,
        "badges_earned": None,
        "rank_source": "snapshot",
    }
    # Should not raise
    render_performance_card({
        "metrics": partial,
        "badges": [_runner_up_badge()],
    })


# ──────────────────────────────────────────────────────────────────────────────
# T9 — RUNNER_UP badge: rank present → no CHAMPION guard triggered
# ──────────────────────────────────────────────────────────────────────────────
def test_T9_runner_up_badge_with_rank_renders_correctly():
    """RUNNER_UP with rank=2 in metrics → normal render, no guard needed."""
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=2, total_participants=24),
        "badges": [_runner_up_badge()],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "#2 of 24 players" in rendered
    assert "No ranking data" not in rendered


# ──────────────────────────────────────────────────────────────────────────────
# T10 — Falsy rank=0: treated as missing, fallback triggers for CHAMPION
# ──────────────────────────────────────────────────────────────────────────────
def test_T10_rank_zero_treated_as_missing_for_champion():
    """
    rank=0 is falsy in Python. For a CHAMPION badge, the guard should
    apply placement=1 from badge_metadata (rank=0 is not a real rank).
    """
    md = _capture_markdown_calls()

    render_performance_card({
        "metrics": _minimal_metrics(rank=0, total_participants=24),
        "badges": [_champion_badge(placement=1, total_participants=24)],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "No ranking data" not in rendered, (
        "T10 FAIL: rank=0 caused 'No ranking data' on CHAMPION badge."
    )


# ──────────────────────────────────────────────────────────────────────────────
# T11 — placement=0 in badge_metadata: guard does NOT apply (falsy placement)
# ──────────────────────────────────────────────────────────────────────────────
def test_T11_placement_zero_guard_not_applied():
    """
    badge_metadata.placement=0 is falsy — guard must not set rank=0.
    Result: 'No ranking data' (graceful — data is genuinely missing).
    """
    md = _capture_markdown_calls()

    badge_zero_placement = {
        "badge_type": "CHAMPION",
        "badge_category": "PLACEMENT",
        "title": "🥇 Champion",
        "icon": "🥇",
        "rarity": "LEGENDARY",
        "badge_metadata": {"placement": 0, "total_participants": 24},
    }

    render_performance_card({
        "metrics": _minimal_metrics(rank=None, total_participants=24),
        "badges": [badge_zero_placement],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    # placement=0 is falsy, guard skips it → acceptable "No ranking data"
    assert "No ranking data" in rendered, (
        "T11: placement=0 should not be used as rank; 'No ranking data' expected."
    )


# ──────────────────────────────────────────────────────────────────────────────
# T12 — Badge priority: CHAMPION > RUNNER_UP
# ──────────────────────────────────────────────────────────────────────────────
def test_T12_badge_priority_champion_over_runner_up():
    """
    Player has both CHAMPION and RUNNER_UP badges.
    Primary badge should be CHAMPION (priority=1 < 2).
    """
    primary = _get_primary_badge([_runner_up_badge(), _champion_badge()])
    assert primary is not None
    assert primary["badge_type"] == "CHAMPION", (
        f"T12 FAIL: Expected CHAMPION as primary badge, got {primary['badge_type']}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# T13 — API error state: metrics with all None values (API returned empty dict)
# ──────────────────────────────────────────────────────────────────────────────
def test_T13_api_returns_all_none_metrics_no_crash():
    """
    Simulate API returning a metrics dict where every value is None
    (e.g. tournament_rankings query returned no rows and fallback failed).
    Component must not raise; it should gracefully render 'No ranking data'.
    """
    all_none_metrics = {
        "rank": None,
        "total_participants": None,
        "points": None,
        "avg_points": None,
        "wins": None,
        "draws": None,
        "losses": None,
        "goals_for": None,
        "xp_earned": None,
        "credits_earned": None,
        "badges_earned": None,
        "rank_source": None,
    }

    md = _capture_markdown_calls()
    render_performance_card({
        "metrics": all_none_metrics,
        "badges": [],
    })

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "No ranking data" in rendered


# ──────────────────────────────────────────────────────────────────────────────
# T14 — Compact size: same CHAMPION guard applies
# ──────────────────────────────────────────────────────────────────────────────
def test_T14_compact_size_champion_guard_applies():
    """CHAMPION guard must fire in 'compact' size mode too."""
    md = _capture_markdown_calls()

    render_performance_card(
        {
            "metrics": _minimal_metrics(rank=None, total_participants=24),
            "badges": [_champion_badge(placement=1, total_participants=24)],
        },
        size="compact",
    )

    rendered = " ".join(str(c) for c in md.call_args_list)
    assert "No ranking data" not in rendered, (
        "T14 FAIL: compact size shows 'No ranking data' for CHAMPION badge."
    )
