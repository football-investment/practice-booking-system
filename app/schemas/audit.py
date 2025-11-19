"""
Audit Log Schemas

Pydantic models for audit log API responses.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    status_code: Optional[int] = None
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    """Response schema for paginated list of audit logs"""
    logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int


class AuditStatisticsResponse(BaseModel):
    """Response schema for audit statistics"""
    total_logs: int
    unique_users: int
    failed_logins: int
    action_counts: Dict[str, int]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
