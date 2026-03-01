#!/usr/bin/env python3
"""
Un-skip POST/PATCH/PUT input validation tests (v2 - fixes indentation issues)

This script removes @pytest.mark.skip decorators from input validation tests
for POST/PATCH/PUT endpoints, preserving proper indentation.

Usage:
    python tools/unskip_input_validation_tests_v2.py --test-dir tests/integration/api_smoke/
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple


def process_test_file(file_path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """
    Process a single test file and remove @pytest.mark.skip decorators
    from POST/PATCH/PUT input validation tests.

    Returns:
        Tuple of (unskipped_count, kept_skipped_count)
    """
    lines = file_path.read_text().splitlines(keepends=True)
    modified_lines = []

    unskipped = 0
    kept_skipped = 0
    skip_next_decorator = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this is a skip decorator for input validation
        if '@pytest.mark.skip(reason="Input validation requires domain-specific payloads")' in line:
            # Look ahead to find the function definition
            func_line_idx = i + 1
            while func_line_idx < len(lines) and not lines[func_line_idx].strip().startswith('def '):
                func_line_idx += 1

            if func_line_idx < len(lines):
                func_def = lines[func_line_idx]

                # Check if this is an input_validation test
                if 'test_' in func_def and '_input_validation' in func_def:
                    # Scan ahead to check if it's POST/PATCH/PUT or GET/DELETE
                    test_body_start = func_line_idx + 1
                    test_body_end = min(test_body_start + 50, len(lines))  # Look ahead 50 lines max
                    test_body = ''.join(lines[test_body_start:test_body_end])

                    # Check for HTTP methods
                    has_post_patch_put = any(method in test_body for method in ['api_client.post', 'api_client.patch', 'api_client.put'])
                    has_get_delete_skip = 'pytest.skip("No input validation for' in test_body

                    if has_post_patch_put and not has_get_delete_skip:
                        # Un-skip this test - skip the decorator line
                        unskipped += 1
                        i += 1  # Skip the decorator line
                        continue
                    else:
                        # Keep it skipped
                        kept_skipped += 1

        # Keep this line
        modified_lines.append(line)
        i += 1

    # Write changes if content changed and not dry run
    new_content = ''.join(modified_lines)
    original_content = ''.join(lines)

    if new_content != original_content and not dry_run:
        file_path.write_text(new_content)

    return unskipped, kept_skipped


def main():
    parser = argparse.ArgumentParser(
        description="Un-skip POST/PATCH/PUT input validation tests (v2)"
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

    return 0


if __name__ == "__main__":
    exit(main())
