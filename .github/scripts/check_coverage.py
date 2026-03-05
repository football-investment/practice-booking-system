"""
Enforce stmt coverage threshold from coverage.xml.

The combined stmt+branch threshold is already enforced by:
  python -m coverage report --fail-under=57

This script adds a SEPARATE stmt-only check so that the
two thresholds are independently visible in CI logs:
  - Combined (stmt+branch) >= 57%  --> enforced by --fail-under=57
  - Stmt-only             >= 63%   --> enforced here via line-rate

Thresholds updated 2026-03-05 (Sprint M — gamification + progress_license + session_group):
  combined  >= 57%   (current: ~57.7%)
  stmt-only >= 63%   (current: ~63.2%)
"""
import sys
import xml.etree.ElementTree as ET

STMT_THRESHOLD = 63.0

root = ET.parse("coverage.xml").getroot()
stmt_pct = float(root.attrib["line-rate"]) * 100
branch_pct = float(root.attrib["branch-rate"]) * 100

print(f"Coverage  stmt-only: {stmt_pct:.1f}%  pure-branch: {branch_pct:.1f}%")
print(f"  (combined stmt+branch enforced separately via --fail-under=57)")

if stmt_pct < STMT_THRESHOLD:
    print(f"FAIL: stmt {stmt_pct:.1f}% < {STMT_THRESHOLD}% threshold", file=sys.stderr)
    sys.exit(1)

print(f"OK: stmt {stmt_pct:.1f}% >= {STMT_THRESHOLD}%")
