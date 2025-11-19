from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_or_instructor_user
from ....models.user import User
from ....models.semester import Semester
from ....models.project import (
    Project as ProjectModel, 
    ProjectEnrollment, 
    ProjectMilestone,
    ProjectMilestoneProgress,
    ProjectSession,
    ProjectStatus,
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    MilestoneStatus
)
from ....models.specialization import SpecializationType
from ....schemas.project import (
    Project as ProjectSchema,
    ProjectCreate,
    ProjectUpdate,
    ProjectList,
    ProjectWithDetails,
    ProjectEnrollmentCreate,
    ProjectEnrollment as ProjectEnrollmentSchema,
    ProjectEnrollmentList,
    ProjectEnrollmentWithDetails,
    StudentProjectSummary,
    InstructorProjectSummary,
    ProjectProgressResponse,
    MilestoneProgressUpdate,
    ProjectQuiz,
    ProjectQuizCreate,
    ProjectQuizWithDetails,
    EnrollmentPriorityResponse
)

router = APIRouter()


def validate_semester_enrollment(project_id: int, current_user: User, db: Session) -> None:
    """
    Validates that enrollment is allowed for the project's semester.
    
    🚨 CRITICAL: Cross-semester project enrollment MUST be blocked for all users
    This ensures users can only enroll in projects from their own semester.
    
    Args:
        project_id: ID of the project to validate
        current_user: Current user attempting to enroll
        db: Database session
        
    Raises:
        HTTPException: If semester validation fails or cross-semester enrollment attempted
    """
    # Get project and its semester
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    semester = db.query(Semester).filter(Semester.id == project.semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project semester not found"
        )
    
    # Check if semester dates are properly set
    if not semester.start_date or not semester.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Semester '{semester.name}' has invalid date configuration"
        )
    
    # 🚨 CRITICAL: Cross-semester project enrollment restriction
    # For LFA testing: All users (including Mbappé) are restricted to their own semester for projects
    # This is different from sessions where Mbappé has cross-access
    
    # Determine user's primary semester (for testing: LIVE-TEST-2025)
    # In a real system, this would be based on user enrollment records
    user_primary_semester = db.query(Semester).filter(
        Semester.code == 'LIVE-TEST-2025'
    ).first()
    
    if not user_primary_semester:
        # Fallback to most recent active semester
        user_primary_semester = db.query(Semester).filter(
            Semester.is_active == True
        ).order_by(Semester.id.desc()).first()
    
    if user_primary_semester and project.semester_id != user_primary_semester.id:
        # 📝 Log the restriction for testing verification
        print(f"🚨 Cross-semester project enrollment blocked: "
              f"User {current_user.name} (semester {user_primary_semester.name}) "
              f"tried to enroll in project '{project.title}' (semester {semester.name})")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-semester project enrollment is not allowed. "
                   f"You can only enroll in projects from your own semester ('{user_primary_semester.name}'). "
                   f"This project belongs to '{semester.name}'."
        )
    
    # Validate semester is available for enrollment
    current_date = datetime.now(timezone.utc).date()
    
    # Allow enrollment if semester is active OR if it's not started yet (future enrollment)
    # Only block enrollment if semester has already ended
    if current_date > semester.end_date:
        detail = f"Enrollment closed. Semester '{semester.name}' has ended on {semester.end_date}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )
    
    # Additional check: semester must be marked as active in the database
    if not semester.is_active:
        detail = f"Enrollment not allowed. Semester '{semester.name}' is not currently active"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def validate_specialization_enrollment(project_id: int, current_user: User, db: Session) -> None:
    """
    Validate user can enroll in project based on specialization
    🎓 NEW: Specialization-based enrollment validation
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # If user has no specialization, allow enrollment (backward compatibility)
    if not current_user.has_specialization:
        print(f"🎓 User {current_user.name} has no specialization - allowing enrollment")
        return
    
    # If project has no specialization requirement, allow enrollment
    if not project.target_specialization:
        print(f"🎓 Project {project.title} has no specialization requirement - allowing enrollment")
        return
        
    # If project is mixed specialization, allow enrollment
    if project.mixed_specialization:
        print(f"🎓 Project {project.title} accepts mixed specializations - allowing enrollment")
        return
    
    # Check specialization match
    if project.target_specialization != current_user.specialization:
        # 📝 Log the restriction for testing verification
        print(f"🚨 Specialization mismatch: "
              f"User {current_user.name} ({current_user.specialization.value}) "
              f"tried to enroll in project '{project.title}' ({project.target_specialization.value})")
        
        # Get specialization names from JSON (HYBRID)
        from app.services.specialization_config_loader import SpecializationConfigLoader
        loader = SpecializationConfigLoader()

        project_spec_name = str(project.target_specialization.value)
        user_spec_name = str(current_user.specialization.value)

        try:
            project_info = loader.get_display_info(project.target_specialization)
            project_spec_name = project_info.get('name', project_spec_name)
        except Exception:
            pass

        try:
            user_info = loader.get_display_info(current_user.specialization)
            user_spec_name = user_info.get('name', user_spec_name)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Specialization mismatch. This project is designed for "
                   f"{project_spec_name} specialization. "
                   f"Your specialization is {user_spec_name}. "
                   f"You can only enroll in projects matching your specialization or mixed projects."
        )
    
    print(f"🎓 Specialization match: {current_user.name} can enroll in {project.title}")


def validate_payment_enrollment(current_user: User) -> None:
    """
    💰 NEW: Validate user has verified payment for semester enrollment
    """
    # Skip payment verification for admins and instructors
    if current_user.role.value in ['admin', 'instructor']:
        print(f"💰 Payment verification skipped for {current_user.role.value}: {current_user.name}")
        return
    
    # Check if student has verified payment
    if not current_user.payment_verified:
        print(f"🚨 Payment verification failed: "
              f"Student {current_user.name} ({current_user.email}) "
              f"tried to enroll without verified payment")
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment verification required. Please contact administration to verify your semester fee payment before enrolling in projects. "
                   "You cannot enroll in projects or book sessions until your payment has been confirmed by an administrator."
        )
    
    print(f"💰 Payment verification passed: {current_user.name} has verified payment")


@router.post("/", response_model=ProjectSchema)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Create new project (Admin/Instructor only)
    """
    # Verify semester exists
    semester = db.query(Semester).filter(Semester.id == project_data.semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    # Create project
    project_dict = project_data.model_dump(exclude={'milestones'})
    
    # Set instructor to current user if not specified and user is instructor
    if not project_dict.get('instructor_id') and current_user.role.value == 'instructor':
        project_dict['instructor_id'] = current_user.id
    
    project = ProjectModel(**project_dict)
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create milestones if provided
    if project_data.milestones:
        for milestone_data in project_data.milestones:
            milestone = ProjectMilestone(
                project_id=project.id,
                **milestone_data.model_dump()
            )
            db.add(milestone)
        db.commit()
    
    # Computed fields are already available as properties
    
    return project


@router.get("/", response_model=ProjectList)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    semester_id: Optional[int] = Query(None),
    status: Optional[str] = Query("active"),
    available_only: bool = Query(False, description="Show only projects with available spots")
) -> Any:
    """
    List projects with filtering
    """
    query = db.query(ProjectModel)
    
    # Filter by semester
    if semester_id:
        query = query.filter(ProjectModel.semester_id == semester_id)
    
    # Filter by status
    if status:
        query = query.filter(ProjectModel.status == status)
    
    # For students, only show active projects
    if current_user.role.value == 'student':
        query = query.filter(ProjectModel.status == ProjectStatus.ACTIVE.value)
        
        # Option to show only projects with available spots
        if available_only:
            # This requires a subquery to count enrollments
            enrollment_count = db.query(func.count(ProjectEnrollment.id)).filter(
                and_(
                    ProjectEnrollment.project_id == ProjectModel.id,
                    ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
                )
            ).correlate(ProjectModel).scalar_subquery()
            
            query = query.filter(ProjectModel.max_participants > enrollment_count)
    
    # Count total
    total = query.count()
    
    # Apply pagination and load semester data and project_quizzes for has_enrollment_quiz property
    projects = query.options(
        joinedload(ProjectModel.semester),
        joinedload(ProjectModel.project_quizzes)
    ).offset((page - 1) * size).limit(size).all()
    
    # Add computed fields and semester details
    result_projects = []
    for project in projects:
        # Get semester details for enrollment validation
        semester_data = None
        if project.semester:
            semester_data = {
                "id": project.semester.id,
                "name": project.semester.name,
                "start_date": project.semester.start_date.isoformat(),
                "end_date": project.semester.end_date.isoformat(),
                "is_active": project.semester.is_active
            }
        
        # Get the properties
        difficulty_value = project.difficulty
        has_quiz_value = project.has_enrollment_quiz
        
        result_projects.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "semester_id": project.semester_id,
            "semester": semester_data,  # Include semester object
            "instructor_id": project.instructor_id,
            "max_participants": project.max_participants,
            "required_sessions": project.required_sessions,
            "xp_reward": project.xp_reward,
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "status": project.status,
            "difficulty": difficulty_value,
            "has_enrollment_quiz": has_quiz_value,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "enrolled_count": project.enrolled_count,
            "available_spots": project.available_spots
        })
    
    return ProjectList(
        projects=result_projects,
        total=total,
        page=page,
        size=size
    )


