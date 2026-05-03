"""
Sponsor audience list + detail templates — form structure and count regression tests.

  SAT-01  promote-form contains no nested <form> elements
  SAT-02  cleanup action forms (/suppress, /delete, /unlink) are outside the promote-form
  SAT-03  entry_ids checkboxes carry form="promote-form"
  SAT-04  promote submit button carries form="promote-form"
  SAT-05  sponsor_detail.html audience count uses active_entries (rejects DELETED)
  SAT-06  sponsor_detail.html age breakdown uses active_entries (rejects DELETED)

These tests parse the raw Jinja2 template files — no running server needed.
"""
import os
import re

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../app/templates/admin/sponsor_audience_list.html",
)

DETAIL_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../app/templates/admin/sponsor_detail.html",
)


def _load_template() -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


def _load_detail_template() -> str:
    with open(DETAIL_TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


def _promote_form_body(html: str) -> str:
    """Return the raw text between the opening of id="promote-form" and its first </form>."""
    start = html.index('id="promote-form"')
    end = html.index("</form>", start) + len("</form>")
    return html[start:end]


# ── SAT-01 ────────────────────────────────────────────────────────────────────

def test_sat_01_promote_form_has_no_nested_form():
    """The promote-form must close before any other <form> tag appears inside it."""
    body = _promote_form_body(_load_template())
    # Strip the opening tag itself; any subsequent <form is a nested form
    first_tag_end = body.index(">") + 1
    inner = body[first_tag_end:]
    assert "<form" not in inner, (
        "Nested <form> found inside #promote-form — cleanup forms must be standalone"
    )


# ── SAT-02 ────────────────────────────────────────────────────────────────────

def test_sat_02_cleanup_forms_outside_promote_form():
    """Cleanup action routes must not appear anywhere inside the promote-form body."""
    body = _promote_form_body(_load_template())
    for keyword in ("/suppress", "/delete", "/unlink"):
        assert keyword not in body, (
            f"Cleanup action '{keyword}' is inside #promote-form — "
            "it will submit the promote route instead of the cleanup route"
        )


# ── SAT-03 ────────────────────────────────────────────────────────────────────

def test_sat_03_entry_ids_checkbox_has_form_attribute():
    """Every entry_ids checkbox must carry form="promote-form" so it belongs to the
    promote form even though it is physically outside the <form> element."""
    html = _load_template()
    # Find all <input … name="entry_ids" … > tags in the template
    pattern = re.compile(r'<input\b[^>]*name="entry_ids"[^>]*>', re.DOTALL)
    matches = pattern.findall(html)
    assert matches, "No input[name=entry_ids] found in template"
    for tag in matches:
        assert 'form="promote-form"' in tag, (
            f"input[name=entry_ids] is missing form=\"promote-form\":\n{tag}"
        )


# ── SAT-04 ────────────────────────────────────────────────────────────────────

def test_sat_04_promote_button_has_form_attribute():
    """The sticky promote submit button must carry form="promote-form"."""
    html = _load_template()
    pattern = re.compile(r'<button\b[^>]*btn-promote[^>]*>', re.DOTALL)
    matches = pattern.findall(html)
    assert matches, "No button.btn-promote found in template"
    for tag in matches:
        assert 'form="promote-form"' in tag, (
            f"btn-promote is missing form=\"promote-form\":\n{tag}"
        )


# ── SAT-05 ────────────────────────────────────────────────────────────────────

def test_sat_05_detail_audience_count_uses_active_entries():
    """Import Audience (N) header must use active_entries, not sponsor.audience_entries.

    If the raw relationship is used, DELETED entries inflate the count and make
    successful rollbacks invisible to the admin (they still see N unchanged).
    """
    html = _load_detail_template()
    # active_entries must be defined via rejectattr('status', 'equalto', 'DELETED')
    assert "rejectattr('status', 'equalto', 'DELETED')" in html, (
        "sponsor_detail.html must filter out DELETED entries via rejectattr"
    )
    # The header count must reference active_entries, not sponsor.audience_entries|length
    assert "active_entries|length" in html, (
        "Import Audience count must use active_entries|length, not sponsor.audience_entries|length"
    )
    # The raw unfiltered length must NOT appear in the header (regression guard)
    # Find the section-header for Import Audience
    header_start = html.index("Import Audience")
    header_end = html.index("</h3>", header_start)
    header = html[header_start:header_end]
    assert "sponsor.audience_entries|length" not in header, (
        "Import Audience header must not use the unfiltered sponsor.audience_entries|length"
    )


# ── SAT-06 ────────────────────────────────────────────────────────────────────

def test_sat_06_detail_age_breakdown_uses_active_entries():
    """Age category breakdown must loop over active_entries, not sponsor.audience_entries."""
    html = _load_detail_template()
    # The age_counts loop must reference active_entries
    assert "for e in active_entries" in html, (
        "Age category breakdown must loop over active_entries, not sponsor.audience_entries"
    )
