"""
Management command to run continuous task monitoring.
Records system metrics and performs health checks.
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from monitoring.services.task_monitor import task_monitoring_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Continuously monitor Celery tasks and record system metrics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Monitoring interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once instead of continuously'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting task monitoring (interval: {interval}s)')
        )
        
        if run_once:
            self._record_metrics()
        else:
            self._continuous_monitoring(interval)
    
    def _continuous_monitoring(self, interval):
        """Run continuous monitoring loop."""
        while True:
            try:
                self._record_metrics()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Monitoring stopped by user'))
                break
            except Exception as e:
                logger.error(f'Error in monitoring loop: {e}')
                self.stdout.write(
                    self.style.ERROR(f'Monitoring error: {e}')
                )
                time.sleep(interval)  # Continue despite errors
    
    def _record_metrics(self):
        """Record system metrics."""
        try:
            start_time = time.time()
            
            # Record system health metrics
            metric = task_monitoring_service.record_system_metrics()
            
            # Get current health status
            health = task_monitoring_service.get_system_health()
            
            duration = time.time() - start_time
            
            self.stdout.write(
                f'[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                f'Recorded metrics (ID: {metric.id}) - '
                f'Status: {health.get("status", "unknown")} - '
                f'Duration: {duration:.3f}s'
            )
            
            # Log health warnings
            if health.get('status') in ['warning', 'critical']:
                self.stdout.write(
                    self.style.WARNING(f'Health warning: {health.get("message", "")}')
                )
                
        except Exception as e:
            logger.error(f'Failed to record metrics: {e}')
            self.stdout.write(
                self.style.ERROR(f'Failed to record metrics: {e}')
            )