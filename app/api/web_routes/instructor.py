"""
Instructor session control routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel

from zoneinfo import ZoneInfo

from ...database import get_db
from ...dependencies import get_current_user_web
from ...models.user import User, UserRole
from ...models.session import Session as SessionModel, SessionType
from ...models.attendance import Attendance, AttendanceStatus
from ...models.performance_review import InstructorSessionReview, StudentPerformanceReview
from ...models.instructor_specialization import InstructorSpecialization
from .helpers import update_specialization_xp as _update_specialization_xp

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


# Pydantic model for toggle request
class ToggleSpecializationRequest(BaseModel):
    specialization: str
    is_active: bool


@router.post("/instructor/specialization/toggle")
async def toggle_instructor_specialization(
    request: Request,
    toggle_data: ToggleSpecializationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """Toggle instructor specialization active/inactive"""
    if user.role != UserRole.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="Only instructors can manage teaching specializations")

    # Find the specialization record
    spec_record = db.query(InstructorSpecialization).filter(
        InstructorSpecialization.user_id == user.id,
        InstructorSpecialization.specialization == toggle_data.specialization
    ).first()

    if not spec_record:
        raise HTTPException(status_code=404, detail="Specialization not found")

    # Update is_active status
    spec_record.is_active = toggle_data.is_active
    db.commit()

    return JSONResponse(content={"success": True, "specialization": toggle_data.specialization, "is_active": toggle_data.is_active})

# ==========================================
# SESSION TIMER/TRACKER ENDPOINTS (On-Site & Hybrid Sessions Only)
# Instructor can start/stop sessions to track actual duration
# ==========================================

@router.post("/sessions/{session_id}/start")
async def start_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor starts the session - records actual start time

    Requirements:
    - User must be instructor
    - Session must be On-Site or Hybrid type
    - Instructor must own this session
    - Session must not be already started
    """
    if user.role != UserRole.INSTRUCTOR:
        return RedirectResponse(url=f"/sessions/{session_id}?error=unauthorized", status_code=303)

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return RedirectResponse(url="/sessions?error=session_not_found", status_code=303)

    # Verify session is On-Site or Hybrid
    if session.session_type not in [SessionType.on_site, SessionType.hybrid]:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=timer_only_onsite_hybrid",
            status_code=303
        )

    # Verify instructor owns this session
    if session.instructor_id != user.id:
        return RedirectResponse(url=f"/sessions/{session_id}?error=not_your_session", status_code=303)

    # Verify session not already started
    if session.actual_start_time is not None:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=session_already_started",
            status_code=303
        )

    # Record actual start time (Budapest timezone)
    budapest_tz = ZoneInfo("Europe/Budapest")
    session.actual_start_time = datetime.now(budapest_tz)
    session.session_status = "in_progress"
    session.updated_at = datetime.now(budapest_tz)

    db.commit()

    print(f"✅ Session {session_id} started by instructor {user.id} at {session.actual_start_time}")

    return RedirectResponse(
        url=f"/sessions/{session_id}?success=session_started",
        status_code=303
    )


