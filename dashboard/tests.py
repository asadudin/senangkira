"""
Test suite for dashboard functionality.
Comprehensive tests for models, services, views, and caching.
"""

import uuid
from decimal import Decimal
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric
from .services import DashboardAggregationService, DashboardCacheService
from .cache import DashboardCache, QueryCache, CacheInvalidationManager

User = get_user_model()


class DashboardModelTests(TestCase):
    """Test dashboard models functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
    def test_dashboard_snapshot_creation(self):
        """Test dashboard snapshot model creation."""
        snapshot = DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            period_type='monthly',
            total_revenue=Decimal('10000.00'),
            total_expenses=Decimal('7000.00'),
            net_profit=Decimal('3000.00')
        )
        
        self.assertEqual(snapshot.owner, self.user)
        self.assertEqual(snapshot.profit_margin, Decimal('30.00'))
        self.assertEqual(snapshot.expense_ratio, Decimal('70.00'))
        
    def test_category_analytics_creation(self):
        """Test category analytics model."""
        analytics = CategoryAnalytics.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            period_type='monthly',
            category_type='expense',
            category_name='office_supplies',
            category_display='Office Supplies',
            total_amount=Decimal('1500.00'),
            transaction_count=25,
            percentage_of_total=Decimal('15.00')
        )
        
        self.assertEqual(analytics.category_type, 'expense')
        self.assertEqual(analytics.transaction_count, 25)
        
    def test_client_analytics_properties(self):
        """Test client analytics calculated properties."""
        client_analytics = ClientAnalytics.objects.create(
            owner=self.user,
            client_id=uuid.uuid4(),
            client_name='Test Client',
            total_revenue=Decimal('5000.00'),
            invoice_count=10,
            first_invoice_date=date.today() - timedelta(days=365),
            last_invoice_date=date.today()
        )
        
        # Test average invoice value
        self.assertEqual(client_analytics.average_invoice_value, Decimal('500.00'))
        
        # Test lifetime value calculation
        self.assertGreater(client_analytics.client_lifetime_value, Decimal('0.00'))
        
    def test_performance_metric_calculations(self):
        """Test performance metric calculated properties."""
        metric = PerformanceMetric.objects.create(
            owner=self.user,
            metric_name='Revenue Growth',
            metric_category='financial',
            current_value=Decimal('120000.0000'),
            previous_value=Decimal('100000.0000'),
            target_value=Decimal('150000.0000'),
            unit='currency',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today()
        )
        
        # Test change percentage
        self.assertEqual(metric.change_percentage, Decimal('20.0000'))
        
        # Test improvement detection
        self.assertTrue(metric.is_improving)
        
        # Test target achievement
        self.assertEqual(metric.target_achievement, Decimal('80.0000'))


class DashboardServiceTests(TestCase):
    """Test dashboard service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.service = DashboardAggregationService(self.user)
        
    def test_period_boundaries_calculation(self):
        """Test period boundary calculations."""
        test_date = date(2024, 6, 15)
        
        # Test monthly boundaries
        start, end = self.service._get_period_boundaries(test_date, 'monthly')
        self.assertEqual(start, date(2024, 6, 1))
        self.assertEqual(end, date(2024, 6, 30))
        
        # Test yearly boundaries
        start, end = self.service._get_period_boundaries(test_date, 'yearly')
        self.assertEqual(start, date(2024, 1, 1))
        self.assertEqual(end, date(2024, 12, 31))
        
    @patch('dashboard.services.Invoice')
    @patch('dashboard.services.Expense')
    def test_financial_metrics_calculation(self, mock_expense, mock_invoice):
        """Test financial metrics calculation."""
        # Mock queryset methods
        mock_invoice.objects.filter.return_value.aggregate.return_value = {
            'total': Decimal('10000.00')
        }
        mock_expense.objects.filter.return_value.aggregate.return_value = {
            'total': Decimal('7000.00')
        }
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        metrics = self.service._calculate_financial_metrics(start_date, end_date)
        
        self.assertEqual(metrics['total_revenue'], Decimal('10000.00'))
        self.assertEqual(metrics['total_expenses'], Decimal('7000.00'))
        self.assertEqual(metrics['net_profit'], Decimal('3000.00'))
        
    def test_dashboard_snapshot_generation(self):
        """Test dashboard snapshot generation."""
        with patch.object(self.service, '_calculate_financial_metrics') as mock_financial:
            mock_financial.return_value = {
                'total_revenue': Decimal('10000.00'),
                'total_expenses': Decimal('7000.00'),
                'net_profit': Decimal('3000.00'),
                'outstanding_amount': Decimal('2000.00'),
                'reimbursable_expenses': Decimal('500.00')
            }
            
            with patch.object(self.service, '_calculate_client_metrics') as mock_client:
                mock_client.return_value = {
                    'total_clients': 15,
                    'new_clients': 3
                }
                
                with patch.object(self.service, '_calculate_invoice_metrics') as mock_invoice:
                    mock_invoice.return_value = {
                        'total_invoices': 25,
                        'total_quotes': 30,
                        'quote_conversion_rate': Decimal('83.33'),
                        'average_invoice_value': Decimal('400.00')
                    }
                    
                    with patch.object(self.service, '_calculate_expense_metrics') as mock_expense:
                        mock_expense.return_value = {
                            'total_expense_count': 45
                        }
                        
                        snapshot = self.service.generate_dashboard_snapshot()
                        
                        self.assertEqual(snapshot.owner, self.user)
                        self.assertEqual(snapshot.total_revenue, Decimal('10000.00'))
                        self.assertEqual(snapshot.total_clients, 15)


