#!/usr/bin/env python3
"""
Fix f-string quote nesting issues in smoke tests

Problem: f"...{test_tournament["key"]}..." is invalid syntax
Solution: Change to f'...{test_tournament["key"]}...' (swap outer quotes)

This was introduced when fixing NameErrors by replacing {variable} with {test_tournament["key"]}

Usage:
    python tools/fix_fstring_quote_nesting.py
"""

import re
from pathlib import Path
from typing import Tuple


def fix_fstring_quotes(file_path: Path) -> Tuple[bool, int]:
    """
    Fix f-string quote nesting by swapping outer quotes.

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
        original_line = line

        # Check if line has problematic f-string quote nesting
        # Pattern: f"...{test_tournament["..."]}..."
        if 'f"' in line and ('test_tournament["' in line or "test_tournament['license_id']" in line):
            # Use regex to find and replace f"..." with f'...' when it contains test_tournament["..."]
            # Pattern: f"(anything not containing unescaped " except in {...})"
            # Simpler: just swap f" to f' and the closing " to ' for lines with this pattern

            # Count how many f-strings with dict access we have
            if line.count('f"') >= 1:
                # Replace f"..." with f'...' for the assertion messages
                # We need to be careful - only replace the f-string that contains test_tournament["

                # Strategy: Find f"..." spans and check if they contain test_tournament["
                # Then swap outer quotes for those specific f-strings

                # For simplicity, given our test structure:
                # Most lines with f" and test_tournament[" have a single f-string in assert statements
                # Let's just swap the first and last " after f to '

                # Find start of f-string
                fstring_start = line.find('f"')
                if fstring_start != -1:
                    # Find the closing " - this is tricky with nested braces
                    # Simple heuristic: find the last " on the line (works for single-line assertions)

                    before_fstring = line[:fstring_start]
                    fstring_and_after = line[fstring_start:]

                    # Replace f" with f'
                    fstring_and_after = fstring_and_after.replace('f"', "f'", 1)

                    # Find the closing " (last one on the line usually)
                    # But we need to be smart - it should be the matching one
                    # For assertion lines, it's typically at the end

                    # Reverse search for the last "
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
    """Find and fix all f-string quote nesting issues."""
    test_dir = Path("tests/integration/api_smoke")

    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    print("🔍 Scanning for f-string quote nesting issues...\n")

    # Find all test files
    test_files = [
        f for f in test_dir.glob("test_*_smoke.py")
        if f.name not in ["conftest.py", "payload_factory.py"]
    ]

    print(f"Found {len(test_files)} smoke test files\n")

    total_files_modified = 0
    total_fixes = 0

    for test_file in sorted(test_files):
        modified, fix_count = fix_fstring_quotes(test_file)

        if modified:
            total_files_modified += 1
            total_fixes += fix_count
            print(f"✅ {test_file.name}: {fix_count} quote fixes")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Total fixes: {total_fixes}")
    print(f"{'='*60}\n")

    if total_files_modified > 0:
        print("✅ All f-string quote nesting issues fixed!")
        return 0
    else:
        print("ℹ️  No quote nesting issues found")
        return 0


if __name__ == "__main__":
    exit(main())
