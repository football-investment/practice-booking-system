"""
Track Management API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....dependencies import get_current_user
from ....database import get_db
from ....models import User, Track, UserTrackProgress
from ....services.track_service import TrackService, TrackEnrollmentError
from ....schemas.track import (
    TrackResponse, TrackEnrollmentRequest, TrackEnrollmentResponse,
    UserTrackProgressResponse, TrackAnalyticsResponse
)

router = APIRouter()


@router.get("/", response_model=List[TrackResponse])
def get_available_tracks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all available tracks for enrollment"""
    track_service = TrackService(db)
    tracks = track_service.get_available_tracks(str(current_user.id))
    return tracks


@router.get("/my", response_model=List[UserTrackProgressResponse])
def get_my_tracks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's track enrollments (supports parallel tracks)"""
    track_service = TrackService(db)
    user_tracks = track_service.get_user_parallel_tracks(str(current_user.id))
    return user_tracks


@router.post("/enroll", response_model=TrackEnrollmentResponse)
def enroll_in_track(
    enrollment_request: TrackEnrollmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enroll user in a track with semester restrictions"""
    track_service = TrackService(db)
    
    try:
        track_progress = track_service.enroll_user_in_track(
            user_id=str(current_user.id),
            track_id=enrollment_request.track_id,
            current_semester_id=enrollment_request.semester_id
        )
        
        return TrackEnrollmentResponse(
            success=True,
            message="Successfully enrolled in track",
            track_progress_id=str(track_progress.id)
        )
    
    except TrackEnrollmentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{track_progress_id}/start")
def start_track(
    track_progress_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start an enrolled track"""
    track_service = TrackService(db)
    
    # Verify ownership
    track_progress = db.query(UserTrackProgress)\
        .filter(UserTrackProgress.id == track_progress_id)\
        .filter(UserTrackProgress.user_id == current_user.id)\
        .first()
    
    if not track_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track progress not found"
        )
    
    try:
        updated_progress = track_service.start_track(track_progress_id)
        return {"message": "Track started successfully", "status": updated_progress.status.value}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{track_progress_id}/modules/{module_id}/start")
def start_module(
    track_progress_id: str,
    module_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a module within a track"""
    track_service = TrackService(db)
    
    # Verify ownership
    track_progress = db.query(UserTrackProgress)\
        .filter(UserTrackProgress.id == track_progress_id)\
        .filter(UserTrackProgress.user_id == current_user.id)\
        .first()
    
    if not track_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track progress not found"
        )
    
    module_progress = track_service.start_module(track_progress_id, module_id)
    return {
        "message": "Module started successfully", 
        "module_progress_id": str(module_progress.id),
        "status": module_progress.status.value
    }


@router.post("/{track_progress_id}/modules/{module_id}/complete")
def complete_module(
    track_progress_id: str,
    module_id: str,
    grade: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete a module within a track"""
    track_service = TrackService(db)
    
    # Verify ownership
    track_progress = db.query(UserTrackProgress)\
        .filter(UserTrackProgress.id == track_progress_id)\
        .filter(UserTrackProgress.user_id == current_user.id)\
        .first()
    
    if not track_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track progress not found"
        )
    
    try:
        module_progress = track_service.complete_module(track_progress_id, module_id, grade)
        return {
            "message": "Module completed successfully",
            "module_progress_id": str(module_progress.id),
            "grade": module_progress.grade,
            "status": module_progress.status.value
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{track_id}/analytics", response_model=TrackAnalyticsResponse)
def get_track_analytics(
    track_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a track (instructor/admin only)"""
    # TODO: Add role-based access control
    if current_user.role.value not in ["instructor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    track_service = TrackService(db)
    analytics = track_service.get_track_analytics(track_id)
    return analytics


@router.get("/{track_progress_id}/progress")
def get_track_progress_detail(
    track_progress_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed progress for a specific track enrollment"""
    # Verify ownership
    track_progress = db.query(UserTrackProgress)\
        .filter(UserTrackProgress.id == track_progress_id)\
        .filter(UserTrackProgress.user_id == current_user.id)\
        .first()
    
    if not track_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track progress not found"
        )
    
    # Get module progresses
    module_progresses = []
    for module_progress in track_progress.module_progresses:
        module_data = {
            "module_progress_id": str(module_progress.id),
            "module": {
                "id": str(module_progress.module.id),
                "name": module_progress.module.name,
                "description": module_progress.module.description,
                "estimated_hours": module_progress.module.estimated_hours,
                "is_mandatory": module_progress.module.is_mandatory,
                "order_in_track": module_progress.module.order_in_track
            },
            "status": module_progress.status.value,
            "grade": module_progress.grade,
            "attempts": module_progress.attempts,
            "time_spent_minutes": module_progress.time_spent_minutes,
            "started_at": module_progress.started_at,
            "completed_at": module_progress.completed_at
        }
        module_progresses.append(module_data)
    
    return {
        "track_progress_id": str(track_progress.id),
        "track": {
            "id": str(track_progress.track.id),
            "name": track_progress.track.name,
            "code": track_progress.track.code,
            "description": track_progress.track.description
        },
        "status": track_progress.status.value,
        "completion_percentage": track_progress.completion_percentage,
        "enrollment_date": track_progress.enrollment_date,
        "started_at": track_progress.started_at,
        "completed_at": track_progress.completed_at,
        "certificate_id": str(track_progress.certificate_id) if track_progress.certificate_id else None,
        "module_progresses": module_progresses
    }