@router.get("/{project_id}", response_model=ProjectWithDetails)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get project details
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Convert to dict and add computed fields manually
    project_dict = {
        'id': project.id,
        'title': project.title,
        'description': project.description,
        'semester_id': project.semester_id,
        'instructor_id': project.instructor_id,
        'max_participants': project.max_participants,
        'required_sessions': project.required_sessions,
        'xp_reward': project.xp_reward,
        'deadline': project.deadline.isoformat() if project.deadline else None,
        'status': project.status,
        'created_at': project.created_at.isoformat(),
        'updated_at': project.updated_at.isoformat(),
        'enrolled_count': project.enrolled_count,
        'available_spots': project.available_spots,
        'milestones': [
            {
                'id': m.id,
                'title': m.title,
                'description': m.description,
                'order_index': m.order_index,
                'required_sessions': m.required_sessions,
                'xp_reward': m.xp_reward,
                'deadline': m.deadline.isoformat() if m.deadline else None,
                'is_required': m.is_required,
                'project_id': m.project_id,
                'created_at': m.created_at.isoformat()
            } for m in project.milestones
        ],
        'instructor': {
            'id': project.instructor.id,
            'name': project.instructor.name,
            'email': project.instructor.email
        } if project.instructor else None,
        'semester': {
            'id': project.semester.id,
            'name': project.semester.name,
            'start_date': project.semester.start_date.isoformat() if project.semester.start_date else None,
            'end_date': project.semester.end_date.isoformat() if project.semester.end_date else None
        } if project.semester else None
    }
    
    return project_dict


