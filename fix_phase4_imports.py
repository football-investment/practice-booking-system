#!/usr/bin/env python3
"""
Fix Phase 4 import issues - Remove duplicate 4-level imports
"""
import re
from pathlib import Path

# Files that need fixing
files_to_fix = [
    "app/api/api_v1/endpoints/specializations/user.py",
    "app/api/api_v1/endpoints/specializations/progress.py",
    "app/api/api_v1/endpoints/specializations/info.py",
    "app/api/api_v1/endpoints/invoices/admin.py",
    "app/api/api_v1/endpoints/invoices/requests.py",
    "app/api/api_v1/endpoints/lfa_player/licenses.py",
    "app/api/api_v1/endpoints/lfa_player/skills.py",
    "app/api/api_v1/endpoints/lfa_player/credits.py",
    "app/api/api_v1/endpoints/instructor_assignments/availability.py",
    "app/api/api_v1/endpoints/instructor_assignments/requests.py",
    "app/api/api_v1/endpoints/instructor_assignments/discovery.py",
]

def fix_imports(file_path):
    """Remove lines with 4-level imports (from ....xxx)"""
    path = Path(file_path)
    if not path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False

    with open(path, 'r') as f:
        lines = f.readlines()

    # Remove lines that start with "from ...." (4 dots)
    new_lines = []
    removed_count = 0
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("from ...."):
            print(f"  Line {i}: Removed '{line.strip()}'")
            removed_count += 1
        else:
            new_lines.append(line)

    if removed_count > 0:
        with open(path, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Fixed {path.name}: Removed {removed_count} duplicate imports")
        return True
    else:
        print(f"✓  {path.name}: No 4-level imports found")
        return False

def main():
    print("=" * 60)
    print("Phase 4 Import Fixer - Removing 4-level imports")
    print("=" * 60)

    fixed_count = 0
    for file_path in files_to_fix:
        print(f"\nChecking: {file_path}")
        if fix_imports(file_path):
            fixed_count += 1

    print("\n" + "=" * 60)
    print(f"Summary: Fixed {fixed_count}/{len(files_to_fix)} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
