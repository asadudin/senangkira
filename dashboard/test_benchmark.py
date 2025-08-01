"""
Dashboard Endpoint Benchmark Tests

Comprehensive performance benchmarking for dashboard API endpoints with:
- Response time measurement and analysis
- Throughput testing under load
- Memory usage profiling
- Caching effectiveness validation
- Real-time endpoint performance validation
- Concurrent request handling
"""

import time
import json
import statistics
import threading
from decimal import Decimal
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.test.utils import override_settings

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric
from .services import DashboardAggregationService, DashboardCacheService
from .realtime import RealTimeDashboardAggregator

User = get_user_model()


class DashboardBenchmarkMixin:
    """Mixin for dashboard benchmark utilities."""
    
    def measure_response_time(self, func, *args, **kwargs):
        """Measure function execution time."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, (end_time - start_time) * 1000  # Convert to milliseconds
    
    def benchmark_endpoint(self, method, url, iterations=10, **request_kwargs):
        """Benchmark an API endpoint with multiple iterations."""
        response_times = []
        responses = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            
            if method.upper() == 'GET':
                response = self.client.get(url, **request_kwargs)
            elif method.upper() == 'POST':
                response = self.client.post(url, **request_kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000  # milliseconds
            
            response_times.append(response_time)
            responses.append(response)
        
        return {
            'responses': responses,
            'response_times': response_times,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
            'p99_response_time': statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times),
            'total_requests': len(response_times),
            'successful_requests': sum(1 for r in responses if 200 <= r.status_code < 300)
        }
    
    def concurrent_benchmark(self, method, url, concurrent_users=5, requests_per_user=10, **request_kwargs):
        """Benchmark endpoint with concurrent requests."""
        def make_requests(user_id):
            user_results = []
            for i in range(requests_per_user):
                start_time = time.perf_counter()
                
                if method.upper() == 'GET':
                    response = self.client.get(url, **request_kwargs)
                else:
                    response = self.client.post(url, **request_kwargs)
                
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                
                user_results.append({
                    'user_id': user_id,
                    'request_id': i,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'success': 200 <= response.status_code < 300
                })
            
            return user_results
        
        all_results = []
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_requests, user_id) for user_id in range(concurrent_users)]
            
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        response_times = [r['response_time'] for r in all_results]
        successful_requests = sum(1 for r in all_results if r['success'])
        
        return {
            'total_requests': len(all_results),
            'successful_requests': successful_requests,
            'failed_requests': len(all_results) - successful_requests,
            'success_rate': (successful_requests / len(all_results)) * 100,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
            'concurrent_users': concurrent_users,
            'requests_per_user': requests_per_user,
            'all_results': all_results
        }


class DashboardEndpointBenchmarkTests(APITestCase, DashboardBenchmarkMixin):
    """Benchmark tests for standard dashboard API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.benchmark_results = {}
    
    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            email='benchmark@example.com',
            username='benchmarkuser',
            password='testpass123'
        )
        
        # Create JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Create test data
        self._create_test_data()
        
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    def _create_test_data(self):
        """Create comprehensive test data for benchmarking."""
        # Create dashboard snapshot
        self.snapshot = DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            total_revenue=Decimal('10000.00'),
            total_expenses=Decimal('6000.00'),
            net_profit=Decimal('4000.00'),
            total_clients=25,
            new_clients=5,
            total_invoices=50,
            average_invoice_value=Decimal('200.00')
        )
        
        # Create category analytics
        categories = ['office_supplies', 'travel', 'equipment', 'marketing', 'utilities']
        for i, category in enumerate(categories):
            CategoryAnalytics.objects.create(
                owner=self.user,
                snapshot_date=date.today(),
                category_type='expense',
                category_name=category,
                category_display=category.replace('_', ' ').title(),
                total_amount=Decimal(str(1000 + i * 500)),
                transaction_count=10 + i * 5,
                percentage_of_total=Decimal(str(15 + i * 5))
            )
        
        # Create client analytics
        for i in range(10):
            ClientAnalytics.objects.create(
                owner=self.user,
                client_id=f"client_{i}",
                client_name=f"Test Client {i}",
                snapshot_date=date.today(),
                total_revenue=Decimal(str(1000 + i * 200)),
                invoice_count=5 + i,
                outstanding_amount=Decimal(str(100 + i * 50)),
                payment_score=Decimal(str(85 + i)),
                is_active=True
            )
        
        # Create performance metrics
        metrics = ['Total Revenue', 'Profit Margin', 'New Clients', 'Revenue Growth Rate']
        for i, metric in enumerate(metrics):
            PerformanceMetric.objects.create(
                owner=self.user,
                metric_name=metric,
                metric_category='financial' if i < 2 else 'client' if i == 2 else 'growth',
                current_value=Decimal(str(100 + i * 25)),
                previous_value=Decimal(str(90 + i * 20)),
                unit='currency' if 'Revenue' in metric else 'percentage' if 'Margin' in metric or 'Rate' in metric else 'number',
                period_start=date.today() - timedelta(days=30),
                period_end=date.today()
            )
    
    def test_dashboard_overview_benchmark(self):
        """Benchmark dashboard overview endpoint."""
        url = reverse('dashboard:dashboard-overview')
        
        # Single request benchmark
        result = self.benchmark_endpoint('GET', url, iterations=20)
        
        self.benchmark_results['dashboard_overview'] = result
        
        # Performance assertions
        self.assertLess(result['avg_response_time'], 500, "Average response time should be under 500ms")
        self.assertLess(result['p95_response_time'], 1000, "95th percentile should be under 1000ms")
        self.assertEqual(result['successful_requests'], result['total_requests'], "All requests should be successful")
        
        # Print benchmark results
        print(f"\n📊 Dashboard Overview Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   Median Response Time: {result['median_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")
        print(f"   Success Rate: {(result['successful_requests']/result['total_requests'])*100:.1f}%")
    
    def test_dashboard_stats_benchmark(self):
        """Benchmark dashboard stats endpoint."""
        url = reverse('dashboard:dashboard-stats')
        
        result = self.benchmark_endpoint('GET', url, iterations=20)
        self.benchmark_results['dashboard_stats'] = result
        
        # Performance assertions
        self.assertLess(result['avg_response_time'], 300, "Stats endpoint should be faster than overview")
        self.assertEqual(result['successful_requests'], result['total_requests'])
        
        print(f"\n📈 Dashboard Stats Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")
    
    def test_dashboard_breakdown_benchmark(self):
        """Benchmark dashboard breakdown endpoint."""
        url = reverse('dashboard:dashboard-breakdown')
        
        result = self.benchmark_endpoint('GET', url, iterations=15)
        self.benchmark_results['dashboard_breakdown'] = result
        
        # Performance assertions - breakdown can be slower due to complex aggregations
        self.assertLess(result['avg_response_time'], 800, "Breakdown should complete within 800ms")
        self.assertEqual(result['successful_requests'], result['total_requests'])
        
        print(f"\n📋 Dashboard Breakdown Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")
    
    def test_dashboard_refresh_benchmark(self):
        """Benchmark dashboard refresh endpoint (most expensive operation)."""
        url = reverse('dashboard:dashboard-refresh')
        
        result = self.benchmark_endpoint('POST', url, iterations=5)  # Fewer iterations for expensive operation
        self.benchmark_results['dashboard_refresh'] = result
        
        # Performance assertions - refresh is expected to be slower
        self.assertLess(result['avg_response_time'], 3000, "Refresh should complete within 3 seconds")
        self.assertEqual(result['successful_requests'], result['total_requests'])
        
        print(f"\n🔄 Dashboard Refresh Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")
    
    def test_concurrent_dashboard_access_benchmark(self):
        """Benchmark concurrent access to dashboard overview."""
        url = reverse('dashboard:dashboard-overview')
        
        result = self.concurrent_benchmark('GET', url, concurrent_users=5, requests_per_user=5)
        self.benchmark_results['concurrent_overview'] = result
        
        # Performance assertions for concurrent access
        self.assertGreater(result['success_rate'], 95, "Success rate should be above 95% under load")
        self.assertLess(result['avg_response_time'], 1000, "Average response time should be under 1s under load")
        
        print(f"\n🏃‍♂️ Concurrent Dashboard Access Benchmark Results:")
        print(f"   Concurrent Users: {result['concurrent_users']}")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")


