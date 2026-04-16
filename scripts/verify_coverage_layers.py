"""
verify_coverage_layers.py
=========================
CI guard: every test in test_critical_e2e.py must have all 3 assertion layers.

Layers required per test function:
  HTTP — assert*.status_code  (or assert*status_code)
  DB   — test_db.query( or db.query(  (SQLAlchemy DB verification)
  UI   — assert "..." in r*.text  or  assert*in*r*.text  (HTML state check)

Exit 0 = all tests have 3 layers.
Exit 1 = one or more tests missing a layer (prints details).

Usage:
  python scripts/verify_coverage_layers.py
"""

import re
import sys
from pathlib import Path

TARGET = Path("tests/integration/web_flows/test_critical_e2e.py")

# Patterns for each layer
HTTP_PATTERN  = re.compile(r"assert\b.*\bstatus_code\b")
DB_PATTERN    = re.compile(r"(?:test_db|db)\.(?:query|refresh|expire_all)\(")
# UI layer: any of these patterns proves HTML/JSON business state is checked:
#   - assert ... in r.text / response.text / r_*.text
#   - in r*.text (inside any() or similar)
#   - response_text = r*.text.lower() pattern → then asserted
#   - assert ... in r*.headers (redirect-target URL proves business state)
UI_PATTERN    = re.compile(
    r'(?:'
    r'assert\b.*\.text'           # assert "X" in r.text  / assert "X" in r_page.text
    r'|in\s+r\w*\.text'           # any(x in r.text for ...) — multiline any()
    r'|response_text\b'           # response_text = r.text.lower() → then asserted
    r'|assert\b.*\.headers'       # assert "/dashboard" in r.headers["location"]
    r')'
)

# Tests explicitly exempted from UI layer (read-only, no HTML response)
UI_EXEMPT = {
    # Add test names here if they have no HTML response to check (e.g., JSON-only endpoints)
    # Example: "test_some_api_only_flow"
}


def extract_test_functions(source: str) -> dict[str, str]:
    """Return {test_name: body_text} for every def test_* in source."""
    tests: dict[str, str] = {}
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^def (test_\w+)\(', line)
        if m:
            name = m.group(1)
            start = i
            # Collect body until next top-level def/class or EOF
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if re.match(r'^def |^class ', next_line):
                    break
                j += 1
            body = "\n".join(lines[start:j])
            tests[name] = body
        i += 1
    return tests


def check_layers(test_name: str, body: str) -> list[str]:
    """Return list of missing layer names."""
    missing = []
    if not HTTP_PATTERN.search(body):
        missing.append("HTTP (assert*.status_code)")
    if not DB_PATTERN.search(body):
        missing.append("DB (test_db.query / db.query / db.refresh)")
    if test_name not in UI_EXEMPT and not UI_PATTERN.search(body):
        missing.append('UI (assert "..." in r*.text)')
    return missing


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found.", file=sys.stderr)
        return 1

    source = TARGET.read_text()
    tests = extract_test_functions(source)

    if not tests:
        print("ERROR: No test functions found.", file=sys.stderr)
        return 1

    failures: list[tuple[str, list[str]]] = []
    for name, body in tests.items():
        missing = check_layers(name, body)
        if missing:
            failures.append((name, missing))

    total = len(tests)
    passed = total - len(failures)

    print(f"verify_coverage_layers: {total} tests checked, {passed} passed, {len(failures)} failed")

    if failures:
        print("\nFAILED — missing layers:")
        for name, missing in failures:
            print(f"  {name}")
            for layer in missing:
                print(f"    ❌ {layer}")
        print(
            "\nFix: add all 3 assertion layers (HTTP + DB + UI) to each failing test.\n"
            "See tests/COVERAGE_BASELINE.md Section 1 for assertion rules."
        )
        return 1

    print("PASS — all tests have HTTP + DB + UI layers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
