"""Base task class with common functionality"""

from celery import Task


class SyncDocTask(Task):
    """Base task class for SyncDoc tasks"""

    autoretry_for = (Exception,)
    max_retries = 3
    default_retry_delay = 60

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        print(f"Task {task_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        print(f"Task {task_id} retrying due to: {exc}")

    def on_success(self, result, task_id, args, kwargs):
        """Handle task success"""
        print(f"Task {task_id} completed successfully")
