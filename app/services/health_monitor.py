"""
Coupling Enforcer Health Monitor
==================================

Periodic integrity checker that validates Progress-License consistency
and logs violations for admin visibility.

P2 Sprint - Observability & Monitoring
Author: Claude Code
Date: 2025-10-25
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.services.progress_license_coupling import ProgressLicenseCoupler

# Setup logging
        import json

        import aiofiles

        # Find most recent violation log

        # Find most recent violation log
logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Health monitoring service for Progress-License coupling integrity.

    Responsibilities:
    - Periodic consistency validation (5-minute intervals)
    - JSON logging of violations
    - Metrics collection for admin dashboard
    """

    def __init__(self, db: Session):
        self.db = db
        self.coupler = ProgressLicenseCoupler(db)
        self.log_dir = Path("logs/integrity_checks")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def check_all_users(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run consistency validation for all users with progress records.

        Args:
            dry_run: If True, only check without logging violations

        Returns:
            {
                'timestamp': ISO timestamp,
                'total_checked': int,
                'consistent': int,
                'inconsistent': int,
                'consistency_rate': float (0-100),
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
        """
        logger.info("🔍 Starting health check for all users...")

        # Get all unique (user_id, specialization) pairs from progress table
        query = text("""
            SELECT DISTINCT student_id, specialization_id
            FROM specialization_progress
            ORDER BY student_id, specialization_id
        """)

        result = self.db.execute(query)
        user_spec_pairs = result.fetchall()

        total_checked = len(user_spec_pairs)
        consistent = 0
        inconsistent = 0
        violations = []

        for row in user_spec_pairs:
            user_id, specialization = row[0], row[1]

            # Validate consistency
            check_result = self.coupler.validate_consistency(user_id, specialization)

            if check_result['consistent']:
                consistent += 1
            else:
                inconsistent += 1
                violations.append({
                    'user_id': user_id,
                    'specialization': specialization,
                    'progress_level': check_result.get('progress_level'),
                    'license_level': check_result.get('license_level'),
                    'recommended_action': check_result.get('recommended_action', 'sync_required')
                })

        # Calculate consistency rate
        consistency_rate = (consistent / total_checked * 100) if total_checked > 0 else 100.0

        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_checked': total_checked,
            'consistent': consistent,
            'inconsistent': inconsistent,
            'consistency_rate': round(consistency_rate, 2),
            'violations': violations
        }

        # Log violations to JSON file (unless dry_run)
        if not dry_run and inconsistent > 0:
            self._log_violations(report)

        logger.info(
            f"✅ Health check complete: {consistent}/{total_checked} consistent "
            f"({consistency_rate:.1f}%)"
        )

        if inconsistent > 0:
            logger.warning(f"⚠️  Found {inconsistent} inconsistencies")

        return report

    def _log_violations(self, report: Dict[str, Any]) -> None:
        """
        Log violations to JSON file for audit trail.

        File format: logs/integrity_checks/YYYYMMDD_HHMMSS_violations.json
        """
        timestamp = datetime.utcnow()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_violations.json"
        filepath = self.log_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"📝 Violations logged to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to log violations: {str(e)}")

    async def get_latest_report_async(self) -> Dict[str, Any]:
        """
        Get the most recent health check report from logs (ASYNC).

        Production-optimized with async file I/O to prevent blocking
        under high concurrency.

        Returns:
            Latest report dict, or None if no reports exist
        """
        log_files = sorted(self.log_dir.glob("*_violations.json"), reverse=True)

        if not log_files:
            return None

        try:
            async with aiofiles.open(log_files[0], 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"❌ Failed to read latest report: {str(e)}")
            return None

    def get_latest_report(self) -> Dict[str, Any]:
        """
        DEPRECATED: Sync version for backward compatibility.
        Use get_latest_report_async() for production endpoints.
        """
        log_files = sorted(self.log_dir.glob("*_violations.json"), reverse=True)

        if not log_files:
            return None

        try:
            with open(log_files[0], 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to read latest report: {str(e)}")
            return None

    async def get_health_summary_async(self) -> Dict[str, Any]:
        """
        Get current health status summary for admin dashboard (ASYNC).

        Production-optimized version with async file I/O.

        Returns:
            {
                'status': 'healthy' | 'degraded' | 'critical',
                'last_check': ISO timestamp or None,
                'consistency_rate': float,
                'total_violations': int,
                'total_users_monitored': int,
                'requires_attention': bool
            }
        """
        latest_report = await self.get_latest_report_async()

        if not latest_report:
            # No checks run yet
            return {
                'status': 'unknown',
                'last_check': None,
                'consistency_rate': None,
                'total_violations': 0,
                'total_users_monitored': 0,
                'requires_attention': False
            }

        consistency_rate = latest_report['consistency_rate']
        total_violations = latest_report['inconsistent']
        total_users_monitored = latest_report.get('total_checked', 0)

        # Determine health status
        if consistency_rate >= 99.0:
            status = 'healthy'
            requires_attention = False
        elif consistency_rate >= 95.0:
            status = 'degraded'
            requires_attention = True
        else:
            status = 'critical'
            requires_attention = True

        return {
            'status': status,
            'last_check': latest_report['timestamp'],
            'consistency_rate': consistency_rate,
            'total_violations': total_violations,
            'total_users_monitored': total_users_monitored,
            'requires_attention': requires_attention,
            'violations': latest_report.get('violations', [])
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """
        DEPRECATED: Sync version for backward compatibility.
        Use get_health_summary_async() for production endpoints.
        """
        latest_report = self.get_latest_report()

        if not latest_report:
            return {
                'status': 'unknown',
                'last_check': None,
                'consistency_rate': None,
                'total_violations': 0,
                'total_users_monitored': 0,
                'requires_attention': False
            }

        consistency_rate = latest_report['consistency_rate']
        total_violations = latest_report['inconsistent']
        total_users_monitored = latest_report.get('total_checked', 0)

        if consistency_rate >= 99.0:
            status = 'healthy'
            requires_attention = False
        elif consistency_rate >= 95.0:
            status = 'degraded'
            requires_attention = True
        else:
            status = 'critical'
            requires_attention = True

        return {
            'status': status,
            'last_check': latest_report['timestamp'],
            'consistency_rate': consistency_rate,
            'total_violations': total_violations,
            'total_users_monitored': total_users_monitored,
            'requires_attention': requires_attention,
            'violations': latest_report.get('violations', [])
        }


def health_check_job():
    """
    Background job function: Run health check every 5 minutes.

    Called by APScheduler from app/background/scheduler.py
    """
    logger.info("🏥 Starting scheduled health check job...")

    db = SessionLocal()
    try:
        monitor = HealthMonitor(db)
        report = monitor.check_all_users(dry_run=False)

        # Log summary
        logger.info(
            f"Health check complete: {report['consistent']}/{report['total_checked']} "
            f"consistent ({report['consistency_rate']}%)"
        )

        if report['inconsistent'] > 0:
            logger.warning(
                f"⚠️  {report['inconsistent']} inconsistencies detected. "
                f"Check logs/integrity_checks/ for details."
            )
    except Exception as e:
        logger.error(f"❌ Health check job failed: {str(e)}", exc_info=True)
    finally:
        db.close()