@router.post("/sessions/{session_id}/stop")
async def stop_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor stops the session - records actual end time

    Requirements:
    - User must be instructor
    - Session must be On-Site or Hybrid type
    - Instructor must own this session
    - Session must be started first
    - Session must not be already stopped
    """
    if user.role != UserRole.INSTRUCTOR:
        return RedirectResponse(url=f"/sessions/{session_id}?error=unauthorized", status_code=303)

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return RedirectResponse(url="/sessions?error=session_not_found", status_code=303)

    # Verify session is On-Site or Hybrid
    if session.session_type not in [SessionType.on_site, SessionType.hybrid]:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=timer_only_onsite_hybrid",
            status_code=303
        )

    # Verify instructor owns this session
    if session.instructor_id != user.id:
        return RedirectResponse(url=f"/sessions/{session_id}?error=not_your_session", status_code=303)

    # Verify session was started
    if session.actual_start_time is None:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=session_not_started",
            status_code=303
        )

    # Verify session not already stopped
    if session.actual_end_time is not None:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=session_already_stopped",
            status_code=303
        )

    # Record actual end time (Budapest timezone)
    budapest_tz = ZoneInfo("Europe/Budapest")
    session.actual_end_time = datetime.now(budapest_tz)
    session.session_status = "completed"
    session.updated_at = datetime.now(budapest_tz)

    db.commit()

    # Calculate actual duration
    duration = session.actual_end_time - session.actual_start_time
    print(f"✅ Session {session_id} stopped by instructor {user.id} at {session.actual_end_time}")
    print(f"   Actual duration: {duration}")

    return RedirectResponse(
        url=f"/sessions/{session_id}?success=session_stopped",
        status_code=303
    )


# ==========================================
# PERFORMANCE REVIEW ENDPOINTS (On-Site Sessions Only)
# Two-way evaluation system for On-Site training sessions
# ==========================================

@router.post("/sessions/{session_id}/evaluate-student/{student_id}")
async def evaluate_student_performance(
    request: Request,
    session_id: int,
    student_id: int,
    punctuality: int = Form(...),
    engagement: int = Form(...),
    focus: int = Form(...),
    collaboration: int = Form(...),
    attitude: int = Form(...),
    comments: str = Form(None),
    update_reason: str = Form(None),  # Required when updating existing review
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor evaluates student performance (On-Site sessions only)

    Requirements:
    - User must be instructor
    - Session must be On-Site type
    - Student must have attended the session
    """
    if user.role != UserRole.INSTRUCTOR:
        return RedirectResponse(url=f"/sessions/{session_id}?error=unauthorized", status_code=303)
    
    # Get session and verify it's On-Site
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return RedirectResponse(url="/sessions?error=session_not_found", status_code=303)

    # Verify instructor owns this session
    if session.instructor_id != user.id:
        return RedirectResponse(url=f"/sessions/{session_id}?error=not_your_session", status_code=303)
    
    # CRITICAL: Verify session has ended before allowing evaluation
    # Use actual_end_time if available (instructor stopped session), otherwise use scheduled date_end
    if session.actual_end_time is None:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=session_not_stopped",
            status_code=303
        )

    # Verify student attended
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == student_id
    ).first()

    if not attendance or attendance.status == AttendanceStatus.absent:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=student_not_attended",
            status_code=303
        )

    # Check if review already exists
    existing_review = db.query(StudentPerformanceReview).filter(
        StudentPerformanceReview.session_id == session_id,
        StudentPerformanceReview.student_id == student_id
    ).first()

    # NOTE: Instructor CAN modify performance review even after session ends (with update_reason)
    # This is different from attendance which CANNOT be modified after session ends

    # Validate scores (1-5)
    scores = [punctuality, engagement, focus, collaboration, attitude]
    if any(score < 1 or score > 5 for score in scores):
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=invalid_scores",
            status_code=303
        )

    if existing_review:
        # Update existing review - require update_reason
        if not update_reason or len(update_reason.strip()) == 0:
            return RedirectResponse(
                url=f"/sessions/{session_id}?error=update_reason_required",
                status_code=303
            )

        # Update existing review
        existing_review.punctuality = punctuality
        existing_review.engagement = engagement
        existing_review.focus = focus
        existing_review.collaboration = collaboration
        existing_review.attitude = attitude

        # Append update reason to comments
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        update_note = f"\n\n---\n[UPDATE {timestamp}]\nReason: {update_reason.strip()}"
        if comments:
            existing_review.comments = comments + update_note
        else:
            existing_review.comments = (existing_review.comments or "") + update_note

        existing_review.updated_at = datetime.now(timezone.utc)

        # RECALCULATE XP when review is updated
        average_score = (punctuality + engagement + focus + collaboration + attitude) / 5.0
        xp_earned = int(50 * (average_score / 5.0))  # Base 50 XP * performance ratio

        # Get student specialization
        student = db.query(User).filter(User.id == student_id).first()
        student_spec = student.specialization.value if student and student.specialization else None

        # Update specialization progress XP
        _update_specialization_xp(db, student_id, student_spec, xp_earned, session_id, is_update=True)

        print(f"♻️ XP RECALCULATED: Student {student_id} | Session {session_id} | Score: {average_score:.1f}/5.0 | XP: {xp_earned}")
    else:
        # Create new review
        review = StudentPerformanceReview(
            session_id=session_id,
            student_id=student_id,
            instructor_id=user.id,
            punctuality=punctuality,
            engagement=engagement,
            focus=focus,
            collaboration=collaboration,
            attitude=attitude,
            comments=comments
        )
        db.add(review)
        db.flush()  # Get review ID

        # AWARD XP for new review
        average_score = (punctuality + engagement + focus + collaboration + attitude) / 5.0
        xp_earned = int(50 * (average_score / 5.0))  # Base 50 XP * performance ratio

        # Get student specialization
        student = db.query(User).filter(User.id == student_id).first()
        student_spec = student.specialization.value if student and student.specialization else None

        # Update specialization progress XP
        _update_specialization_xp(db, student_id, student_spec, xp_earned, session_id, is_update=False)

        print(f"🎉 XP AWARDED: Student {student_id} | Session {session_id} | Spec: {student_spec} | Score: {average_score:.1f}/5.0 | XP: {xp_earned}")

    db.commit()

    return RedirectResponse(
        url=f"/sessions/{session_id}?success=student_evaluated",
        status_code=303
    )


