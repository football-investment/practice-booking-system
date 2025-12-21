"""
Curriculum module endpoints
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User

router = APIRouter()

@router.post("/module/{module_id}/view")
def mark_module_viewed(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a module as viewed/in progress"""

    # Check if progress record exists
    existing = db.execute(text("""
        SELECT id, status FROM user_module_progress
        WHERE user_id = :user_id AND module_id = :module_id
    """), {"user_id": current_user.id, "module_id": module_id}).fetchone()

    if existing:
        # Update existing record
        db.execute(text("""
            UPDATE user_module_progress
            SET status = 'IN_PROGRESS', last_accessed_at = NOW()
            WHERE id = :id
        """), {"id": existing[0]})
    else:
        # Create new record
        db.execute(text("""
            INSERT INTO user_module_progress (user_id, module_id, status, last_accessed_at)
            VALUES (:user_id, :module_id, 'IN_PROGRESS', NOW())
        """), {"user_id": current_user.id, "module_id": module_id})

    # Update lesson progress
    _update_lesson_progress(module_id, current_user.id, db)

    db.commit()

    return {"status": "success", "message": "Module marked as viewed"}


@router.post("/module/{module_id}/complete")
def mark_module_complete(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a module as completed"""

    # Get module XP reward
    module = db.execute(text("""
        SELECT xp_reward FROM lesson_modules WHERE id = :module_id
    """), {"module_id": module_id}).fetchone()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    xp_reward = module[0] or 0

    # Check if progress record exists
    existing = db.execute(text("""
        SELECT id FROM user_module_progress
        WHERE user_id = :user_id AND module_id = :module_id
    """), {"user_id": current_user.id, "module_id": module_id}).fetchone()

    if existing:
        # Update to completed
        db.execute(text("""
            UPDATE user_module_progress
            SET status = 'COMPLETED', completed_at = NOW()
            WHERE id = :id
        """), {"id": existing[0]})
    else:
        # Create completed record
        db.execute(text("""
            INSERT INTO user_module_progress (user_id, module_id, status, completed_at)
            VALUES (:user_id, :module_id, 'COMPLETED', NOW())
        """), {"user_id": current_user.id, "module_id": module_id})

    # Award XP to user
    if xp_reward > 0:
        db.execute(text("""
            UPDATE users SET total_xp = total_xp + :xp WHERE id = :user_id
        """), {"xp": xp_reward, "user_id": current_user.id})

    # Update lesson progress
    _update_lesson_progress(module_id, current_user.id, db)

    db.commit()

    return {
        "status": "success",
        "message": "Module completed",
        "xp_awarded": xp_reward
    }


def _update_lesson_progress(module_id: int, user_id: int, db: Session):
    """Helper function to recalculate lesson progress based on module completion"""

    # Get lesson_id for this module
    lesson = db.execute(text("""
        SELECT lesson_id FROM lesson_modules WHERE id = :module_id
    """), {"module_id": module_id}).fetchone()

    if not lesson:
        return

    lesson_id = lesson[0]

    # Count total modules and completed modules
    stats = db.execute(text("""
        SELECT
            COUNT(lm.id) as total_modules,
            COUNT(CASE WHEN ump.status = 'COMPLETED' THEN 1 END) as completed_modules
        FROM lesson_modules lm
        LEFT JOIN user_module_progress ump
            ON lm.id = ump.module_id AND ump.user_id = :user_id
        WHERE lm.lesson_id = :lesson_id
    """), {"user_id": user_id, "lesson_id": lesson_id}).fetchone()

    total = stats[0] or 1
    completed = stats[1] or 0
    completion_pct = int((completed / total) * 100)

    # Determine status
    if completed == 0:
        status = 'UNLOCKED'
    elif completed == total:
        status = 'COMPLETED'
    else:
        status = 'IN_PROGRESS'

    # Update or insert lesson progress
    existing = db.execute(text("""
        SELECT id FROM user_lesson_progress
        WHERE user_id = :user_id AND lesson_id = :lesson_id
    """), {"user_id": user_id, "lesson_id": lesson_id}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE user_lesson_progress
            SET status = :status,
                completion_percentage = :pct,
                completed_at = CASE WHEN :status = 'COMPLETED' THEN NOW() ELSE completed_at END
            WHERE id = :id
        """), {"status": status, "pct": completion_pct, "id": existing[0]})
    else:
        db.execute(text("""
            INSERT INTO user_lesson_progress
                (user_id, lesson_id, status, completion_percentage, started_at)
            VALUES (:user_id, :lesson_id, :status, :pct, NOW())
        """), {"user_id": user_id, "lesson_id": lesson_id, "status": status, "pct": completion_pct})


# =====================================================
# EXERCISE SUBMISSION ENDPOINTS
# =====================================================

