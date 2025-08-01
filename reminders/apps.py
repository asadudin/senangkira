"""
Reminders App Configuration for SenangKira.
"""
from django.apps import AppConfig


class RemindersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reminders'
    verbose_name = 'Email Reminders'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        try:
            import reminders.signals  # noqa
        except ImportError:
            pass