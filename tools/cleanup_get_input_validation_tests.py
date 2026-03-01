#!/usr/bin/env python3
"""
Cleanup script for removing meaningless GET/DELETE input validation tests.

Background:
- Auto-generated smoke tests include input_validation tests for ALL endpoints
- GET/DELETE endpoints do NOT validate request body (no payload to validate)
- These tests always skip themselves: pytest.skip("No input validation for GET endpoints")
- Cleanup: Remove 338 GET/DELETE input_validation tests (52% of 651 total)

Usage:
    python tools/cleanup_get_input_validation_tests.py --dry-run  # Preview changes
    python tools/cleanup_get_input_validation_tests.py            # Execute deletion
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse


def extract_http_method_from_happy_path(content: str, base_test_name: str) -> str:
    """
    Determines HTTP method by finding corresponding happy_path test.

    Args:
        content: Full test file content
        base_test_name: Test name without _input_validation suffix

    Returns:
        HTTP method (GET, POST, PATCH, PUT, DELETE) or UNKNOWN
    """
    happy_path_pattern = rf'def {base_test_name}[\s\S]*?(?=\n    def |\Z)'
    match = re.search(happy_path_pattern, content)

    if not match:
        return "UNKNOWN"

    happy_path_code = match.group(0)

    # Check for HTTP method calls (in priority order to handle multiple methods)
    if "api_client.get(" in happy_path_code:
        return "GET"
    elif "api_client.delete(" in happy_path_code:
        return "DELETE"
    elif "api_client.post(" in happy_path_code:
        return "POST"
    elif "api_client.patch(" in happy_path_code:
        return "PATCH"
    elif "api_client.put(" in happy_path_code:
        return "PUT"
    else:
        return "UNKNOWN"


def find_input_validation_test_block(content: str, test_name: str) -> Tuple[int, int]:
    """
    Finds the start and end position of an input_validation test function.

    Args:
        content: Full test file content
        test_name: Name of the test function (e.g., test_get_user_input_validation)

    Returns:
        Tuple of (start_pos, end_pos) in the content string
        Returns (-1, -1) if not found
    """
    # Find the skip decorator (if exists) before the function
    skip_pattern = rf'(    @pytest\.mark\.skip.*?\n)'
    # Find the function definition
    func_pattern = rf'    def {test_name}\('

    # Search for the function
    func_match = re.search(func_pattern, content)
    if not func_match:
        return (-1, -1)

    func_start = func_match.start()

    # Check if there's a skip decorator before it
    # Look backward up to 200 chars for skip decorator
    look_back = max(0, func_start - 200)
    before_func = content[look_back:func_start]
    skip_match = re.search(skip_pattern, before_func)

    if skip_match:
        # Start from skip decorator
        start_pos = look_back + skip_match.start()
    else:
        # Start from function definition
        start_pos = func_start

    # Find the end: next function definition at same indentation level or end of class
    # Look for: "    def " (4 spaces) or "\n\nclass " or end of file
    next_func_pattern = rf'\n    def |\n\nclass |\Z'
    next_match = re.search(next_func_pattern, content[func_start:])

    if next_match:
        # End position is just before the next function/class
        end_pos = func_start + next_match.start()
        # Include the newline before next function
        if content[end_pos:end_pos+1] == '\n':
            end_pos += 1
    else:
        # No next function found, go to end
        end_pos = len(content)

    return (start_pos, end_pos)


def cleanup_file(file_path: Path, dry_run: bool = True) -> Dict[str, int]:
    """
    Removes GET/DELETE input_validation tests from a single file.

    Args:
        file_path: Path to smoke test file
        dry_run: If True, only preview changes without modifying file

    Returns:
        Dict with counts of removed tests by HTTP method
    """
    content = file_path.read_text()
    original_content = content

    stats = {"GET": 0, "DELETE": 0, "SKIPPED_NON_GET_DELETE": 0}

    # Find all input_validation test functions
    input_val_tests = re.findall(r'def (test_\w+_input_validation)', content)

    tests_to_remove = []

    for test_name in input_val_tests:
        # Determine HTTP method
        base_name = test_name.replace("_input_validation", "_happy_path")
        http_method = extract_http_method_from_happy_path(content, base_name)

        # Only remove GET/DELETE
        if http_method in ["GET", "DELETE"]:
            start, end = find_input_validation_test_block(content, test_name)
            if start != -1:
                tests_to_remove.append((start, end, test_name, http_method))
                stats[http_method] += 1
        else:
            stats["SKIPPED_NON_GET_DELETE"] += 1

    # Remove tests in reverse order to maintain correct positions
    tests_to_remove.sort(reverse=True)

    for start, end, test_name, http_method in tests_to_remove:
        # Remove the test block
        content = content[:start] + content[end:]

    # Only write if content changed
    if content != original_content:
        if not dry_run:
            file_path.write_text(content)
            print(f"✅ {file_path.name}: Removed {stats['GET']} GET + {stats['DELETE']} DELETE tests")
        else:
            print(f"🔍 {file_path.name}: Would remove {stats['GET']} GET + {stats['DELETE']} DELETE tests")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Cleanup GET/DELETE input validation tests")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    args = parser.parse_args()

    smoke_dir = Path("tests/integration/api_smoke")

    if not smoke_dir.exists():
        print(f"❌ Error: Directory {smoke_dir} not found")
        print("   Run this script from the project root directory")
        sys.exit(1)

    print("="  * 70)
    print("🧹 Cleanup GET/DELETE Input Validation Tests")
    print("=" * 70)
    print(f"Mode: {'DRY-RUN (preview only)' if args.dry_run else 'EXECUTE (files will be modified)'}")
    print(f"Directory: {smoke_dir}")
    print()

    total_stats = {"GET": 0, "DELETE": 0, "SKIPPED_NON_GET_DELETE": 0}
    files_modified = 0

    test_files = sorted(smoke_dir.glob("test_*_smoke.py"))

    for test_file in test_files:
        file_stats = cleanup_file(test_file, dry_run=args.dry_run)

        if file_stats["GET"] + file_stats["DELETE"] > 0:
            files_modified += 1

        for key in total_stats:
            total_stats[key] += file_stats[key]

    print()
    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"Files processed: {len(test_files)}")
    print(f"Files modified: {files_modified}")
    print(f"\nTests removed:")
    print(f"  - GET:    {total_stats['GET']}")
    print(f"  - DELETE: {total_stats['DELETE']}")
    print(f"  - TOTAL:  {total_stats['GET'] + total_stats['DELETE']}")
    print(f"\nTests preserved (POST/PATCH/PUT):")
    print(f"  - COUNT:  {total_stats['SKIPPED_NON_GET_DELETE']}")
    print()

    if args.dry_run:
        print("⚠️  DRY-RUN MODE: No files were modified")
        print("   Run without --dry-run to execute deletion")
    else:
        print("✅ Cleanup complete!")
        print(f"   {total_stats['GET'] + total_stats['DELETE']} tests removed")
        print(f"   {total_stats['SKIPPED_NON_GET_DELETE']} POST/PATCH/PUT tests preserved")

    print("=" * 70)


if __name__ == "__main__":
    main()
