"""
Celery App Configuration for Dashboard Tasks

This module sets up the Celery app specifically for dashboard-related tasks.
It includes task definitions and integration with the caching system.
"""

import os
import logging
from datetime import timedelta
from celery import Celery
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')

# Create Celery instance
app = Celery('dashboard')

# Configure Celery with Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Get logger
logger = logging.getLogger(__name__)
User = get_user_model()

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery setup."""
    print(f'Request: {self.request!r}')
    return f'Request: {self.request!r}'

# Task registration for dashboard operations
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for dashboard maintenance."""
    # Schedule dashboard cache refresh every hour
    sender.add_periodic_task(
        3600.0,
        refresh_dashboard_cache.s(),
        name='Refresh dashboard cache every hour'
    )
    
    # Schedule cache warming daily
    sender.add_periodic_task(
        86400.0,
        warm_dashboard_cache.s(),
        name='Warm dashboard cache daily'
    )
    
    # Schedule performance analysis every 6 hours
    sender.add_periodic_task(
        21600.0,
        performance_analysis.s(),
        name='Performance analysis every 6 hours'
    )

@app.task(bind=True, max_retries=3)
def refresh_dashboard_cache(self, user_id=None):
    """
    Refresh dashboard cache for a specific user or all users.
    
    Args:
        user_id (int, optional): Specific user ID to refresh. If None, refresh all users.
    """
    try:
        from .cache_advanced import get_advanced_cache_manager
        from .services_optimized import OptimizedDashboardCacheService
        
        if user_id:
            # Refresh for specific user
            try:
                user = User.objects.get(id=user_id)
                cache_manager = get_advanced_cache_manager(user)
                cache_service = OptimizedDashboardCacheService(user)
                
                # Force refresh dashboard cache
                cache_service.refresh_dashboard_cache_optimized(force_refresh=True)
                
                logger.info(f"Dashboard cache refreshed for user {user_id}")
                return f"Dashboard cache refreshed for user {user_id}"
                
            except User.DoesNotExist:
                logger.error(f"User {user_id} not found")
                return f"User {user_id} not found"
        else:
            # Refresh for all users
            users = User.objects.all()
            refreshed_count = 0
            
            for user in users:
                try:
                    cache_service = OptimizedDashboardCacheService(user)
                    cache_service.refresh_dashboard_cache_optimized(force_refresh=True)
                    refreshed_count += 1
                except Exception as e:
                    logger.error(f"Failed to refresh cache for user {user.id}: {e}")
                    
            logger.info(f"Dashboard cache refreshed for {refreshed_count} users")
            return f"Dashboard cache refreshed for {refreshed_count} users"
            
    except Exception as exc:
        logger.error(f"Dashboard cache refresh failed: {exc}")
        # Retry on failure
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@app.task(bind=True, max_retries=3)
def warm_dashboard_cache(self, user_id=None):
    """
    Warm dashboard cache for a specific user or all users.
    
    Args:
        user_id (int, optional): Specific user ID to warm cache for. If None, warm for all users.
    """
    try:
        from .cache_advanced import get_advanced_cache_manager, DashboardCacheWarmer
        
        if user_id:
            # Warm cache for specific user
            try:
                user = User.objects.get(id=user_id)
                warmer = DashboardCacheWarmer(user)
                warmer.warm_dashboard_caches('background')
                
                logger.info(f"Dashboard cache warmed for user {user_id}")
                return f"Dashboard cache warmed for user {user_id}"
                
            except User.DoesNotExist:
                logger.error(f"User {user_id} not found")
                return f"User {user_id} not found"
        else:
            # Warm cache for all users
            users = User.objects.all()
            warmed_count = 0
            
            for user in users:
                try:
                    warmer = DashboardCacheWarmer(user)
                    warmer.warm_dashboard_caches('background')
                    warmed_count += 1
                except Exception as e:
                    logger.error(f"Failed to warm cache for user {user.id}: {e}")
                    
            logger.info(f"Dashboard cache warmed for {warmed_count} users")
            return f"Dashboard cache warmed for {warmed_count} users"
            
    except Exception as exc:
        logger.error(f"Dashboard cache warming failed: {exc}")
        # Retry on failure
        raise self.retry(exc=exc, countdown=60, max_retries=3)

