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
    # Verification codes live 10 minutes; sweeping hourly is enough to keep the table from
    # accumulating unused ones without competing with the requests that read it.
    "purge-expired-email-verifications": {
        "task": "app.workers.tasks.purge_expired_email_verifications",
        "schedule": 3600.0,
    },
}
