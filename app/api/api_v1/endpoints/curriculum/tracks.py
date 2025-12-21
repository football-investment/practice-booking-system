"""
Curriculum track and progress endpoints
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User

router = APIRouter()

@router.get("/track/{specialization_id}")
def get_curriculum_track(
    specialization_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get curriculum track for a specialization"""

    result = db.execute(text("""
        SELECT id, specialization_id, name, description, total_lessons, total_hours
        FROM curriculum_tracks
        WHERE specialization_id = :spec_id
    """), {"spec_id": specialization_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Curriculum track not found")

    return {
        "id": result[0],
        "specialization_id": result[1],
        "name": result[2],
        "description": result[3],
        "total_lessons": result[4],
        "total_hours": result[5]
    }


@router.get("/track/{specialization_id}/lessons")
def get_curriculum_lessons(
    specialization_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all lessons in a curriculum track"""

    results = db.execute(text("""
        SELECT l.id, l.title, l.description, l.order_number, l.estimated_hours,
               l.xp_reward, l.level_id, l.is_mandatory
        FROM lessons l
        JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
        WHERE ct.specialization_id = :spec_id
        ORDER BY l.order_number
    """), {"spec_id": specialization_id}).fetchall()

    lessons = []
    for r in results:
        lessons.append({
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "order_number": r[3],
            "estimated_hours": float(r[4]) if r[4] else 0,
            "xp_reward": r[5],
            "level_id": r[6],
            "is_mandatory": r[7]
        })

    return lessons


@router.get("/progress/{specialization_id}")
def get_user_curriculum_progress(
    specialization_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's progress across all lessons in a curriculum"""

    results = db.execute(text("""
        SELECT ulp.lesson_id, ulp.status, ulp.completion_percentage,
               ulp.started_at, ulp.completed_at, ulp.xp_earned
        FROM user_lesson_progress ulp
        JOIN lessons l ON ulp.lesson_id = l.id
        JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
        WHERE ct.specialization_id = :spec_id AND ulp.user_id = :user_id
    """), {"spec_id": specialization_id, "user_id": current_user.id}).fetchall()

    progress = {}
    for r in results:
        progress[r[0]] = {
            "status": r[1],
            "completion_percentage": r[2] or 0,
            "started_at": r[3].isoformat() if r[3] else None,
            "completed_at": r[4].isoformat() if r[4] else None,
            "xp_earned": r[5] or 0
        }

    return progress


