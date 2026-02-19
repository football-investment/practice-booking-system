"""
Instructor project management.

This module provides:
- Instructor project listing
- Student enrollment management by instructors
- Student removal from projects
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from .....database import get_db
from .....dependencies import get_current_user
from .....models.user import User
from .....models.project import (
    Project as ProjectModel, 
    ProjectEnrollment,
    ProjectMilestone,
    ProjectMilestoneProgress,
    ProjectEnrollmentStatus,
    ProjectProgressStatus,
    MilestoneStatus
)

router = APIRouter()


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
