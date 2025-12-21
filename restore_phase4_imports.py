#!/usr/bin/env python3
"""
Restore correct 5-level imports to Phase 4 files
"""
from pathlib import Path

# Define correct imports for each module type
COMMON_IMPORTS = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Dict, Optional

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
"""

ADMIN_IMPORTS = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Dict, Optional

from .....database import get_db
from .....dependencies import get_current_admin_user
from .....models.user import User
"""

SPECIALIZATION_IMPORTS = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Dict, Optional

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....models.specialization import SpecializationType
"""

files_to_fix = {
    "app/api/api_v1/endpoints/specializations/user.py": SPECIALIZATION_IMPORTS,
    "app/api/api_v1/endpoints/specializations/progress.py": SPECIALIZATION_IMPORTS,
    "app/api/api_v1/endpoints/specializations/info.py": SPECIALIZATION_IMPORTS,
    "app/api/api_v1/endpoints/invoices/admin.py": ADMIN_IMPORTS,
    "app/api/api_v1/endpoints/invoices/requests.py": COMMON_IMPORTS,
    "app/api/api_v1/endpoints/lfa_player/licenses.py": COMMON_IMPORTS,
    "app/api/api_v1/endpoints/lfa_player/skills.py": COMMON_IMPORTS,
    "app/api/api_v1/endpoints/lfa_player/credits.py": COMMON_IMPORTS,
    "app/api/api_v1/endpoints/instructor_assignments/availability.py": COMMON_IMPORTS,
    "app/api/api_v1/endpoints/instructor_assignments/requests.py": COMMON_IMPORTS,
    "app/api/api_v1/endpoints/instructor_assignments/discovery.py": ADMIN_IMPORTS,
}

def restore_imports(file_path, correct_imports):
    """Add correct imports at the top after docstring"""
    path = Path(file_path)
    if not path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False

    with open(path, 'r') as f:
        content = f.read()

    # Find where to insert imports (after first docstring or at start)
    lines = content.split('\n')
    insert_pos = 0
    in_docstring = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check for docstring
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                # Check if it's a one-line docstring
                if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    insert_pos = i + 1
                    break
            else:
                in_docstring = False
                insert_pos = i + 1
                break
        # If we hit imports or code, stop
        elif stripped and not stripped.startswith('#'):
            if not stripped.startswith('from') and not stripped.startswith('import'):
                break

    # Insert imports
    new_lines = lines[:insert_pos] + [''] + correct_imports.strip().split('\n') + [''] + lines[insert_pos:]

    with open(path, 'w') as f:
        f.write('\n'.join(new_lines))

    print(f"✅ Restored imports in {path.name}")
    return True

def main():
    print("=" * 60)
    print("Phase 4 Import Restorer - Adding correct 5-level imports")
    print("=" * 60)

    fixed_count = 0
    for file_path, imports in files_to_fix.items():
        print(f"\nRestoring: {file_path}")
        if restore_imports(file_path, imports):
            fixed_count += 1

    print("\n" + "=" * 60)
    print(f"Summary: Restored imports in {fixed_count}/{len(files_to_fix)} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
