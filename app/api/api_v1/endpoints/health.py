"""
Health Monitoring API Endpoints
================================

Admin endpoints for Progress-License coupling health monitoring.

P2 Sprint - Observability & Monitoring
Author: Claude Code
Date: 2025-10-25
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.health_monitor import HealthMonitor
from app.services.redis_cache import cache
from app.models.user import User
from app.api.deps import require_admin


router = APIRouter()


@router.get("/status", response_model=Dict[str, Any])
async def get_health_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get current health status summary (admin only)

    PRODUCTION-OPTIMIZED:
    - Async file I/O
    - Redis cache with 30s TTL

    Returns:
        {
            'status': 'healthy' | 'degraded' | 'critical',
            'last_check': ISO timestamp or None,
            'consistency_rate': float,
            'total_violations': int,
            'requires_attention': bool,
            'violations': [...]  # Only if violations exist
        }

    Permissions:
        - ADMIN role required
    """
    try:
        # Try cache first
        cache_key = "health:status"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Cache miss - fetch from DB
        monitor = HealthMonitor(db)
        summary = await monitor.get_health_summary_async()

        # Cache for 30 seconds
        cache.set(cache_key, summary, ttl=30)

        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve health status: {str(e)}"
        )


@router.get("/latest-report", response_model=Dict[str, Any])
async def get_latest_health_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get the most recent health check report (admin only)

    PRODUCTION-OPTIMIZED: Uses async file I/O.

    Returns:
        {
            'timestamp': ISO timestamp,
            'total_checked': int,
            'consistent': int,
            'inconsistent': int,
            'consistency_rate': float,
            'violations': [
                {
                    'user_id': int,
                    'specialization': str,
                    'progress_level': int,
                    'license_level': int,
                    'recommended_action': str
                },
                ...
            ]
        }

    Permissions:
        - ADMIN role required
    """
    try:
        monitor = HealthMonitor(db)
        report = await monitor.get_latest_report_async()

        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No health reports available yet. The first check runs in 5 minutes."
            )

        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest report: {str(e)}"
        )


@router.post("/check-now", response_model=Dict[str, Any])
def run_health_check_now(
    dry_run: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Manually trigger health check (admin only)

    Args:
        dry_run: If true, only check without logging violations

    Returns:
        Full health check report (same format as /latest-report)

    Permissions:
        - ADMIN role required

    Use Cases:
        - Manual integrity verification after bulk operations
        - Testing health monitoring functionality
        - Emergency diagnostics
    """
    try:
        monitor = HealthMonitor(db)
        report = monitor.check_all_users(dry_run=dry_run)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/violations", response_model=List[Dict[str, Any]])
async def get_current_violations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get list of current consistency violations (admin only)

    PRODUCTION-OPTIMIZED: Uses async file I/O.

    Returns:
        [
            {
                'user_id': int,
                'specialization': str,
                'progress_level': int,
                'license_level': int,
                'recommended_action': str
            },
            ...
        ]

    Permissions:
        - ADMIN role required
    """
    try:
        monitor = HealthMonitor(db)
        summary = await monitor.get_health_summary_async()

        if not summary.get('violations'):
            return []

        return summary['violations']
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve violations: {str(e)}"
        )


@router.get("/metrics", response_model=Dict[str, Any])
async def get_health_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get aggregated health metrics for dashboard (admin only)

    PRODUCTION-OPTIMIZED:
    - Async file I/O
    - Redis cache with 30s TTL

    Returns:
        {
            'consistency_rate': float,
            'total_users_monitored': int,
            'violations_count': int,
            'status': 'healthy' | 'degraded' | 'critical',
            'last_check': ISO timestamp,
            'uptime_percentage': float,  # Future: track check success rate
        }

    Permissions:
        - ADMIN role required
    """
    try:
        # Try cache first
        cache_key = "health:metrics"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Cache miss - fetch from DB
        monitor = HealthMonitor(db)
        summary = await monitor.get_health_summary_async()

        # Add total monitored users from latest report
        latest_report = await monitor.get_latest_report_async()

        # Extract metrics with all required fields
        metrics = {
            'consistency_rate': summary.get('consistency_rate'),
            'violations_count': summary.get('total_violations', 0),
            'status': summary.get('status'),
            'last_check': summary.get('last_check'),
            'requires_attention': summary.get('requires_attention', False)
        }

        # Add fields from latest report
        if latest_report:
            metrics['total_users'] = latest_report.get('total_checked', 0)
            metrics['consistent'] = latest_report.get('consistent', 0)
            metrics['inconsistent'] = latest_report.get('inconsistent', 0)
            metrics['total_users_monitored'] = latest_report.get('total_checked', 0)
        else:
            metrics['total_users'] = 0
            metrics['consistent'] = 0
            metrics['inconsistent'] = 0
            metrics['total_users_monitored'] = 0

        # Cache for 30 seconds
        cache.set(cache_key, metrics, ttl=30)

        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )
