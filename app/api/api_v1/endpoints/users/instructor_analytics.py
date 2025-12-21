"""
Instructor analytics and student management endpoints
View students, their details, and progress tracking
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User, UserRole
from .....models.booking import Booking
from .....models.attendance import Attendance
from .....models.feedback import Feedback
from .helpers import calculate_pagination, serialize_enum_value

router = APIRouter()


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
    from .....models.project import ProjectEnrollment, ProjectEnrollmentStatus
    from .....models.session import Session as SessionTypel
    
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
        SessionTypel, Booking.session_id == SessionTypel.id
    ).filter(
        SessionTypel.instructor_id == current_user.id,
        User.role == UserRole.STUDENT
    ).distinct()
    
    # Combine and get unique students
    all_students = project_students.union(session_students).order_by(User.name)
    
    # Get total count
    total = all_students.count()
    
    # Apply pagination
    offset = (page - 1) * size
    students = all_students.offset(offset).limit(size).all()

    # OPTIMIZED: Batch fetch all enrollments with projects (reduces N+1 queries to 1 query)
    student_ids = [s.id for s in students]

    enrollments = db.query(ProjectEnrollment).options(
        joinedload(ProjectEnrollment.project)
    ).join(ProjectEnrollment.project).filter(
        ProjectEnrollment.user_id.in_(student_ids),
        ProjectEnrollment.project.has(instructor_id=current_user.id)
    ).all()

    # Group enrollments by student ID
    enrollments_by_student = {}
    for enrollment in enrollments:
        if enrollment.user_id not in enrollments_by_student:
            enrollments_by_student[enrollment.user_id] = []
        enrollments_by_student[enrollment.user_id].append(enrollment)

    # Build response with enrollment info (no queries in loop)
    student_list = []
    for student in students:
        student_enrollments = enrollments_by_student.get(student.id, [])

        enrollment_data = []
        for enrollment in student_enrollments:
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
    from .....models.project import Project, ProjectEnrollment
    from .....models.session import Session as SessionTypel
    
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
                SessionTypel, Booking.session_id == SessionTypel.id
            ).filter(
                Booking.user_id == student_id,
                SessionTypel.instructor_id == current_user.id
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
            SessionTypel, Booking.session_id == SessionTypel.id
        ).filter(
            Booking.user_id == student_id,
            SessionTypel.instructor_id == current_user.id
        ).all()
    except Exception:
        bookings = []
    
    # Get attendance records
    try:
        attendance_records = db.query(Attendance).join(
            SessionTypel, Attendance.session_id == SessionTypel.id
        ).filter(
            Attendance.user_id == student_id,
            SessionTypel.instructor_id == current_user.id
        ).all()
    except Exception:
        attendance_records = []
    
    # Get feedback given by student
    try:
        feedback_records = db.query(Feedback).join(
            SessionTypel, Feedback.session_id == SessionTypel.id
        ).filter(
            Feedback.user_id == student_id,
            SessionTypel.instructor_id == current_user.id
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
                'status': serialize_enum_value(enrollment.status),
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
                'status': serialize_enum_value(booking.status),
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
                'status': serialize_enum_value(attendance.status),
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
    from .....models.project import Project, ProjectEnrollment
    from .....models.session import Session as SessionTypel
    try:
        from .....models.quiz import QuizAttempt, Quiz
    except ImportError:
        QuizAttempt = None
        Quiz = None
    try:
        from .....models.gamification import UserAchievement, Achievement
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
                SessionTypel, Booking.session_id == SessionTypel.id
            ).filter(
                Booking.user_id == student_id,
                SessionTypel.instructor_id == current_user.id
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
                    'status': serialize_enum_value(enrollment.status),
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
            SessionTypel, Attendance.session_id == SessionTypel.id
        ).filter(
            Attendance.user_id == student_id,
            SessionTypel.instructor_id == current_user.id
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
                SessionTypel, Quiz.session_id == SessionTypel.id
            ).filter(
                QuizAttempt.user_id == student_id,
                SessionTypel.instructor_id == current_user.id
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
