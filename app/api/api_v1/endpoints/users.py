from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_user
from ....core.security import get_password_hash
from ....models.user import User, UserRole
from ....models.booking import Booking
from ....models.attendance import Attendance
from ....models.feedback import Feedback
from ....schemas.user import (
    User as UserSchema, UserCreate, UserUpdate, UserUpdateSelf,
    UserWithStats, UserList
)
from ....schemas.auth import ResetPassword

router = APIRouter()


@router.post("/", response_model=UserSchema)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Create new user (Admin only)
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user
    from ....models.specialization import SpecializationType

    # Convert specialization string to enum if provided
    specialization_enum = None
    if user_data.specialization:
        try:
            specialization_enum = SpecializationType[user_data.specialization]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid specialization: {user_data.specialization}"
            )

    user = User(
        name=user_data.name,
        email=user_data.email,
        nickname=user_data.nickname,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=user_data.is_active,
        phone=user_data.phone,
        emergency_contact=user_data.emergency_contact,
        emergency_phone=user_data.emergency_phone,
        date_of_birth=user_data.date_of_birth,
        medical_notes=user_data.medical_notes,
        position=user_data.position,
        specialization=specialization_enum,
        onboarding_completed=user_data.onboarding_completed if hasattr(user_data, 'onboarding_completed') else False,
        created_by=current_user.id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/", response_model=UserList)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> Any:
    """
    List users with pagination and filtering (Admin only)
    """
    query = db.query(User)
    
    # Apply filters
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            User.name.contains(search) | User.email.contains(search)
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()
    
    return UserList(
        users=users,
        total=total,
        page=page,
        size=size
    )


@router.get("/me", response_model=UserSchema)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user profile
    """
    # Keep interests as JSON string for schema compatibility
    user_data = current_user.__dict__.copy()
    # Ensure interests is a string (not parsed to list)
    if user_data.get('interests') is None:
        user_data['interests'] = None
    
    return user_data


@router.patch("/me", response_model=UserSchema)
def update_own_profile(
    user_update: UserUpdateSelf,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update own profile
    """
    # Check email uniqueness if email is being updated
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

    # Validate that emergency phone is different from user phone
    update_data = user_update.model_dump(exclude_unset=True)
    user_phone = update_data.get('phone', current_user.phone)
    emergency_phone = update_data.get('emergency_phone', current_user.emergency_phone)

    if user_phone and emergency_phone and user_phone == emergency_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A vészhelyzeti telefonszám nem lehet ugyanaz, mint a saját telefonszámod"
        )

    # Handle NDA acceptance with timestamp
    if 'nda_accepted' in update_data and update_data['nda_accepted']:
        from datetime import datetime, timezone
        setattr(current_user, 'nda_accepted_at', datetime.now(timezone.utc))

    # Update fields
    for field, value in update_data.items():
        if field == 'interests' and isinstance(value, list):
            # Convert interests list to JSON string for database storage
            import json
            setattr(current_user, field, json.dumps(value))
        else:
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    # Keep interests as JSON string for schema compatibility
    user_data = current_user.__dict__.copy()
    # Ensure interests is a string (not parsed to list)
    if user_data.get('interests') is None:
        user_data['interests'] = None

    return user_data


