"""
Instructor session control routes
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form, status, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List
from pydantic import BaseModel

from ...database import get_db
from ...dependencies import get_current_user_web, get_current_user_optional
from ...models.user import User, UserRole
from .helpers import update_specialization_xp, get_lfa_age_category

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


@router.post("/sessions/{session_id}/unlock-quiz")
async def unlock_quiz(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Instructor unlocks the quiz for HYBRID sessions

    Requirements:
    - User must be instructor
    - Session must be HYBRID type
    - Instructor must own this session
    - Session must be started (in progress)
    """
    if user.role != UserRole.INSTRUCTOR:
        return RedirectResponse(url=f"/sessions/{session_id}?error=unauthorized", status_code=303)

    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return RedirectResponse(url="/sessions?error=session_not_found", status_code=303)

    # Verify session is HYBRID
    if session.session_type != SessionType.hybrid:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=unlock_only_hybrid",
            status_code=303
        )

    # Verify instructor owns this session
    if session.instructor_id != user.id:
        return RedirectResponse(url=f"/sessions/{session_id}?error=not_your_session", status_code=303)

    # Verify session was started
    if session.actual_start_time is None:
        return RedirectResponse(
            url=f"/sessions/{session_id}?error=session_not_started_unlock",
            status_code=303
        )

    # Unlock quiz
    session.quiz_unlocked = True
    db.commit()

    print(f"🔓 Quiz unlocked for HYBRID session {session_id} by instructor {user.id}")

    return RedirectResponse(
        url=f"/sessions/{session_id}?success=quiz_unlocked",
        status_code=303
    )


# ==========================================
# QUIZ TAKING ROUTES (Web Interface)
# ==========================================

