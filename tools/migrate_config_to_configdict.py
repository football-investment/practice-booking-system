#!/usr/bin/env python3
"""
Migrate Pydantic v1 `class Config:` to v2 `model_config = ConfigDict(...)`

This script converts all schemas from old v1 style to v2 style.

Usage:
    python tools/migrate_config_to_configdict.py --schema-dir app/schemas/
"""

import argparse
import re
from pathlib import Path


def process_file(file_path: Path, dry_run: bool = False) -> int:
    """Convert class Config: to model_config in a single file"""
    content = file_path.read_text()
    original_content = content

    # Ensure ConfigDict is imported
    if 'ConfigDict' not in content and 'class Config:' in content:
        # Add ConfigDict to import
        content = re.sub(
            r'(from pydantic import.*BaseModel)',
            r'\1, ConfigDict',
            content,
            count=1
        )

    # Find all class Config: blocks
    pattern = re.compile(
        r'\n    class Config:\n        from_attributes = True\n',
        re.MULTILINE
    )

    # Replace with model_config
    content = pattern.sub(
        '\n    model_config = ConfigDict(from_attributes=True)\n',
        content
    )

    modified = content != original_content

    if modified and not dry_run:
        file_path.write_text(content)

    return 1 if modified else 0


def main():
    parser = argparse.ArgumentParser(description="Migrate class Config to model_config")
    parser.add_argument(
        "--schema-dir",
        type=Path,
        action='append',
        default=[],
        help="Directory to scan (can specify multiple times)",
    )
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if not args.schema_dir:
        args.schema_dir = [Path("app/schemas/"), Path("app/api/api_v1/endpoints/")]

    total = 0
    for schema_dir in args.schema_dir:
        if not schema_dir.exists():
            continue

        for py_file in schema_dir.rglob("*.py"):
            if py_file.name == "__init__.py" or "test_" in py_file.name:
                continue

            modified = process_file(py_file, dry_run=args.dry_run)
            if modified:
                total += 1
                print(f"{'Would modify' if args.dry_run else '✓ Modified'}: {py_file}")

    print(f"\nTotal files {'to be modified' if args.dry_run else 'modified'}: {total}")
    return 0


if __name__ == "__main__":
    exit(main())
