#!/usr/bin/env python3
"""
Fix NameError issues in auto-generated smoke tests

Problem: Assertion messages use undefined variables (e.g., {booking_id}, {student_id})
         while the actual API calls use correct fixtures (e.g., {test_tournament["session_ids"][0]}, {test_student_id})

Solution: Replace undefined variables in assertion messages with the correct fixture references.

Usage:
    python tools/fix_test_fixture_nameerrors.py
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of undefined variables to their correct fixture references
# Based on analysis of test code and CI NameError failures
VARIABLE_FIXES = {
    # booking_id appears in paths like /api/v1/{booking_id}/checkin
    # Actual usage: test_tournament["session_ids"][0]
    r'\{booking_id\}': r'{test_tournament["session_ids"][0]}',

    # student_id in paths like /api/v1/students/{student_id}/...
    # Actual usage: test_student_id
    r'\{student_id\}': r'{test_student_id}',

    # session_id in paths (when fixture is test_session_id)
    # Note: check if using test_session_id fixture
    r'\{session_id\}': r'{test_session_id}',

    # event_id in paths
    r'\{event_id\}': r'{test_tournament["event_id"]}',

    # project_id in paths
    r'\{project_id\}': r'{test_tournament["project_id"]}',

    # skill_name in paths
    r'\{skill_name\}': r'{test_tournament["skill_name"]}',

    # test_tournament with quotes (for dictionary access in assertions)
    r"test_tournament\['session_id'\]": r'test_session_id',
    r'test_tournament\["session_id"\]': r'test_session_id',
    r"test_tournament\['user_id'\]": r'test_student_id',
    r'test_tournament\["user_id"\]': r'test_student_id',

    # session_id in paths (when NOT using test_session_id fixture)
    # Some tests use test_tournament["session_ids"][0]
    # NOTE: This is only for assertion messages where test_tournament is the fixture
    # We'll handle this contextually

    # campus_id in paths
    # Actual usage: test_campus_id fixture exists
    r'\{campus_id\}': r'{test_campus_id}',

    # location_id in paths
    # Actual usage: test_tournament["location_id"] or similar
    r'\{location_id\}': r'{test_tournament["location_id"]}',

    # coupon_id in paths
    # Actual usage: test_tournament["coupon_id"] placeholder
    r'\{coupon_id\}': r'{test_tournament["coupon_id"]}',

    # invoice_id in paths
    # Actual usage: test_tournament["invoice_id"] placeholder
    r'\{invoice_id\}': r'{test_tournament["invoice_id"]}',

    # quiz_id in paths
    # Actual usage: test_tournament["quiz_id"] placeholder
    r'\{quiz_id\}': r'{test_tournament["quiz_id"]}',

    # assessment_id in paths
    # Actual usage: test_tournament["assessment_id"] placeholder
    r'\{assessment_id\}': r'{test_tournament["assessment_id"]}',

    # milestone_id in paths
    # Actual usage: test_tournament["milestone_id"] placeholder
    r'\{milestone_id\}': r'{test_tournament["milestone_id"]}',

    # offer_id in paths
    # Actual usage: test_tournament["offer_id"] placeholder
    r'\{offer_id\}': r'{test_tournament["offer_id"]}',

    # application_id in paths
    # Actual usage: test_tournament["application_id"] placeholder
    r'\{application_id\}': r'{test_tournament["application_id"]}',

    # assignment_id in paths
    # Actual usage: test_tournament["assignment_id"] placeholder
    r'\{assignment_id\}': r'{test_tournament["assignment_id"]}',

    # master_id in paths
    # Actual usage: test_tournament["master_id"] placeholder
    r'\{master_id\}': r'{test_tournament["master_id"]}',

    # position_id in paths
    # Actual usage: test_tournament["position_id"] placeholder
    r'\{position_id\}': r'{test_tournament["position_id"]}',

    # code (invitation codes) - special case, not an ID
    # Actual usage: test_tournament["code"] for tournament code
    r'\{code\}': r'{test_tournament["code"]}',
}


def fix_assertion_messages(file_path: Path) -> Tuple[bool, int]:
    """
    Fix undefined variables in assertion messages.

    Args:
        file_path: Path to test file

    Returns:
        (modified, fix_count) - whether file was modified and number of fixes
    """
    content = file_path.read_text()
    original_content = content
    fix_count = 0

    # Apply all variable fixes to lines containing f-strings
    # (assertion messages are often multi-line, so we check each line individually)
    lines = content.split('\n')
    modified_lines = []

    for line in lines:
        original_line = line
        # Check if this line contains an f-string with potential undefined variables
        if 'f"' in line or "f'" in line:
            # Apply all fixes to this line
            for pattern, replacement in VARIABLE_FIXES.items():
                new_line = re.sub(pattern, replacement, line)
                if new_line != line:
                    line = new_line
                    fix_count += 1

        modified_lines.append(line)

    content = '\n'.join(modified_lines)

    if content != original_content:
        file_path.write_text(content)
        return True, fix_count

    return False, 0


def main():
    """Find and fix all NameError issues in smoke tests."""
    test_dir = Path("tests/integration/api_smoke")

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    print("🔍 Scanning for smoke test files with NameError issues...\n")

    # Find all test files (excluding conftest.py and payload_factory.py)
    test_files = [
        f for f in test_dir.glob("test_*_smoke.py")
        if f.name not in ["conftest.py", "payload_factory.py"]
    ]

    print(f"Found {len(test_files)} smoke test files\n")

    total_files_modified = 0
    total_fixes = 0

    for test_file in sorted(test_files):
        modified, fix_count = fix_assertion_messages(test_file)

        if modified:
            total_files_modified += 1
            total_fixes += fix_count
            print(f"✅ {test_file.name}: {fix_count} fixes")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Total fixes: {total_fixes}")
    print(f"{'='*60}\n")

    if total_files_modified > 0:
        print("✅ All NameError issues fixed!")
        print("\nNext steps:")
        print("1. Run smoke tests locally:")
        print("   pytest tests/integration/api_smoke/ -v --tb=short")
        print("2. Verify no NameError failures")
        print("3. Commit changes:")
        print("   git add tests/integration/api_smoke/")
        print('   git commit -m "fix(tests): Fix NameError in smoke test assertions"')
        return 0
    else:
        print("ℹ️  No NameError issues found (all tests already fixed)")
        return 0


if __name__ == "__main__":
    exit(main())
