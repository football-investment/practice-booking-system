"""
Shadow endpoint detector — run at sprint end.

A "shadow endpoint" is a .py file that is unreachable because a same-named
package directory (with __init__.py) takes precedence in Python's import system.

Example:  app/api/api_v1/endpoints/sessions.py    ← shadow (dead)
          app/api/api_v1/endpoints/sessions/       ← live package

Usage:
    python scripts/check_shadow_endpoints.py
    python scripts/check_shadow_endpoints.py --root app/api
    python scripts/check_shadow_endpoints.py --exit-code   # non-zero if shadows found
"""

import argparse
import sys
from pathlib import Path


def find_shadow_files(root: Path) -> list[tuple[Path, Path]]:
    """
    Return list of (shadow_file, package_dir) pairs where shadow_file
    is unreachable because package_dir takes import precedence.
    """
    shadows: list[tuple[Path, Path]] = []

    for py_file in sorted(root.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        # Candidate package directory: same stem as the .py file
        pkg_dir = py_file.parent / py_file.stem
        if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
            shadows.append((py_file, pkg_dir))

    return shadows


def find_orphaned_routes(root: Path) -> list[Path]:
    """
    Find Python files in app/api/routes/ that are never imported anywhere.
    These are a common source of dead code in this codebase.
    """
    routes_dir = root / "api" / "routes"
    if not routes_dir.exists():
        return []

    orphans: list[Path] = []
    for py_file in sorted(routes_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module_name = py_file.stem  # e.g. "lfa_player_routes"
        # Search for any import of this module name in the codebase
        found = False
        for candidate in root.rglob("*.py"):
            try:
                content = candidate.read_text(errors="ignore")
            except OSError:
                continue
            if module_name in content:
                found = True
                break
        if not found:
            orphans.append(py_file)

    return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect shadow endpoint files")
    parser.add_argument(
        "--root",
        default="app",
        help="Root directory to scan (default: app)",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with non-zero status if shadows are found",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: root directory not found: {root}", file=sys.stderr)
        return 2

    shadows = find_shadow_files(root)
    orphans = find_orphaned_routes(root)

    total = len(shadows) + len(orphans)

    if shadows:
        print(f"\n{'='*60}")
        print(f"SHADOW FILES ({len(shadows)}) — unreachable .py files")
        print(f"{'='*60}")
        for shadow, pkg in shadows:
            print(f"  SHADOW  {shadow}")
            print(f"  LIVE    {pkg}/")
            print()
    else:
        print("Shadow files: NONE (clean)")

    if orphans:
        print(f"\n{'='*60}")
        print(f"ORPHANED ROUTE FILES ({len(orphans)}) — never imported")
        print(f"{'='*60}")
        for f in orphans:
            print(f"  ORPHAN  {f}")
        print()
    else:
        print("Orphaned route files: NONE (clean)")

    if total > 0:
        print(f"\nTotal dead endpoint files: {total}")
        print("Action: delete or register them to keep coverage denominator clean.")
        return 1 if args.exit_code else 0
    else:
        print("\nAll clear — no shadow or orphaned endpoint files found.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
