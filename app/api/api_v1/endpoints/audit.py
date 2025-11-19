"""
Audit Log API Endpoints

Provides access to audit logs for users and administrators.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ....database import get_db
from ....dependencies import get_current_user, get_current_admin_user
from ....models.user import User, UserRole
from ....models.audit_log import AuditLog
from ....services.audit_service import AuditService
from ....schemas.audit import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditStatisticsResponse
)


router = APIRouter()


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Dependency to get AuditService instance"""
    return AuditService(db)


@router.get("/my-logs", response_model=AuditLogListResponse)
async def get_my_audit_logs(
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get audit logs for the current user.

    Returns a list of all actions performed by the authenticated user.
    Users can only see their own audit logs.

    Query Parameters:
    - limit: Maximum number of results (1-1000, default 100)
    - offset: Pagination offset
    - action: Filter by specific action type (e.g., "LOGIN", "LICENSE_ISSUED")
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    """
    logs = audit_service.get_user_logs(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
        action=action
    )

    # Get total count for pagination
    from sqlalchemy import func
    from ....models.audit_log import AuditLog
    db = audit_service.db
    total = db.query(func.count(AuditLog.id)).filter(
        AuditLog.user_id == current_user.id
    ).scalar()

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/logs", response_model=AuditLogListResponse)
async def get_all_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[int] = Query(None, description="Filter by resource ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_admin_user),  # Admin only
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Search and filter audit logs (Admin only).

    Administrators can search all audit logs with various filters.
    This is a powerful tool for security monitoring and compliance.

    Query Parameters:
    - user_id: Filter by specific user
    - action: Filter by action type
    - resource_type: Filter by resource type (e.g., "license", "project")
    - resource_id: Filter by specific resource ID
    - ip_address: Filter by IP address
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    - limit: Maximum number of results (1-1000, default 100)
    - offset: Pagination offset

    Security: Requires ADMIN role
    """
    logs = audit_service.search_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    # Get total count for pagination
    from sqlalchemy import func, and_
    from ....models.audit_log import AuditLog
    db = audit_service.db
    query = db.query(func.count(AuditLog.id))

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        query = query.filter(AuditLog.resource_id == resource_id)
    if ip_address:
        query = query.filter(AuditLog.ip_address == ip_address)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    total = query.scalar()

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user: User = Depends(get_current_admin_user),  # Admin only
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get audit log statistics (Admin only).

    Returns aggregate statistics about audit logs:
    - Total number of logs
    - Number of unique users
    - Failed login attempts
    - Breakdown by action type

    Query Parameters:
    - start_date: Start of date range (optional)
    - end_date: End of date range (optional)

    Security: Requires ADMIN role
    """
    stats = audit_service.get_statistics(
        start_date=start_date,
        end_date=end_date
    )

    return AuditStatisticsResponse(**stats)


@router.get("/security-events", response_model=AuditLogListResponse)
async def get_security_events(
    hours: int = Query(24, ge=1, le=168, description="Look back N hours (max 7 days)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    current_user: User = Depends(get_current_admin_user),  # Admin only
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get recent security-related events (Admin only).

    Returns audit logs for security-sensitive actions:
    - Failed login attempts
    - Password changes
    - Password resets
    - User role changes
    - Admin access

    Query Parameters:
    - hours: Number of hours to look back (1-168, default 24)
    - limit: Maximum number of results (1-1000, default 100)

    Security: Requires ADMIN role
    """
    logs = audit_service.get_security_events(
        hours=hours,
        limit=limit
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=len(logs),
        limit=limit,
        offset=0
    )


@router.get("/failed-logins", response_model=AuditLogListResponse)
async def get_failed_login_attempts(
    hours: int = Query(24, ge=1, le=168, description="Look back N hours (max 7 days)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    current_user: User = Depends(get_current_admin_user),  # Admin only
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get recent failed login attempts (Admin only).

    Returns audit logs for failed authentication attempts.
    Useful for detecting brute force attacks or unauthorized access attempts.

    Query Parameters:
    - hours: Number of hours to look back (1-168, default 24)
    - limit: Maximum number of results (1-1000, default 100)

    Security: Requires ADMIN role
    """
    logs = audit_service.get_failed_logins(
        hours=hours,
        limit=limit
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=len(logs),
        limit=limit,
        offset=0
    )


@router.get("/resource/{resource_type}/{resource_id}", response_model=AuditLogListResponse)
async def get_resource_audit_logs(
    resource_type: str,
    resource_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_admin_user),  # Admin only
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Get audit logs for a specific resource (Admin only).

    Returns all audit logs related to a specific resource.
    Useful for tracking the complete history of a license, project, etc.

    Path Parameters:
    - resource_type: Type of resource (e.g., "license", "project", "user")
    - resource_id: ID of the resource

    Query Parameters:
    - limit: Maximum number of results (1-1000, default 100)
    - offset: Pagination offset

    Security: Requires ADMIN role
    """
    logs = audit_service.get_resource_logs(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset
    )

    # Get total count
    from sqlalchemy import func, and_
    from ....models.audit_log import AuditLog
    db = audit_service.db
    total = db.query(func.count(AuditLog.id)).filter(
        and_(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )
    ).scalar()

    return AuditLogListResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset
    )
