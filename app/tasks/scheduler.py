"""
Background Scheduler for Periodic Tasks
Uses APScheduler for cron-like job scheduling
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging

from app.database import SessionLocal
from app.services.adaptive_learning_service import AdaptiveLearningService

logger = logging.getLogger(__name__)


def create_daily_snapshots_for_all_users():
    """
    Create daily performance snapshots for all active users
    Runs at midnight every day (00:00)
    """
    logger.info(f"🕐 Starting daily snapshot creation at {datetime.now()}")

    db: Session = SessionLocal()

    try:
        # Get all active students who have started learning
        active_users = db.execute(text("""
            SELECT DISTINCT u.id
            FROM users u
            JOIN user_lesson_progress ulp ON ulp.user_id = u.id
            WHERE u.is_active = true
                AND u.role = 'STUDENT'
                AND ulp.started_at IS NOT NULL
        """)).fetchall()

        service = AdaptiveLearningService(db)

        success_count = 0
        error_count = 0

        for user_row in active_users:
            user_id = user_row.id
            try:
                service.create_daily_snapshot(user_id)
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to create snapshot for user {user_id}: {e}")
                error_count += 1

        logger.info(f"✅ Daily snapshots completed: {success_count} success, {error_count} errors")

    except Exception as e:
        logger.error(f"❌ Critical error in daily snapshot job: {e}")
    finally:
        db.close()


def refresh_all_recommendations():
    """
    Refresh recommendations for all active users weekly
    Runs every Monday at 06:00
    """
    logger.info(f"🔄 Starting weekly recommendation refresh at {datetime.now()}")

    db: Session = SessionLocal()

    try:
        # Get all active students
        active_users = db.execute(text("""
            SELECT DISTINCT u.id
            FROM users u
            JOIN user_lesson_progress ulp ON ulp.user_id = u.id
            WHERE u.is_active = true
                AND u.role = 'STUDENT'
        """)).fetchall()

        service = AdaptiveLearningService(db)

        success_count = 0
        error_count = 0

        for user_row in active_users:
            user_id = user_row.id
            try:
                service.generate_recommendations(
                    user_id=user_id,
                    refresh=True
                )
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to refresh recommendations for user {user_id}: {e}")
                error_count += 1

        logger.info(f"✅ Weekly recommendation refresh completed: {success_count} success, {error_count} errors")

    except Exception as e:
        logger.error(f"❌ Critical error in weekly recommendation job: {e}")
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler for periodic tasks

    Jobs:
    - Daily snapshot creation (every day at 00:00)
    - Weekly recommendation refresh (every Monday at 06:00)
    """
    scheduler = BackgroundScheduler()

    # Job 1: Daily snapshot creation at midnight (00:00)
    scheduler.add_job(
        create_daily_snapshots_for_all_users,
        trigger=CronTrigger(hour=0, minute=0),  # Every day at 00:00
        id='daily_snapshots',
        name='Create daily performance snapshots',
        replace_existing=True
    )

    # Job 2: Weekly recommendation refresh (every Monday at 06:00)
    scheduler.add_job(
        refresh_all_recommendations,
        trigger=CronTrigger(day_of_week='mon', hour=6, minute=0),  # Every Monday at 06:00
        id='weekly_recommendations',
        name='Refresh weekly recommendations',
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Background scheduler started successfully")
    logger.info("📅 Jobs scheduled:")
    logger.info("   - Daily snapshots: Every day at 00:00")
    logger.info("   - Weekly recommendations: Every Monday at 06:00")

    return scheduler
