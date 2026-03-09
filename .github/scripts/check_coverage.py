"""
Enforce stmt and branch coverage thresholds from coverage.xml.

Sprint 51 — stmt ≥88%, branch ≥80% (actual: 88.5% stmt, 81.4% branch)

The combined stmt+branch threshold is already enforced by:
  python -m coverage report --fail-under=85

This script adds SEPARATE stmt-only and branch-only checks so that the
thresholds are independently visible in CI logs:
  - Combined (stmt+branch) >= 85%  --> enforced by --fail-under=85
  - Stmt-only             >= 88%   --> enforced here via line-rate
  - Branch-only           >= 80%   --> enforced here via branch-rate
"""
import sys
import xml.etree.ElementTree as ET

STMT_THRESHOLD = 88.0
BRANCH_THRESHOLD = 80.0

root = ET.parse("coverage.xml").getroot()
stmt_pct = float(root.attrib["line-rate"]) * 100
branch_pct = float(root.attrib["branch-rate"]) * 100

print(f"Coverage  stmt-only: {stmt_pct:.1f}%  pure-branch: {branch_pct:.1f}%")
print(f"  (combined stmt+branch enforced separately via --fail-under=85)")

if stmt_pct < STMT_THRESHOLD:
    print(f"FAIL: stmt {stmt_pct:.1f}% < {STMT_THRESHOLD}% threshold", file=sys.stderr)
    sys.exit(1)

print(f"OK: stmt {stmt_pct:.1f}% >= {STMT_THRESHOLD}%")

if branch_pct < BRANCH_THRESHOLD:
    print(f"FAIL: branch {branch_pct:.1f}% < {BRANCH_THRESHOLD}% threshold", file=sys.stderr)
    sys.exit(1)

print(f"OK: branch {branch_pct:.1f}% >= {BRANCH_THRESHOLD}%")
