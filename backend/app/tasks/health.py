"""Health check tasks"""

from app.celery_app import app
from app.tasks.base import SyncDocTask


@app.task(base=SyncDocTask, bind=True)
def health_check(self):
    """Test Celery worker connectivity"""
    return {
        "status": "healthy",
        "worker_name": self.request.hostname,
        "task_id": self.request.id,
    }
