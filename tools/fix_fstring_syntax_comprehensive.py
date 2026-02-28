#!/usr/bin/env python3
"""
Comprehensive f-string syntax fix

Problem 1: f"...{test_tournament["key"]}..." - nested double quotes
Problem 2: f'...{test_tournament['key']}...' - nested single quotes (created by previous fix)

Solution:
1. Standardize ALL dictionary access to use double quotes: test_tournament["key"]
2. Change outer f-strings to single quotes when they contain test_tournament["..."]

Usage:
    python tools/fix_fstring_syntax_comprehensive.py
"""

import re
from pathlib import Path
from typing import Tuple


def fix_fstring_syntax(file_path: Path) -> Tuple[bool, int]:
    """
    Fix all f-string syntax issues.

    Args:
        file_path: Path to test file

    Returns:
        (modified, fix_count) - whether file was modified and number of fixes
    """
    content = file_path.read_text()
    original_content = content
    fix_count = 0

    lines = content.split('\n')
    modified_lines = []

    for line in lines:
        # Step 1: Standardize test_tournament['key'] to test_tournament["key"]
        # This ensures ALL dictionary access uses double quotes
        if "test_tournament['" in line:
            # Replace test_tournament['key'] with test_tournament["key"]
            line = re.sub(
                r"test_tournament\['([^']+)'\]",
                r'test_tournament["\1"]',
                line
            )
            fix_count += 1

        # Step 2: Fix f-string quote nesting
        # If line has f' and test_tournament[" (from step 1 or existing), change f' back to f"
        if "f'" in line and 'test_tournament["' in line:
            # This is an f-string with single quotes containing test_tournament["..."]
            # This is VALID - f'...{test_tournament["key"]}...' is correct syntax
            # No change needed - this is fine
            pass

        # Step 3: Fix f"..." with test_tournament["..."] inside (invalid nesting)
        elif 'f"' in line and 'test_tournament["' in line:
            # Invalid: f"...{test_tournament["key"]}..."
            # Fix: change to f'...{test_tournament["key"]}...'

            # Find the f-string and swap outer quotes
            fstring_start = line.find('f"')
            if fstring_start != -1:
                before_fstring = line[:fstring_start]
                fstring_and_after = line[fstring_start:]

                # Replace f" with f'
                fstring_and_after = fstring_and_after.replace('f"', "f'", 1)

                # Find the closing " (should be at end for assertion lines)
                last_quote_idx = fstring_and_after.rfind('"')
                if last_quote_idx != -1:
                    fstring_and_after = (
                        fstring_and_after[:last_quote_idx] +
                        "'" +
                        fstring_and_after[last_quote_idx + 1:]
                    )
                    fix_count += 1

                line = before_fstring + fstring_and_after

        modified_lines.append(line)

    content = '\n'.join(modified_lines)

    if content != original_content:
        file_path.write_text(content)
        return True, fix_count

    return False, 0


def main():
    """Fix all f-string syntax issues."""
    test_dir = Path("tests/integration/api_smoke")

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    print("🔧 Fixing f-string syntax issues comprehensively...\n")

    test_files = [
        f for f in test_dir.glob("test_*_smoke.py")
        if f.name not in ["conftest.py", "payload_factory.py"]
    ]

    print(f"Found {len(test_files)} smoke test files\n")

    total_files_modified = 0
    total_fixes = 0

    for test_file in sorted(test_files):
        modified, fix_count = fix_fstring_syntax(test_file)

        if modified:
            total_files_modified += 1
            total_fixes += fix_count
            print(f"✅ {test_file.name}: {fix_count} syntax fixes")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Total fixes: {total_fixes}")
    print(f"{'='*60}\n")

    if total_files_modified > 0:
        print("✅ All f-string syntax issues fixed!")
        print("\nChanges made:")
        print("  1. Standardized test_tournament['key'] → test_tournament[\"key\"]")
        print("  2. Fixed f-string quote nesting where needed")
        return 0
    else:
        print("ℹ️  No syntax issues found")
        return 0


if __name__ == "__main__":
    exit(main())
