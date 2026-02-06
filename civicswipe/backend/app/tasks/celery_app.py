"""
Celery application configuration
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "civicswipe",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.ingestion",
        "app.tasks.summarization",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="America/Phoenix",
    enable_utc=True,

    # Task settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task

    # Result settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)

# Periodic task schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    # Federal data ingestion - every 1 hour
    "ingest-federal-hourly": {
        "task": "app.tasks.ingestion.ingest_federal_data",
        "schedule": crontab(minute=0),  # Every hour at :00
        "kwargs": {"congress": 118, "limit": 100},
    },

    # Arizona data ingestion - every 2 hours
    "ingest-arizona-every-2-hours": {
        "task": "app.tasks.ingestion.ingest_arizona_data",
        "schedule": crontab(minute=15, hour="*/2"),  # Every 2 hours at :15
        "kwargs": {"limit": 50, "pages": 2},
    },

    # Phoenix data ingestion - every 30 minutes
    "ingest-phoenix-every-30-min": {
        "task": "app.tasks.ingestion.ingest_phoenix_data",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
        "kwargs": {"days": 14, "max_events": 10},
    },

    # Summarization - every hour at :45
    "summarize-pending-hourly": {
        "task": "app.tasks.summarization.summarize_pending_measures",
        "schedule": crontab(minute=45),  # Every hour at :45
        "kwargs": {"limit": 20},
    },
}
