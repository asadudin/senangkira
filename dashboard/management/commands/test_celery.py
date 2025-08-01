"""
Management command to test Celery setup and task execution.
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
    help = 'Test Celery setup by running dashboard tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            default='debug',
            help='Task to run: debug, refresh, warm, performance'
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
        
        self.stdout.write(f"Running task: {task_name}")
        
        try:
            if task_name == 'debug':
                if sync:
                    result = debug_task()
                    self.stdout.write(f"Debug task result (sync): {result}")
                else:
                    result = debug_task.delay()
                    self.stdout.write(f"Debug task queued: {result.id}")
                    
            elif task_name == 'refresh':
                if sync:
                    result = refresh_dashboard_cache(user_id=user_id)
                    self.stdout.write(f"Refresh task result (sync): {result}")
                else:
                    result = refresh_dashboard_cache.delay(user_id=user_id)
                    self.stdout.write(f"Refresh task queued: {result.id}")
                    
            elif task_name == 'warm':
                if sync:
                    result = warm_dashboard_cache(user_id=user_id)
                    self.stdout.write(f"Warm task result (sync): {result}")
                else:
                    result = warm_dashboard_cache.delay(user_id=user_id)
                    self.stdout.write(f"Warm task queued: {result.id}")
                    
            elif task_name == 'performance':
                if sync:
                    result = performance_analysis()
                    self.stdout.write(f"Performance task result (sync): {result}")
                else:
                    result = performance_analysis.delay()
                    self.stdout.write(f"Performance task queued: {result.id}")
                    
            else:
                self.stdout.write(self.style.ERROR(f"Unknown task: {task_name}"))
                return
                
            if not sync:
                self.stdout.write(
                    self.style.SUCCESS(f'Task {task_name} queued successfully')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running task {task_name}: {e}')
            )