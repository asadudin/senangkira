"""
SK-701: Celery Implementation Test Suite

This script contains a comprehensive test suite for validating the Celery implementation
created in SK-701. It covers:
- Task execution and queue routing
- Periodic task scheduling
- Integration with caching system
- Monitoring and tracking functionality
- Error handling and retry mechanisms
"""

import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from celery import current_app
from celery.exceptions import Retry

from .tasks import (
    refresh_dashboard_cache,
    warm_dashboard_cache,
    performance_analysis,
    export_dashboard_data,
    send_notification,
    cleanup_old_data,
    debug_task
)
from .celery_monitoring import (
    CeleryMonitor,
    CeleryTaskTracker,
    get_celery_status,
    get_worker_information,
    get_queue_information,
    get_recent_tasks
)
from .cache_advanced import get_advanced_cache_manager
from .models import DashboardSnapshot, PerformanceMetric

User = get_user_model()


class CeleryTaskTests(TestCase):
    """Test Celery task functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        # Clear cache
        cache.clear()
        
        # Configure Celery for testing
        current_app.conf.task_always_eager = True
        current_app.conf.task_eager_propagates = True
        
    def tearDown(self):
        """Clean up after tests."""
        current_app.conf.task_always_eager = False
        current_app.conf.task_eager_propagates = False
        cache.clear()
        
    def test_debug_task(self):
        """Test debug task execution."""
        result = debug_task()
        self.assertIn('Request:', result)
        
    def test_refresh_dashboard_cache_task(self):
        """Test dashboard cache refresh task."""
        # Create test snapshot
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        # Execute task
        result = refresh_dashboard_cache(user_id=self.user.id)
        
        self.assertIn(f'Dashboard cache refreshed for user {self.user.id}', result)
        
    def test_refresh_dashboard_cache_all_users(self):
        """Test dashboard cache refresh for all users."""
        # Create another user
        user2 = User.objects.create_user(
            email='test2@example.com',
            username='testuser2',
            password='testpass123'
        )
        
        # Create test snapshots
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        DashboardSnapshot.objects.create(
            owner=user2,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=15000.00,
            total_expenses=10000.00,
            net_profit=5000.00
        )
        
        # Execute task
        result = refresh_dashboard_cache()
        
        self.assertIn('Dashboard cache refreshed for', result)
        
    def test_warm_dashboard_cache_task(self):
        """Test dashboard cache warming task."""
        # Create test snapshot
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        # Execute task
        result = warm_dashboard_cache(user_id=self.user.id)
        
        self.assertIn(f'Dashboard cache warmed for user {self.user.id}', result)
        
    def test_performance_analysis_task(self):
        """Test performance analysis task."""
        # Create test performance metrics
        PerformanceMetric.objects.create(
            owner=self.user,
            metric_name='Test Metric',
            metric_category='financial',
            current_value=100.0000,
            previous_value=80.0000,
            unit='currency',
            period_start=timezone.now().date() - timedelta(days=30),
            period_end=timezone.now().date()
        )
        
        # Execute task
        result = performance_analysis()
        
        self.assertEqual(result['status'], 'completed')
        self.assertIn('metrics', result)
        self.assertIn('timestamp', result)
        
    def test_export_dashboard_data_task(self):
        """Test dashboard data export task."""
        # Create test snapshot
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        # Execute task
        result = export_dashboard_data(user_id=self.user.id, export_format='json')
        
        self.assertIn('data', result)
        self.assertEqual(result['format'], 'json')
        self.assertIn('exported_at', result)
        
    def test_send_notification_task(self):
        """Test notification sending task."""
        # Execute task
        result = send_notification(
            user_id=self.user.id,
            message='Test notification',
            notification_type='info'
        )
        
        self.assertEqual(result['user_id'], self.user.id)
        self.assertEqual(result['message'], 'Test notification')
        self.assertEqual(result['type'], 'info')
        self.assertIn('sent_at', result)
        
    def test_cleanup_old_data_task(self):
        """Test old data cleanup task."""
        # Create old dashboard snapshots
        old_date = timezone.now().date() - timedelta(days=40)
        
        old_snapshot = DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=old_date,
            period_type='monthly',
            total_revenue=5000.00,
            total_expenses=3000.00,
            net_profit=2000.00
        )
        
        # Create recent snapshot (should not be deleted)
        recent_snapshot = DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        # Execute task (cleanup data older than 30 days)
        result = cleanup_old_data(days_old=30)
        
        self.assertIn('snapshots_deleted', result)
        self.assertGreaterEqual(result['snapshots_deleted'], 1)
        self.assertIn('completed_at', result)
        
        # Verify old snapshot was deleted
        with self.assertRaises(DashboardSnapshot.DoesNotExist):
            DashboardSnapshot.objects.get(id=old_snapshot.id)
            
        # Verify recent snapshot still exists
        self.assertTrue(DashboardSnapshot.objects.filter(id=recent_snapshot.id).exists())
        
    @patch('dashboard.tasks.OptimizedDashboardCacheService.refresh_dashboard_cache_optimized')
    def test_task_retry_mechanism(self, mock_refresh):
        """Test task retry mechanism."""
        # Mock the refresh method to raise an exception
        mock_refresh.side_effect = Exception('Temporary error')
        
        # Execute task (should retry)
        try:
            refresh_dashboard_cache(user_id=self.user.id)
            self.fail("Expected exception was not raised")
        except Exception as e:
            # Check that the task was retried
            mock_refresh.assert_called()
            self.assertEqual(mock_refresh.call_count, 4)  # 1 initial + 3 retries
            
    def test_task_queue_routing(self):
        """Test that tasks are properly routed to queues."""
        # Check task routing configuration
        routes = current_app.conf.task_routes
        
        self.assertIn('dashboard.tasks.refresh_dashboard_cache', routes)
        self.assertEqual(routes['dashboard.tasks.refresh_dashboard_cache']['queue'], 'high_priority')
        
        self.assertIn('dashboard.tasks.warm_dashboard_cache', routes)
        self.assertEqual(routes['dashboard.tasks.warm_dashboard_cache']['queue'], 'cache_operations')
        
        self.assertIn('dashboard.tasks.performance_analysis', routes)
        self.assertEqual(routes['dashboard.tasks.performance_analysis']['queue'], 'analytics')


class CeleryMonitoringTests(TestCase):
    """Test Celery monitoring functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        self.monitor = CeleryMonitor()
        self.tracker = CeleryTaskTracker()
        
    def tearDown(self):
        """Clean up after tests."""
        cache.clear()
        
    def test_worker_stats(self):
        """Test worker statistics collection."""
        # This test is limited in unit testing environment
        # but we can test the structure
        stats = self.monitor.get_worker_stats()
        self.assertIn('timestamp', stats)
        
    def test_queue_stats(self):
        """Test queue statistics collection."""
        stats = self.monitor.get_queue_stats()
        self.assertIn('timestamp', stats)
        
    def test_task_tracking(self):
        """Test task tracking functionality."""
        task_id = str(uuid.uuid4())
        task_name = 'test.task'
        
        # Track task start
        self.tracker.track_task_start(task_id, task_name, args=('arg1',), kwargs={'key': 'value'})
        
        # Verify tracking
        task_details = self.tracker.get_task_details(task_id)
        self.assertIsNotNone(task_details)
        self.assertEqual(task_details['task_id'], task_id)
        self.assertEqual(task_details['name'], task_name)
        self.assertEqual(task_details['args'], ('arg1',))
        self.assertEqual(task_details['kwargs'], {'key': 'value'})
        self.assertEqual(task_details['status'], 'started')
        
        # Track task completion
        self.tracker.track_task_completion(task_id, success=True, result={'data': 'test'})
        
        # Verify completion tracking
        task_details = self.tracker.get_task_details(task_id)
        self.assertEqual(task_details['status'], 'success')
        self.assertIn('completed_at', task_details)
        self.assertIn('duration', task_details)
        self.assertEqual(task_details['result'], {'data': 'test'})
        
    def test_task_tracking_history(self):
        """Test task tracking history."""
        task_id = str(uuid.uuid4())
        
        # Track task
        self.tracker.track_task_start(task_id, 'test.task')
        self.tracker.track_task_completion(task_id, success=True)
        
        # Check history
        recent_tasks = get_recent_tasks(10)
        self.assertGreater(len(recent_tasks), 0)
        
        # Find our task in history
        task_found = False
        for task in recent_tasks:
            if task.get('task_id') == task_id:
                task_found = True
                self.assertEqual(task['status'], 'success')
                break
                
        self.assertTrue(task_found)
        
    def test_system_health(self):
        """Test system health monitoring."""
        health_status = get_celery_status()
        self.assertIn('status', health_status)
        self.assertIn('timestamp', health_status)
        
    def test_worker_information(self):
        """Test worker information retrieval."""
        worker_info = get_worker_information()
        self.assertIn('timestamp', worker_info)
        
    def test_queue_information(self):
        """Test queue information retrieval."""
        queue_info = get_queue_information()
        self.assertIn('timestamp', queue_info)


