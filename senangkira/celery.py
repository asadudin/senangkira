"""
Celery configuration for SenangKira Django project.

This module contains the Celery application instance and configuration
for the entire SenangKira project.
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')

# Create the Celery application instance
app = Celery('senangkira')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup."""
    print(f'Request: {self.request!r}')


@app.task(bind=True)
def health_check(self):
    """Health check task for monitoring."""
    return {'status': 'healthy', 'worker_id': self.request.id}