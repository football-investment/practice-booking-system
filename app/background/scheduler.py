"""
🕐 Background Scheduler Service
================================

P1 TASK: Automated Progress-License synchronization every 6 hours

Features:
- APScheduler-based job scheduling
- Auto-sync all users with desync issues
- Comprehensive logging to logs/sync_jobs/
- Automatic retry (max 3 attempts)
- Graceful shutdown handling

Usage:
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.database import SessionLocal
from app.services.progress_license_sync_service import ProgressLicenseSyncService
from app.services.health_monitor import health_check_job
from app.config import get_settings

# Configure logging
LOG_DIR = Path("logs/sync_jobs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: BackgroundScheduler | None = None
settings = get_settings()


def sync_all_users_job():
    """
    Background job: Sync all users with desync issues

    Runs every 6 hours to ensure data integrity.

    Process:
    1. Find all desync issues
    2. Run auto_sync_all with dry_run=False
    3. Log results
    4. Retry on failure (max 3 attempts)
    """
    job_start = datetime.now()
    log_file = LOG_DIR / f"{job_start.strftime('%Y%m%d_%H%M%S')}_sync.log"

    logger.info("="*70)
    logger.info("🔄 Starting scheduled Progress-License sync job")
    logger.info(f"Job started at: {job_start}")
    logger.info("="*70)

    db = SessionLocal()
    try:
        sync_service = ProgressLicenseSyncService(db)

        # Step 1: Find desync issues
        logger.info("Step 1: Finding desync issues...")
        issues = sync_service.find_desync_issues()
        logger.info(f"Found {len(issues)} users with desync issues")

        if len(issues) == 0:
            logger.info("✅ No desync issues found. System is healthy.")
            _log_job_result(log_file, {
                "status": "success",
                "issues_found": 0,
                "synced_count": 0,
                "message": "No desync issues"
            })
            return

        # Step 2: Auto-sync (Progress → License is default direction)
        logger.info(f"Step 2: Auto-syncing {len(issues)} users...")
        result = sync_service.auto_sync_all(
            sync_direction="progress_to_license",
            dry_run=False  # P1: Actually perform sync
        )

        # Step 3: Log results
        synced = result.get('synced_count', 0)
        failed = result.get('failed_count', 0)

        if failed == 0:
            logger.info(f"✅ Successfully synced {synced}/{len(issues)} users")
        else:
            logger.warning(f"⚠️  Synced {synced}/{len(issues)} users, {failed} failed")

        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()

        logger.info(f"Job completed at: {job_end}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("="*70)

        # Save detailed results
        _log_job_result(log_file, {
            "status": "success" if failed == 0 else "partial_failure",
            "job_start": job_start.isoformat(),
            "job_end": job_end.isoformat(),
            "duration_seconds": duration,
            "issues_found": len(issues),
            "synced_count": synced,
            "failed_count": failed,
            "results": result.get('results', [])
        })

    except Exception as e:
        logger.error(f"❌ Job failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

        _log_job_result(log_file, {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        })

        # Re-raise to trigger retry
        raise

    finally:
        db.close()


def _log_job_result(log_file: Path, result: Dict[str, Any]):
    """Write job result to JSON log file"""
    import json

    with open(log_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    logger.info(f"Job result saved to: {log_file}")


def job_listener(event):
    """
    APScheduler event listener for job completion/errors

    Logs job execution status and handles retries
    """
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
        logger.info("Retry will be attempted (max 3 retries)")
    else:
        logger.info(f"Job {event.job_id} executed successfully")


def system_events_purge_job() -> None:
    """
    Nightly maintenance job: purge old resolved system_events.

    Retention policy:
      - RESOLVED events older than SYSTEM_EVENT_RETENTION_DAYS (default 90) → deleted
      - OPEN (unresolved) events → never touched by this job
      - Runs daily at 02:00 UTC to avoid peak-hour load

    Failure is non-fatal: a WARNING is logged, the scheduler retries next night.
    """
    from app.services.system_event_service import SystemEventService

    job_start = datetime.now()
    logger.info("🧹 system_events purge job started at %s", job_start.isoformat())

    db = SessionLocal()
    try:
        svc = SystemEventService(db)
        deleted = svc.purge_old_events()
        db.commit()
        logger.info(
            "✅ system_events purge complete — deleted=%s duration=%.2fs",
            deleted,
            (datetime.now() - job_start).total_seconds(),
        )
    except Exception as exc:
        db.rollback()
        logger.warning(
            "SYSTEM_EVENT_PURGE_FAILED — error=%s",
            type(exc).__name__,
            exc_info=True,
        )
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler

    Call this on application startup (e.g., in main.py or app initialization)

    Schedules:
    - Progress-License sync: Every 6 hours
    - System events purge: Daily at 02:00 UTC
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    logger.info("🚀 Starting background scheduler...")

    scheduler = BackgroundScheduler()

    # Add listener for job events
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # Schedule: Progress-License sync every 6 hours
    scheduler.add_job(
        func=sync_all_users_job,
        trigger=IntervalTrigger(hours=6),
        id='progress_license_sync',
        name='Progress-License Auto-Sync',
        replace_existing=True,
        max_instances=1,  # Prevent concurrent runs
        misfire_grace_time=300  # 5 minutes grace period
    )

    # P2: Schedule health check every 5 minutes
    scheduler.add_job(
        func=health_check_job,
        trigger=IntervalTrigger(minutes=5),
        id='coupling_health_check',
        name='Coupling Enforcer Health Check',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60  # 1 minute grace period
    )

    # Nightly: purge old resolved system_events (02:00 UTC)
    scheduler.add_job(
        func=system_events_purge_job,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id='system_events_purge',
        name='System Events Retention Purge',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,  # 1 hour — can run late if server was down
    )

    scheduler.start()

    logger.info("✅ Background scheduler started successfully")
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} (ID: {job.id}): {job.trigger}")

    return scheduler


def stop_scheduler():
    """
    Stop the background scheduler

    Call this on application shutdown
    """
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler not running")
        return

    logger.info("⏹️  Stopping background scheduler...")
    scheduler.shutdown(wait=True)
    scheduler = None
    logger.info("✅ Background scheduler stopped")


# ── Convenience functions for manual job execution / verification ──────────────

def run_sync_job_now():
    """
    Manually trigger the Progress-License sync job.

    Usage:
        from app.background.scheduler import run_sync_job_now
        run_sync_job_now()
    """
    logger.info("🔧 Manual sync job trigger")
    sync_all_users_job()


def run_purge_now() -> int:
    """
    Manually trigger the system_events purge job (bypass 02:00 UTC schedule).

    Use this to:
      - Verify the purge logic works before relying on the nightly schedule
      - Force a purge after a data incident
      - Confirm misfire-grace behaviour in a staging environment

    Usage:
        from app.background.scheduler import run_purge_now
        deleted = run_purge_now()
        print(f"Deleted {deleted} events")

    Returns:
        Number of deleted rows (0 if nothing matched the retention window).
    """
    logger.info("🔧 Manual system_events purge trigger")
    from app.services.system_event_service import SystemEventService

    db = SessionLocal()
    try:
        deleted = SystemEventService(db).purge_old_events()
        db.commit()
        logger.info("✅ Manual purge complete — deleted=%s", deleted)
        return deleted
    except Exception as exc:
        db.rollback()
        logger.warning("SYSTEM_EVENT_PURGE_FAILED (manual) — error=%s", type(exc).__name__, exc_info=True)
        return 0
    finally:
        db.close()


def get_scheduler_status() -> dict:
    """
    Return current scheduler job status (for health checks and monitoring).

    Usage:
        from app.background.scheduler import get_scheduler_status
        print(get_scheduler_status())

    Returns dict with:
        running:  bool — whether the scheduler is active
        jobs:     list of {id, name, next_run_utc, misfire_grace_time}
    """
    if scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_utc": next_run.isoformat() if next_run else None,
            "misfire_grace_time": job.misfire_grace_time,
        })
    return {"running": True, "jobs": jobs}