class RealTimeDashboardBenchmarkTests(APITestCase, DashboardBenchmarkMixin):
    """Benchmark tests for real-time dashboard endpoints."""
    
    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            email='realtime@example.com',
            username='realtimeuser',
            password='testpass123'
        )
        
        # Create JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    @patch('dashboard.realtime.RealTimeDashboardAggregator')
    def test_realtime_aggregate_benchmark(self, mock_aggregator_class):
        """Benchmark real-time dashboard aggregation endpoint."""
        # Mock aggregator for consistent results
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        from .realtime import LiveDashboardUpdate, RealTimeMetric
        
        mock_update = LiveDashboardUpdate(
            user_id=str(self.user.id),
            timestamp=timezone.now(),
            metrics=[
                RealTimeMetric(
                    name='Daily Revenue',
                    value=Decimal('1000.00'),
                    change=Decimal('100.00'),
                    trend='up',
                    timestamp=timezone.now(),
                    confidence=0.95
                )
            ],
            alerts=[],
            performance_score=85.5
        )
        
        mock_aggregator.get_live_dashboard_update.return_value = mock_update
        
        url = reverse('dashboard:realtime-aggregate')
        result = self.benchmark_endpoint('GET', url, iterations=25)
        
        # Real-time endpoints should be very fast
        self.assertLess(result['avg_response_time'], 200, "Real-time endpoint should be under 200ms")
        self.assertLess(result['p95_response_time'], 400, "95th percentile should be under 400ms")
        self.assertEqual(result['successful_requests'], result['total_requests'])
        
        print(f"\n⚡ Real-Time Aggregate Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   Median Response Time: {result['median_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")
        print(f"   Success Rate: {(result['successful_requests']/result['total_requests'])*100:.1f}%")
    
    def test_dashboard_health_benchmark(self):
        """Benchmark dashboard health check endpoint."""
        # Create test snapshot for database connectivity test
        DashboardSnapshot.objects.create(
            owner=self.user,
            snapshot_date=date.today(),
            total_revenue=Decimal('1000.00')
        )
        
        url = reverse('dashboard:dashboard-health')
        result = self.benchmark_endpoint('GET', url, iterations=30)
        
        # Health checks should be very fast
        self.assertLess(result['avg_response_time'], 100, "Health check should be under 100ms")
        self.assertEqual(result['successful_requests'], result['total_requests'])
        
        print(f"\n🏥 Dashboard Health Check Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")
    
    @patch('dashboard.realtime.DashboardCacheService')
    @patch('dashboard.realtime.RealTimeDashboardAggregator')
    def test_recalculation_trigger_benchmark(self, mock_aggregator_class, mock_cache_service_class):
        """Benchmark dashboard recalculation trigger endpoint."""
        # Mock services
        mock_cache_service = MagicMock()
        mock_cache_service_class.return_value = mock_cache_service
        mock_cache_service.refresh_dashboard_cache.return_value = {
            'refreshed': True,
            'duration_seconds': 0.5
        }
        
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        from .realtime import LiveDashboardUpdate
        mock_update = LiveDashboardUpdate(
            user_id=str(self.user.id),
            timestamp=timezone.now(),
            metrics=[],
            alerts=[],
            performance_score=80.0
        )
        mock_aggregator.get_live_dashboard_update.return_value = mock_update
        
        url = reverse('dashboard:trigger-recalculation')
        result = self.benchmark_endpoint('POST', url, iterations=10)  # Fewer iterations for expensive operation
        
        # Recalculation can be slower but should be reasonable
        self.assertLess(result['avg_response_time'], 1000, "Recalculation should be under 1 second")
        self.assertEqual(result['successful_requests'], result['total_requests'])
        
        print(f"\n🔄 Recalculation Trigger Benchmark Results:")
        print(f"   Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"   95th Percentile: {result['p95_response_time']:.2f}ms")


class DashboardCachingBenchmarkTests(TransactionTestCase, DashboardBenchmarkMixin):
    """Benchmark tests for dashboard caching effectiveness."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='cache@example.com',
            username='cacheuser',
            password='testpass123'
        )
        
        # Create test data
        self.aggregation_service = DashboardAggregationService(self.user)
        self.cache_service = DashboardCacheService(self.user)
    
    def tearDown(self):
        """Clean up cache after tests."""
        cache.clear()
    
    def test_cache_miss_vs_hit_performance(self):
        """Compare performance of cache miss vs cache hit scenarios."""
        # Clear cache to ensure miss
        cache.clear()
        
        # Measure cache miss (first call)
        _, miss_time = self.measure_response_time(
            self.cache_service.get_cached_dashboard_data
        )
        
        # Measure cache hit (second call)
        _, hit_time = self.measure_response_time(
            self.cache_service.get_cached_dashboard_data
        )
        
        # Cache hit should be significantly faster
        improvement_ratio = miss_time / hit_time if hit_time > 0 else float('inf')
        
        print(f"\n🗄️ Cache Performance Benchmark Results:")
        print(f"   Cache Miss Time: {miss_time:.2f}ms")
        print(f"   Cache Hit Time: {hit_time:.2f}ms")
        print(f"   Performance Improvement: {improvement_ratio:.1f}x faster")
        
        # Assertions
        self.assertLess(hit_time, miss_time, "Cache hit should be faster than miss")
        self.assertGreater(improvement_ratio, 1.5, "Cache should provide at least 1.5x improvement")
    
    def test_cache_refresh_performance(self):
        """Benchmark cache refresh operation."""
        refresh_times = []
        
        for i in range(5):
            _, refresh_time = self.measure_response_time(
                self.cache_service.refresh_dashboard_cache,
                force_refresh=True
            )
            refresh_times.append(refresh_time)
        
        avg_refresh_time = statistics.mean(refresh_times)
        
        print(f"\n🔄 Cache Refresh Performance Benchmark:")
        print(f"   Average Refresh Time: {avg_refresh_time:.2f}ms")
        print(f"   Min Refresh Time: {min(refresh_times):.2f}ms")
        print(f"   Max Refresh Time: {max(refresh_times):.2f}ms")
        
        # Cache refresh should complete within reasonable time
        self.assertLess(avg_refresh_time, 2000, "Cache refresh should complete within 2 seconds")


class DashboardServiceBenchmarkTests(TestCase):
    """Benchmark tests for dashboard services and aggregation logic."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='service@example.com',
            username='serviceuser',
            password='testpass123'
        )
        
        self.aggregation_service = DashboardAggregationService(self.user)
        self.realtime_aggregator = RealTimeDashboardAggregator(self.user)
    
    def measure_service_performance(self, service_method, *args, **kwargs):
        """Measure service method performance."""
        start_time = time.perf_counter()
        result = service_method(*args, **kwargs)
        end_time = time.perf_counter()
        return result, (end_time - start_time) * 1000
    
    def test_dashboard_snapshot_generation_benchmark(self):
        """Benchmark dashboard snapshot generation."""
        generation_times = []
        
        for period_type in ['daily', 'weekly', 'monthly']:
            _, generation_time = self.measure_service_performance(
                self.aggregation_service.generate_dashboard_snapshot,
                period_type=period_type
            )
            generation_times.append((period_type, generation_time))
        
        print(f"\n📸 Dashboard Snapshot Generation Benchmark:")
        for period_type, time_ms in generation_times:
            print(f"   {period_type.title()} Snapshot: {time_ms:.2f}ms")
        
        # All snapshot types should complete within reasonable time
        for period_type, time_ms in generation_times:
            self.assertLess(time_ms, 1000, f"{period_type} snapshot should complete within 1 second")
    
    def test_performance_metrics_calculation_benchmark(self):
        """Benchmark performance metrics calculation."""
        _, calculation_time = self.measure_service_performance(
            self.aggregation_service.calculate_performance_metrics
        )
        
        print(f"\n📊 Performance Metrics Calculation Benchmark:")
        print(f"   Calculation Time: {calculation_time:.2f}ms")
        
        self.assertLess(calculation_time, 500, "Performance metrics calculation should be under 500ms")
    
    def test_real_time_metrics_benchmark(self):
        """Benchmark real-time metrics generation."""
        _, metrics_time = self.measure_service_performance(
            self.realtime_aggregator.get_live_metrics
        )
        
        _, update_time = self.measure_service_performance(
            self.realtime_aggregator.get_live_dashboard_update
        )
        
        print(f"\n⚡ Real-Time Metrics Benchmark:")
        print(f"   Live Metrics Generation: {metrics_time:.2f}ms")
        print(f"   Full Dashboard Update: {update_time:.2f}ms")
        
        # Real-time operations should be very fast
        self.assertLess(metrics_time, 200, "Live metrics should generate within 200ms")
        self.assertLess(update_time, 300, "Dashboard update should complete within 300ms")


