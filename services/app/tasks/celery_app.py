import os
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

app = Celery(
    "value_partner",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Discover tasks within the services.app.tasks package
app.autodiscover_tasks(["services.app.tasks"])

app.conf.beat_schedule = {
    "nightly-data-download": {
        "task": "services.app.tasks.data_acquisition.nightly_download",
        "schedule": 60 * 60 * 24,  # every 24h
        "options": {"queue": "data_acquisition"},
    },
}