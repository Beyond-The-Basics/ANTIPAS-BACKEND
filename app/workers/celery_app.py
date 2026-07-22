from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "kickoff",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    timezone="UTC",
)

# Periodically expire stale listings (72h default). Runs every 10 minutes.
celery_app.conf.beat_schedule = {
    "expire-stale-listings": {
        "task": "app.workers.tasks.expire_stale_listings",
        "schedule": 600.0,
    },
}