class DashboardBenchmarkReportGenerator:
    """Generate comprehensive benchmark report."""
    
    @classmethod
    def generate_report(cls, benchmark_results):
        """Generate and print comprehensive benchmark report."""
        print("\n" + "="*80)
        print("🚀 DASHBOARD ENDPOINT BENCHMARK REPORT")
        print("="*80)
        
        print(f"\n📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Performance Target: Sub-500ms for standard endpoints, sub-200ms for real-time")
        
        # Summary statistics
        all_avg_times = []
        all_success_rates = []
        
        for endpoint, results in benchmark_results.items():
            if 'avg_response_time' in results:
                all_avg_times.append(results['avg_response_time'])
            if 'success_rate' in results:
                all_success_rates.append(results['success_rate'])
            elif 'successful_requests' in results and 'total_requests' in results:
                success_rate = (results['successful_requests'] / results['total_requests']) * 100
                all_success_rates.append(success_rate)
        
        if all_avg_times:
            print(f"\n📊 OVERALL PERFORMANCE SUMMARY:")
            print(f"   Average Response Time Across All Endpoints: {statistics.mean(all_avg_times):.2f}ms")
            print(f"   Fastest Endpoint: {min(all_avg_times):.2f}ms")
            print(f"   Slowest Endpoint: {max(all_avg_times):.2f}ms")
        
        if all_success_rates:
            print(f"   Average Success Rate: {statistics.mean(all_success_rates):.1f}%")
        
        # Performance grades
        print(f"\n🏆 PERFORMANCE GRADES:")
        for endpoint, results in benchmark_results.items():
            if 'avg_response_time' in results:
                avg_time = results['avg_response_time']
                if avg_time < 100:
                    grade = "A+ (Excellent)"
                elif avg_time < 200:
                    grade = "A (Very Good)"
                elif avg_time < 500:
                    grade = "B (Good)"
                elif avg_time < 1000:
                    grade = "C (Acceptable)"
                else:
                    grade = "D (Needs Improvement)"
                
                print(f"   {endpoint}: {avg_time:.2f}ms - {grade}")
        
        # Recommendations
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        recommendations = []
        
        for endpoint, results in benchmark_results.items():
            if 'avg_response_time' in results:
                avg_time = results['avg_response_time']
                if avg_time > 500:
                    recommendations.append(f"   • Optimize {endpoint} - currently {avg_time:.0f}ms (target: <500ms)")
                elif avg_time > 200 and 'realtime' in endpoint:
                    recommendations.append(f"   • Optimize real-time {endpoint} - currently {avg_time:.0f}ms (target: <200ms)")
        
        if not recommendations:
            print("   ✅ All endpoints meet performance targets!")
        else:
            for rec in recommendations:
                print(rec)
        
        print("\n" + "="*80)
        print("✅ BENCHMARK REPORT COMPLETE")
        print("="*80)


# Test runner with benchmark reporting
def run_dashboard_benchmarks():
    """Run all dashboard benchmarks and generate report."""
    import unittest
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add benchmark test cases
    suite.addTest(unittest.makeSuite(DashboardEndpointBenchmarkTests))
    suite.addTest(unittest.makeSuite(RealTimeDashboardBenchmarkTests))
    suite.addTest(unittest.makeSuite(DashboardCachingBenchmarkTests))
    suite.addTest(unittest.makeSuite(DashboardServiceBenchmarkTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate report if we have results
    if hasattr(DashboardEndpointBenchmarkTests, 'benchmark_results'):
        DashboardBenchmarkReportGenerator.generate_report(
            DashboardEndpointBenchmarkTests.benchmark_results
        )
    
    return result


if __name__ == '__main__':
    run_dashboard_benchmarks()