"""Static template tests for Live-2 templates — PR Live-2.

Tests parse the raw Jinja2/HTML template files — no running server required.

LS-01  tournament_live.html contains live-format-section div
LS-02  tournament_live.html includes _live_group_knockout.html dispatch
LS-03  _live_group_knockout.html contains group standings table headers
LS-04  _live_group_knockout.html contains live-snapshot fetch call
"""
import pathlib

_TEMPLATES = pathlib.Path(__file__).parents[2] / "app" / "templates" / "admin"
_LIVE = (_TEMPLATES / "tournament_live.html").read_text(encoding="utf-8")
_GK = (_TEMPLATES / "_live_group_knockout.html").read_text(encoding="utf-8")


# ── LS-01 ─────────────────────────────────────────────────────────────────────

def test_ls_01_live_html_contains_format_section():
    assert 'id="live-format-section"' in _LIVE, (
        "tournament_live.html is missing id='live-format-section'"
    )


# ── LS-02 ─────────────────────────────────────────────────────────────────────

def test_ls_02_live_html_dispatches_group_knockout():
    assert "_live_group_knockout.html" in _LIVE, (
        "tournament_live.html does not include _live_group_knockout.html"
    )


# ── LS-03 ─────────────────────────────────────────────────────────────────────

def test_ls_03_group_knockout_standings_table():
    for header in ("Pts", "GD", "GF"):
        assert header in _GK, (
            f"_live_group_knockout.html is missing standings column: {header}"
        )


# ── LS-04 ─────────────────────────────────────────────────────────────────────

def test_ls_04_live_html_snapshot_fetch():
    assert "live-snapshot" in _LIVE, (
        "tournament_live.html is missing snapshot fetch call"
    )
