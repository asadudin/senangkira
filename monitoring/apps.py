"""
Django app configuration for monitoring.
"""
from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Task Monitoring'

    def ready(self):
        """Initialize monitoring signals and services."""
        try:
            # Import signals to register them
            from . import signals
        except ImportError:
            pass