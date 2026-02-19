"""
Audit Service

Centralized service for logging and querying audit events.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models.audit_log import AuditLog, AuditAction


class AuditService:
    """
    Service for managing audit logs.

    Provides methods to:
    - Log audit events
    - Query audit logs with various filters
    - Generate audit reports
    """

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> AuditLog:
        """
        Log an audit event.

        Args:
            action: Action type (use AuditAction constants)
            user_id: ID of user who performed the action
            resource_type: Type of resource affected (e.g., "user", "license", "project")
            resource_id: ID of the affected resource
            details: Additional context as JSON
            ip_address: IP address of the request
            user_agent: User agent string
            request_method: HTTP method (GET, POST, etc.)
            request_path: Request URL path
            status_code: HTTP response status code

        Returns:
            Created AuditLog entry
        """
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            status_code=status_code
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User ID to query
            limit: Maximum number of results
            offset: Pagination offset
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            action: Filter by specific action type

        Returns:
            List of AuditLog entries
        """
        query = self.db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if action:
            query = query.filter(AuditLog.action == action)

        return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    def get_logs_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """
        Get audit logs by action type.

        Args:
            action: Action type to filter
            limit: Maximum number of results
            offset: Pagination offset
            start_date: Filter logs after this date
            end_date: Filter logs before this date

        Returns:
            List of AuditLog entries
        """
        query = self.db.query(AuditLog).filter(AuditLog.action == action)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    def get_resource_logs(
        self,
        resource_type: str,
        resource_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get all audit logs for a specific resource.

        Args:
            resource_type: Type of resource (e.g., "user", "license")
            resource_id: ID of the resource
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of AuditLog entries
        """
        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )
        ).order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    def get_recent_logs(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get recent audit logs from the last N hours.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of results

        Returns:
            List of AuditLog entries
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return self.db.query(AuditLog).filter(
            AuditLog.timestamp >= cutoff
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_failed_logins(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get recent failed login attempts.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of results

        Returns:
            List of failed login AuditLog entries
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.action == AuditAction.LOGIN_FAILED,
                AuditLog.timestamp >= cutoff
            )
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_logs_by_ip(
        self,
        ip_address: str,
        limit: int = 100,
        hours: int = 24
    ) -> List[AuditLog]:
        """
        Get audit logs from a specific IP address.

        Args:
            ip_address: IP address to query
            limit: Maximum number of results
            hours: Number of hours to look back

        Returns:
            List of AuditLog entries
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.ip_address == ip_address,
                AuditLog.timestamp >= cutoff
            )
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_security_events(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get security-related audit logs (failed logins, unauthorized access, etc.).

        Args:
            hours: Number of hours to look back
            limit: Maximum number of results

        Returns:
            List of security-related AuditLog entries
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        security_actions = [
            AuditAction.LOGIN_FAILED,
            AuditAction.PASSWORD_CHANGE,
            AuditAction.PASSWORD_RESET,
            AuditAction.USER_ROLE_CHANGED,
            AuditAction.ADMIN_ACCESS
        ]

        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.action.in_(security_actions),
                AuditLog.timestamp >= cutoff
            )
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(AuditLog)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        total_logs = query.count()

        # Count by action
        action_counts = self.db.query(
            AuditLog.action,
            func.count(AuditLog.id)
        ).filter(
            query.whereclause if query.whereclause is not None else True
        ).group_by(AuditLog.action).all()

        # Count unique users
        unique_users = self.db.query(
            func.count(func.distinct(AuditLog.user_id))
        ).filter(
            query.whereclause if query.whereclause is not None else True
        ).scalar()

        # Count failed logins
        failed_logins = query.filter(
            AuditLog.action == AuditAction.LOGIN_FAILED
        ).count()

        return {
            "total_logs": total_logs,
            "unique_users": unique_users,
            "failed_logins": failed_logins,
            "action_counts": {action: count for action, count in action_counts},
            "start_date": start_date,
            "end_date": end_date
        }

    def search_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Search audit logs with multiple filters.

        Args:
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            ip_address: Filter by IP address
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of AuditLog entries matching filters
        """
        query = self.db.query(AuditLog)

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

        return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