@app.task(bind=True, max_retries=2)
def performance_analysis(self):
    """Run performance analysis on the dashboard system."""
    try:
        from .performance_monitor import get_performance_monitor
        
        monitor = get_performance_monitor()
        performance_status = monitor.get_performance_summary()
        
        # Log performance metrics
        logger.info(f"Performance analysis completed: {performance_status}")
        
        # Store performance metrics (could send to monitoring system)
        return {
            'status': 'completed',
            'metrics': performance_status,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Performance analysis failed: {exc}")
        # Retry on failure
        raise self.retry(exc=exc, countdown=300, max_retries=2)

@app.task(bind=True)
def export_dashboard_data(self, user_id, export_format='json', date_range=None):
    """
    Export dashboard data for a user.
    
    Args:
        user_id (int): User ID to export data for
        export_format (str): Format to export data in (json, csv, pdf)
        date_range (dict): Date range for export
    """
    try:
        from .services_optimized import OptimizedDashboardCacheService
        
        user = User.objects.get(id=user_id)
        cache_service = OptimizedDashboardCacheService(user)
        
        # Get dashboard data
        dashboard_data = cache_service.get_cached_dashboard_data_optimized()
        
        # Process export based on format
        if export_format.lower() == 'json':
            export_result = {
                'data': dashboard_data,
                'format': 'json',
                'exported_at': timezone.now().isoformat()
            }
        elif export_format.lower() == 'csv':
            # Convert to CSV format
            export_result = {
                'data': 'CSV data would be generated here',
                'format': 'csv',
                'exported_at': timezone.now().isoformat()
            }
        else:
            export_result = {
                'data': str(dashboard_data),
                'format': export_format,
                'exported_at': timezone.now().isoformat()
            }
        
        logger.info(f"Dashboard data exported for user {user_id} in {export_format} format")
        return export_result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for export")
        return f"User {user_id} not found"
    except Exception as exc:
        logger.error(f"Dashboard data export failed: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=1)

@app.task(bind=True)
def send_notification(self, user_id, message, notification_type='info'):
    """
    Send notification to user (could be email, push, etc.).
    
    Args:
        user_id (int): User ID to send notification to
        message (str): Notification message
        notification_type (str): Type of notification (info, warning, alert)
    """
    try:
        user = User.objects.get(id=user_id)
        
        # In a real implementation, this would send actual notifications
        # For now, we'll just log it
        logger.info(f"Notification sent to user {user_id}: {message} (type: {notification_type})")
        
        return {
            'user_id': user_id,
            'message': message,
            'type': notification_type,
            'sent_at': timezone.now().isoformat()
        }
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for notification")
        return f"User {user_id} not found"
    except Exception as exc:
        logger.error(f"Notification sending failed: {exc}")
        raise self.retry(exc=exc, countdown=300, max_retries=2)

@app.task(bind=True)
def cleanup_old_data(self, days_old=30):
    """
    Clean up old dashboard data.
    
    Args:
        days_old (int): Number of days old data to clean up
    """
    try:
        from .models import DashboardSnapshot, PerformanceMetric
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        # Clean up old snapshots
        old_snapshots = DashboardSnapshot.objects.filter(snapshot_date__lt=cutoff_date)
        snapshot_count = old_snapshots.count()
        old_snapshots.delete()
        
        # Clean up old performance metrics
        old_metrics = PerformanceMetric.objects.filter(calculation_date__lt=cutoff_date)
        metric_count = old_metrics.count()
        old_metrics.delete()
        
        result = {
            'snapshots_deleted': snapshot_count,
            'metrics_deleted': metric_count,
            'cutoff_date': cutoff_date.isoformat(),
            'completed_at': timezone.now().isoformat()
        }
        
        logger.info(f"Cleaned up old data: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"Data cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=3600, max_retries=1)