@router.post("/sessions/{session_id}/evaluate-instructor")
async def evaluate_instructor_session(
    request: Request,
    session_id: int,
    instructor_clarity: int = Form(...),
    support_approachability: int = Form(...),
    session_structure: int = Form(...),
    relevance: int = Form(...),
    environment: int = Form(...),
    engagement_feeling: int = Form(...),
    feedback_quality: int = Form(...),
    satisfaction: int = Form(...),
    comments: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Student evaluates instructor and session quality (On-Site sessions only)

    Requirements:
    - User must be student
    - Session must be On-Site type
    - Student must have attended the session (present/late status)
    """
    if user.role != UserRole.STUDENT:
        return RedirectResponse(url=f"/sessions/{session_id}?error=students_only", status_code=303)
    
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return RedirectResponse(url="/sessions?error=session_not_found", status_code=303)

    # CRITICAL: Verify session has ended before allowing evaluation
    # Use actual_end_time if available (instructor stopped session), otherwise use scheduled date_end
    if session.actual_end_time is None:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=session_not_stopped",
            status_code=303
        )

    # CRITICAL: Verify student attended (present or late - NOT absent)
    attendance = db.query(Attendance).filter(
        Attendance.session_id == session_id,
        Attendance.user_id == user.id
    ).first()
    
    if not attendance or attendance.status == AttendanceStatus.absent:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=must_attend_to_review",
            status_code=303
        )
    
    # Validate scores (1-5)
    scores = [
        instructor_clarity, support_approachability, session_structure,
        relevance, environment, engagement_feeling, feedback_quality, satisfaction
    ]
    if any(score < 1 or score > 5 for score in scores):
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=invalid_scores",
            status_code=303
        )
    
    # Check if review already exists
    existing_review = db.query(InstructorSessionReview).filter(
        InstructorSessionReview.session_id == session_id,
        InstructorSessionReview.student_id == user.id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.instructor_clarity = instructor_clarity
        existing_review.support_approachability = support_approachability
        existing_review.session_structure = session_structure
        existing_review.relevance = relevance
        existing_review.environment = environment
        existing_review.engagement_feeling = engagement_feeling
        existing_review.feedback_quality = feedback_quality
        existing_review.satisfaction = satisfaction
        existing_review.comments = comments
        existing_review.updated_at = datetime.now(timezone.utc)
    else:
        # Create new review
        review = InstructorSessionReview(
            session_id=session_id,
            student_id=user.id,
            instructor_id=session.instructor_id,
            instructor_clarity=instructor_clarity,
            support_approachability=support_approachability,
            session_structure=session_structure,
            relevance=relevance,
            environment=environment,
            engagement_feeling=engagement_feeling,
            feedback_quality=feedback_quality,
            satisfaction=satisfaction,
            comments=comments
        )
        db.add(review)
    
    db.commit()

    return RedirectResponse(
        url=f"/sessions/{session_id}?success=instructor_evaluated",
        status_code=303
    )


