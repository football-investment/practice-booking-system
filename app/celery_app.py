"""
Celery Application Factory

Configures Celery with Redis as broker and result backend.

Usage:
    # Start worker (from project root):
    celery -A app.celery_app worker --loglevel=info --concurrency=4

    # Start worker with dedicated queue for tournaments:
    celery -A app.celery_app worker -Q tournaments --loglevel=info

    # Monitor tasks:
    celery -A app.celery_app flower

Environment variables (override via .env or shell):
    CELERY_BROKER_URL      default: redis://localhost:6379/0
    CELERY_RESULT_BACKEND  default: redis://localhost:6379/1
"""
from celery import Celery

from app.config import settings


def create_celery() -> Celery:
    celery = Celery(
        "lfa_intern_system",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "app.tasks.tournament_tasks",
        ],
    )

    celery.conf.update(
        # Serialisation
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # Timezone
        timezone="UTC",
        enable_utc=True,
        # Result expiry (24 hours — tasks are polled immediately after generation)
        result_expires=86_400,
        # Reliability
        task_acks_late=True,               # ACK only after successful execution
        task_reject_on_worker_lost=True,   # Re-queue if worker crashes mid-task
        worker_prefetch_multiplier=1,      # One task at a time per worker thread
        # Routing: large tournament generation goes to dedicated queue
        task_routes={
            "app.tasks.tournament_tasks.generate_sessions_task": {"queue": "tournaments"},
        },
        # Queues
        task_default_queue="default",
        task_queues={
            "default": {},
            "tournaments": {},
        },
        # Rate limiting (protect DB under heavy load)
        task_annotations={
            "app.tasks.tournament_tasks.generate_sessions_task": {
                "rate_limit": "10/m",  # max 10 large-tournament generations per minute
            }
        },
    )

    return celery


celery_app = create_celery()
