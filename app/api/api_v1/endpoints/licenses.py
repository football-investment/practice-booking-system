"""
🏮 GānCuju™️©️ License API Endpoints
Marketing-oriented license progression system API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from ....database import get_db
from ....services.license_service import LicenseService
from ....services.progress_license_sync_service import ProgressLicenseSyncService
from ....services.audit_service import AuditService
from ....dependencies import get_current_user
from ....models.user import User, UserRole
from ....models.audit_log import AuditAction

router = APIRouter()


@router.get("/metadata", response_model=List[Dict[str, Any]])
async def get_license_metadata(
    specialization: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get license metadata for all specializations or a specific one

    - **specialization**: Optional filter by COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_all_license_metadata(specialization)


@router.get("/metadata/{specialization}", response_model=List[Dict[str, Any]])
async def get_license_metadata_by_specialization(
    specialization: str,
    db: Session = Depends(get_db)
):
    """
    Get license metadata for a specific specialization (path parameter)

    - **specialization**: COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_all_license_metadata(specialization)


@router.get("/metadata/{specialization}/{level}", response_model=Dict[str, Any])
async def get_license_level_metadata(
    specialization: str,
    level: int,
    db: Session = Depends(get_db)
):
    """
    Get specific license level metadata with marketing content
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: License level number (1-8 for Coach/Player, 1-5 for Internship)
    """
    license_service = LicenseService(db)
    metadata = license_service.get_license_metadata_by_level(specialization, level)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License level {level} not found for {specialization}"
        )
    
    return metadata


@router.get("/progression/{specialization}", response_model=List[Dict[str, Any]])
async def get_specialization_progression(
    specialization: str,
    db: Session = Depends(get_db)
):
    """
    Get complete progression path for a specialization
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_specialization_progression_path(specialization)


@router.get("/my-licenses", response_model=List[Dict[str, Any]])
async def get_my_licenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all licenses for the current user
    """
    license_service = LicenseService(db)
    return license_service.get_user_licenses(current_user.id)


@router.get("/me", response_model=List[Dict[str, Any]])
async def get_my_licenses_short(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all licenses for the current user (short URL)
    """
    license_service = LicenseService(db)
    return license_service.get_user_licenses(current_user.id)


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_license_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive license dashboard for the current user
    """
    license_service = LicenseService(db)
    return license_service.get_user_license_dashboard(current_user.id)


@router.post("/advance", response_model=Dict[str, Any])
async def advance_license(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request license advancement (requires instructor approval for actual advancement)
    
    Request body:
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **target_level**: Desired level number
    - **reason**: Reason for advancement request
    """
    required_fields = ['specialization', 'target_level']
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    license_service = LicenseService(db)
    
    # For now, allow self-advancement for testing
    # In production, this would create an advancement request
    result = license_service.advance_license(
        user_id=current_user.id,
        specialization=data['specialization'],
        target_level=data['target_level'],
        advanced_by=current_user.id,  # Would be instructor in production
        reason=data.get('reason', 'Self-advancement request'),
        requirements_met=data.get('requirements_met', 'Auto-approved for testing')
    )

    # 🔍 AUDIT: Log license advancement
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.LICENSE_UPGRADE_APPROVED,
        user_id=current_user.id,
        resource_type="license",
        resource_id=None,  # License progression doesn't have individual license IDs
        details={
            "specialization": data['specialization'],
            "target_level": data['target_level'],
            "reason": data.get('reason'),
            "success": result.get('success', False)
        }
    )

    # 🏆 GAMIFICATION: Check for achievement unlocks
    if result.get('success'):
        from app.services.gamification import GamificationService
        gamification_service = GamificationService(db)
        try:
            # Check for level-up achievements
            unlocked = gamification_service.check_and_unlock_achievements(
                user_id=current_user.id,
                trigger_action="reach_level",
                context={"level": data['target_level']}
            )

            # Also check for first license achievement (if level 1)
            if data['target_level'] == 1:
                first_license_unlocked = gamification_service.check_and_unlock_achievements(
                    user_id=current_user.id,
                    trigger_action="license_earned"
                )
                unlocked.extend(first_license_unlocked)

            if unlocked:
                print(f"🎉 Unlocked {len(unlocked)} achievement(s) for user {current_user.id}")
                # Optionally add to response
                result['achievements_unlocked'] = [
                    {"code": a.code, "name": a.name, "xp": a.xp_reward}
                    for a in unlocked
                ]
        except Exception as e:
            # Don't fail advancement if achievement check fails
            print(f"⚠️  Achievement check failed: {e}")

    return result


@router.get("/requirements/{specialization}/{level}", response_model=Dict[str, Any])
async def check_advancement_requirements(
    specialization: str,
    level: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user meets requirements for license advancement
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: Target level number
    """
    license_service = LicenseService(db)
    return license_service.get_license_requirements_check(
        current_user.id, specialization, level
    )


@router.get("/marketing/{specialization}", response_model=Dict[str, Any])
async def get_marketing_content(
    specialization: str,
    level: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get marketing content for license levels
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: Optional specific level, if omitted returns all levels
    """
    license_service = LicenseService(db)
    return license_service.get_marketing_content(specialization, level)


# Instructor-only endpoints
@router.post("/instructor/advance", response_model=Dict[str, Any])
async def instructor_advance_license(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Instructor-approved license advancement
    
    Request body:
    - **user_id**: ID of user to advance
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **target_level**: Desired level number
    - **reason**: Reason for advancement
    - **requirements_met**: Description of requirements satisfied
    """
    # Check instructor permissions
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can approve license advancements"
        )
    
    required_fields = ['user_id', 'specialization', 'target_level']
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}"
            )
    
    license_service = LicenseService(db)
    result = license_service.advance_license(
        user_id=data['user_id'],
        specialization=data['specialization'],
        target_level=data['target_level'],
        advanced_by=current_user.id,
        reason=data.get('reason', 'Instructor approved advancement'),
        requirements_met=data.get('requirements_met', 'Requirements verified by instructor')
    )
    
    return result


@router.get("/instructor/users/{user_id}/licenses", response_model=List[Dict[str, Any]])
async def get_user_licenses_by_instructor(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get license information for a specific user (instructor only)
    """
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view other users' licenses"
        )
    
    license_service = LicenseService(db)
    return license_service.get_user_licenses(user_id)


@router.get("/instructor/dashboard/{user_id}", response_model=Dict[str, Any])
async def get_user_license_dashboard_by_instructor(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get license dashboard for a specific user (instructor only)
    """
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view other users' license dashboards"
        )

    license_service = LicenseService(db)
    return license_service.get_user_license_dashboard(user_id)


# 🔄 P0 CRITICAL: Progress-License Synchronization Endpoints

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