class DashboardCacheTests(TestCase):
    """Test dashboard caching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.cache_manager = DashboardCache(self.user)
        
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
        
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key = self.cache_manager.get_cache_key('overview', period='monthly')
        self.assertTrue(key.startswith(f'user_{self.user.id}_overview_'))
        
    def test_cache_set_and_get(self):
        """Test caching and retrieval."""
        test_data = {'revenue': 10000, 'expenses': 7000}
        
        # Set cache
        success = self.cache_manager.set_cached_data('overview', test_data)
        self.assertTrue(success)
        
        # Get cache
        cached_data = self.cache_manager.get_cached_data('overview')
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data['data'], test_data)
        
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        test_data = {'revenue': 10000}
        
        # Set cache
        self.cache_manager.set_cached_data('overview', test_data)
        
        # Verify cache exists
        self.assertIsNotNone(self.cache_manager.get_cached_data('overview'))
        
        # Invalidate cache
        success = self.cache_manager.invalidate_cache('overview')
        self.assertTrue(success)
        
        # Verify cache is gone
        self.assertIsNone(self.cache_manager.get_cached_data('overview'))
        
    def test_get_or_set_functionality(self):
        """Test get_or_set cache functionality."""
        def expensive_calculation():
            return {'calculated': True, 'value': 42}
        
        # First call should execute function
        data = self.cache_manager.get_or_set('calculation', expensive_calculation)
        self.assertEqual(data, {'calculated': True, 'value': 42})
        
        # Second call should use cache
        data = self.cache_manager.get_or_set('calculation', lambda: {'should_not_execute': True})
        self.assertEqual(data, {'calculated': True, 'value': 42})


class DashboardAPITests(APITestCase):
    """Test dashboard API endpoints."""
    
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
        
        # Create test dashboard data
        self.snapshot = DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            period_type='monthly',
            total_revenue=Decimal('10000.00'),
            total_expenses=Decimal('7000.00'),
            net_profit=Decimal('3000.00')
        )
        
    def test_dashboard_overview_endpoint(self):
        """Test dashboard overview API endpoint."""
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_revenue', response.data)
        self.assertIn('total_expenses', response.data)
        self.assertIn('net_profit', response.data)
        
    def test_dashboard_stats_endpoint(self):
        """Test dashboard stats API endpoint."""
        url = reverse('dashboard:dashboard-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('revenue_this_month', response.data)
        self.assertIn('profit_this_month', response.data)
        
    def test_dashboard_refresh_endpoint(self):
        """Test dashboard cache refresh endpoint."""
        url = reverse('dashboard:dashboard-refresh')
        response = self.client.post(url, {'force_refresh': True})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('refreshed', response.data)
        
    def test_kpis_endpoint(self):
        """Test KPIs endpoint."""
        # Create test performance metric
        PerformanceMetric.objects.create(
            owner=self.user,
            metric_name='Test Metric',
            metric_category='financial',
            current_value=Decimal('100.0000'),
            previous_value=Decimal('80.0000'),
            unit='currency',
            period_start=date.today() - timedelta(days=30),
            period_end=date.today()
        )
        
        url = reverse('dashboard:dashboard-kpis')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
    def test_unauthorized_access(self):
        """Test that unauthorized requests are rejected."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_dashboard_snapshots_list(self):
        """Test listing dashboard snapshots."""
        url = reverse('dashboard:dashboard-snapshots-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_dashboard_snapshots_create(self):
        """Test creating dashboard snapshots."""
        url = reverse('dashboard:dashboard-snapshots-list')
        data = {
            'snapshot_date': date.today().isoformat(),
            'period_type': 'monthly',
            'total_revenue': '15000.00',
            'total_expenses': '10000.00',
            'net_profit': '5000.00'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DashboardSnapshot.objects.filter(owner=self.user).count(), 2)


class DashboardIntegrationTests(TransactionTestCase):
    """Integration tests for complete dashboard workflows."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
    def test_complete_dashboard_workflow(self):
        """Test complete dashboard data generation workflow."""
        service = DashboardAggregationService(self.user)
        cache_service = DashboardCacheService(self.user)
        
        # Generate snapshot
        with patch.object(service, '_calculate_financial_metrics') as mock_financial:
            mock_financial.return_value = {
                'total_revenue': Decimal('10000.00'),
                'total_expenses': Decimal('7000.00'),
                'net_profit': Decimal('3000.00'),
                'outstanding_amount': Decimal('2000.00'),
                'reimbursable_expenses': Decimal('500.00')
            }
            
            with patch.object(service, '_calculate_client_metrics') as mock_client:
                mock_client.return_value = {'total_clients': 10, 'new_clients': 2}
                
                with patch.object(service, '_calculate_invoice_metrics') as mock_invoice:
                    mock_invoice.return_value = {
                        'total_invoices': 20, 'total_quotes': 25,
                        'quote_conversion_rate': Decimal('80.00'),
                        'average_invoice_value': Decimal('500.00')
                    }
                    
                    with patch.object(service, '_calculate_expense_metrics') as mock_expense:
                        mock_expense.return_value = {'total_expense_count': 35}
                        
                        # Generate all dashboard data
                        snapshot = service.generate_dashboard_snapshot()
                        
                        # Verify snapshot creation
                        self.assertIsNotNone(snapshot)
                        self.assertEqual(snapshot.total_revenue, Decimal('10000.00'))
                        
                        # Test cache functionality
                        dashboard_data = cache_service.get_cached_dashboard_data()
                        self.assertIsNotNone(dashboard_data)
                        self.assertIn('snapshot', dashboard_data)
                        
                        # Test cache refresh
                        refresh_results = cache_service.refresh_dashboard_cache(force_refresh=True)
                        self.assertTrue(refresh_results['refreshed'])


class DashboardPerformanceTests(TestCase):
    """Performance tests for dashboard functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        
    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        # Create multiple snapshots
        snapshots = []
        for i in range(100):
            snapshots.append(DashboardSnapshot(
                owner=self.user,
                snapshot_date=date.today() - timedelta(days=i),
                period_type='daily',
                total_revenue=Decimal(f'{1000 + i}.00'),
                total_expenses=Decimal(f'{700 + i}.00'),
                net_profit=Decimal(f'{300 + i}.00')
            ))
        
        DashboardSnapshot.objects.bulk_create(snapshots)
        
        # Test query performance
        start_time = timezone.now()
        latest_snapshots = DashboardSnapshot.objects.filter(
            owner=self.user
        ).order_by('-snapshot_date')[:10]
        
        # Force evaluation
        list(latest_snapshots)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        self.assertLess(duration, 1.0)  # Less than 1 second
        
    def test_cache_performance(self):
        """Test caching performance."""
        cache_manager = DashboardCache(self.user)
        
        # Test cache write performance
        large_data = {'data': list(range(1000))}
        
        start_time = timezone.now()
        cache_manager.set_cached_data('performance_test', large_data)
        end_time = timezone.now()
        
        write_duration = (end_time - start_time).total_seconds()
        self.assertLess(write_duration, 0.1)  # Less than 100ms
        
        # Test cache read performance
        start_time = timezone.now()
        cached_data = cache_manager.get_cached_data('performance_test')
        end_time = timezone.now()
        
        read_duration = (end_time - start_time).total_seconds()
        self.assertLess(read_duration, 0.05)  # Less than 50ms
        self.assertIsNotNone(cached_data)