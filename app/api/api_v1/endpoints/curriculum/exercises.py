"""
Curriculum exercise endpoints
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_or_instructor_user
from .....models.user import User

router = APIRouter()

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
    result = db.execute(text("""
        INSERT INTO user_exercise_submissions
            (user_id, exercise_id, submission_type, submission_url, submission_text,
             submission_data, status, submitted_at)
        VALUES
            (:user_id, :exercise_id, :submission_type, :submission_url, :submission_text,
             :submission_data, :status,
             CASE WHEN :status = 'SUBMITTED' THEN NOW() ELSE NULL END)
        RETURNING id
    """), {
        "user_id": current_user.id,
        "exercise_id": exercise_id,
        "submission_type": payload.get("submission_type", "FILE"),
        "submission_url": payload.get("submission_url"),
        "submission_text": payload.get("submission_text"),
        "submission_data": json.dumps(payload.get("submission_data")) if payload.get("submission_data") else None,
        "status": payload.get("status", "SUBMITTED")  # Changed default to SUBMITTED
    })

    submission_id = result.fetchone().id
    db.commit()

    return {
        "status": "success",
        "message": "Submission created",
        "submission_id": submission_id
    }


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
    # TODO: Implement XP tracking system
    # if xp_awarded > 0:
    #     db.execute(text("""
    #         UPDATE users
    #         SET total_xp = total_xp + :xp
    #         WHERE id = :user_id
    #     """), {"xp": xp_awarded, "user_id": submission.student_id})

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
