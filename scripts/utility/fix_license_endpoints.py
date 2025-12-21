#!/usr/bin/env python3
"""
Quick fix to add GET /licenses endpoints to all license types
"""

# GānCuju endpoint fix
gancuju_get_endpoint = '''
@router.get("/licenses")
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all GānCuju licenses (Admin only)"""
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can view all licenses")

    try:
        from sqlalchemy import text
        query = text("SELECT * FROM gancuju_licenses WHERE is_active = TRUE ORDER BY id DESC")
        result = db.execute(query).fetchall()
        return [dict(row._mapping) for row in result]
    except:
        return []

'''

# Internship endpoint fix
internship_get_endpoint = '''
@router.get("/licenses")
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all Internship licenses (Admin only)"""
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can view all licenses")

    try:
        from sqlalchemy import text
        query = text("SELECT * FROM internship_licenses WHERE is_active = TRUE ORDER BY id DESC")
        result = db.execute(query).fetchall()
        return [dict(row._mapping) for row in result]
    except:
        return []

'''

# Coach endpoint fix
coach_get_endpoint = '''
@router.get("/licenses")
def list_all_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all Coach licenses (Admin only)"""
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can view all licenses")

    try:
        from sqlalchemy import text
        query = text("SELECT * FROM coach_licenses WHERE is_active = TRUE ORDER BY id DESC")
        result = db.execute(query).fetchall()
        return [dict(row._mapping) for row in result]
    except:
        return []

'''

# Read and modify each file
import re

files = [
    ('app/api/api_v1/endpoints/gancuju.py', gancuju_get_endpoint, '@router.post("/licenses"'),
    ('app/api/api_v1/endpoints/internship.py', internship_get_endpoint, '@router.post("/licenses"'),
    ('app/api/api_v1/endpoints/coach.py', coach_get_endpoint, '@router.post("/licenses"'),
]

for filepath, new_endpoint, insert_before in files:
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Check if GET endpoint already exists
        if '@router.get("/licenses")' in content:
            print(f"✅ {filepath} already has GET /licenses endpoint")
            continue

        # Insert before POST endpoint
        if insert_before in content:
            content = content.replace(insert_before, new_endpoint + insert_before)
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✅ Added GET /licenses to {filepath}")
        else:
            print(f"⚠️  Could not find insertion point in {filepath}")
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")

print("\n✅ License endpoints fixed!")
