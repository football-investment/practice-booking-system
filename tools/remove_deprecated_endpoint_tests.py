#!/usr/bin/env python3
"""
Remove deprecated endpoint tests (REMOVE_TEST category from decision matrix)

These endpoints should NOT exist in the API:
1. POST /api/v1/onboarding/set-birthdate - Legacy onboarding (deprecated)
2. POST /api/v1/specialization/select - Legacy specialization (deprecated)
3. POST /api/v1/profile/edit - Should use PATCH /profile instead

Usage:
    python tools/remove_deprecated_endpoint_tests.py
"""

import re
from pathlib import Path
from typing import List, Tuple


# Deprecated endpoints to remove (endpoint -> file mapping)
DEPRECATED_TESTS = {
    '/api/v1/onboarding/set-birthdate': {
        'file': 'test_onboarding_smoke.py',
        'test_names': [
            'test_set_birthdate_happy_path',
            'test_set_birthdate_auth_required',
            'test_set_birthdate_input_validation',
        ],
    },
    '/api/v1/specialization/select': {
        'file': 'test_specialization_smoke.py',
        'test_names': [
            'test_select_specialization_happy_path',
            'test_select_specialization_auth_required',
            'test_select_specialization_input_validation',
        ],
    },
    '/api/v1/profile/edit': {
        'file': 'test_profile_smoke.py',
        'test_names': [
            'test_edit_profile_happy_path',
            'test_edit_profile_auth_required',
            'test_edit_profile_input_validation',
        ],
    },
}


def remove_test_function(content: str, test_name: str) -> Tuple[str, bool]:
    """
    Remove a test function from file content.

    Args:
        content: File content
        test_name: Name of test function to remove

    Returns:
        (new_content, was_removed) tuple
    """
    # Pattern to match test function definition and its entire body
    # Matches: def test_name(...): ... until next def or end of class
    pattern = rf'    def {test_name}\([^)]*\):.*?(?=\n    def |\n\nclass |\Z)'

    # Check if pattern exists
    if not re.search(pattern, content, re.DOTALL):
        return content, False

    # Remove the function
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)

    return new_content, True


def main():
    """Remove deprecated endpoint tests."""
    test_dir = Path("tests/integration/api_smoke")

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    print("🗑️  Removing deprecated endpoint tests...\n")

    total_removed = 0
    total_files_modified = 0

    for endpoint, info in DEPRECATED_TESTS.items():
        file_path = test_dir / info['file']

        if not file_path.exists():
            print(f"⚠️  File not found: {file_path.name}")
            continue

        content = file_path.read_text()
        original_content = content
        removed_count = 0

        print(f"📄 {file_path.name}")
        print(f"   Endpoint: {endpoint}")

        for test_name in info['test_names']:
            content, was_removed = remove_test_function(content, test_name)
            if was_removed:
                removed_count += 1
                total_removed += 1
                print(f"   ✅ Removed: {test_name}")
            else:
                print(f"   ⚠️  Not found: {test_name}")

        if content != original_content:
            file_path.write_text(content)
            total_files_modified += 1
            print(f"   Saved with {removed_count} removals\n")
        else:
            print(f"   No changes made\n")

    print(f"{'='*60}")
    print(f"Summary:")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Tests removed: {total_removed}")
    print(f"{'='*60}\n")

    if total_removed > 0:
        print("✅ Deprecated tests removed!")
        print("\nReason for removal:")
        print("  - /onboarding/set-birthdate: Legacy endpoint, deprecated")
        print("  - /specialization/select: Legacy endpoint, deprecated")
        print("  - /profile/edit: Use PATCH /profile instead")
        return 0
    else:
        print("ℹ️  No tests found to remove")
        return 0


if __name__ == "__main__":
    exit(main())
