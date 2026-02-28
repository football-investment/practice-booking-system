#!/usr/bin/env python3
"""
Add ConfigDict(extra='forbid') to all request schemas

This script adds `model_config = ConfigDict(extra='forbid')` to all Pydantic BaseModel
schemas that are used for API requests (Create, Update, Request, etc.).

This ensures proper validation - endpoints will reject payloads with unknown fields,
returning HTTP 422 instead of silently ignoring them.

Usage:
    python tools/add_extra_forbid_to_schemas.py --schema-dir app/schemas/
    python tools/add_extra_forbid_to_schemas.py --schema-dir app/api/ --dry-run
"""

import argparse
import re
from pathlib import Path
from typing import Tuple


def should_add_extra_forbid(class_name: str) -> bool:
    """Check if this schema should have extra='forbid' based on naming convention"""
    request_patterns = [
        'Create', 'Update', 'Request', 'Base', 'Config',
        'Override', 'Submission', 'Rejection', 'Confirm', 'Cancel'
    ]
    return any(pattern in class_name for pattern in request_patterns)


def already_has_config(class_content: str) -> bool:
    """Check if class already has model_config defined"""
    return 'model_config' in class_content


def has_configdict_import(file_content: str) -> bool:
    """Check if file already imports ConfigDict"""
    return 'ConfigDict' in file_content


def add_configdict_import(file_content: str) -> str:
    """Add ConfigDict to pydantic import if not already present"""
    if has_configdict_import(file_content):
        return file_content

    # Pattern 1: from pydantic import BaseModel
    pattern1 = re.compile(r'(from pydantic import (?!.*ConfigDict).*BaseModel(?!.*ConfigDict)[^\n]*)')
    match1 = pattern1.search(file_content)

    if match1:
        old_import = match1.group(1)
        # Add ConfigDict after BaseModel
        new_import = old_import.replace('BaseModel', 'BaseModel, ConfigDict')
        file_content = file_content.replace(old_import, new_import, 1)

    return file_content


def process_file(file_path: Path, dry_run: bool = False) -> Tuple[int, int]:
    """
    Process a single Python file and add ConfigDict(extra='forbid') to request schemas.

    Returns:
        Tuple of (modified_count, skipped_count)
    """
    content = file_path.read_text()
    original_content = content

    modified = 0
    skipped = 0

    # First, ensure ConfigDict is imported
    content = add_configdict_import(content)

    # Pattern to match class definitions
    class_pattern = re.compile(
        r'(class (\w+)\(BaseModel\):.*?)(?=\n    \w+:|""")',
        re.DOTALL
    )

    for match in class_pattern.finditer(content):
        class_def = match.group(1)
        class_name = match.group(2)

        # Check if this is a request schema
        if not should_add_extra_forbid(class_name):
            continue

        # Check if already has model_config
        if already_has_config(class_def):
            skipped += 1
            continue

        # Find the position after the docstring (if any) or after class definition line
        lines = class_def.split('\n')
        insert_line_idx = 1  # Default: right after class definition

        # Check if there's a docstring
        if len(lines) > 1 and lines[1].strip().startswith('"""'):
            # Find end of docstring
            for i in range(2, len(lines)):
                if '"""' in lines[i]:
                    insert_line_idx = i + 1
                    break

        # Build new class definition with model_config
        new_lines = lines[:]
        indent = '    '  # Standard Python class body indent
        config_line = f'{indent}model_config = ConfigDict(extra=\'forbid\')\n'

        new_lines.insert(insert_line_idx, config_line)
        new_class_def = '\n'.join(new_lines)

        # Replace in content
        content = content.replace(class_def, new_class_def, 1)
        modified += 1

    # Write changes if content changed and not dry run
    if content != original_content and not dry_run:
        file_path.write_text(content)

    return modified, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Add ConfigDict(extra='forbid') to request schemas"
    )
    parser.add_argument(
        "--schema-dir",
        type=Path,
        action='append',
        default=[],
        help="Directory to scan for schema files (can specify multiple times)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    args = parser.parse_args()

    if not args.schema_dir:
        args.schema_dir = [
            Path("app/schemas/"),
            Path("app/api/api_v1/endpoints/"),
        ]

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning schema files...")
    print()

    total_modified = 0
    total_skipped = 0
    files_processed = 0

    for schema_dir in args.schema_dir:
        if not schema_dir.exists():
            print(f"⚠️  Directory not found: {schema_dir}")
            continue

        for py_file in schema_dir.rglob("*.py"):
            # Skip __init__.py and test files
            if py_file.name == "__init__.py" or "test_" in py_file.name:
                continue

            modified, skipped = process_file(py_file, dry_run=args.dry_run)

            if modified > 0:
                files_processed += 1
                status = "Would modify" if args.dry_run else "✓ Modified"
                print(f"{status}: {py_file}")
                print(f"  Added extra='forbid' to {modified} schemas")
                if skipped > 0:
                    print(f"  Skipped {skipped} schemas (already configured)")

            total_modified += modified
            total_skipped += skipped

    print()
    print("=" * 60)
    print(f"{'DRY RUN ' if args.dry_run else ''}SUMMARY")
    print("=" * 60)
    print(f"Files {'to be modified' if args.dry_run else 'modified'}: {files_processed}")
    print(f"Schemas modified: {total_modified}")
    print(f"Schemas skipped: {total_skipped} (already configured)")
    print()

    if args.dry_run:
        print("ℹ️  This was a dry run. Run without --dry-run to apply changes.")
    else:
        print("✅ Changes applied successfully!")
        print()
        print("Next steps:")
        print("  1. Run tests: pytest tests/integration/api_smoke/ -v")
        print("  2. Expect 422 for invalid payloads (input_validation tests should pass)")

    return 0


if __name__ == "__main__":
    exit(main())
