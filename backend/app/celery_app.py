"""Celery application configuration"""

from celery import Celery

from app.core.config import settings

# Create Celery app
app = Celery("syncdoc")

# Configure from settings
app.conf.broker_url = settings.redis_url
app.conf.result_backend = settings.redis_url

# Task configuration
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.timezone = "UTC"
app.conf.enable_utc = True

# Periodic tasks (beat schedule)
app.conf.beat_schedule = {
    "auto-sync-sources": {
        "task": "app.tasks.sync.auto_sync_sources",
        "schedule": 60.0,  # Run every 60 seconds; the task itself checks which sources are due
    },
}

# Auto-discover tasks from app.tasks
app.autodiscover_tasks(["app.tasks"])


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f"Request: {self.request!r}")