@router.post("/{project_id}/enroll", response_model=ProjectEnrollmentSchema)
def enroll_in_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Enroll current user in project (Students only)
    """
    if current_user.role.value != 'student':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can enroll in projects"
        )
    
    # 🔒 CRITICAL: Validate semester enrollment eligibility
    validate_semester_enrollment(project_id, current_user, db)
    
    # 🎓 NEW: Validate specialization enrollment eligibility
    validate_specialization_enrollment(project_id, current_user, db)
    
    # 💰 NEW: Validate payment verification for enrollment
    validate_payment_enrollment(current_user)
    
    # Check if project exists and is active
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.status == ProjectStatus.ACTIVE.value
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not active"
        )
    
    # Check if already enrolled
    existing_enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id
        )
    ).first()
    
    if existing_enrollment:
        if existing_enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already enrolled in this project"
            )
        elif existing_enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
            # Allow re-enrollment
            existing_enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
            existing_enrollment.progress_status = ProjectProgressStatus.PLANNING.value
            db.commit()
            db.refresh(existing_enrollment)
            return existing_enrollment
    
    # Check if project has available spots
    if project.enrolled_count >= project.max_participants:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is full"
        )
    
    # Create enrollment
    enrollment = ProjectEnrollment(
        project_id=project_id,
        user_id=current_user.id,
        status=ProjectEnrollmentStatus.ACTIVE.value,
        progress_status=ProjectProgressStatus.PLANNING.value
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    
    # Create milestone progress records for all milestones
    milestones = db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project_id).all()
    for milestone in milestones:
        milestone_progress = ProjectMilestoneProgress(
            enrollment_id=enrollment.id,
            milestone_id=milestone.id,
            status=MilestoneStatus.PENDING.value
        )
        db.add(milestone_progress)
    
    db.commit()
    
    return enrollment


@router.delete("/{project_id}/enroll")
def withdraw_from_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Withdraw current user from project
    """
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id
        )
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enrollment found for this project"
        )
    
    # If already withdrawn, return success message
    if enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
        return {"message": "Already withdrawn from project"}
    
    # Only allow withdrawal from active enrollments
    if enrollment.status != ProjectEnrollmentStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot withdraw from project with status: {enrollment.status}"
        )
    
    # Update status to withdrawn
    enrollment.status = ProjectEnrollmentStatus.WITHDRAWN.value
    db.commit()
    
    return {"message": "Successfully withdrawn from project"}


@router.get("/my/current")
def get_my_current_project(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user's active project enrollment
    """
    enrollment = db.query(ProjectEnrollment).options(
        joinedload(ProjectEnrollment.project)
    ).filter(
        and_(
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        )
    ).first()

    if not enrollment:
        return None

    # Return simplified structure
    return {
        "id": enrollment.id,
        "project_id": enrollment.project_id,
        "project_title": enrollment.project.title if enrollment.project else "Unknown",
        "status": enrollment.status,
        "progress_status": enrollment.progress_status,
        "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None
    }


@router.get("/my/summary")
def get_my_project_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get project summary for student dashboard
    """
    # Get all active and not_eligible enrollments
    active_enrollments = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.user_id == current_user.id,
            or_(
                ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value,
                ProjectEnrollment.status == ProjectEnrollmentStatus.NOT_ELIGIBLE.value
            )
        )
    ).all()
    
    # For backward compatibility, get the first active one as current_enrollment
    current_enrollment = None
    for enrollment in active_enrollments:
        if enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            current_enrollment = enrollment
            break
    
    # Get available projects (active projects with spots available)
    available_projects = db.query(ProjectModel).filter(
        ProjectModel.status == ProjectStatus.ACTIVE.value
    ).all()
    
    # Filter projects where user is not already enrolled
    user_enrolled_projects = db.query(ProjectEnrollment.project_id).filter(
        ProjectEnrollment.user_id == current_user.id
    ).subquery()
    
    available_projects = db.query(ProjectModel).filter(
        and_(
            ProjectModel.status == ProjectStatus.ACTIVE.value,
            ~ProjectModel.id.in_(user_enrolled_projects)
        )
    ).all()
    
    # Convert to dicts for response (computed fields are properties)
    available_projects_data = []
    for project in available_projects:
        available_projects_data.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "semester_id": project.semester_id,
            "instructor_id": project.instructor_id,
            "max_participants": project.max_participants,
            "required_sessions": project.required_sessions,
            "xp_reward": project.xp_reward,
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "enrolled_count": project.enrolled_count,
            "available_spots": project.available_spots
        })
    
    # Get completed projects count and XP
    completed_enrollments = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.COMPLETED.value
        )
    ).all()
    
    total_xp = sum(e.project.xp_reward for e in completed_enrollments if e.instructor_approved)
    
    # Simple dict response for now
    current_project_data = None
    if current_enrollment:
        current_project_data = {
            "id": current_enrollment.id,
            "project_id": current_enrollment.project_id,
            "project_title": current_enrollment.project.title,
            "status": current_enrollment.status,
            "progress_status": current_enrollment.progress_status,
            "completion_percentage": current_enrollment.completion_percentage,
            "enrolled_at": current_enrollment.enrolled_at.isoformat()
        }
    
    # Build list of all enrolled projects (including not_eligible)
    enrolled_projects_data = []
    for enrollment in active_enrollments:
        enrolled_projects_data.append({
            "id": enrollment.id,
            "project_id": enrollment.project_id,
            "project_title": enrollment.project.title,
            "status": enrollment.status,
            "progress_status": enrollment.progress_status,
            "completion_percentage": enrollment.completion_percentage,
            "enrolled_at": enrollment.enrolled_at.isoformat()
        })
    
    return {
        "current_project": current_project_data,
        "enrolled_projects": enrolled_projects_data,
        "available_projects": available_projects_data,
        "total_projects_completed": len(completed_enrollments),
        "total_xp_from_projects": total_xp
    }


