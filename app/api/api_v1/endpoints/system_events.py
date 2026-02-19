"""
System Events API — admin-only endpoints for the Rendszerüzenetek panel.

GET   /system-events                  → list with filters (level, event_type, resolved)
PATCH /system-events/{id}/resolve     → mark event as resolved
PATCH /system-events/{id}/unresolve   → reopen a resolved event
POST  /system-events/purge            → delete resolved events older than N days (default 90)
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.system_event import SystemEventLevel
from app.services.system_event_service import SystemEventService

router = APIRouter()


# ── Pydantic response schemas ─────────────────────────────────────────────────

class SystemEventResponse(BaseModel):
    id: int
    created_at: str
    level: str
    event_type: str
    user_id: Optional[int]
    role: Optional[str]
    payload_json: Optional[Dict[str, Any]]
    resolved: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_safe(cls, obj: Any) -> "SystemEventResponse":
        return cls(
            id=obj.id,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            level=obj.level.value if hasattr(obj.level, "value") else str(obj.level),
            event_type=obj.event_type,
            user_id=obj.user_id,
            role=obj.role,
            payload_json=obj.payload_json,
            resolved=obj.resolved,
        )


class SystemEventListResponse(BaseModel):
    items: List[SystemEventResponse]
    total: int
    limit: int
    offset: int


class PurgeResponse(BaseModel):
    deleted: int
    retention_days: int
    message: str


# ── Dependency ────────────────────────────────────────────────────────────────

def get_service(db: Session = Depends(get_db)) -> SystemEventService:
    return SystemEventService(db)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=SystemEventListResponse)
def list_system_events(
    level: Optional[str] = Query(None, description="Filter by level: INFO | WARNING | SECURITY"),
    event_type: Optional[str] = Query(None, description="Filter by event_type"),
    resolved: Optional[bool] = Query(None, description="True = resolved only, False = open only"),
    user_id: Optional[int] = Query(None, description="Filter by user_id"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: Any = Depends(get_current_admin_user),
    svc: SystemEventService = Depends(get_service),
) -> SystemEventListResponse:
    """List system events with optional filtering.  Admin only."""
    rows, total = svc.get_events(
        level=level,
        event_type=event_type,
        resolved=resolved,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return SystemEventListResponse(
        items=[SystemEventResponse.from_orm_safe(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{event_id}/resolve", response_model=SystemEventResponse)
def resolve_event(
    event_id: int,
    _: Any = Depends(get_current_admin_user),
    svc: SystemEventService = Depends(get_service),
    db: Session = Depends(get_db),
) -> SystemEventResponse:
    """Mark a system event as resolved.  Admin only."""
    event = svc.mark_resolved(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System event {event_id} not found.",
        )
    db.commit()
    return SystemEventResponse.from_orm_safe(event)


@router.patch("/{event_id}/unresolve", response_model=SystemEventResponse)
def unresolve_event(
    event_id: int,
    _: Any = Depends(get_current_admin_user),
    svc: SystemEventService = Depends(get_service),
    db: Session = Depends(get_db),
) -> SystemEventResponse:
    """Reopen a resolved system event.  Admin only."""
    event = svc.mark_unresolved(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System event {event_id} not found.",
        )
    db.commit()
    return SystemEventResponse.from_orm_safe(event)


@router.post("/purge", response_model=PurgeResponse)
def purge_old_events(
    retention_days: int = Query(
        90,
        ge=7,
        le=3650,
        description="Delete RESOLVED events older than this many days (default 90).",
    ),
    _: Any = Depends(get_current_admin_user),
    svc: SystemEventService = Depends(get_service),
    db: Session = Depends(get_db),
) -> PurgeResponse:
    """
    Purge resolved system events older than `retention_days` days.

    - Only RESOLVED events are deleted; open events are always kept.
    - Default retention: 90 days (SYSTEM_EVENT_RETENTION_DAYS env var).
    - Admin only.
    """
    deleted = svc.purge_old_events(retention_days=retention_days)
    db.commit()
    return PurgeResponse(
        deleted=deleted,
        retention_days=retention_days,
        message=f"Purged {deleted} resolved event(s) older than {retention_days} days.",
    )
