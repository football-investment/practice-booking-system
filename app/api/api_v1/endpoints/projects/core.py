"""
Core project CRUD operations.

This module provides:
- Create new projects
- List projects with filtering
- Get project details
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_

from .....database import get_db
from .....dependencies import get_current_user, get_current_admin_or_instructor_user
from .....models.user import User
from .....models.semester import Semester
from .....models.project import (
    Project as ProjectModel, 
    ProjectEnrollment,
    ProjectMilestone,
    ProjectStatus,
    ProjectEnrollmentStatus
)
from .....schemas.project import (
    Project as ProjectSchema,
    ProjectCreate,
    ProjectList,
    ProjectWithDetails
)

router = APIRouter()


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
    
    # OPTIMIZED: Apply pagination and eager load relationships to avoid N+1 query pattern
    projects = query.options(
        joinedload(ProjectModel.semester),
        joinedload(ProjectModel.instructor),
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
