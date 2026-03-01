#!/usr/bin/env python3
"""
Fix 404 errors caused by duplicated URL segments in auto-generated tests

Problem: Test generator duplicated path segments:
  - /api/v1/admin/admin/analytics → /api/v1/admin/analytics
  - /api/v1/instructor/instructor/enrollments → /api/v1/instructor/enrollments
  - /api/v1/coupons/coupons/apply → /api/v1/coupons/apply

Solution: Fix URL patterns in test files

Usage:
    python tools/fix_404_url_patterns.py
"""

import re
from pathlib import Path
from typing import List, Tuple

# URL pattern fixes
# Format: (regex_pattern, replacement)
URL_FIXES = [
    # Fix duplicated /admin/admin/ → /admin/
    (r'/api/v1/admin/admin/', r'/api/v1/admin/'),

    # Fix duplicated /instructor/instructor/ → /instructor/
    (r'/api/v1/instructor/instructor/', r'/api/v1/instructor/'),

    # Fix duplicated /coupons/coupons/ → /coupons/
    (r'/api/v1/coupons/coupons/', r'/api/v1/coupons/'),

    # Fix duplicated /invitation-codes/invitation-codes/ → /invitation-codes/
    (r'/api/v1/invitation-codes/invitation-codes/', r'/api/v1/invitation-codes/'),

    # Fix duplicated /locations/locations/ → /locations/
    (r'/api/v1/locations/locations/', r'/api/v1/locations/'),

    # Fix duplicated /motivation/motivation/ → /motivation/
    (r'/api/v1/motivation/motivation/', r'/api/v1/motivation/'),

    # Fix duplicated /onboarding/onboarding/ → /onboarding/
    (r'/api/v1/onboarding/onboarding/', r'/api/v1/onboarding/'),

    # Fix duplicated /profile/profile/ → /profile/
    (r'/api/v1/profile/profile/', r'/api/v1/profile/'),

    # Fix duplicated /quiz/quiz/ → /quiz/
    (r'/api/v1/quiz/quiz/', r'/api/v1/quiz/'),

    # Fix duplicated /specialization/specialization/ → /specialization/
    (r'/api/v1/specialization/specialization/', r'/api/v1/specialization/'),

    # Fix duplicated /dashboard/dashboard/ → /dashboard/
    (r'/api/v1/dashboard/dashboard/', r'/api/v1/dashboard/'),

    # Fix duplicated /sessions/sessions/ → /sessions/
    (r'/api/v1/sessions/sessions/', r'/api/v1/sessions/'),

    # Fix duplicated /tournaments/tournaments/ → /tournaments/
    (r'/api/v1/tournaments/tournaments/', r'/api/v1/tournaments/'),

    # Fix duplicated /campuses/campuses/ → /campuses/
    (r'/api/v1/campuses/campuses/', r'/api/v1/campuses/'),

    # Fix duplicated /instructor-management// → /instructor-management/
    (r'/api/v1/instructor-management//', r'/api/v1/instructor-management/'),

    # Fix trailing slashes on API calls (empty endpoint paths)
    # /api/v1/auth/ → /api/v1/auth (for endpoints like /auth, not /auth/)
    (r'(\'/api/v1/auth/\')(?!\w)', r"'/api/v1/auth'"),  # /auth/ → /auth
    (r'(\'/api/v1/locations/\')(?!\w)', r"'/api/v1/locations'"),  # /locations/ → /locations
    (r'(\'/api/v1/tournaments/\')(?!\w)', r"'/api/v1/tournaments'"),  # /tournaments/ → /tournaments
    (r'(\'/api/v1/quiz/\')(?!\w)', r"'/api/v1/quiz'"),  # /quiz/ → /quiz
    (r'(\'/api/v1/instructor-management/\')(?!\w)', r"'/api/v1/instructor-management'"),  # /instructor-management/ → /instructor-management
]


def fix_url_patterns(file_path: Path) -> Tuple[bool, int]:
    """
    Fix URL patterns in test file.

    Args:
        file_path: Path to test file

    Returns:
        (modified, fix_count) - whether file was modified and number of fixes
    """
    content = file_path.read_text()
    original_content = content
    fix_count = 0

    # Apply all URL fixes
    for pattern, replacement in URL_FIXES:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            # Count how many instances were replaced
            count = len(re.findall(pattern, content))
            fix_count += count
            content = new_content

    if content != original_content:
        file_path.write_text(content)
        return True, fix_count

    return False, 0


def main():
    """Find and fix all URL pattern issues in smoke tests."""
    test_dir = Path("tests/integration/api_smoke")

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    print("🔍 Scanning for smoke test files with URL pattern issues...\n")

    # Find all test files (excluding conftest.py and payload_factory.py)
    test_files = [
        f for f in test_dir.glob("test_*_smoke.py")
        if f.name not in ["conftest.py", "payload_factory.py"]
    ]

    print(f"Found {len(test_files)} smoke test files\n")

    total_files_modified = 0
    total_fixes = 0

    for test_file in sorted(test_files):
        modified, fix_count = fix_url_patterns(test_file)

        if modified:
            total_files_modified += 1
            total_fixes += fix_count
            print(f"✅ {test_file.name}: {fix_count} URL fixes")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Total URL fixes: {total_fixes}")
    print(f"{'='*60}\n")

    if total_files_modified > 0:
        print("✅ All URL pattern issues fixed!")
        print("\nNext steps:")
        print("1. Run smoke tests locally:")
        print("   pytest tests/integration/api_smoke/ -v --tb=short")
        print("2. Verify 404 errors are reduced")
        print("3. Commit changes:")
        print("   git add tests/integration/api_smoke/")
        print('   git commit -m "fix(tests): Fix duplicated URL segments in smoke tests"')
        return 0
    else:
        print("ℹ️  No URL pattern issues found (all tests already fixed)")
        return 0


if __name__ == "__main__":
    exit(main())
