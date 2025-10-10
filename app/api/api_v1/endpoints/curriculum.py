from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from app.database import get_db
from ....dependencies import get_current_user
from app.models.user import User, UserRole
from app.services.competency_service import CompetencyService
from app.services.adaptive_learning_service import AdaptiveLearningService
import json

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
            except:
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
            except:
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

@router.get("/exercise/{exercise_id}")
def get_exercise_details(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed exercise information"""

    result = db.execute(text("""
        SELECT id, title, description, exercise_type, instructions, requirements,
               max_points, passing_score, xp_reward, order_number,
               estimated_time_minutes, is_mandatory, allow_resubmission, deadline_days,
               lesson_id
        FROM exercises
        WHERE id = :exercise_id
    """), {"exercise_id": exercise_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Exercise not found")

    requirements = None
    if result[5]:
        try:
            requirements = json.loads(result[5]) if isinstance(result[5], str) else result[5]
        except:
            requirements = result[5]

    return {
        "id": result[0],
        "title": result[1],
        "description": result[2],
        "exercise_type": result[3],
        "instructions": result[4],
        "requirements": requirements,
        "max_points": result[6],
        "passing_score": float(result[7]) if result[7] else 70.0,
        "xp_reward": result[8],
        "order_number": result[9],
        "estimated_time_minutes": result[10],
        "is_mandatory": result[11],
        "allow_resubmission": result[12],
        "deadline_days": result[13],
        "lesson_id": result[14]
    }


@router.get("/exercise/{exercise_id}/submission")
def get_exercise_submission(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's submission for an exercise"""

    result = db.execute(text("""
        SELECT id, submission_type, submission_url, submission_text, submission_data,
               status, score, passed, xp_awarded, instructor_feedback,
               submitted_at, reviewed_by, reviewed_at, created_at, updated_at
        FROM user_exercise_submissions
        WHERE user_id = :user_id AND exercise_id = :exercise_id
        ORDER BY created_at DESC
        LIMIT 1
    """), {"user_id": current_user.id, "exercise_id": exercise_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="No submission found")

    submission_data = None
    if result[4]:
        try:
            submission_data = json.loads(result[4]) if isinstance(result[4], str) else result[4]
        except:
            submission_data = result[4]

    return {
        "id": result[0],
        "submission_type": result[1],
        "submission_url": result[2],
        "submission_text": result[3],
        "submission_data": submission_data,
        "status": result[5],
        "score": float(result[6]) if result[6] else None,
        "passed": result[7],
        "xp_awarded": result[8] or 0,
        "instructor_feedback": result[9],
        "submitted_at": result[10].isoformat() if result[10] else None,
        "reviewed_by": result[11],
        "reviewed_at": result[12].isoformat() if result[12] else None,
        "created_at": result[13].isoformat() if result[13] else None,
        "updated_at": result[14].isoformat() if result[14] else None
    }


@router.post("/exercise/{exercise_id}/submit")
def submit_exercise(
    exercise_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new exercise submission"""

    # Validate exercise exists
    exercise = db.execute(text("""
        SELECT id FROM exercises WHERE id = :exercise_id
    """), {"exercise_id": exercise_id}).fetchone()

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Create submission
    db.execute(text("""
        INSERT INTO user_exercise_submissions
            (user_id, exercise_id, submission_type, submission_url, submission_text,
             submission_data, status, submitted_at)
        VALUES
            (:user_id, :exercise_id, :submission_type, :submission_url, :submission_text,
             :submission_data, :status,
             CASE WHEN :status = 'SUBMITTED' THEN NOW() ELSE NULL END)
    """), {
        "user_id": current_user.id,
        "exercise_id": exercise_id,
        "submission_type": payload.get("submission_type", "FILE"),
        "submission_url": payload.get("submission_url"),
        "submission_text": payload.get("submission_text"),
        "submission_data": json.dumps(payload.get("submission_data")) if payload.get("submission_data") else None,
        "status": payload.get("status", "DRAFT")
    })

    db.commit()

    return {"status": "success", "message": "Submission created"}


@router.put("/exercise/submission/{submission_id}")
def update_exercise_submission(
    submission_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update existing exercise submission"""

    # Verify ownership
    existing = db.execute(text("""
        SELECT user_id FROM user_exercise_submissions WHERE id = :id
    """), {"id": submission_id}).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Submission not found")

    if existing[0] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update submission
    db.execute(text("""
        UPDATE user_exercise_submissions
        SET submission_type = :submission_type,
            submission_url = :submission_url,
            submission_text = :submission_text,
            submission_data = :submission_data,
            status = :status,
            submitted_at = CASE WHEN :status = 'SUBMITTED' AND submitted_at IS NULL THEN NOW() ELSE submitted_at END,
            updated_at = NOW()
        WHERE id = :id
    """), {
        "id": submission_id,
        "submission_type": payload.get("submission_type", "FILE"),
        "submission_url": payload.get("submission_url"),
        "submission_text": payload.get("submission_text"),
        "submission_data": json.dumps(payload.get("submission_data")) if payload.get("submission_data") else None,
        "status": payload.get("status", "DRAFT")
    })

    db.commit()

    return {"status": "success", "message": "Submission updated"}


@router.post("/exercise/submission/{submission_id}/upload")
async def upload_exercise_file(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    File upload endpoint for exercise submissions.

    NOTE: This is a placeholder. In production, integrate with:
    - AWS S3
    - Google Cloud Storage
    - Azure Blob Storage
    - Or local file storage
    """

    # For now, return a mock URL
    # In production, implement actual file upload logic here

    import time
    mock_file_url = f"https://storage.lfa-academy.com/exercises/{current_user.id}/{submission_id}/{int(time.time())}.mp4"

    return {
        "status": "success",
        "file_url": mock_file_url,
        "message": "File upload placeholder - implement S3/storage integration"
    }


# =====================================================
# INSTRUCTOR: EXERCISE GRADING ENDPOINT
# =====================================================

@router.post("/exercise/submission/{submission_id}/grade")
def grade_exercise_submission(
    submission_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Grade an exercise submission (Instructor only)

    Payload:
    {
        "score": 85,  // 0-100
        "feedback": "Good work!",
        "status": "APPROVED"  // APPROVED, NEEDS_REVISION, REJECTED
    }
    """
    # Only instructors can grade
    if current_user.role not in [UserRole.INSTRUCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can grade submissions"
        )

    # Get submission
    submission = db.execute(text("""
        SELECT ues.*, e.max_points, e.passing_score, e.xp_reward, e.lesson_id,
               ct.specialization_id, u.id as student_id
        FROM user_exercise_submissions ues
        JOIN exercises e ON e.id = ues.exercise_id
        JOIN lessons l ON l.id = e.lesson_id
        JOIN curriculum_tracks ct ON ct.id = l.curriculum_track_id
        JOIN users u ON u.id = ues.user_id
        WHERE ues.id = :submission_id
    """), {"submission_id": submission_id}).fetchone()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Extract payload
    score = payload.get("score")
    feedback = payload.get("feedback", "")
    grade_status = payload.get("status", "APPROVED")

    if score is None or not (0 <= score <= 100):
        raise HTTPException(status_code=400, detail="Score must be between 0-100")

    # Calculate if passed
    passing_score = float(submission.passing_score) if submission.passing_score else 70.0
    passed = score >= passing_score

    # Calculate XP earned
    xp_awarded = 0
    if passed and grade_status == "APPROVED":
        xp_awarded = submission.xp_reward or 0

    # Update submission
    db.execute(text("""
        UPDATE user_exercise_submissions
        SET
            status = :status,
            score = :score,
            passed = :passed,
            xp_awarded = :xp,
            instructor_feedback = :feedback,
            reviewed_by = :reviewer_id,
            reviewed_at = NOW(),
            updated_at = NOW()
        WHERE id = :submission_id
    """), {
        "submission_id": submission_id,
        "status": grade_status,
        "score": score,
        "passed": passed,
        "xp": xp_awarded,
        "feedback": feedback,
        "reviewer_id": current_user.id
    })

    # Award XP to student if passed
    if xp_awarded > 0:
        db.execute(text("""
            UPDATE users
            SET total_xp = total_xp + :xp
            WHERE id = :user_id
        """), {"xp": xp_awarded, "user_id": submission.student_id})

    db.commit()

    # ==========================================
    # 🆕 HOOK 2: AUTOMATIC COMPETENCY ASSESSMENT
    # ==========================================
    # Use SEPARATE session to avoid transaction conflicts
    from ....database import SessionLocal
    hook_db = None

    try:
        # Create new session for hooks
        hook_db = SessionLocal()

        # Initialize services with separate session
        comp_service = CompetencyService(hook_db)
        adapt_service = AdaptiveLearningService(hook_db)

        # Assess competency from exercise (automatic based on exercise type/lesson)
        comp_service.assess_from_exercise(
            user_id=submission.student_id,
            exercise_submission_id=submission_id,
            score=float(score)
        )

        # Update adaptive learning profile
        adapt_service.update_profile_metrics(submission.student_id)

        # Commit hook transaction
        hook_db.commit()

    except Exception as e:
        # Log error but don't fail grading
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in exercise grading hooks for submission {submission_id}: {e}")
        if hook_db:
            hook_db.rollback()

    finally:
        # Always close the hook session
        if hook_db:
            hook_db.close()

    return {
        "status": "success",
        "message": "Exercise graded successfully",
        "submission_id": submission_id,
        "grade_status": grade_status,
        "score": score,
        "passed": passed,
        "xp_awarded": xp_awarded
    }