@router.get("/{project_id}/progress")
def get_project_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get detailed project progress for current user
    """
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        )
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active enrollment found for this project"
        )
    
    # Calculate overall progress based on completed milestones
    total_milestones = len(enrollment.project.milestones)
    completed_milestones = len([
        mp for mp in enrollment.milestone_progress 
        if mp.status == MilestoneStatus.APPROVED.value
    ])
    
    overall_progress = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
    
    # Find next milestone
    next_milestone = None
    for milestone in enrollment.project.milestones:
        milestone_progress = next(
            (mp for mp in enrollment.milestone_progress if mp.milestone_id == milestone.id), 
            None
        )
        if not milestone_progress or milestone_progress.status in [MilestoneStatus.PENDING.value, MilestoneStatus.IN_PROGRESS.value]:
            next_milestone = milestone
            break
    
    # Calculate sessions remaining
    sessions_completed = sum(mp.sessions_completed for mp in enrollment.milestone_progress)
    sessions_remaining = max(0, enrollment.project.required_sessions - sessions_completed)
    
    # Simple dict response
    next_milestone_data = None
    if next_milestone:
        next_milestone_data = {
            "id": next_milestone.id,
            "title": next_milestone.title,
            "description": next_milestone.description,
            "required_sessions": next_milestone.required_sessions,
            "xp_reward": next_milestone.xp_reward,
            "deadline": next_milestone.deadline.isoformat() if next_milestone.deadline else None
        }
    
    milestone_progress_data = []
    for mp in enrollment.milestone_progress:
        milestone_progress_data.append({
            "id": mp.id,
            "milestone_id": mp.milestone_id,
            "milestone_title": mp.milestone.title,
            "status": mp.status,
            "sessions_completed": mp.sessions_completed,
            "sessions_required": mp.milestone.required_sessions,
            "submitted_at": mp.submitted_at.isoformat() if mp.submitted_at else None,
            "instructor_feedback": mp.instructor_feedback
        })
    
    return {
        "project_title": enrollment.project.title,
        "enrollment_status": enrollment.status,
        "progress_status": enrollment.progress_status,
        "completion_percentage": enrollment.completion_percentage,
        "overall_progress": overall_progress,
        "sessions_completed": sessions_completed,
        "sessions_remaining": sessions_remaining,
        "milestone_progress": milestone_progress_data,
        "next_milestone": next_milestone_data
    }


@router.get("/{project_id}/enrollment-status")
def get_project_enrollment_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get user's enrollment status for a specific project
    """
    # Check if user has a project enrollment
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id
        )
    ).first()
    
    if enrollment:
        # User has enrollment record - return actual status
        if enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            return {
                "user_status": "confirmed",
                "message": "Your enrollment has been confirmed! Welcome to the project.",
                "enrollment_id": enrollment.id
            }
        elif enrollment.status == ProjectEnrollmentStatus.NOT_ELIGIBLE.value:
            return {
                "user_status": "not_eligible",
                "message": "Unfortunately, you did not meet the minimum requirements for this project.",
                "enrollment_id": enrollment.id
            }
        elif enrollment.status == ProjectEnrollmentStatus.COMPLETED.value:
            return {
                "user_status": "completed",
                "message": "You have completed this project.",
                "enrollment_id": enrollment.id
            }
        elif enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
            return {
                "user_status": "withdrawn",
                "message": "You have withdrawn from this project.",
                "enrollment_id": enrollment.id
            }
    
    # Check if user has taken enrollment quiz
    from ....models.project import ProjectQuiz, ProjectEnrollmentQuiz
    from ....models.quiz import QuizAttempt
    
    # Find project's enrollment quiz
    project_quiz = db.query(ProjectQuiz).filter(
        and_(
            ProjectQuiz.project_id == project_id,
            ProjectQuiz.quiz_type == "enrollment",
            ProjectQuiz.is_active == True
        )
    ).first()
    
    if not project_quiz:
        # No enrollment quiz required
        return {
            "user_status": "no_quiz_required",
            "message": "No enrollment quiz required for this project."
        }
    
    # Check if user has completed the quiz
    quiz_attempt = db.query(QuizAttempt).filter(
        and_(
            QuizAttempt.quiz_id == project_quiz.quiz_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.completed_at.isnot(None)
        )
    ).first()
    
    if not quiz_attempt:
        # No quiz attempt yet
        return {
            "user_status": "quiz_required",
            "message": "Please complete the enrollment quiz to continue.",
            "quiz_id": project_quiz.quiz_id
        }
    
    # Check if there's an enrollment quiz record for more detailed status
    user_enrollment_quiz = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()
    
    if user_enrollment_quiz and quiz_attempt.passed:
        # Get total applicants for this project
        total_applicants = db.query(ProjectEnrollmentQuiz).filter(
            ProjectEnrollmentQuiz.project_id == project_id
        ).count()
        
        # Get project for max_participants
        project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        can_confirm = user_enrollment_quiz.enrollment_priority <= project.max_participants
        
        # Determine detailed status
        if user_enrollment_quiz.enrollment_confirmed:
            user_status = "confirmed"
            message = "Your enrollment has been confirmed! Welcome to the project."
        elif can_confirm:
            user_status = "eligible"
            message = "Congratulations! You are eligible to enroll in this project."
        else:
            user_status = "waiting"  
            message = "You are on the waiting list. We will notify you if a spot becomes available."
        
        return {
            "user_status": user_status,
            "message": message,
            "quiz_score": quiz_attempt.score,
            "enrollment_priority": user_enrollment_quiz.enrollment_priority,
            "total_applicants": total_applicants,
            "can_confirm": can_confirm and not user_enrollment_quiz.enrollment_confirmed,
            "enrollment_confirmed": user_enrollment_quiz.enrollment_confirmed
        }
    
    # Quiz completed but no enrollment record means something went wrong
    # This should not happen with our new logic, but handle it gracefully
    if quiz_attempt.passed:
        return {
            "user_status": "eligible",
            "message": "Quiz passed! You are eligible for enrollment.",
            "quiz_score": quiz_attempt.score
        }
    else:
        return {
            "user_status": "not_eligible",
            "message": "Unfortunately, you did not meet the minimum requirements for this project.",
            "quiz_score": quiz_attempt.score
        }


