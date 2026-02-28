#!/usr/bin/env python3
"""
Un-skip POST/PATCH/PUT input validation tests

This script removes @pytest.mark.skip decorators from input validation tests
for POST/PATCH/PUT endpoints, allowing them to execute and validate schema constraints.

GET/DELETE endpoints remain skipped since they don't have request bodies.

Usage:
    python tools/unskip_input_validation_tests.py --test-dir tests/integration/api_smoke/
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple


def is_post_patch_put_test(test_content: str) -> bool:
    """Check if test uses POST/PATCH/PUT methods"""
    methods = ['api_client.post', 'api_client.patch', 'api_client.put']
    return any(method in test_content for method in methods)


def has_get_delete_skip_call(test_content: str) -> bool:
    """Check if test has pytest.skip() call for GET/DELETE endpoints"""
    skip_patterns = [
        r'pytest\.skip\("No input validation for (GET|DELETE) endpoints"\)',
        r'pytest\.skip\("No input validation for GET/DELETE endpoints"\)',
    ]
    return any(re.search(pattern, test_content) for pattern in skip_patterns)


def process_test_file(file_path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """
    Process a single test file and remove @pytest.mark.skip decorators
    from POST/PATCH/PUT input validation tests.

    Returns:
        Tuple of (unskipped_count, kept_skipped_count)
    """
    content = file_path.read_text()
    original_content = content

    unskipped = 0
    kept_skipped = 0

    # Pattern to match input validation test functions with skip decorator
    pattern = re.compile(
        r'(@pytest\.mark\.skip\(reason="Input validation requires domain-specific payloads"\)\s*\n)'
        r'(\s*def test_\w+_input_validation\([^)]*\):.*?)(?=\n    def |\n\nclass |\Z)',
        re.DOTALL
    )

    matches = list(pattern.finditer(content))

    for match in matches:
        decorator = match.group(1)
        test_function = match.group(2)

        # Check if this is a POST/PATCH/PUT test
        if is_post_patch_put_test(test_function):
            # Check if it has GET/DELETE skip call inside
            if has_get_delete_skip_call(test_function):
                # This is a GET/DELETE test mislabeled - keep it skipped
                kept_skipped += 1
            else:
                # This is a POST/PATCH/PUT test - un-skip it
                content = content.replace(match.group(0), test_function)
                unskipped += 1
        else:
            # Not a POST/PATCH/PUT test, or has GET/DELETE skip call - keep skipped
            kept_skipped += 1

    # Write changes if content changed and not dry run
    if content != original_content and not dry_run:
        file_path.write_text(content)

    return unskipped, kept_skipped


def main():
    parser = argparse.ArgumentParser(
        description="Un-skip POST/PATCH/PUT input validation tests"
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path("tests/integration/api_smoke/"),
        help="Directory containing smoke test files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    args = parser.parse_args()

    if not args.test_dir.exists():
        print(f"❌ Test directory not found: {args.test_dir}")
        return 1

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning test files in {args.test_dir}...")
    print()

    total_unskipped = 0
    total_kept_skipped = 0
    files_modified = 0

    for test_file in sorted(args.test_dir.glob("test_*_smoke.py")):
        unskipped, kept_skipped = process_test_file(test_file, dry_run=args.dry_run)

        if unskipped > 0:
            files_modified += 1
            status = "Would modify" if args.dry_run else "✓ Modified"
            print(f"{status}: {test_file.name}")
            print(f"  Un-skipped: {unskipped} POST/PATCH/PUT tests")
            if kept_skipped > 0:
                print(f"  Kept skipped: {kept_skipped} GET/DELETE tests")

        total_unskipped += unskipped
        total_kept_skipped += kept_skipped

    print()
    print("=" * 60)
    print(f"{'DRY RUN ' if args.dry_run else ''}SUMMARY")
    print("=" * 60)
    print(f"Files {'to be modified' if args.dry_run else 'modified'}: {files_modified}")
    print(f"Tests un-skipped: {total_unskipped} (POST/PATCH/PUT with invalid payloads)")
    print(f"Tests kept skipped: {total_kept_skipped} (GET/DELETE - no request body)")
    print()

    if args.dry_run:
        print("ℹ️  This was a dry run. Run without --dry-run to apply changes.")
    else:
        print("✅ Changes applied successfully!")
        print()
        print("Next steps:")
        print("  1. Run tests: pytest tests/integration/api_smoke/ -v --tb=short")
        print("  2. Verify 0 failures (expect 422 for invalid payloads)")
        print("  3. Check final count: should see ~242 more executed tests")

    return 0


if __name__ == "__main__":
    exit(main())
