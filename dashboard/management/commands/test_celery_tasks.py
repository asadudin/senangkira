"""
Management command to test Celery task execution and monitoring.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from dashboard.tasks import (
    refresh_dashboard_cache, 
    warm_dashboard_cache, 
    performance_analysis,
    debug_task
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Test Celery task execution and monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            default='all',
            help='Task to run: debug, refresh, warm, performance, all'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID for user-specific tasks'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run task synchronously (for testing)'
        )

    def handle(self, *args, **options):
        task_name = options['task']
        user_id = options['user_id']
        sync = options['sync']
        
        # Get a test user if needed
        if not user_id:
            user = User.objects.first()
            if user:
                user_id = user.id
                self.stdout.write(f"Using user ID: {user_id}")
            else:
                self.stdout.write(
                    self.style.WARNING('No users found. Some tasks may fail.')
                )
        
        try:
            if task_name == 'all':
                self.test_all_tasks(user_id, sync)
            elif task_name == 'debug':
                self.test_debug_task(sync)
            elif task_name == 'refresh':
                self.test_refresh_task(user_id, sync)
            elif task_name == 'warm':
                self.test_warm_task(user_id, sync)
            elif task_name == 'performance':
                self.test_performance_task(sync)
            else:
                self.stdout.write(self.style.ERROR(f"Unknown task: {task_name}"))
                return
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running task {task_name}: {e}')
            )

    def test_all_tasks(self, user_id, sync):
        """Test all Celery tasks."""
        self.stdout.write("Testing all Celery tasks...")
        
        # Test debug task
        self.test_debug_task(sync)
        
        # Test refresh task
        self.test_refresh_task(user_id, sync)
        
        # Test warm task
        self.test_warm_task(user_id, sync)
        
        # Test performance task
        self.test_performance_task(sync)
        
        self.stdout.write(
            self.style.SUCCESS('All tasks completed successfully')
        )

    def test_debug_task(self, sync):
        """Test debug task."""
        self.stdout.write("Running debug task...")
        
        if sync:
            result = debug_task()
            self.stdout.write(f"Debug task result (sync): {result}")
        else:
            result = debug_task.delay()
            self.stdout.write(f"Debug task queued: {result.id}")

    def test_refresh_task(self, user_id, sync):
        """Test dashboard cache refresh task."""
        self.stdout.write(f"Running refresh task for user {user_id}...")
        
        if sync:
            result = refresh_dashboard_cache(user_id=user_id)
            self.stdout.write(f"Refresh task result (sync): {result}")
        else:
            result = refresh_dashboard_cache.delay(user_id=user_id)
            self.stdout.write(f"Refresh task queued: {result.id}")

    def test_warm_task(self, user_id, sync):
        """Test dashboard cache warm task."""
        self.stdout.write(f"Running warm task for user {user_id}...")
        
        if sync:
            result = warm_dashboard_cache(user_id=user_id)
            self.stdout.write(f"Warm task result (sync): {result}")
        else:
            result = warm_dashboard_cache.delay(user_id=user_id)
            self.stdout.write(f"Warm task queued: {result.id}")

    def test_performance_task(self, sync):
        """Test performance analysis task."""
        self.stdout.write("Running performance analysis task...")
        
        if sync:
            result = performance_analysis()
            self.stdout.write(f"Performance task result (sync): {result}")
        else:
            result = performance_analysis.delay()
            self.stdout.write(f"Performance task queued: {result.id}")