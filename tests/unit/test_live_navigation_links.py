"""Static template tests for Live navigation links — PR Live-1.

Tests:
  LNL-01  tournament_edit.html contains a Live link URL
  LNL-02  tournament_edit.html Live link is guarded by IN_PROGRESS condition
  LNL-03  sponsor_detail.html contains a Live link URL in the event-row loop
  LNL-04  sponsor_detail.html Live link is guarded by ev_status == 'IN_PROGRESS'

These tests parse the raw Jinja2 template files — no running server required.
"""
import pathlib
import re

_TEMPLATES = pathlib.Path(__file__).parents[2] / "app" / "templates" / "admin"
_EDIT = (_TEMPLATES / "tournament_edit.html").read_text(encoding="utf-8")
_SPONSOR = (_TEMPLATES / "sponsor_detail.html").read_text(encoding="utf-8")


# ── LNL-01 ───────────────────────────────────────────────────────────────────

def test_lnl_01_edit_page_contains_live_link():
    """tournament_edit.html must reference /admin/tournaments/{{ t.id }}/live."""
    assert '/admin/tournaments/{{ t.id }}/live' in _EDIT, (
        "tournament_edit.html is missing the Live link href "
        "'/admin/tournaments/{{ t.id }}/live'"
    )


# ── LNL-02 ───────────────────────────────────────────────────────────────────

def test_lnl_02_edit_page_live_link_guarded_by_in_progress():
    """The Live link in tournament_edit.html must be inside an IN_PROGRESS if-block."""
    link_pos = _EDIT.index('/admin/tournaments/{{ t.id }}/live')
    # Search backward from the link for the nearest {% if %} block
    preceding = _EDIT[:link_pos]
    last_if = preceding.rfind("{%")
    assert last_if != -1, "No Jinja2 block found before the Live link"
    if_block = _EDIT[last_if : last_if + 120]
    assert "IN_PROGRESS" in if_block, (
        f"Live link in tournament_edit.html is not guarded by IN_PROGRESS.\n"
        f"Nearest preceding block: {if_block!r}"
    )


# ── LNL-03 ───────────────────────────────────────────────────────────────────

def test_lnl_03_sponsor_detail_contains_live_link():
    """sponsor_detail.html must reference /admin/tournaments/{{ ev.id }}/live."""
    assert '/admin/tournaments/{{ ev.id }}/live' in _SPONSOR, (
        "sponsor_detail.html is missing the Live link href "
        "'/admin/tournaments/{{ ev.id }}/live'"
    )


# ── LNL-04 ───────────────────────────────────────────────────────────────────

def test_lnl_04_sponsor_detail_live_link_guarded_by_ev_status():
    """The Live link in sponsor_detail.html must be inside an ev_status == 'IN_PROGRESS' block."""
    link_pos = _SPONSOR.index('/admin/tournaments/{{ ev.id }}/live')
    preceding = _SPONSOR[:link_pos]
    last_if = preceding.rfind("{%")
    assert last_if != -1, "No Jinja2 block found before the Live link in sponsor_detail.html"
    if_block = _SPONSOR[last_if : last_if + 120]
    assert "IN_PROGRESS" in if_block, (
        f"Live link in sponsor_detail.html is not guarded by IN_PROGRESS.\n"
        f"Nearest preceding block: {if_block!r}"
    )
    assert "ev_status" in if_block, (
        f"Live link guard does not reference ev_status.\n"
        f"Nearest preceding block: {if_block!r}"
    )
