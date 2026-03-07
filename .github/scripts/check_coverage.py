"""
Enforce stmt coverage threshold from coverage.xml.

The combined stmt+branch threshold is already enforced by:
  python -m coverage report --fail-under=75

This script adds a SEPARATE stmt-only check so that the
two thresholds are independently visible in CI logs:
  - Combined (stmt+branch) >= 75%  --> enforced by --fail-under=75
  - Stmt-only             >= 75%   --> enforced here via line-rate

Thresholds updated 2026-03-07 (Sprint 33 — game_presets/crud + masters/applications +
  tournament_repository + spec_validation + spec_info):
  combined  >= 75%   (current: ~85%)
  stmt-only >= 75%   (current: ~87.1%)
"""
import sys
import xml.etree.ElementTree as ET

STMT_THRESHOLD = 75.0

root = ET.parse("coverage.xml").getroot()
stmt_pct = float(root.attrib["line-rate"]) * 100
branch_pct = float(root.attrib["branch-rate"]) * 100

print(f"Coverage  stmt-only: {stmt_pct:.1f}%  pure-branch: {branch_pct:.1f}%")
print(f"  (combined stmt+branch enforced separately via --fail-under=75)")

if stmt_pct < STMT_THRESHOLD:
    print(f"FAIL: stmt {stmt_pct:.1f}% < {STMT_THRESHOLD}% threshold", file=sys.stderr)
    sys.exit(1)

print(f"OK: stmt {stmt_pct:.1f}% >= {STMT_THRESHOLD}%")