@router.get("/quizzes/{quiz_id}/take")
async def take_quiz(
    request: Request,
    quiz_id: int,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Quiz taking page for students

    This is a web interface for quiz-taking linked from sessions.
    Students can take quizzes through this interface.
    """
    quiz = db.query(Quiz).options(
        joinedload(Quiz.questions).joinedload(QuizQuestion.answer_options)
    ).filter(Quiz.id == quiz_id).first()

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # CRITICAL: Check if this quiz is linked to a session, and if so, verify the user is BOOKED
    if session_id:
        session_quiz = db.query(SessionQuiz).filter(
            SessionQuiz.session_id == session_id,
            SessionQuiz.quiz_id == quiz_id
        ).first()

        if not session_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found for this session")

        # Get the session to check start time
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check if session has started (quiz only available after session start time)
        budapest_tz = ZoneInfo("Europe/Budapest")
        now = datetime.now(budapest_tz)
        session_start = session.date_start
        if session_start.tzinfo is None:
            session_start = session_start.replace(tzinfo=budapest_tz)

        if now < session_start:
            raise HTTPException(
                status_code=403,
                detail=f"Quiz not available yet. Session starts at {session_start.strftime('%Y-%m-%d %H:%M')}."
            )

        # Check if user is BOOKED for this session
        booking = db.query(Booking).filter(
            Booking.session_id == session_id,
            Booking.user_id == user.id,
            Booking.status == 'CONFIRMED'
        ).first()

        if not booking:
            raise HTTPException(
                status_code=403,
                detail="You must book this session before taking the quiz. Please enroll first!"
            )

    # Check if user already has an active (incomplete) attempt
    active_attempt = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user.id,
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.completed_at == None
    ).first()

    # If no active attempt, create one
    if not active_attempt:
        active_attempt = QuizAttempt(
            user_id=user.id,
            quiz_id=quiz_id,
            started_at=datetime.now(timezone.utc),
            total_questions=len(quiz.questions)
        )
        db.add(active_attempt)
        db.commit()
        db.refresh(active_attempt)

    # Calculate remaining time
    elapsed_seconds = (datetime.now(timezone.utc) - active_attempt.started_at).total_seconds()
    time_limit_seconds = quiz.time_limit_minutes * 60
    remaining_seconds = max(0, int(time_limit_seconds - elapsed_seconds))

    # If time expired, auto-submit with 0 score
    if remaining_seconds == 0:
        active_attempt.completed_at = datetime.now(timezone.utc)
        active_attempt.score = 0.0
        active_attempt.correct_answers = 0
        active_attempt.passed = False
        active_attempt.xp_awarded = 0
        active_attempt.time_spent_minutes = quiz.time_limit_minutes
        db.commit()

        return templates.TemplateResponse("quiz_result.html", {
            "request": request,
            "user": user,
            "quiz": quiz,
            "session": None,
            "session_id": session_id,
            "score": 0.0,
            "passed": False,
            "correct_count": 0,
            "total_questions": len(quiz.questions),
            "xp_awarded": 0,
            "time_spent": quiz.time_limit_minutes
        })

    # Get session if provided
    session = None
    if session_id:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()

    return templates.TemplateResponse("quiz_take.html", {
        "request": request,
        "user": user,
        "quiz": quiz,
        "session": session,
        "session_id": session_id,
        "attempt_id": active_attempt.id,
        "remaining_seconds": remaining_seconds
    })


@router.post("/quizzes/{quiz_id}/submit")
async def submit_quiz(
    request: Request,
    quiz_id: int,
    session_id: Optional[str] = Form(None),
    attempt_id: int = Form(...),
    time_spent: float = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web)
):
    """
    Submit quiz answers and calculate score
    Simple scoring system: Understood (pass) / Needs Review (fail)
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # CRITICAL: Check if this quiz is linked to a session, and if so, verify the user is BOOKED
    if session_id and session_id != "None":
        session_id_int = int(session_id)
        session_quiz = db.query(SessionQuiz).filter(
            SessionQuiz.session_id == session_id_int,
            SessionQuiz.quiz_id == quiz_id
        ).first()

        if not session_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found for this session")

        # Get the session to check start time
        session = db.query(SessionModel).filter(SessionModel.id == session_id_int).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check if session has started (quiz only available after session start time)
        budapest_tz = ZoneInfo("Europe/Budapest")
        now = datetime.now(budapest_tz)
        session_start = session.date_start
        if session_start.tzinfo is None:
            session_start = session_start.replace(tzinfo=budapest_tz)

        if now < session_start:
            raise HTTPException(
                status_code=403,
                detail=f"Quiz not available yet. Session starts at {session_start.strftime('%Y-%m-%d %H:%M')}."
            )

        # Check if user is BOOKED for this session
        booking = db.query(Booking).filter(
            Booking.session_id == session_id_int,
            Booking.user_id == user.id,
            Booking.status == 'CONFIRMED'
        ).first()

        if not booking:
            raise HTTPException(
                status_code=403,
                detail="You must book this session before submitting the quiz!"
            )

    # Get the active attempt
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == attempt_id,
        QuizAttempt.user_id == user.id,
        QuizAttempt.quiz_id == quiz_id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    # Check if already completed
    if attempt.completed_at:
        raise HTTPException(status_code=400, detail="Quiz already submitted")

    # Get form data
    form_data = await request.form()

    # Calculate score
    correct_count = 0
    total_points = 0
    earned_points = 0

    for question in quiz.questions:
        total_points += question.points
        field_name = f"question_{question.id}"
        selected_option_id = form_data.get(field_name)

        if selected_option_id:
            selected_option_id = int(selected_option_id)
            option = db.query(QuizAnswerOption).filter(QuizAnswerOption.id == selected_option_id).first()

            if option and option.is_correct:
                correct_count += 1
                earned_points += question.points

            # Save user answer
            user_answer = QuizUserAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_id=selected_option_id,
                is_correct=option.is_correct if option else False
            )
            db.add(user_answer)

    # Calculate percentage score
    score = (earned_points / total_points * 100) if total_points > 0 else 0
    # CRITICAL: passing_score is stored as decimal (0.75 = 75%), score is percentage (75)
    passed = score >= (quiz.passing_score * 100)

    # Update attempt with completion
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.time_spent_minutes = time_spent
    attempt.score = score
    attempt.correct_answers = correct_count
    attempt.passed = passed
    attempt.xp_awarded = quiz.xp_reward if passed else 0

    # Update user_stats with earned XP (GAMIFICATION SYNC)
    if attempt.xp_awarded > 0:
        user_stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()

        if not user_stats:
            # Create user_stats if doesn't exist
            user_stats = UserStats(
                user_id=user.id,
                total_xp=attempt.xp_awarded,
                level=1
            )
            db.add(user_stats)
        else:
            # Add XP to existing total
            user_stats.total_xp = (user_stats.total_xp or 0) + attempt.xp_awarded
            # Update level (1000 XP per level)
            user_stats.level = max(1, user_stats.total_xp // 1000)

    db.commit()

    # Get session for back link
    session = None
    if session_id and session_id.strip():
        try:
            session = db.query(SessionModel).filter(SessionModel.id == int(session_id)).first()

            # VIRTUAL SESSION: Auto-mark attendance if quiz passed
            if session and session.session_type.value == 'virtual' and passed:
                booking = db.query(Booking).filter(
                    Booking.user_id == user.id,
                    Booking.session_id == session.id
                ).first()

                if booking:
                    # Check if attendance already exists
                    existing_attendance = db.query(Attendance).filter(
                        Attendance.user_id == user.id,
                        Attendance.session_id == session.id
                    ).first()

                    if not existing_attendance:
                        # Auto-create attendance as 'present' for successful quiz
                        auto_attendance = Attendance(
                            user_id=user.id,
                            session_id=session.id,
                            booking_id=booking.id,
                            status='present',
                            check_in_time=datetime.now(timezone.utc)
                        )
                        db.add(auto_attendance)
                        db.commit()
                        print(f"✅ Auto-marked attendance for VIRTUAL session {session.id} - student {user.email}")

        except ValueError:
            pass

    # Render result page
    return templates.TemplateResponse("quiz_result.html", {
        "request": request,
        "user": user,
        "quiz": quiz,
        "session": session,
        "session_id": session_id,
        "score": score,
        "passed": passed,
        "correct_count": correct_count,
        "total_questions": len(quiz.questions),
        "xp_awarded": attempt.xp_awarded,
        "time_spent": time_spent
    })


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


