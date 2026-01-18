#!/usr/bin/env python3
"""
Automated Duplicate Import Cleanup Script

This script automatically removes duplicate import statements from Python files
while preserving:
- Import order and grouping
- Comments associated with imports
- Code formatting and style

Usage:
    python scripts/fix_duplicate_imports.py [--dry-run] [--file <path>]

Options:
    --dry-run: Show what would be changed without modifying files
    --file: Process only a specific file
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Set, Tuple, Dict


def extract_import_blocks(content: str) -> Tuple[List[str], List[Tuple[int, str]], List[str]]:
    """
    Extract import statements and preserve file structure.

    Returns:
        - Lines before imports
        - List of (line_number, import_statement) tuples
        - Lines after imports
    """
    lines = content.split('\n')

    before_imports = []
    import_lines = []
    after_imports = []

    in_import_section = False
    import_section_ended = False
    current_line_num = 0

    # Track multiline imports
    multiline_import = []
    multiline_start = -1

    for i, line in enumerate(lines):
        current_line_num = i + 1
        stripped = line.strip()

        # Handle multiline imports
        if multiline_import:
            multiline_import.append(line)
            if ')' in line or (stripped and not stripped.endswith('\\')):
                # End of multiline import
                full_import = '\n'.join(multiline_import)
                import_lines.append((multiline_start, full_import))
                multiline_import = []
                multiline_start = -1
                in_import_section = True
            continue

        # Check if line is an import
        if stripped.startswith(('import ', 'from ')):
            in_import_section = True
            import_section_ended = False

            # Check if multiline import
            if '(' in line and ')' not in line:
                multiline_import = [line]
                multiline_start = current_line_num
                continue

            import_lines.append((current_line_num, line))

        # Line is not an import
        elif in_import_section and not stripped:
            # Empty line in import section - could be separator
            import_lines.append((current_line_num, line))

        elif in_import_section and (stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''")):
            # Comment in import section
            import_lines.append((current_line_num, line))

        else:
            # Non-import line
            if in_import_section and stripped:
                # First non-import code after imports
                import_section_ended = True
                in_import_section = False

            if not import_section_ended and not in_import_section:
                before_imports.append(line)
            else:
                after_imports.append(line)

    return before_imports, import_lines, after_imports


def normalize_import(import_line: str) -> str:
    """
    Normalize import statement for comparison.
    Handles multiline imports and removes extra whitespace.
    """
    # Remove comments
    if '#' in import_line:
        import_line = import_line[:import_line.index('#')]

    # Collapse whitespace and newlines
    normalized = ' '.join(import_line.split())

    # Remove parentheses and normalize spacing
    normalized = normalized.replace('( ', '(').replace(' )', ')')
    normalized = normalized.replace(',', ', ')
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()


def deduplicate_imports(import_lines: List[Tuple[int, str]]) -> List[str]:
    """
    Remove duplicate imports while preserving order and grouping.

    Strategy:
    1. Keep first occurrence of each unique import
    2. Preserve empty lines between import groups
    3. Preserve comments
    """
    seen_imports: Set[str] = set()
    deduplicated: List[str] = []

    for line_num, line in import_lines:
        stripped = line.strip()

        # Preserve empty lines and comments
        if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            deduplicated.append(line)
            continue

        # Check if import statement
        if stripped.startswith(('import ', 'from ')):
            normalized = normalize_import(line)

            if normalized not in seen_imports:
                seen_imports.add(normalized)
                deduplicated.append(line)
            # else: skip duplicate

    return deduplicated


def clean_import_section(deduplicated: List[str]) -> List[str]:
    """
    Clean up the deduplicated import section:
    - Remove excessive empty lines
    - Ensure proper grouping
    """
    cleaned = []
    prev_empty = False

    for line in deduplicated:
        stripped = line.strip()

        # Handle empty lines
        if not stripped:
            if not prev_empty and cleaned:  # Allow one empty line, but not at start
                cleaned.append(line)
                prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False

    # Remove trailing empty lines from import section
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    return cleaned


def process_file(file_path: str, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Process a single Python file to remove duplicate imports.

    Returns:
        - Whether changes were made
        - Number of duplicates removed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Extract sections
        before_imports, import_lines, after_imports = extract_import_blocks(original_content)

        # Count original imports
        original_import_count = sum(1 for _, line in import_lines
                                   if line.strip() and line.strip().startswith(('import ', 'from ')))

        # Deduplicate
        deduplicated = deduplicate_imports(import_lines)

        # Count deduplicated imports
        new_import_count = sum(1 for line in deduplicated
                              if line.strip() and line.strip().startswith(('import ', 'from ')))

        duplicates_removed = original_import_count - new_import_count

        if duplicates_removed > 0:
            # Clean up
            cleaned_imports = clean_import_section(deduplicated)

            # Reconstruct file
            new_content_parts = []

            if before_imports:
                new_content_parts.append('\n'.join(before_imports))

            if cleaned_imports:
                new_content_parts.append('\n'.join(cleaned_imports))

            if after_imports:
                new_content_parts.append('\n'.join(after_imports))

            new_content = '\n'.join(new_content_parts)

            # Write back
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

            return True, duplicates_removed

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def find_python_files(project_root: str, exclude_dirs: Set[str]) -> List[str]:
    """Find all Python files in the project."""
    python_files = []

    for root, dirs, files in os.walk(project_root):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        # Find Python files
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                python_files.append(file_path)

    return python_files


def main():
    parser = argparse.ArgumentParser(description='Remove duplicate imports from Python files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without modifying files')
    parser.add_argument('--file', type=str,
                       help='Process only a specific file')

    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    exclude_dirs = {
        'venv', '__pycache__', '.git', 'node_modules',
        '.pytest_cache', 'htmlcov', 'dist', 'build',
        '.mypy_cache', '.ruff_cache'
    }

    # Get files to process
    if args.file:
        files_to_process = [args.file]
    else:
        files_to_process = find_python_files(project_root, exclude_dirs)

    print(f"{'DRY RUN - ' if args.dry_run else ''}Processing {len(files_to_process)} Python files...\n")

    total_files_changed = 0
    total_duplicates_removed = 0
    changed_files = []

    for file_path in sorted(files_to_process):
        changed, duplicates = process_file(file_path, dry_run=args.dry_run)

        if changed:
            total_files_changed += 1
            total_duplicates_removed += duplicates
            rel_path = os.path.relpath(file_path, project_root)
            changed_files.append((rel_path, duplicates))

            status = "Would fix" if args.dry_run else "Fixed"
            print(f"✓ {status}: {rel_path} ({duplicates} duplicates removed)")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"Summary:")
    print(f"  Files processed: {len(files_to_process)}")
    print(f"  Files {'that would be ' if args.dry_run else ''}changed: {total_files_changed}")
    print(f"  Total duplicates removed: {total_duplicates_removed}")

    if args.dry_run and total_files_changed > 0:
        print(f"\nRun without --dry-run to apply these changes.")

    if total_files_changed > 0:
        print(f"\nTop 10 files with most duplicates removed:")
        for rel_path, count in sorted(changed_files, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {count:3d} - {rel_path}")


if __name__ == '__main__':
    main()
