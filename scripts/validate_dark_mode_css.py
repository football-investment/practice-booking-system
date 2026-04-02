#!/usr/bin/env python3
"""
validate_dark_mode_css.py — DM-STATIC-01..11 CSS Audit
=======================================================
Static filesystem checks for the global dark mode CSS system.
No database or running server required.

Exit 0 = all checks pass
Exit 1 = one or more checks failed

Tests:
  DM-STATIC-01  dark-mode.css exists
  DM-STATIC-02  dark-mode.css contains @media (prefers-color-scheme: dark)
  DM-STATIC-03  All 11 --app-* tokens defined inside the dark @media block
  DM-STATIC-04  All 11 --app-* tokens defined in style.css :root
  DM-STATIC-05  No bare 'background: white' / 'background-color: white' in
                the 4 main CSS files (case-insensitive)
  DM-STATIC-06  base.html AND admin/admin_base.html both link dark-mode.css
                AND the link appears AFTER the block tag (correct load order)
  DM-STATIC-07  achievements.html — no inline style="color: #7f8c8d/95a5a6" attrs
  DM-STATIC-08  sessions.html — no inline style="color: #..." on block elements
  DM-STATIC-09  student.css — no embedded @media (prefers-color-scheme: dark) block
  DM-STATIC-10  admin/tournament_attendance.html — no 'background: white' in <style>
  DM-STATIC-11  admin/tournament_edit.html — .sgw-modal no 'background: white' in <style>
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DARK_CSS            = Path("app/static/css/dark-mode.css")
STYLE_CSS           = Path("app/static/css/style.css")
STUDENT_CSS         = Path("app/static/css/student.css")
BASE_HTML           = Path("app/templates/base.html")
ADMIN_BASE_HTML     = Path("app/templates/admin/admin_base.html")
ACHIEVEMENTS_HTML   = Path("app/templates/achievements.html")
SESSIONS_HTML       = Path("app/templates/sessions.html")
ATT_HTML            = Path("app/templates/admin/tournament_attendance.html")
EDIT_HTML           = Path("app/templates/admin/tournament_edit.html")

CSS_FILES_AUDIT = [
    Path("app/static/css/style.css"),
    Path("app/static/css/admin.css"),
    Path("app/static/css/student.css"),
    Path("app/static/css/components.css"),
]

REQUIRED_TOKENS = [
    "--app-bg",
    "--app-card",
    "--app-card-alt",
    "--app-input-bg",
    "--app-text",
    "--app-text-muted",
    "--app-border",
    "--app-shadow",
    "--app-success",
    "--app-warning",
    "--app-error",
]

DARK_MEDIA_QUERY = "@media (prefers-color-scheme: dark)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"

failures: list[str] = []


def check(name: str, condition: bool, message: str) -> None:
    status = PASS if condition else FAIL
    print(f"  {status}  {name}: {message}")
    if not condition:
        failures.append(name)


def extract_dark_block(content: str) -> str:
    """Return the text inside the first @media (prefers-color-scheme: dark) { ... } block."""
    start = content.find(DARK_MEDIA_QUERY)
    if start == -1:
        return ""
    # Find the matching closing brace (naïve, but sufficient for well-formed CSS)
    depth = 0
    i = start
    block_start = -1
    while i < len(content):
        if content[i] == "{":
            depth += 1
            if block_start == -1:
                block_start = i
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                return content[block_start : i + 1]
        i += 1
    return content[block_start:]  # unclosed block — return remainder


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_dm_static_01() -> None:
    check(
        "DM-STATIC-01",
        DARK_CSS.exists(),
        f"{DARK_CSS} {'exists' if DARK_CSS.exists() else 'NOT FOUND'}",
    )


def run_dm_static_02() -> None:
    if not DARK_CSS.exists():
        check("DM-STATIC-02", False, "Skipped — dark-mode.css missing")
        return
    content = DARK_CSS.read_text()
    has_query = DARK_MEDIA_QUERY in content
    check(
        "DM-STATIC-02",
        has_query,
        f"'@media (prefers-color-scheme: dark)' {'found' if has_query else 'NOT FOUND'} in {DARK_CSS}",
    )


def run_dm_static_03() -> None:
    if not DARK_CSS.exists():
        check("DM-STATIC-03", False, "Skipped — dark-mode.css missing")
        return
    content = DARK_CSS.read_text()
    dark_block = extract_dark_block(content)
    if not dark_block:
        check("DM-STATIC-03", False, "No @media dark block found in dark-mode.css")
        return
    missing = [t for t in REQUIRED_TOKENS if t not in dark_block]
    check(
        "DM-STATIC-03",
        not missing,
        (
            "All 11 --app-* tokens present in dark block"
            if not missing
            else f"Missing from dark block: {missing}"
        ),
    )


def run_dm_static_04() -> None:
    if not STYLE_CSS.exists():
        check("DM-STATIC-04", False, f"{STYLE_CSS} not found")
        return
    content = STYLE_CSS.read_text()
    missing = [t for t in REQUIRED_TOKENS if t not in content]
    check(
        "DM-STATIC-04",
        not missing,
        (
            f"All 11 --app-* tokens defined in {STYLE_CSS}"
            if not missing
            else f"Missing from style.css: {missing}"
        ),
    )


def run_dm_static_05() -> None:
    pattern = re.compile(
        r"background(-color)?\s*:\s*white\b",
        re.IGNORECASE,
    )
    all_ok = True
    for css_file in CSS_FILES_AUDIT:
        if not css_file.exists():
            print(f"  ⚠️  WARN  DM-STATIC-05: {css_file} not found — skipped")
            continue
        content = css_file.read_text()
        matches = pattern.findall(content)
        if matches:
            check(
                "DM-STATIC-05",
                False,
                f"{css_file} still has {len(matches)} 'background: white' occurrence(s)",
            )
            all_ok = False
    if all_ok:
        check(
            "DM-STATIC-05",
            True,
            "No bare 'background: white' in any of the 4 CSS files",
        )


def _check_base_template_dark_link(html_path: Path, block_tag: str) -> tuple[bool, str]:
    """Return (ok, message) for dark-mode.css link order in a base template."""
    if not html_path.exists():
        return False, f"{html_path} not found"
    content = html_path.read_text()
    if "dark-mode.css" not in content:
        return False, f"dark-mode.css link NOT found in {html_path}"
    block_pos   = content.find(block_tag)
    dark_pos    = content.find("dark-mode.css")
    order_ok    = block_pos != -1 and dark_pos > block_pos
    if order_ok:
        return True, f"{html_path}: dark-mode.css AFTER {block_tag!r} ✓"
    return False, f"{html_path}: dark-mode.css BEFORE {block_tag!r} — wrong order!"


def run_dm_static_06() -> None:
    ok1, msg1 = _check_base_template_dark_link(BASE_HTML,       "{% block extra_head %}")
    ok2, msg2 = _check_base_template_dark_link(ADMIN_BASE_HTML, "{% block extra_styles %}")
    overall   = ok1 and ok2
    check(
        "DM-STATIC-06",
        overall,
        (f"{msg1} | {msg2}" if overall else f"FAIL — {msg1} | {msg2}"),
    )


def _style_block_white_bgs(content: str) -> list[str]:
    """Return 'background: white' hits found inside <style>...</style> blocks."""
    style_blocks = re.findall(r'<style[^>]*>([\s\S]*?)</style>', content, re.IGNORECASE)
    hits = []
    for block in style_blocks:
        hits.extend(re.findall(r'background(?:-color)?\s*:\s*white\b', block, re.IGNORECASE))
    return hits


def run_dm_static_07() -> None:
    """achievements.html — no inline style="color: #7f8c8d" or "#95a5a6"."""
    if not ACHIEVEMENTS_HTML.exists():
        check("DM-STATIC-07", False, f"{ACHIEVEMENTS_HTML} not found")
        return
    content = ACHIEVEMENTS_HTML.read_text()
    bad_colors = ["#7f8c8d", "#95a5a6"]
    found = []
    for color in bad_colors:
        pattern = re.compile(
            rf'style=["\'][^"\']*color\s*:\s*{re.escape(color)}[^"\']*["\']',
            re.IGNORECASE,
        )
        matches = pattern.findall(content)
        if matches:
            found.extend(matches)
    check(
        "DM-STATIC-07",
        not found,
        (
            f"{ACHIEVEMENTS_HTML}: no hardcoded grey inline color attrs ✓"
            if not found
            else f"{ACHIEVEMENTS_HTML}: {len(found)} hardcoded inline color(s) found: {found[:3]}"
        ),
    )


def run_dm_static_08() -> None:
    """sessions.html — no inline style="color: #..." hardcoded grey attrs."""
    if not SESSIONS_HTML.exists():
        check("DM-STATIC-08", False, f"{SESSIONS_HTML} not found")
        return
    content = SESSIONS_HTML.read_text()
    bad_colors = ["#7f8c8d", "#2d3748", "#95a5a6", "#555"]
    found = []
    for color in bad_colors:
        pattern = re.compile(
            rf'style=["\'][^"\']*color\s*:\s*{re.escape(color)}[^"\']*["\']',
            re.IGNORECASE,
        )
        matches = pattern.findall(content)
        if matches:
            found.extend(matches)
    check(
        "DM-STATIC-08",
        not found,
        (
            f"{SESSIONS_HTML}: no hardcoded inline color attrs ✓"
            if not found
            else f"{SESSIONS_HTML}: {len(found)} hardcoded inline color(s) found: {found[:3]}"
        ),
    )


def run_dm_static_09() -> None:
    """student.css — no embedded @media (prefers-color-scheme: dark) block."""
    if not STUDENT_CSS.exists():
        check("DM-STATIC-09", False, f"{STUDENT_CSS} not found")
        return
    content = STUDENT_CSS.read_text()
    has_dark = DARK_MEDIA_QUERY in content
    check(
        "DM-STATIC-09",
        not has_dark,
        (
            f"{STUDENT_CSS}: no redundant embedded dark block ✓"
            if not has_dark
            else f"{STUDENT_CSS}: still contains '@media (prefers-color-scheme: dark)' — must be removed"
        ),
    )


def run_dm_static_10() -> None:
    """admin/tournament_attendance.html — no 'background: white' in <style> blocks."""
    if not ATT_HTML.exists():
        check("DM-STATIC-10", False, f"{ATT_HTML} not found")
        return
    content = ATT_HTML.read_text()
    hits = _style_block_white_bgs(content)
    check(
        "DM-STATIC-10",
        not hits,
        (
            f"{ATT_HTML}: no 'background: white' in <style> blocks ✓"
            if not hits
            else f"{ATT_HTML}: {len(hits)} 'background: white' found in <style> blocks"
        ),
    )


def run_dm_static_11() -> None:
    """admin/tournament_edit.html — .sgw-modal no 'background: white' in <style>."""
    if not EDIT_HTML.exists():
        check("DM-STATIC-11", False, f"{EDIT_HTML} not found")
        return
    content = EDIT_HTML.read_text()
    hits = _style_block_white_bgs(content)
    check(
        "DM-STATIC-11",
        not hits,
        (
            f"{EDIT_HTML}: no 'background: white' in <style> blocks ✓"
            if not hits
            else f"{EDIT_HTML}: {len(hits)} 'background: white' found in <style> blocks"
        ),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print("━" * 60)
    print("  Dark Mode CSS Static Audit (DM-STATIC-01..11)")
    print("━" * 60)

    run_dm_static_01()
    run_dm_static_02()
    run_dm_static_03()
    run_dm_static_04()
    run_dm_static_05()
    run_dm_static_06()
    run_dm_static_07()
    run_dm_static_08()
    run_dm_static_09()
    run_dm_static_10()
    run_dm_static_11()

    print("━" * 60)
    if failures:
        print(f"\n  \033[91m❌ {len(failures)} check(s) FAILED: {failures}\033[0m\n")
        sys.exit(1)
    else:
        print(f"\n  \033[92m✅ All 11 static checks PASSED\033[0m\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
