"""
Curriculum lesson endpoints
"""
import json
import logging
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/lesson/{lesson_id}")
def get_lesson_details(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed lesson information"""

    result = db.execute(text("""
        SELECT l.id, l.title, l.description, l.order_number, l.estimated_hours,
               l.xp_reward, l.level_id, l.is_mandatory, ct.specialization_id
        FROM lessons l
        JOIN curriculum_tracks ct ON l.curriculum_track_id = ct.id
        WHERE l.id = :lesson_id
    """), {"lesson_id": lesson_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return {
        "id": result[0],
        "title": result[1],
        "description": result[2],
        "order_number": result[3],
        "estimated_hours": float(result[4]) if result[4] else 0,
        "xp_reward": result[5],
        "level_id": result[6],
        "is_mandatory": result[7],
        "specialization_id": result[8]
    }


@router.get("/lesson/{lesson_id}/modules")
def get_lesson_modules(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all modules in a lesson"""

    results = db.execute(text("""
        SELECT id, title, module_type, content, content_data,
               duration_minutes, xp_reward, order_number, is_mandatory
        FROM lesson_modules
        WHERE lesson_id = :lesson_id
        ORDER BY order_number
    """), {"lesson_id": lesson_id}).fetchall()

    modules = []
    for r in results:
        content_data = None
        if r[4]:  # content_data is JSONB
            try:
                content_data = json.loads(r[4]) if isinstance(r[4], str) else r[4]
            except Exception as e:
                logger.error(f"Error parsing module content_data JSON: {e}")
                content_data = r[4]

        modules.append({
            "id": r[0],
            "title": r[1],
            "module_type": r[2],
            "content": r[3],
            "content_data": content_data,
            "duration_minutes": r[5],
            "xp_reward": r[6],
            "order_number": r[7],
            "is_mandatory": r[8]
        })

    return modules


@router.get("/lesson/{lesson_id}/quizzes")
def get_lesson_quizzes(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all quizzes linked to a lesson"""

    results = db.execute(text("""
        SELECT q.id, q.title, q.description, q.category, q.difficulty,
               q.time_limit_minutes, q.xp_reward, q.passing_score, q.is_active,
               lq.is_prerequisite, lq.order_number
        FROM quizzes q
        JOIN lesson_quizzes lq ON q.id = lq.quiz_id
        WHERE lq.lesson_id = :lesson_id
        ORDER BY lq.order_number
    """), {"lesson_id": lesson_id}).fetchall()

    quizzes = []
    for r in results:
        quizzes.append({
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "category": r[3],
            "difficulty": r[4],
            "time_limit_minutes": r[5],
            "xp_reward": r[6],
            "passing_score": float(r[7]) if r[7] else 70.0,
            "is_active": r[8],
            "is_prerequisite": r[9],
            "order_number": r[10]
        })

    return quizzes


@router.get("/lesson/{lesson_id}/exercises")
def get_lesson_exercises(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all exercises in a lesson"""

    results = db.execute(text("""
        SELECT id, title, description, exercise_type, instructions, requirements,
               max_points, passing_score, xp_reward, order_number,
               estimated_time_minutes, is_mandatory, allow_resubmission, deadline_days
        FROM exercises
        WHERE lesson_id = :lesson_id
        ORDER BY order_number
    """), {"lesson_id": lesson_id}).fetchall()

    exercises = []
    for r in results:
        requirements = None
        if r[5]:  # requirements is JSONB
            try:
                requirements = json.loads(r[5]) if isinstance(r[5], str) else r[5]
            except Exception as e:
                logger.error(f"Error parsing exercise requirements JSON: {e}")
                requirements = r[5]

        exercises.append({
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "exercise_type": r[3],
            "instructions": r[4],
            "requirements": requirements,
            "max_points": r[6],
            "passing_score": float(r[7]) if r[7] else 70.0,
            "xp_reward": r[8],
            "order_number": r[9],
            "estimated_time_minutes": r[10],
            "is_mandatory": r[11],
            "allow_resubmission": r[12],
            "deadline_days": r[13]
        })

    return exercises


@router.get("/lesson/{lesson_id}/progress")
def get_lesson_progress(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's detailed progress within a lesson"""

    # Get overall lesson progress
    lesson_progress = db.execute(text("""
        SELECT status, completion_percentage, started_at, completed_at, xp_earned
        FROM user_lesson_progress
        WHERE user_id = :user_id AND lesson_id = :lesson_id
    """), {"user_id": current_user.id, "lesson_id": lesson_id}).fetchone()

    # Get module progress
    module_results = db.execute(text("""
        SELECT module_id, status, time_spent_minutes, completed_at
        FROM user_module_progress
        WHERE user_id = :user_id AND module_id IN (
            SELECT id FROM lesson_modules WHERE lesson_id = :lesson_id
        )
    """), {"user_id": current_user.id, "lesson_id": lesson_id}).fetchall()

    modules = {}
    for mr in module_results:
        modules[mr[0]] = {
            "status": mr[1],
            "time_spent_minutes": mr[2] or 0,
            "completed_at": mr[3].isoformat() if mr[3] else None
        }

    # Get exercise submissions
    exercise_results = db.execute(text("""
        SELECT ues.exercise_id, ues.status, ues.score, ues.passed,
               ues.xp_awarded, ues.submitted_at, ues.instructor_feedback
        FROM user_exercise_submissions ues
        WHERE ues.user_id = :user_id AND ues.exercise_id IN (
            SELECT id FROM exercises WHERE lesson_id = :lesson_id
        )
    """), {"user_id": current_user.id, "lesson_id": lesson_id}).fetchall()

    exercises = {}
    for er in exercise_results:
        exercises[er[0]] = {
            "status": er[1],
            "score": float(er[2]) if er[2] else None,
            "passed": er[3],
            "xp_awarded": er[4] or 0,
            "submitted_at": er[5].isoformat() if er[5] else None,
            "instructor_feedback": er[6]
        }

    return {
        "status": lesson_progress[0] if lesson_progress else "LOCKED",
        "completion_percentage": lesson_progress[1] if lesson_progress else 0,
        "started_at": lesson_progress[2].isoformat() if lesson_progress and lesson_progress[2] else None,
        "completed_at": lesson_progress[3].isoformat() if lesson_progress and lesson_progress[3] else None,
        "xp_earned": lesson_progress[4] if lesson_progress else 0,
        "modules": modules,
        "exercises": exercises
    }