@router.get("/search", response_model=List[UserSchema])
def search_users(
    q: str = Query(..., min_length=1, description="Search query for user name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> List[User]:
    """
    Search users by name or email (Admin only)
    Returns a list of users matching the search criteria.
    """
    # Build base query
    query = db.query(User).filter(
        or_(
            User.name.ilike(f"%{q}%"),
            User.email.ilike(f"%{q}%")
        )
    )
    
    # Apply filters
    if role is not None:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Execute query with limit
    users = query.limit(limit).all()
    
    # Return just the users list - Pydantic will handle serialization
    return users


@router.get("/{user_id}", response_model=UserWithStats)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Get user by ID with statistics (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user statistics
    total_bookings = db.query(func.count(Booking.id)).filter(Booking.user_id == user_id).scalar()
    completed_sessions = db.query(func.count(Attendance.id)).filter(
        and_(Attendance.user_id == user_id, Attendance.status == "present")
    ).scalar()
    feedback_count = db.query(func.count(Feedback.id)).filter(Feedback.user_id == user_id).scalar()
    
    return UserWithStats(
        **user.__dict__,
        total_bookings=total_bookings or 0,
        completed_sessions=completed_sessions or 0,
        feedback_count=feedback_count or 0
    )


@router.patch("/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Update user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check email uniqueness if email is being updated
    if user_update.email and user_update.email != user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
    
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Delete user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Soft delete by deactivating the user instead of hard delete
    # to preserve referential integrity
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    password_data: ResetPassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Reset user password (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}


@router.get("/instructor/students")
def get_instructor_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get students for current instructor
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Import here to avoid circular imports
    from ....models.project import ProjectEnrollment, ProjectEnrollmentStatus
    from ....models.session import Session as SessionModel
    
    # Get students enrolled in instructor's projects or sessions
    # First get all students enrolled in instructor's projects
    project_students = db.query(User).join(
        ProjectEnrollment, User.id == ProjectEnrollment.user_id
    ).join(
        ProjectEnrollment.project
    ).filter(
        ProjectEnrollment.project.has(instructor_id=current_user.id),
        User.role == UserRole.STUDENT
    ).distinct()
    
    # Also get students who booked instructor's sessions
    session_students = db.query(User).join(
        Booking, User.id == Booking.user_id
    ).join(
        SessionModel, Booking.session_id == SessionModel.id
    ).filter(
        SessionModel.instructor_id == current_user.id,
        User.role == UserRole.STUDENT
    ).distinct()
    
    # Combine and get unique students
    all_students = project_students.union(session_students).order_by(User.name)
    
    # Get total count
    total = all_students.count()
    
    # Apply pagination
    offset = (page - 1) * size
    students = all_students.offset(offset).limit(size).all()
    
    # Build response with enrollment info
    student_list = []
    for student in students:
        # Get project enrollments for this instructor
        enrollments = db.query(ProjectEnrollment).join(
            ProjectEnrollment.project
        ).filter(
            ProjectEnrollment.user_id == student.id,
            ProjectEnrollment.project.has(instructor_id=current_user.id)
        ).all()
        
        enrollment_data = []
        for enrollment in enrollments:
            enrollment_data.append({
                'id': enrollment.id,
                'project_id': enrollment.project_id,
                'project': {
                    'id': enrollment.project.id,
                    'title': enrollment.project.title,
                    'completion_percentage': getattr(enrollment, 'completion_percentage', 0)
                },
                'status': enrollment.status,
                'enrolled_at': enrollment.enrolled_at.isoformat()
            })
        
        student_dict = {
            'id': student.id,
            'name': student.name,
            'email': student.email,
            'is_active': student.is_active,
            'created_at': student.created_at.isoformat(),
            'enrollments': enrollment_data
        }
        student_list.append(student_dict)
    
    return {
        'students': student_list,
        'total': total,
        'page': page,
        'size': size
    }


@router.get("/instructor/students/{student_id}")
def get_instructor_student_details(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get detailed information for a specific student (Instructor only)
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Get the student
    student = db.query(User).filter(
        User.id == student_id, 
        User.role == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Import here to avoid circular imports
    from ....models.project import Project, ProjectEnrollment
    from ....models.session import Session as SessionModel
    
    # Verify instructor has access to this student (student must be in instructor's projects/sessions)
    has_access = False
    
    # Check project access
    try:
        project_access = db.query(ProjectEnrollment).join(
            Project, ProjectEnrollment.project_id == Project.id
        ).filter(
            ProjectEnrollment.user_id == student_id,
            Project.instructor_id == current_user.id
        ).first()
        if project_access:
            has_access = True
    except Exception:
        pass
    
    # If no project access, check session access
    if not has_access:
        try:
            session_access = db.query(Booking).join(
                SessionModel, Booking.session_id == SessionModel.id
            ).filter(
                Booking.user_id == student_id,
                SessionModel.instructor_id == current_user.id
            ).first()
            if session_access:
                has_access = True
        except Exception:
            pass
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student not in your projects or sessions."
        )
    
    # Get detailed student information
    try:
        enrollments = db.query(ProjectEnrollment).join(
            Project, ProjectEnrollment.project_id == Project.id
        ).filter(
            ProjectEnrollment.user_id == student_id,
            Project.instructor_id == current_user.id
        ).all()
    except Exception:
        enrollments = []
    
    # Get session bookings
    try:
        bookings = db.query(Booking).join(
            SessionModel, Booking.session_id == SessionModel.id
        ).filter(
            Booking.user_id == student_id,
            SessionModel.instructor_id == current_user.id
        ).all()
    except Exception:
        bookings = []
    
    # Get attendance records
    try:
        attendance_records = db.query(Attendance).join(
            SessionModel, Attendance.session_id == SessionModel.id
        ).filter(
            Attendance.user_id == student_id,
            SessionModel.instructor_id == current_user.id
        ).all()
    except Exception:
        attendance_records = []
    
    # Get feedback given by student
    try:
        feedback_records = db.query(Feedback).join(
            SessionModel, Feedback.session_id == SessionModel.id
        ).filter(
            Feedback.user_id == student_id,
            SessionModel.instructor_id == current_user.id
        ).all()
    except Exception:
        feedback_records = []
    
    enrollment_data = []
    for enrollment in enrollments:
        try:
            enrollment_data.append({
                'id': enrollment.id,
                'project_id': enrollment.project_id,
                'project': {
                    'id': enrollment.project.id,
                    'title': enrollment.project.title,
                    'description': getattr(enrollment.project, 'description', ''),
                    'completion_percentage': getattr(enrollment, 'completion_percentage', 0)
                },
                'status': enrollment.status.value if hasattr(enrollment.status, 'value') else str(enrollment.status),
                'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
            })
        except Exception:
            continue
    
    booking_data = []
    for booking in bookings:
        try:
            booking_data.append({
                'id': booking.id,
                'session_id': booking.session_id,
                'session': {
                    'id': booking.session.id,
                    'title': booking.session.title,
                    'date_start': booking.session.date_start.isoformat(),
                    'date_end': booking.session.date_end.isoformat(),
                    'location': getattr(booking.session, 'location', 'N/A')
                },
                'status': booking.status.value if hasattr(booking.status, 'value') else str(booking.status),
                'created_at': booking.created_at.isoformat()
            })
        except Exception:
            continue
    
    attendance_data = []
    for attendance in attendance_records:
        try:
            attendance_data.append({
                'id': attendance.id,
                'session_id': attendance.session_id,
                'session': {
                    'title': attendance.session.title,
                    'date_start': attendance.session.date_start.isoformat()
                },
                'status': attendance.status.value if hasattr(attendance.status, 'value') else str(attendance.status),
                'checked_in_at': attendance.checked_in_at.isoformat() if attendance.checked_in_at else None
            })
        except Exception:
            continue
    
    feedback_data = []
    for feedback in feedback_records:
        try:
            feedback_data.append({
                'id': feedback.id,
                'session_id': feedback.session_id,
                'session': {
                    'title': feedback.session.title,
                    'date_start': feedback.session.date_start.isoformat()
                },
                'rating': feedback.rating,
                'comment': feedback.comment,
                'created_at': feedback.created_at.isoformat()
            })
        except Exception:
            continue
    
    return {
        'id': student.id,
        'name': student.name,
        'email': student.email,
        'is_active': student.is_active,
        'created_at': student.created_at.isoformat(),
        'enrollments': enrollment_data,
        'bookings': booking_data,
        'attendance': attendance_data,
        'feedback': feedback_data,
        'stats': {
            'total_enrollments': len(enrollment_data),
            'active_enrollments': len([e for e in enrollment_data if e['status'] == 'active']),
            'total_bookings': len(booking_data),
            'total_attendance': len(attendance_data),
            'present_sessions': len([a for a in attendance_data if a['status'] == 'present']),
            'feedback_given': len(feedback_data)
        }
    }


@router.get("/instructor/students/{student_id}/progress")
def get_instructor_student_progress(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get progress information for a specific student (Instructor only)
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Get the student
    student = db.query(User).filter(
        User.id == student_id, 
        User.role == UserRole.STUDENT
    ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Import here to avoid circular imports
    from ....models.project import Project, ProjectEnrollment
    from ....models.session import Session as SessionModel
    try:
        from ....models.quiz import QuizAttempt, Quiz
    except ImportError:
        QuizAttempt = None
        Quiz = None
    try:
        from ....models.gamification import UserAchievement, Achievement
    except ImportError:
        UserAchievement = None
        Achievement = None
    
    # Verify instructor has access to this student
    has_access = False
    
    # Check project access
    try:
        project_access = db.query(ProjectEnrollment).join(
            Project, ProjectEnrollment.project_id == Project.id
        ).filter(
            ProjectEnrollment.user_id == student_id,
            Project.instructor_id == current_user.id
        ).first()
        if project_access:
            has_access = True
    except Exception:
        pass
    
    # If no project access, check session access
    if not has_access:
        try:
            session_access = db.query(Booking).join(
                SessionModel, Booking.session_id == SessionModel.id
            ).filter(
                Booking.user_id == student_id,
                SessionModel.instructor_id == current_user.id
            ).first()
            if session_access:
                has_access = True
        except Exception:
            pass
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Student not in your projects or sessions."
        )
    
    # Get project progress
    project_progress = []
    try:
        enrollments = db.query(ProjectEnrollment).join(
            Project, ProjectEnrollment.project_id == Project.id
        ).filter(
            ProjectEnrollment.user_id == student_id,
            Project.instructor_id == current_user.id
        ).all()
        
        for enrollment in enrollments:
            try:
                project_progress.append({
                    'project_id': enrollment.project_id,
                    'project_title': enrollment.project.title,
                    'status': enrollment.status.value if hasattr(enrollment.status, 'value') else str(enrollment.status),
                    'completion_percentage': getattr(enrollment, 'completion_percentage', 0),
                    'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
                })
            except Exception:
                continue
    except Exception:
        pass
    
    # Get session attendance progress
    attendance_records = []
    try:
        attendance_records = db.query(Attendance).join(
            SessionModel, Attendance.session_id == SessionModel.id
        ).filter(
            Attendance.user_id == student_id,
            SessionModel.instructor_id == current_user.id
        ).all()
    except Exception:
        pass
    
    total_sessions = len(attendance_records)
    present_sessions = len([a for a in attendance_records if a.status == 'present'])
    attendance_rate = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Get quiz progress (for instructor's sessions/projects)
    quiz_progress = []
    if QuizAttempt and Quiz:
        try:
            quiz_attempts = db.query(QuizAttempt).join(
                Quiz, QuizAttempt.quiz_id == Quiz.id
            ).join(
                SessionModel, Quiz.session_id == SessionModel.id
            ).filter(
                QuizAttempt.user_id == student_id,
                SessionModel.instructor_id == current_user.id
            ).all()
            
            for attempt in quiz_attempts:
                quiz_progress.append({
                    'quiz_id': attempt.quiz_id,
                    'quiz_title': attempt.quiz.title,
                    'session_title': attempt.quiz.session.title if attempt.quiz.session else 'N/A',
                    'score': attempt.score,
                    'passed': attempt.passed,
                    'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
                    'time_spent_minutes': attempt.time_spent_minutes
                })
        except Exception:
            quiz_progress = []
    
    # Get achievements
    achievement_data = []
    if UserAchievement and Achievement:
        try:
            achievements = db.query(UserAchievement).join(
                Achievement, UserAchievement.achievement_id == Achievement.id
            ).filter(
                UserAchievement.user_id == student_id
            ).all()
            
            for user_achievement in achievements:
                achievement_data.append({
                    'achievement_id': user_achievement.achievement_id,
                    'achievement_name': user_achievement.achievement.name,
                    'achievement_description': user_achievement.achievement.description,
                    'earned_at': user_achievement.earned_at.isoformat() if user_achievement.earned_at else None
                })
        except Exception:
            achievement_data = []
    
    # Calculate overall progress metrics
    avg_project_completion = sum([p['completion_percentage'] for p in project_progress]) / len(project_progress) if project_progress else 0
    avg_quiz_score = sum([q['score'] for q in quiz_progress]) / len(quiz_progress) if quiz_progress else 0
    quiz_pass_rate = len([q for q in quiz_progress if q['passed']]) / len(quiz_progress) * 100 if quiz_progress else 0
    
    return {
        'student': {
            'id': student.id,
            'name': student.name,
            'email': student.email
        },
        'project_progress': project_progress,
        'attendance': {
            'total_sessions': total_sessions,
            'present_sessions': present_sessions,
            'attendance_rate': round(attendance_rate, 1)
        },
        'quiz_progress': quiz_progress,
        'achievements': achievement_data,
        'overall_metrics': {
            'avg_project_completion': round(avg_project_completion, 1),
            'avg_quiz_score': round(avg_quiz_score, 1),
            'quiz_pass_rate': round(quiz_pass_rate, 1),
            'total_achievements': len(achievement_data)
        }
    }


@router.get("/check-nickname/{nickname}")
def check_nickname_availability(
    nickname: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Check if a nickname is available for use
    """
    # Basic validation
    if not nickname or len(nickname.strip()) < 3:
        return {
            "available": False,
            "message": "A becenév legalább 3 karakter hosszú legyen"
        }
    
    if len(nickname) > 30:
        return {
            "available": False,
            "message": "A becenév maximum 30 karakter lehet"
        }
    
    # Check for inappropriate characters
    import re
    if not re.match("^[a-zA-Z0-9_áéíóöőúüűÁÉÍÓÖŐÚÜŰ]+$", nickname):
        return {
            "available": False,
            "message": "A becenév csak betűket, számokat és aláhúzást tartalmazhat"
        }
    
    # Check if already exists (case insensitive)
    existing_user = db.query(User).filter(
        and_(
            func.lower(User.nickname) == nickname.lower(),
            User.id != current_user.id  # Allow user to keep their own nickname
        )
    ).first()
    
    if existing_user:
        return {
            "available": False,
            "message": "Ez a becenév már foglalt. Kérjük, válasszon másikat!"
        }
    
    # Check against reserved nicknames
    reserved_nicknames = ['admin', 'moderator', 'system', 'support', 'help', 'info', 'test']
    if nickname.lower() in reserved_nicknames:
        return {
            "available": False,
            "message": "Ez a becenév foglalt. Kérjük, válasszon másikat!"
        }
    
    return {
        "available": True,
        "message": "Remek! Ez a becenév elérhető."
    }