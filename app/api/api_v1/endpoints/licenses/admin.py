"""
Admin license sync operations
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_admin_user_web, get_current_user
from .....models.user import User
from .....services.progress_license_sync_service import ProgressLicenseSyncService
from .....services.audit_service import AuditService
from .....models.audit_log import AuditAction

router = APIRouter()

@router.get("/admin/sync/desync-issues", response_model=List[Dict[str, Any]])
async def get_desync_issues(
    specialization: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Find all users with desync issues between SpecializationProgress and UserLicense

    **Admin/Instructor only**

    - **specialization**: Optional filter for COACH, PLAYER, or INTERNSHIP

    Returns list of users with:
    - Different levels between Progress and License
    - Progress without License
    - License without Progress
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can view sync issues"
        )

    sync_service = ProgressLicenseSyncService(db)
    return sync_service.find_desync_issues(specialization)


@router.post("/admin/sync/user/{user_id}", response_model=Dict[str, Any])
async def sync_user_progress_license(
    user_id: int,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync Progress and License for a specific user

    **Admin/Instructor only**

    Request body:
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **direction**: "progress_to_license" or "license_to_progress"

    Use cases:
    - **progress_to_license**: Student leveled up via gameplay, sync license
    - **license_to_progress**: Admin manually advanced license, sync progress
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can sync progress"
        )

    if 'specialization' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: specialization"
        )

    direction = data.get('direction', 'progress_to_license')
    if direction not in ['progress_to_license', 'license_to_progress']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be 'progress_to_license' or 'license_to_progress'"
        )

    sync_service = ProgressLicenseSyncService(db)

    if direction == 'progress_to_license':
        result = sync_service.sync_progress_to_license(
            user_id=user_id,
            specialization=data['specialization'],
            synced_by=current_user.id
        )
    else:
        result = sync_service.sync_license_to_progress(
            user_id=user_id,
            specialization=data['specialization']
        )

    return result


@router.post("/admin/sync/user/{user_id}/all", response_model=Dict[str, Any])
async def sync_user_all_specializations(
    user_id: int,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync all specializations for a specific user

    **Admin/Instructor only**

    Request body:
    - **direction**: "progress_to_license" or "license_to_progress" (default: progress_to_license)
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can sync progress"
        )

    direction = data.get('direction', 'progress_to_license')
    if direction not in ['progress_to_license', 'license_to_progress']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be 'progress_to_license' or 'license_to_progress'"
        )

    sync_service = ProgressLicenseSyncService(db)
    return sync_service.sync_user_all_specializations(user_id, direction)


@router.post("/admin/sync/all", response_model=Dict[str, Any])
async def sync_all_users(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-sync all users with desync issues

    **Admin only - Use with caution!**

    Request body:
    - **direction**: "progress_to_license" or "license_to_progress" (default: progress_to_license)
    - **dry_run**: If true, only report what would be synced (default: true)

    This endpoint is intended for:
    - Background job execution
    - Manual admin-triggered bulk sync
    - Data migration/cleanup
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform bulk sync"
        )

    direction = data.get('direction', 'progress_to_license')
    dry_run = data.get('dry_run', True)  # Default to dry_run for safety

    if direction not in ['progress_to_license', 'license_to_progress']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be 'progress_to_license' or 'license_to_progress'"
        )

    sync_service = ProgressLicenseSyncService(db)
    return sync_service.auto_sync_all(sync_direction=direction, dry_run=dry_run)


# 💳 ADMIN: Payment Verification for UserLicenses
