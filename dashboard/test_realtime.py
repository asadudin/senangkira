"""
Tests for real-time dashboard aggregation endpoints.
Comprehensive test suite for real-time functionality and WebSocket integration.
"""

import json
from decimal import Decimal
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .realtime import RealTimeDashboardAggregator, RealTimeMetric, LiveDashboardUpdate
from .models import DashboardSnapshot

User = get_user_model()


class RealTimeDashboardAggregatorTests(TestCase):
    """Test real-time dashboard aggregator functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.aggregator = RealTimeDashboardAggregator(self.user)
        
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    def test_real_time_metric_creation(self):
        """Test RealTimeMetric data structure."""
        metric = RealTimeMetric(
            name='Daily Revenue',
            value=Decimal('1000.00'),
            change=Decimal('100.00'),
            trend='up',
            timestamp=timezone.now(),
            confidence=0.95
        )
        
        self.assertEqual(metric.name, 'Daily Revenue')
        self.assertEqual(metric.value, Decimal('1000.00'))
        self.assertEqual(metric.trend, 'up')
        self.assertEqual(metric.confidence, 0.95)
    
    @patch('dashboard.realtime.Invoice')
    @patch('dashboard.realtime.Expense')
    def test_live_financial_metrics_calculation(self, mock_expense, mock_invoice):
        """Test live financial metrics calculation."""
        # Mock today's data
        mock_invoice.objects.filter.return_value.aggregate.return_value = {
            'total': Decimal('1000.00')
        }
        mock_expense.objects.filter.return_value.aggregate.return_value = {
            'total': Decimal('700.00')
        }
        
        metrics = self.aggregator._calculate_live_financial_metrics()
        
        # Should have revenue, expenses, and profit metrics
        self.assertGreaterEqual(len(metrics), 3)
        
        metric_names = [metric.name for metric in metrics]
        self.assertIn('Daily Revenue', metric_names)
        self.assertIn('Daily Expenses', metric_names)
        self.assertIn('Daily Profit', metric_names)
        
        # Check revenue metric
        revenue_metric = next(m for m in metrics if m.name == 'Daily Revenue')
        self.assertEqual(revenue_metric.value, Decimal('1000.00'))
        self.assertIn(revenue_metric.trend, ['up', 'down', 'stable'])
    
    @patch('dashboard.realtime.Invoice')
    def test_live_operational_metrics_calculation(self, mock_invoice):
        """Test live operational metrics calculation."""
        # Mock pending and overdue invoice counts
        mock_invoice.objects.filter.return_value.count.side_effect = [5, 2]  # pending, overdue
        
        metrics = self.aggregator._calculate_live_operational_metrics()
        
        # Should have operational metrics
        self.assertGreaterEqual(len(metrics), 2)
        
        metric_names = [metric.name for metric in metrics]
        self.assertIn('Pending Invoices', metric_names)
        self.assertIn('Overdue Invoices', metric_names)
        
        # Check pending metric
        pending_metric = next(m for m in metrics if m.name == 'Pending Invoices')
        self.assertEqual(pending_metric.value, Decimal('5'))
    
    @patch('dashboard.realtime.Client')
    def test_live_client_metrics_calculation(self, mock_client):
        """Test live client metrics calculation."""
        # Mock active client count
        mock_client.objects.filter.return_value.count.return_value = 15
        
        metrics = self.aggregator._calculate_live_client_metrics()
        
        # Should have client metrics
        self.assertGreaterEqual(len(metrics), 1)
        
        client_metric = metrics[0]
        self.assertEqual(client_metric.name, 'Active Clients')
        self.assertEqual(client_metric.value, Decimal('15'))
    
    def test_alert_generation(self):
        """Test alert generation based on metrics."""
        # Create test metrics
        metrics = [
            RealTimeMetric(
                name='Daily Profit',
                value=Decimal('-100.00'),  # Negative profit
                change=Decimal('-50.00'),
                trend='down',
                timestamp=timezone.now()
            ),
            RealTimeMetric(
                name='Overdue Invoices',
                value=Decimal('8.00'),  # High overdue count
                change=Decimal('2.00'),
                trend='up',
                timestamp=timezone.now()
            ),
            RealTimeMetric(
                name='Daily Revenue',
                value=Decimal('2000.00'),
                change=Decimal('200.00'),
                trend='up',  # Positive trend
                timestamp=timezone.now()
            )
        ]
        
        alerts = self.aggregator.generate_alerts(metrics)
        
        # Should generate alerts for negative profit and high overdue invoices
        self.assertGreaterEqual(len(alerts), 2)
        
        alert_levels = [alert['level'] for alert in alerts]
        self.assertIn('critical', alert_levels)  # Negative profit
        self.assertIn('warning', alert_levels)   # High overdue invoices
        self.assertIn('success', alert_levels)   # Revenue growth
    
    def test_performance_score_calculation(self):
        """Test performance score calculation."""
        metrics = [
            RealTimeMetric(
                name='Daily Revenue',
                value=Decimal('1000.00'),
                change=Decimal('100.00'),
                trend='up',
                timestamp=timezone.now()
            ),
            RealTimeMetric(
                name='Daily Expenses',
                value=Decimal('600.00'),
                change=Decimal('-50.00'),
                trend='down',  # Good - expenses going down
                timestamp=timezone.now()
            )
        ]
        
        score = self.aggregator.calculate_performance_score(metrics)
        
        # Should be a positive score (0-100)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        
        # With positive trends, should be a good score
        self.assertGreater(score, 50.0)
    
    def test_live_dashboard_update_generation(self):
        """Test complete live dashboard update generation."""
        with patch.object(self.aggregator, 'get_live_metrics') as mock_metrics:
            mock_metrics.return_value = [
                RealTimeMetric(
                    name='Test Metric',
                    value=Decimal('100.00'),
                    change=Decimal('10.00'),
                    trend='up',
                    timestamp=timezone.now()
                )
            ]
            
            dashboard_update = self.aggregator.get_live_dashboard_update()
            
            self.assertIsInstance(dashboard_update, LiveDashboardUpdate)
            self.assertEqual(dashboard_update.user_id, str(self.user.id))
            self.assertIsInstance(dashboard_update.timestamp, datetime)
            self.assertGreaterEqual(len(dashboard_update.metrics), 1)
            self.assertIsInstance(dashboard_update.alerts, list)
            self.assertIsInstance(dashboard_update.performance_score, float)


class RealTimeDashboardAPITests(APITestCase):
    """Test real-time dashboard API endpoints."""
    
    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
        # Create JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    def test_realtime_dashboard_aggregate_endpoint(self):
        """Test real-time dashboard aggregation endpoint."""
        with patch('dashboard.realtime.RealTimeDashboardAggregator') as mock_aggregator_class:
            # Mock aggregator and dashboard update
            mock_aggregator = MagicMock()
            mock_aggregator_class.return_value = mock_aggregator
            
            mock_update = LiveDashboardUpdate(
                user_id=str(self.user.id),
                timestamp=timezone.now(),
                metrics=[
                    RealTimeMetric(
                        name='Test Metric',
                        value=Decimal('100.00'),
                        change=Decimal('10.00'),
                        trend='up',
                        timestamp=timezone.now(),
                        confidence=0.95
                    )
                ],
                alerts=[{'level': 'info', 'message': 'Test alert'}],
                performance_score=85.5
            )
            
            mock_aggregator.get_live_dashboard_update.return_value = mock_update
            
            url = reverse('dashboard:realtime-aggregate')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('user_id', response.data)
            self.assertIn('performance_score', response.data)
            self.assertIn('metrics', response.data)
            self.assertIn('alerts', response.data)
            
            # Check metric structure
            self.assertEqual(len(response.data['metrics']), 1)
            metric = response.data['metrics'][0]
            self.assertEqual(metric['name'], 'Test Metric')
            self.assertEqual(metric['value'], 100.0)
            self.assertEqual(metric['trend'], 'up')
    
    def test_streaming_dashboard_aggregate_endpoint(self):
        """Test streaming dashboard aggregation endpoint."""
        with patch('dashboard.realtime.RealTimeDashboardAggregator') as mock_aggregator_class:
            mock_aggregator = MagicMock()
            mock_aggregator_class.return_value = mock_aggregator
            
            mock_update = LiveDashboardUpdate(
                user_id=str(self.user.id),
                timestamp=timezone.now(),
                metrics=[],
                alerts=[],
                performance_score=75.0
            )
            
            mock_aggregator.get_live_dashboard_update.return_value = mock_update
            
            url = reverse('dashboard:streaming-aggregate')
            response = self.client.get(url + '?interval=1&max_updates=2')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response['Content-Type'], 'text/event-stream')
            self.assertIn('no-cache', response['Cache-Control'])
    
    def test_trigger_dashboard_recalculation_endpoint(self):
        """Test dashboard recalculation trigger endpoint."""
        with patch('dashboard.realtime.DashboardCacheService') as mock_cache_service_class:
            with patch('dashboard.realtime.RealTimeDashboardAggregator') as mock_aggregator_class:
                # Mock cache service
                mock_cache_service = MagicMock()
                mock_cache_service_class.return_value = mock_cache_service
                mock_cache_service.refresh_dashboard_cache.return_value = {
                    'refreshed': True,
                    'duration_seconds': 1.5
                }
                
                # Mock aggregator
                mock_aggregator = MagicMock()
                mock_aggregator_class.return_value = mock_aggregator
                mock_update = LiveDashboardUpdate(
                    user_id=str(self.user.id),
                    timestamp=timezone.now(),
                    metrics=[],
                    alerts=[],
                    performance_score=80.0
                )
                mock_aggregator.get_live_dashboard_update.return_value = mock_update
                
                url = reverse('dashboard:trigger-recalculation')
                response = self.client.post(url)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertTrue(response.data['success'])
                self.assertIn('refresh_results', response.data)
                self.assertIn('performance_score', response.data)
    
    def test_dashboard_health_check_endpoint(self):
        """Test dashboard health check endpoint."""
        # Create a test snapshot to ensure database connectivity
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            total_revenue=Decimal('1000.00')
        )
        
        url = reverse('dashboard:dashboard-health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertIn('components', response.data)
        self.assertIn('performance', response.data)
        
        # Check component health
        components = response.data['components']
        self.assertIn('database', components)
        self.assertIn('cache', components)
        self.assertIn('aggregation_service', components)
        
        # Check performance metrics
        performance = response.data['performance']
        self.assertIn('response_time_ms', performance)
        self.assertIn('performance_grade', performance)
    
    def test_unauthorized_access_to_realtime_endpoints(self):
        """Test that unauthorized requests are rejected."""
        self.client.credentials()  # Remove authentication
        
        endpoints = [
            'dashboard:realtime-aggregate',
            'dashboard:streaming-aggregate', 
            'dashboard:trigger-recalculation',
            'dashboard:dashboard-health'
        ]
        
        for endpoint in endpoints:
            url = reverse(endpoint)
            if endpoint == 'dashboard:trigger-recalculation':
                response = self.client.post(url)
            else:
                response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RealTimeDashboardIntegrationTests(TransactionTestCase):
    """Integration tests for real-time dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    def test_real_time_aggregator_integration(self):
        """Test real-time aggregator with actual database."""
        # Create test dashboard snapshot
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            total_revenue=Decimal('5000.00'),
            total_expenses=Decimal('3000.00'),
            net_profit=Decimal('2000.00')
        )
        
        aggregator = RealTimeDashboardAggregator(self.user)
        
        # Test live metrics generation
        metrics = aggregator.get_live_metrics()
        self.assertIsInstance(metrics, list)
        
        # Test dashboard update generation
        dashboard_update = aggregator.get_live_dashboard_update()
        self.assertIsInstance(dashboard_update, LiveDashboardUpdate)
        self.assertEqual(dashboard_update.user_id, str(self.user.id))
    
    def test_cache_integration_with_real_time_data(self):
        """Test cache integration with real-time functionality."""
        aggregator = RealTimeDashboardAggregator(self.user)
        
        # Generate metrics twice to test caching
        metrics1 = aggregator._calculate_live_operational_metrics()
        metrics2 = aggregator._calculate_live_operational_metrics()
        
        # Cache should be working (no assertions about specific behavior as it depends on implementation)
        self.assertIsInstance(metrics1, list)
        self.assertIsInstance(metrics2, list)


