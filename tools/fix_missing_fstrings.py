"""
P0 Fix Tool: Add missing f-string prefixes to test paths

Problem: Enhancement script missed some paths that need f-string conversion
Solution: Add f-string prefix where needed
"""

import re
from pathlib import Path


def fix_missing_fstrings(content: str) -> str:
    """Add f-string prefix to paths that contain {test_*} parameters."""

    # Pattern: api_client.METHOD("/path/with/{test_*}", ...)
    # Should be: api_client.METHOD(f"/path/with/{test_*}", ...)

    # Fix patterns like: get("/badges/showcase/{test_student_id}"
    # to: get(f"/badges/showcase/{test_student_id}"

    patterns_to_fix = [
        (r'api_client\.(get|post|put|patch|delete)\("(/[^"]*\{test_[^}]+\}[^"]*)"',
         r'api_client.\1(f"\2"'),
    ]

    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)

    return content


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent.parent
    test_file = root_dir / "tests/integration/api_smoke/test_tournaments_smoke.py"

    print("P0: Fixing missing f-string prefixes...")
    print(f"Test file: {test_file}")

    # Read content
    content = test_file.read_text()

    # Count issues before fix
    issues_before = len(re.findall(r'api_client\.\w+\("(/[^"]*\{test_[^}]+\}[^"]*)"', content))
    print(f"\nIssues found: {issues_before} paths missing f-string prefix")

    # Fix
    fixed_content = fix_missing_fstrings(content)

    # Count issues after fix
    issues_after = len(re.findall(r'api_client\.\w+\("(/[^"]*\{test_[^}]+\}[^"]*)"', fixed_content))

    # Write back
    test_file.write_text(fixed_content)

    print(f"\n✅ Fixed: {issues_before - issues_after} f-string prefixes added")
    print(f"Remaining issues: {issues_after}")

    if issues_after == 0:
        print("\n✅ All f-string issues resolved!")
    else:
        print(f"\n⚠️ {issues_after} issues remain (may need manual review)")


if __name__ == "__main__":
    main()
