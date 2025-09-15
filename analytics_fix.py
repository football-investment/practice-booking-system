#!/usr/bin/env python3
"""
GYORS IMPORT FIX - Analytics endpoints
"""

import os
from pathlib import Path

def fix_analytics_import():
    """Fix the import error in analytics.py"""
    
    analytics_file = Path("app/api/api_v1/endpoints/analytics.py")
    
    if not analytics_file.exists():
        print("❌ Analytics file not found!")
        return False
    
    # Read current content
    content = analytics_file.read_text()
    
    # Fix the import line
    old_import = "from app.core.permissions import get_current_admin_or_instructor_user"
    new_import = "from app.dependencies import get_current_admin_or_instructor_user"
    
    # Replace the problematic import
    fixed_content = content.replace(old_import, new_import)
    
    # Write back the fixed content
    analytics_file.write_text(fixed_content)
    
    print("✅ Import hiba javítva!")
    return True


if __name__ == "__main__":
    print("🔧 GYORS IMPORT FIX")
    print("===================")
    
    if fix_analytics_import():
        print("✅ Import javítva - most már indulnia kell a backend-nek!")
        print("\n📋 NEXT:")
        print("uvicorn app.main:app --reload")
    else:
        print("❌ Hiba a javítás során")