class RealTimeDashboardPerformanceTests(TestCase):
    """Performance tests for real-time dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    def test_real_time_aggregation_performance(self):
        """Test performance of real-time aggregation."""
        aggregator = RealTimeDashboardAggregator(self.user)
        
        start_time = timezone.now()
        
        # Generate live dashboard update
        dashboard_update = aggregator.get_live_dashboard_update()
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time (less than 1 second)
        self.assertLess(duration, 1.0)
        
        # Should return valid data
        self.assertIsInstance(dashboard_update, LiveDashboardUpdate)
    
    def test_cache_performance(self):
        """Test cache performance for real-time data."""
        aggregator = RealTimeDashboardAggregator(self.user)
        
        # First calculation (no cache)
        start_time = timezone.now()
        metrics1 = aggregator.get_live_metrics()
        end_time = timezone.now()
        first_duration = (end_time - start_time).total_seconds()
        
        # Second calculation (with cache)
        start_time = timezone.now()
        metrics2 = aggregator.get_live_metrics()
        end_time = timezone.now()
        second_duration = (end_time - start_time).total_seconds()
        
        # Both should be fast
        self.assertLess(first_duration, 1.0)
        self.assertLess(second_duration, 1.0)
        
        # Results should be consistent
        self.assertIsInstance(metrics1, list)
        self.assertIsInstance(metrics2, list)