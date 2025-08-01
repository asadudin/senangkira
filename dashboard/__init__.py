"""
Celery App Configuration for Dashboard Module

This module sets up the Celery app for the dashboard Django application.
"""

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)