#!/usr/bin/env python3
"""
Duplicate Import Audit Script
Checks all Python files for duplicate import statements
"""
import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def extract_imports(file_path: str) -> Tuple[List[str], Dict[str, List[int]]]:
    """
    Extract all import statements from a Python file

    Returns:
        - List of all imports (for duplicate detection)
        - Dict mapping import statement to line numbers
    """
    imports = []
    import_lines = defaultdict(list)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Match "import X" or "from X import Y"
                if line.startswith('import ') or line.startswith('from '):
                    # Skip commented imports
                    if not line.startswith('#'):
                        imports.append(line)
                        import_lines[line].append(line_num)
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")

    return imports, import_lines


def find_duplicate_imports(project_root: str, exclude_dirs: Set[str] = None) -> Dict[str, List[Tuple[str, List[int]]]]:
    """
    Find all duplicate imports in Python files

    Returns:
        Dict mapping file_path to list of (import_statement, line_numbers)
    """
    if exclude_dirs is None:
        exclude_dirs = {'venv', '__pycache__', '.git', 'node_modules', '.pytest_cache', 'htmlcov'}

    duplicates = {}

    for root, dirs, files in os.walk(project_root):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports, import_lines = extract_imports(file_path)

                # Find duplicates in this file
                file_duplicates = []
                for import_stmt, line_numbers in import_lines.items():
                    if len(line_numbers) > 1:
                        file_duplicates.append((import_stmt, line_numbers))

                if file_duplicates:
                    # Store relative path
                    rel_path = os.path.relpath(file_path, project_root)
                    duplicates[rel_path] = file_duplicates

    return duplicates


def print_audit_report(duplicates: Dict[str, List[Tuple[str, List[int]]]]):
    """Print formatted audit report"""
    print("=" * 80)
    print("🔍 DUPLICATE IMPORTS AUDIT REPORT")
    print("=" * 80)
    print()

    if not duplicates:
        print("✅ No duplicate imports found!")
        print()
        return

    total_files = len(duplicates)
    total_duplicates = sum(len(dups) for dups in duplicates.values())

    print(f"📊 Summary:")
    print(f"   - Files with duplicates: {total_files}")
    print(f"   - Total duplicate imports: {total_duplicates}")
    print()
    print("-" * 80)
    print()

    for file_path, file_duplicates in sorted(duplicates.items()):
        print(f"📄 {file_path}")
        print()

        for import_stmt, line_numbers in file_duplicates:
            print(f"   ❌ Duplicate import on lines {', '.join(map(str, line_numbers))}:")
            print(f"      {import_stmt}")
            print()

        print("-" * 80)
        print()

    print("=" * 80)
    print(f"🎯 Action Items:")
    print(f"   1. Review {total_files} file(s) with duplicate imports")
    print(f"   2. Remove {total_duplicates} duplicate import statement(s)")
    print(f"   3. Verify no functionality is broken after cleanup")
    print("=" * 80)


def main():
    """Main audit execution"""
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"🔍 Scanning project: {project_root}")
    print()

    # Find duplicates
    duplicates = find_duplicate_imports(str(project_root))

    # Print report
    print_audit_report(duplicates)

    # Return exit code
    if duplicates:
        return 1  # Exit with error if duplicates found
    return 0


if __name__ == "__main__":
    exit(main())