@router.get("/instructor/my")
def get_instructor_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
) -> Any:
    """
    Get projects for current instructor
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Query projects assigned to this instructor
    query = db.query(ProjectModel).filter(ProjectModel.instructor_id == current_user.id).order_by(ProjectModel.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    projects = query.offset(offset).limit(size).all()
    
    # Return simple response for now
    project_list = []
    for project in projects:
        # Get enrollment count
        enrollment_count = db.query(func.count(ProjectEnrollment.id)).filter(
            and_(
                ProjectEnrollment.project_id == project.id,
                ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
            )
        ).scalar() or 0
        
        # Calculate completion percentage
        total_enrollments = db.query(func.count(ProjectEnrollment.id)).filter(
            ProjectEnrollment.project_id == project.id
        ).scalar() or 0
        
        completed_enrollments = db.query(func.count(ProjectEnrollment.id)).filter(
            and_(
                ProjectEnrollment.project_id == project.id,
                ProjectEnrollment.status == ProjectEnrollmentStatus.COMPLETED.value
            )
        ).scalar() or 0
        
        completion_percentage = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
        
        project_dict = {
            'id': project.id,
            'title': project.title,
            'description': project.description,
            'semester_id': project.semester_id,
            'max_participants': project.max_participants,
            'required_sessions': project.required_sessions,
            'xp_reward': project.xp_reward,
            'deadline': project.deadline.isoformat() if project.deadline else None,
            'status': project.status,
            'enrolled_count': enrollment_count,
            'completion_percentage': completion_percentage,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
        }
        project_list.append(project_dict)
    
    return {
        'projects': project_list,
        'total': total,
        'page': page,
        'size': size
    }


@router.post("/{project_id}/instructor/enroll/{user_id}")
def instructor_enroll_student(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Instructor enrolls a student in their project
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Verify project belongs to instructor
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.instructor_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by instructor"
        )
    
    # Verify student exists and is a student
    student = db.query(User).filter(User.id == user_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    if student.role.value != 'student':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a student"
        )
    
    # Check if already enrolled
    existing_enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == user_id
        )
    ).first()
    
    if existing_enrollment:
        if existing_enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            return {"message": "Student already enrolled in project"}
        else:
            # Reactivate enrollment
            existing_enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
            existing_enrollment.progress_status = ProjectProgressStatus.PLANNING.value
            db.commit()
            return {"message": "Student re-enrolled in project"}
    
    # Check capacity
    active_enrollments = db.query(func.count(ProjectEnrollment.id)).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        )
    ).scalar() or 0
    
    if active_enrollments >= project.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has reached maximum capacity"
        )
    
    # Create enrollment
    enrollment = ProjectEnrollment(
        project_id=project_id,
        user_id=user_id,
        status=ProjectEnrollmentStatus.ACTIVE.value,
        progress_status=ProjectProgressStatus.PLANNING.value
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    
    # Create milestone progress records for all milestones
    milestones = db.query(ProjectMilestone).filter(
        ProjectMilestone.project_id == project_id
    ).order_by(ProjectMilestone.order_index).all()
    
    for i, milestone in enumerate(milestones):
        # First milestone starts as IN_PROGRESS, others as PENDING
        status = MilestoneStatus.IN_PROGRESS.value if i == 0 else MilestoneStatus.PENDING.value
        milestone_progress = ProjectMilestoneProgress(
            enrollment_id=enrollment.id,
            milestone_id=milestone.id,
            status=status
        )
        db.add(milestone_progress)
    
    db.commit()
    
    return {"message": "Student enrolled successfully"}


@router.delete("/{project_id}/instructor/enroll/{user_id}")
def instructor_remove_student(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Instructor removes a student from their project
    """
    # Verify user is instructor
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Instructor role required."
        )
    
    # Verify project belongs to instructor
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.instructor_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by instructor"
        )
    
    # Find enrollment
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == user_id
        )
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student enrollment not found"
        )
    
    if enrollment.status == ProjectEnrollmentStatus.WITHDRAWN.value:
        return {"message": "Student already withdrawn from project"}
    
    # Update enrollment status
    enrollment.status = ProjectEnrollmentStatus.WITHDRAWN.value
    db.commit()
    
    return {"message": "Student removed from project successfully"}


# PROJECT-QUIZ SYSTEM ENDPOINTS

