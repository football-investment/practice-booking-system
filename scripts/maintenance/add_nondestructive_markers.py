#!/usr/bin/env python3
"""
Add @pytest.mark.nondestructive to all E2E tests that don't have it.

The pytest-playwright plugin blocks tests on sensitive URLs unless marked nondestructive.
This script automatically adds the marker to test functions.
"""

import os
import re
from pathlib import Path

# Test files to update
TEST_DIR = Path("tests_e2e")
TEST_FILES = [
    "test_01_quick_test_full_flow.py",
    "test_01_create_new_tournament.py",
    "test_02_draft_continue.py",
    "test_03_in_progress_continue.py",
    "test_04_history_tabs.py",
    "test_05_multiple_selection.py",
    "test_06_error_scan.py",
    "test_performance_card_unit.py",
]


def add_nondestructive_marker(file_path: Path) -> int:
    """Add @pytest.mark.nondestructive to test functions that don't have it."""

    with open(file_path, "r") as f:
        content = f.read()

    # Pattern: Find test function definitions that don't already have nondestructive marker
    # Look for @pytest.mark.* lines followed by def test_
    pattern = r'(@pytest\.mark\.[^\n]+\n)*?(def test_[a-z_0-9]+\()'

    changes = 0

    def add_marker(match):
        nonlocal changes
        markers = match.group(1) or ""
        func_def = match.group(2)

        # Check if nondestructive already present
        if "nondestructive" in markers:
            return match.group(0)  # No change

        # Add nondestructive marker
        changes += 1
        if markers:
            # Add to existing markers
            return markers + "@pytest.mark.nondestructive\n" + func_def
        else:
            # Add as first marker
            return "@pytest.mark.nondestructive\n" + func_def

    new_content = re.sub(pattern, add_marker, content)

    if changes > 0:
        with open(file_path, "w") as f:
            f.write(new_content)
        print(f"✅ {file_path.name}: Added {changes} nondestructive marker(s)")
    else:
        print(f"⏭️  {file_path.name}: Already has markers or no test functions")

    return changes


def main():
    print("Adding @pytest.mark.nondestructive to E2E tests...\n")

    total_changes = 0

    for test_file in TEST_FILES:
        file_path = TEST_DIR / test_file

        if not file_path.exists():
            print(f"⚠️  {test_file}: File not found, skipping")
            continue

        changes = add_nondestructive_marker(file_path)
        total_changes += changes

    print(f"\n{'='*60}")
    print(f"Total changes: {total_changes} nondestructive markers added")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
