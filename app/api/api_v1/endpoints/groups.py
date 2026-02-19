from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_user
from ....models.user import User
from ....models.semester import Semester
from ....models.group import Group
from ....models.session import Session as SessionTypel
from ....models.booking import Booking
from ....schemas.group import (
    Group as GroupSchema, GroupCreate, GroupUpdate, GroupWithRelations,
    GroupWithStats, GroupList, GroupUserAdd
)

router = APIRouter()


@router.post("/", response_model=GroupSchema)
def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Create new group (Admin only)
    """
    # Check if semester exists
    semester = db.query(Semester).filter(Semester.id == group_data.semester_id).first()
    if not semester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Semester not found"
        )
    
    group = Group(**group_data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return group


@router.get("/", response_model=GroupList)
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    semester_id: Optional[int] = Query(None)
) -> Any:
    """
    List groups with optional filtering by semester
    """
    query = db.query(Group)
    
    if semester_id:
        query = query.filter(Group.semester_id == semester_id)
    
    groups = query.all()
    
    group_stats = []
    for group in groups:
        # Calculate statistics
        user_count = db.query(func.count(User.id)).join(Group.users).filter(Group.id == group.id).scalar() or 0
        session_count = db.query(func.count(SessionTypel.id)).filter(SessionTypel.group_id == group.id).scalar() or 0
        total_bookings = db.query(func.count(Booking.id)).join(SessionTypel).filter(SessionTypel.group_id == group.id).scalar() or 0
        
        group_stats.append(GroupWithStats(
            **group.__dict__,
            semester=group.semester,
            user_count=user_count,
            session_count=session_count,
            total_bookings=total_bookings
        ))
    
    return GroupList(
        groups=group_stats,
        total=len(group_stats)
    )


@router.get("/{group_id}", response_model=GroupWithRelations)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get group by ID with relations
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    return GroupWithRelations(
        **group.__dict__,
        semester=group.semester,
        users=group.users
    )


@router.patch("/{group_id}", response_model=GroupSchema)
def update_group(
    group_id: int,
    group_update: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Update group (Admin only)
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if new semester exists if semester_id is being updated
    if group_update.semester_id and group_update.semester_id != group.semester_id:
        semester = db.query(Semester).filter(Semester.id == group_update.semester_id).first()
        if not semester:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Semester not found"
            )
    
    # Update fields
    update_data = group_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    
    return group


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Delete group (Admin only)
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Check if there are any sessions in this group
    session_count = db.query(func.count(SessionTypel.id)).filter(SessionTypel.group_id == group_id).scalar()
    if session_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete group with existing sessions"
        )
    
    db.delete(group)
    db.commit()
    
    return {"message": "Group deleted successfully"}


@router.post("/{group_id}/users")
def add_user_to_group(
    group_id: int,
    user_data: GroupUserAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Add user to group (Admin only)
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    user = db.query(User).filter(User.id == user_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already in group
    if user in group.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already in this group"
        )
    
    group.users.append(user)
    db.commit()
    
    return {"message": "User added to group successfully"}


@router.delete("/{group_id}/users/{user_id}")
def remove_user_from_group(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Any:
    """
    Remove user from group (Admin only)
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is in group
    if user not in group.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not in this group"
        )
    
    group.users.remove(user)
    db.commit()
    
    return {"message": "User removed from group successfully"}