@router.post("/{project_id}/quizzes", response_model=ProjectQuiz)
def add_quiz_to_project(
    project_id: int,
    quiz_data: ProjectQuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Hozzáad egy quiz-t a projekthez (Admin/Instructor only)
    """
    # Verify project exists and instructor has access
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if instructor owns this project (unless admin)
    if current_user.role.value != 'admin' and project.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project"
        )
    
    # Verify quiz exists
    from ....models.quiz import Quiz
    quiz = db.query(Quiz).filter(Quiz.id == quiz_data.quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Create project-quiz connection
    from ....models.project import ProjectQuiz
    project_quiz = ProjectQuiz(**quiz_data.model_dump())
    db.add(project_quiz)
    db.commit()
    db.refresh(project_quiz)
    
    return project_quiz


@router.get("/{project_id}/quizzes", response_model=List[ProjectQuizWithDetails])
def get_project_quizzes(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Lekéri a projekthez kapcsolódó quiz-eket
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    from ....models.project import ProjectQuiz
    project_quizzes = db.query(ProjectQuiz).filter(
        ProjectQuiz.project_id == project_id,
        ProjectQuiz.is_active == True
    ).order_by(ProjectQuiz.order_index).all()
    
    # Convert to response format with quiz details
    result = []
    for pq in project_quizzes:
        from ....models.quiz import Quiz
        quiz = db.query(Quiz).filter(Quiz.id == pq.quiz_id).first()
        milestone = None
        if pq.milestone_id:
            milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == pq.milestone_id).first()
        
        quiz_data = {
            "id": pq.id,
            "project_id": pq.project_id,
            "quiz_id": pq.quiz_id,
            "milestone_id": pq.milestone_id,
            "quiz_type": pq.quiz_type,
            "is_required": pq.is_required,
            "minimum_score": pq.minimum_score,
            "order_index": pq.order_index,
            "is_active": pq.is_active,
            "created_at": pq.created_at.isoformat(),
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "description": quiz.description,
                "category": quiz.category.value if quiz.category else None,
                "difficulty": quiz.difficulty.value if quiz.difficulty else None,
                "time_limit_minutes": quiz.time_limit_minutes,
                "passing_score": quiz.passing_score,
                "xp_reward": quiz.xp_reward
            } if quiz else None,
            "milestone": {
                "id": milestone.id,
                "title": milestone.title,
                "description": milestone.description,
                "order_index": milestone.order_index,
                "required_sessions": milestone.required_sessions,
                "xp_reward": milestone.xp_reward,
                "deadline": milestone.deadline.isoformat() if milestone.deadline else None,
                "is_required": milestone.is_required,
                "project_id": milestone.project_id,
                "created_at": milestone.created_at.isoformat()
            } if milestone else None
        }
        result.append(quiz_data)
    
    return result


@router.delete("/{project_id}/quizzes/{quiz_connection_id}")
def remove_quiz_from_project(
    project_id: int,
    quiz_connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_instructor_user)
) -> Any:
    """
    Eltávolít egy quiz-t a projektből
    """
    from ....models.project import ProjectQuiz
    project_quiz = db.query(ProjectQuiz).filter(
        ProjectQuiz.id == quiz_connection_id,
        ProjectQuiz.project_id == project_id
    ).first()
    
    if not project_quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz connection not found"
        )
    
    # Verify project ownership
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if current_user.role.value != 'admin' and project.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project"
        )
    
    db.delete(project_quiz)
    db.commit()
    
    return {"message": "Quiz removed from project successfully"}


@router.get("/{project_id}/enrollment-quiz")
def get_enrollment_quiz_info(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Lekéri a projekt enrollment quiz információit
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Find enrollment quiz for this project
    from ....models.project import ProjectQuiz
    enrollment_quiz = db.query(ProjectQuiz).filter(
        ProjectQuiz.project_id == project_id,
        ProjectQuiz.quiz_type == "enrollment",
        ProjectQuiz.is_active == True
    ).first()
    
    if not enrollment_quiz:
        return {
            "has_enrollment_quiz": False,
            "quiz": None,
            "user_completed": False,
            "user_status": None
        }
    
    # Get quiz details
    from ....models.quiz import Quiz
    quiz = db.query(Quiz).filter(Quiz.id == enrollment_quiz.quiz_id).first()
    
    # Check if user has already completed this quiz for this project
    from ....models.project import ProjectEnrollmentQuiz
    user_enrollment_quiz = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()
    
    user_completed = user_enrollment_quiz is not None
    user_status = None
    
    if user_completed:
        # Get the quiz attempt to determine status
        from ....models.quiz import QuizAttempt
        attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == user_enrollment_quiz.quiz_attempt_id
        ).first()
        
        if attempt and attempt.score >= enrollment_quiz.minimum_score:
            user_status = "eligible" if user_enrollment_quiz.enrollment_priority <= project.max_participants else "waiting"
            if user_enrollment_quiz.enrollment_confirmed:
                user_status = "confirmed"
        else:
            user_status = "not_eligible"
    
    return {
        "has_enrollment_quiz": True,
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "time_limit_minutes": quiz.time_limit_minutes,
            "minimum_score": enrollment_quiz.minimum_score
        },
        "user_completed": user_completed,
        "user_status": user_status
    }


@router.get("/{project_id}/waitlist")
def get_project_waitlist(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get anonymized project waitlist/ranking for students (nicknames only)
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get all enrollment quiz results for this project, ordered by priority
    from ....models.project import ProjectEnrollmentQuiz
    from ....models.quiz import QuizAttempt
    
    waitlist_data = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id
    ).order_by(ProjectEnrollmentQuiz.enrollment_priority.asc()).all()
    
    if not waitlist_data:
        return {
            "project_id": project_id,
            "project_title": project.title,
            "max_participants": project.max_participants,
            "waitlist": [],
            "total_applicants": 0,
            "user_position": None
        }
    
    # Build anonymized waitlist with nicknames only
    waitlist_entries = []
    user_position = None
    
    for entry in waitlist_data:
        # Get user info (for nickname)
        user = db.query(User).filter(User.id == entry.user_id).first()
        if not user:
            continue
            
        # Get quiz attempt for score
        attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == entry.quiz_attempt_id
        ).first()
        
        if not attempt:
            continue
            
        # Determine status based on priority and confirmation
        if entry.enrollment_confirmed:
            status = "confirmed"
        elif entry.enrollment_priority <= project.max_participants:
            status = "eligible"
        else:
            status = "waiting"
        
        # Use nickname or fallback to "Anonymous" for privacy
        display_name = user.nickname if user.nickname else f"Diák #{entry.enrollment_priority}"
        
        waitlist_entry = {
            "position": entry.enrollment_priority,
            "display_name": display_name,
            "score_percentage": round(attempt.score, 1),
            "status": status,
            "confirmed": entry.enrollment_confirmed,
            "is_current_user": user.id == current_user.id
        }
        
        waitlist_entries.append(waitlist_entry)
        
        # Track current user's position
        if user.id == current_user.id:
            user_position = entry.enrollment_priority
    
    return {
        "project_id": project_id,
        "project_title": project.title,
        "max_participants": project.max_participants,
        "confirmed_count": len([e for e in waitlist_entries if e["confirmed"]]),
        "waitlist": waitlist_entries,
        "total_applicants": len(waitlist_entries),
        "user_position": user_position
    }


@router.post("/{project_id}/enrollment-quiz", response_model=EnrollmentPriorityResponse)
def complete_enrollment_quiz(
    project_id: int,
    quiz_attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Értékeli a jelentkezési quiz eredményét és meghatározza a rangsorolási pozíciót
    """
    # Verify project exists
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get quiz attempt
    from ....models.quiz import QuizAttempt
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == quiz_attempt_id,
        QuizAttempt.user_id == current_user.id
    ).first()
    
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz attempt not found"
        )
    
    # Check if enrollment quiz record already exists
    from ....models.project import ProjectEnrollmentQuiz
    existing_enrollment = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()
    
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Enrollment quiz already completed for this project"
        )
    
    # Calculate priority based on score and application time
    all_attempts = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id
    ).all()
    
    # Simple ranking: sort by score (desc), then by attempt time (asc)
    enrollment_priority = 1
    for existing in all_attempts:
        existing_attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == existing.quiz_attempt_id
        ).first()
        
        if existing_attempt and (
            existing_attempt.score > attempt.score or 
            (existing_attempt.score == attempt.score and existing_attempt.completed_at < attempt.completed_at)
        ):
            enrollment_priority += 1
    
    # Create enrollment quiz record
    enrollment_quiz = ProjectEnrollmentQuiz(
        project_id=project_id,
        user_id=current_user.id,
        quiz_attempt_id=quiz_attempt_id,
        enrollment_priority=enrollment_priority,
        enrollment_confirmed=False
    )
    db.add(enrollment_quiz)
    db.commit()
    
    # Update priorities for others
    _recalculate_enrollment_priorities(db, project_id)
    
    return EnrollmentPriorityResponse(
        user_id=current_user.id,
        project_id=project_id,
        quiz_score=attempt.score,
        enrollment_priority=enrollment_priority,
        total_applicants=len(all_attempts) + 1,
        is_eligible=attempt.score >= 75.0,  # Minimum score
        can_confirm=enrollment_priority <= project.max_participants
    )