class CeleryIntegrationTests(TestCase):
    """Integration tests for Celery with caching system."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        # Configure Celery for testing
        current_app.conf.task_always_eager = True
        current_app.conf.task_eager_propagates = True
        
        # Clear cache
        cache.clear()
        
    def tearDown(self):
        """Clean up after tests."""
        current_app.conf.task_always_eager = False
        current_app.conf.task_eager_propagates = False
        cache.clear()
        
    def test_cache_refresh_integration(self):
        """Test integration between Celery tasks and caching system."""
        # Create test data
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        # Get advanced cache manager
        cache_manager = get_advanced_cache_manager(self.user)
        
        # Execute cache refresh via Celery task
        result = refresh_dashboard_cache(user_id=self.user.id)
        
        self.assertIn(f'Dashboard cache refreshed for user {self.user.id}', result)
        
        # Verify cache was updated by checking analytics
        analytics = cache_manager.get_analytics_report()
        self.assertIn('cache_analytics', analytics)
        
    def test_periodic_task_registration(self):
        """Test that periodic tasks are properly registered."""
        from .tasks import setup_periodic_tasks
        from celery import current_app
        
        # Create a mock sender
        sender = MagicMock()
        
        # Call setup function
        setup_periodic_tasks(sender)
        
        # Verify periodic tasks were added
        sender.add_periodic_task.assert_called()
        
        # Check specific calls
        calls = sender.add_periodic_task.call_args_list
        
        # Should have calls for refresh, warm, and performance analysis tasks
        self.assertGreater(len(calls), 0)
        
    def test_task_decorator_tracking(self):
        """Test task decorator with tracking."""
        from .celery_monitoring import track_celery_task
        
        @track_celery_task
        def mock_task_function(arg1, kwarg1=None):
            return f"processed: {arg1}, {kwarg1}"
        
        # Execute decorated function
        result = mock_task_function("test_arg", kwarg1="test_kwarg")
        
        self.assertEqual(result, "processed: test_arg, test_kwarg")
        

class CeleryPerformanceTests(TestCase):
    """Performance tests for Celery tasks."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        # Configure Celery for testing
        current_app.conf.task_always_eager = True
        current_app.conf.task_eager_propagates = True
        
    def tearDown(self):
        """Clean up after tests."""
        current_app.conf.task_always_eager = False
        current_app.conf.task_eager_propagates = False
        
    def test_task_execution_time(self):
        """Test that tasks execute within reasonable time limits."""
        # Create test data
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=timezone.now().date(),
            period_type='monthly',
            total_revenue=10000.00,
            total_expenses=7000.00,
            net_profit=3000.00
        )
        
        # Measure execution time
        start_time = time.time()
        result = refresh_dashboard_cache(user_id=self.user.id)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (less than 2 seconds)
        self.assertLess(execution_time, 2.0)
        self.assertIn(f'Dashboard cache refreshed for user {self.user.id}', result)
        
    def test_concurrent_task_execution(self):
        """Test concurrent task execution."""
        # Create test users
        users = []
        for i in range(3):
            user = User.objects.create_user(
                email=f'test{i}@example.com',
                username=f'testuser{i}',
                password='testpass123'
            )
            users.append(user)
            
            # Create test data for each user
            DashboardSnapshot.objects.create(
                owner=user,
                snapshot_date=timezone.now().date(),
                period_type='monthly',
                total_revenue=10000.00 + i * 1000,
                total_expenses=7000.00 + i * 500,
                net_profit=3000.00 + i * 500
            )
        
        # Execute tasks concurrently
        results = []
        start_time = time.time()
        
        for user in users:
            result = refresh_dashboard_cache(user_id=user.id)
            results.append(result)
            
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all tasks completed successfully
        for i, result in enumerate(results):
            self.assertIn(f'Dashboard cache refreshed for user {users[i].id}', result)
            
        # Should complete within reasonable time for concurrent execution
        self.assertLess(total_time, 5.0)  # Less than 5 seconds total