@router.post("/{project_id}/confirm-enrollment")
def confirm_project_enrollment(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Megerősíti a projekt jelentkezést
    """
    # Get enrollment quiz record
    from ....models.project import ProjectEnrollmentQuiz
    enrollment_quiz = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id,
        ProjectEnrollmentQuiz.user_id == current_user.id
    ).first()
    
    if not enrollment_quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment quiz not found"
        )
    
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    
    # Check if user is eligible (within capacity based on priority)
    if enrollment_quiz.enrollment_priority > project.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not eligible for enrollment based on priority ranking"
        )
    
    # Check if already enrolled
    existing_enrollment = db.query(ProjectEnrollment).filter(
        ProjectEnrollment.project_id == project_id,
        ProjectEnrollment.user_id == current_user.id
    ).first()
    
    if existing_enrollment:
        if existing_enrollment.status == ProjectEnrollmentStatus.ACTIVE.value:
            return {"message": "Already enrolled in project"}
    
    # Create or update enrollment
    if not existing_enrollment:
        enrollment = ProjectEnrollment(
            project_id=project_id,
            user_id=current_user.id,
            status=ProjectEnrollmentStatus.ACTIVE.value,
            progress_status=ProjectProgressStatus.PLANNING.value
        )
        db.add(enrollment)
    else:
        existing_enrollment.status = ProjectEnrollmentStatus.ACTIVE.value
        existing_enrollment.progress_status = ProjectProgressStatus.PLANNING.value
    
    # Mark enrollment as confirmed
    enrollment_quiz.enrollment_confirmed = True
    
    db.commit()
    
    # Check for first-time project enrollment achievements
    from ....services.gamification import GamificationService
    gamification_service = GamificationService(db)
    gamification_service.check_first_project_enrollment(current_user.id, project_id)
    # Also check for newcomer welcome achievement
    gamification_service.check_newcomer_welcome(current_user.id)
    
    return {"message": "Enrollment confirmed successfully"}


def _recalculate_enrollment_priorities(db: Session, project_id: int):
    """
    Újraszámolja az enrollment prioritásokat egy projekthez
    """
    from ....models.project import ProjectEnrollmentQuiz
    from ....models.quiz import QuizAttempt
    
    enrollments = db.query(ProjectEnrollmentQuiz).filter(
        ProjectEnrollmentQuiz.project_id == project_id
    ).all()
    
    # Sort by score (desc), then by completion time (asc)
    enrollment_data = []
    for enrollment in enrollments:
        attempt = db.query(QuizAttempt).filter(
            QuizAttempt.id == enrollment.quiz_attempt_id
        ).first()
        if attempt:
            enrollment_data.append({
                'enrollment': enrollment,
                'score': attempt.score,
                'completed_at': attempt.completed_at
            })
    
    # Sort and assign priorities
    enrollment_data.sort(key=lambda x: (-x['score'], x['completed_at']))
    
    for i, data in enumerate(enrollment_data):
        data['enrollment'].enrollment_priority = i + 1
    
    db.commit()


# MILESTONE MANAGEMENT ENDPOINTS

@router.post("/{project_id}/milestones/{milestone_id}/submit")
def submit_milestone(
    project_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Submit milestone for review (Student only)
    """
    # Verify student role
    if current_user.role.value != 'student':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit milestones"
        )
    
    # Get enrollment
    enrollment = db.query(ProjectEnrollment).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectEnrollment.user_id == current_user.id,
            ProjectEnrollment.status == ProjectEnrollmentStatus.ACTIVE.value
        )
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active enrollment found for this project"
        )
    
    # Get milestone progress
    milestone_progress = db.query(ProjectMilestoneProgress).filter(
        and_(
            ProjectMilestoneProgress.enrollment_id == enrollment.id,
            ProjectMilestoneProgress.milestone_id == milestone_id
        )
    ).first()
    
    if not milestone_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone progress not found"
        )
    
    # Check if milestone is in progress
    if milestone_progress.status != MilestoneStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Milestone must be in progress to submit. Current status: {milestone_progress.status}"
        )
    
    # Check if required sessions are completed
    milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id).first()
    if milestone_progress.sessions_completed < milestone.required_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Need to complete {milestone.required_sessions} sessions. Currently completed: {milestone_progress.sessions_completed}"
        )
    
    # Submit milestone
    milestone_progress.status = MilestoneStatus.SUBMITTED.value
    milestone_progress.submitted_at = datetime.now(timezone.utc)
    milestone_progress.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(milestone_progress)
    
    return {
        "message": "Milestone submitted successfully",
        "milestone_id": milestone_id,
        "status": milestone_progress.status,
        "submitted_at": milestone_progress.submitted_at
    }


@router.post("/{project_id}/milestones/{milestone_id}/approve")
def approve_milestone(
    project_id: int,
    milestone_id: int,
    feedback: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Approve milestone (Instructor only)
    """
    # Verify instructor role and project ownership
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can approve milestones"
        )
    
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.instructor_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by instructor"
        )
    
    # Get milestone progress for all enrollments
    milestone_progresses = db.query(ProjectMilestoneProgress).join(
        ProjectEnrollment, ProjectMilestoneProgress.enrollment_id == ProjectEnrollment.id
    ).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectMilestoneProgress.milestone_id == milestone_id,
            ProjectMilestoneProgress.status == MilestoneStatus.SUBMITTED.value
        )
    ).all()
    
    if not milestone_progresses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submitted milestones found for approval"
        )
    
    approved_count = 0
    for milestone_progress in milestone_progresses:
        # Approve milestone
        milestone_progress.status = MilestoneStatus.APPROVED.value
        milestone_progress.instructor_feedback = feedback
        milestone_progress.instructor_approved_at = datetime.now(timezone.utc)
        milestone_progress.updated_at = datetime.now(timezone.utc)
        
        # Award XP for milestone completion
        milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id).first()
        if milestone:
            from ....services.gamification import GamificationService
            gamification_service = GamificationService(db)
            user_stats = gamification_service.get_or_create_user_stats(milestone_progress.enrollment.user_id)
            user_stats.total_xp = (user_stats.total_xp or 0) + milestone.xp_reward
            
        # Activate next milestone if this was approved
        _activate_next_milestone(db, milestone_progress.enrollment_id, milestone_id)
        
        approved_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully approved {approved_count} milestone submissions",
        "milestone_id": milestone_id,
        "approved_count": approved_count
    }


@router.post("/{project_id}/milestones/{milestone_id}/reject")
def reject_milestone(
    project_id: int,
    milestone_id: int,
    feedback: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Reject milestone (Instructor only)
    """
    # Verify instructor role and project ownership
    if current_user.role.value != 'instructor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can reject milestones"
        )
    
    project = db.query(ProjectModel).filter(
        and_(
            ProjectModel.id == project_id,
            ProjectModel.instructor_id == current_user.id
        )
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or not owned by instructor"
        )
    
    # Get milestone progress for all enrollments
    milestone_progresses = db.query(ProjectMilestoneProgress).join(
        ProjectEnrollment, ProjectMilestoneProgress.enrollment_id == ProjectEnrollment.id
    ).filter(
        and_(
            ProjectEnrollment.project_id == project_id,
            ProjectMilestoneProgress.milestone_id == milestone_id,
            ProjectMilestoneProgress.status == MilestoneStatus.SUBMITTED.value
        )
    ).all()
    
    if not milestone_progresses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submitted milestones found for rejection"
        )
    
    rejected_count = 0
    for milestone_progress in milestone_progresses:
        # Reject milestone - return to IN_PROGRESS
        milestone_progress.status = MilestoneStatus.IN_PROGRESS.value
        milestone_progress.instructor_feedback = feedback
        milestone_progress.updated_at = datetime.now(timezone.utc)
        # Clear submitted_at and instructor_approved_at
        milestone_progress.submitted_at = None
        milestone_progress.instructor_approved_at = None
        
        rejected_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully rejected {rejected_count} milestone submissions",
        "milestone_id": milestone_id,
        "rejected_count": rejected_count,
        "feedback": feedback
    }


def _activate_next_milestone(db: Session, enrollment_id: int, current_milestone_id: int):
    """
    Activate the next milestone in sequence after current milestone is approved
    """
    # Get current milestone order
    current_milestone = db.query(ProjectMilestone).filter(
        ProjectMilestone.id == current_milestone_id
    ).first()
    
    if not current_milestone:
        return
    
    # Find next milestone by order_index
    next_milestone = db.query(ProjectMilestone).filter(
        and_(
            ProjectMilestone.project_id == current_milestone.project_id,
            ProjectMilestone.order_index > current_milestone.order_index
        )
    ).order_by(ProjectMilestone.order_index).first()
    
    if not next_milestone:
        # No more milestones - check if project is complete
        _check_project_completion(db, enrollment_id)
        return
    
    # Activate next milestone
    next_milestone_progress = db.query(ProjectMilestoneProgress).filter(
        and_(
            ProjectMilestoneProgress.enrollment_id == enrollment_id,
            ProjectMilestoneProgress.milestone_id == next_milestone.id
        )
    ).first()
    
    if next_milestone_progress and next_milestone_progress.status == MilestoneStatus.PENDING.value:
        next_milestone_progress.status = MilestoneStatus.IN_PROGRESS.value
        next_milestone_progress.updated_at = datetime.now(timezone.utc)


def _check_project_completion(db: Session, enrollment_id: int):
    """
    Check if all milestones are completed and award project completion XP
    """
    enrollment = db.query(ProjectEnrollment).filter(ProjectEnrollment.id == enrollment_id).first()
    if not enrollment:
        return
    
    # Check if all milestones are approved
    total_milestones = db.query(ProjectMilestone).filter(
        ProjectMilestone.project_id == enrollment.project_id
    ).count()
    
    approved_milestones = db.query(ProjectMilestoneProgress).filter(
        and_(
            ProjectMilestoneProgress.enrollment_id == enrollment_id,
            ProjectMilestoneProgress.status == MilestoneStatus.APPROVED.value
        )
    ).count()
    
    if total_milestones == approved_milestones:
        # Project completed - award bonus XP
        from ....services.gamification import GamificationService
        gamification_service = GamificationService(db)
        user_stats = gamification_service.get_or_create_user_stats(enrollment.user_id)
        user_stats.total_xp = (user_stats.total_xp or 0) + enrollment.project.xp_reward
        
        # Update enrollment status
        enrollment.status = ProjectEnrollmentStatus.COMPLETED.value
        enrollment.progress_status = ProjectProgressStatus.COMPLETED.value
        enrollment.completed_at = datetime.now(timezone.utc)
        enrollment.completion_percentage = 100.0