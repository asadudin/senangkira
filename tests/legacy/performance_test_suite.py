#!/usr/bin/env python3
"""
Comprehensive Performance Test Suite for SenangKira
SK-003: Performance Testing Implementation

This script executes comprehensive performance testing including:
1. Database query performance analysis
2. API endpoint response time testing  
3. Concurrent load testing
4. Memory usage profiling
5. Cache effectiveness testing
"""

import os
import sys
import time
import asyncio
import statistics
import concurrent.futures
from datetime import datetime, timedelta, date
from decimal import Decimal
import psutil
import threading
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.core.cache import cache
from django.urls import reverse

from clients.models import Client as ClientModel
from invoicing.models import Quote, Invoice, QuoteLineItem
from dashboard.performance_monitor import get_performance_monitor, PerformanceMetric
from dashboard.services_optimized import OptimizedDashboardAggregationService

User = get_user_model()


class PerformanceTestResult:
    """Container for performance test results."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0
        self.memory_before = 0
        self.memory_after = 0
        self.memory_delta = 0
        self.success = False
        self.error = None
        self.metrics = {}
        
    def start(self):
        """Start timing the test."""
        self.start_time = time.time()
        self.memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        
    def end(self, success: bool = True, error: str = None):
        """End timing the test."""
        self.end_time = time.time()
        self.memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.memory_delta = self.memory_after - self.memory_before
        self.success = success
        self.error = error
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'test_name': self.test_name,
            'duration_ms': round(self.duration_ms, 2),
            'memory_delta_mb': round(self.memory_delta, 2),
            'success': self.success,
            'error': self.error,
            'metrics': self.metrics
        }


class SenangKiraPerformanceTestSuite:
    """Comprehensive performance test suite."""
    
    def __init__(self):
        self.results = []
        self.test_user = None
        self.test_clients = []
        self.test_quotes = []
        self.monitor = get_performance_monitor()
        
    def setup_test_data(self):
        """Set up test data for performance testing."""
        print("Setting up test data...")
        
        # Create test user
        self.test_user, created = User.objects.get_or_create(
            email='perftest@senangkira.com',
            defaults={
                'username': 'perftest',
                'first_name': 'Performance',
                'last_name': 'Test'
            }
        )
        
        if created:
            self.test_user.set_password('TestPass123!')
            self.test_user.save()
        
        # Create test clients (bulk create for performance)
        if not ClientModel.objects.filter(owner=self.test_user).exists():
            clients_data = []
            for i in range(50):
                clients_data.append(ClientModel(
                    name=f'Performance Test Client {i}',
                    email=f'client{i}@perftest.com',
                    phone=f'+1555000{i:04d}',
                    owner=self.test_user
                ))
            
            ClientModel.objects.bulk_create(clients_data)
        
        self.test_clients = list(ClientModel.objects.filter(owner=self.test_user))
        
        # Create test quotes with line items (use regular create to trigger save() method)
        if not Quote.objects.filter(owner=self.test_user).exists():
            for i, client in enumerate(self.test_clients[:20]):  # 20 quotes
                quote = Quote.objects.create(
                    title=f'Performance Test Quote {i}',
                    client=client,
                    owner=self.test_user,
                    tax_rate=Decimal('0.08'),
                    status='Draft',
                    issue_date=date.today()
                )
            
            # Create line items for quotes
            self.test_quotes = list(Quote.objects.filter(owner=self.test_user))
            line_items_data = []
            for quote in self.test_quotes:
                for j in range(3):  # 3 line items per quote
                    line_items_data.append(QuoteLineItem(
                        quote=quote,
                        description=f'Line item {j+1} for quote {quote.id}',
                        quantity=Decimal(str(j + 1)),
                        unit_price=Decimal(f'{100 + j * 50}.00')
                    ))
            
            QuoteLineItem.objects.bulk_create(line_items_data)
        
        print(f"Test data ready: {len(self.test_clients)} clients, {len(self.test_quotes)} quotes")
    
    def test_database_query_performance(self):
        """Test database query performance with various scenarios."""
        print("\n=== Database Query Performance Testing ===")
        
        # Test 1: Simple client query
        result = PerformanceTestResult("db_query_simple_clients")
        result.start()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM clients_client 
                    WHERE owner_id = %s
                """, [self.test_user.id])
                count = cursor.fetchone()[0]
                result.metrics['client_count'] = count
            result.end(success=True)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
        
        # Test 2: Complex join query (quotes with clients and line items)
        result = PerformanceTestResult("db_query_complex_joins")
        result.start()
        
        try:
            quotes = Quote.objects.filter(owner=self.test_user).select_related('client').prefetch_related('quoteline_items')
            quote_data = []
            for quote in quotes:
                quote_data.append({
                    'id': quote.id,
                    'client_name': quote.client.name,
                    'line_item_count': quote.quoteline_items.count(),
                    'total': float(quote.total_amount)
                })
            result.metrics['quotes_processed'] = len(quote_data)
            result.end(success=True)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
        
        # Test 3: Aggregation query
        result = PerformanceTestResult("db_query_aggregations")
        result.start()
        
        try:
            from django.db.models import Sum, Count, Avg
            stats = Quote.objects.filter(owner=self.test_user).aggregate(
                total_revenue=Sum('total_amount'),
                quote_count=Count('id'),
                average_quote_value=Avg('total_amount')
            )
            result.metrics['aggregation_results'] = {
                k: float(v) if v else 0 for k, v in stats.items()
            }
            result.end(success=True)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
    
    def test_dashboard_performance(self):
        """Test dashboard service performance."""
        print("\n=== Dashboard Performance Testing ===")
        
        # Test dashboard aggregation service
        result = PerformanceTestResult("dashboard_aggregation_service")
        result.start()
        
        try:
            service = OptimizedDashboardAggregationService(self.test_user)
            snapshot = service.generate_dashboard_snapshot_optimized()
            result.metrics['snapshot_id'] = str(snapshot.id)
            result.metrics['total_revenue'] = float(snapshot.total_revenue or 0)
            result.end(success=True)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
        
        # Test cached vs non-cached dashboard access
        result = PerformanceTestResult("dashboard_cache_effectiveness")
        result.start()
        
        try:
            # Clear cache first
            cache.clear()
            
            # First access (cache miss)
            service = OptimizedDashboardAggregationService(self.test_user)
            start_time = time.time()
            snapshot1 = service.generate_dashboard_snapshot_optimized(selective_refresh=False)
            first_access_time = (time.time() - start_time) * 1000
            
            # Second access (should be faster due to caching)
            start_time = time.time()
            snapshot2 = service.generate_dashboard_snapshot_optimized(selective_refresh=True)
            second_access_time = (time.time() - start_time) * 1000
            
            result.metrics['first_access_ms'] = round(first_access_time, 2)
            result.metrics['second_access_ms'] = round(second_access_time, 2)
            result.metrics['cache_improvement'] = round(
                ((first_access_time - second_access_time) / first_access_time) * 100, 1
            )
            result.end(success=True)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
    
    def test_api_endpoint_performance(self):
        """Test API endpoint response times."""
        print("\n=== API Endpoint Performance Testing ===")
        
        client = Client()
        
        # Login first
        login_result = client.login(email='perftest@senangkira.com', password='TestPass123!')
        if not login_result:
            print("Warning: Could not login for API testing")
            return
        
        # Test various endpoints
        endpoints = [
            ('client_list', '/api/clients/'),
            ('quote_list', '/api/quotes/'),
            ('dashboard_overview', '/api/dashboard/overview/'),
        ]
        
        for endpoint_name, url in endpoints:
            result = PerformanceTestResult(f"api_endpoint_{endpoint_name}")
            result.start()
            
            try:
                response = client.get(url)
                result.metrics['status_code'] = response.status_code
                result.metrics['response_size_bytes'] = len(response.content)
                
                if hasattr(response, 'json'):
                    try:
                        data = response.json()
                        if isinstance(data, dict) and 'results' in data:
                            result.metrics['result_count'] = len(data['results'])
                        elif isinstance(data, list):
                            result.metrics['result_count'] = len(data)
                    except:
                        pass
                
                result.end(success=response.status_code < 400)
            except Exception as e:
                result.end(success=False, error=str(e))
            
            self.results.append(result)
    
    def test_concurrent_load(self):
        """Test concurrent load performance."""
        print("\n=== Concurrent Load Testing ===")
        
        def simulate_user_activity():
            """Simulate a user's activity on the dashboard."""
            try:
                service = OptimizedDashboardAggregationService(self.test_user)
                snapshot = service.generate_dashboard_snapshot_optimized()
                return True, None
            except Exception as e:
                return False, str(e)
        
        result = PerformanceTestResult("concurrent_load_test")
        result.start()
        
        try:
            # Test with 10 concurrent operations
            concurrent_users = 10
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []
                
                # Submit concurrent tasks
                for i in range(concurrent_users):
                    future = executor.submit(simulate_user_activity)
                    futures.append(future)
                
                # Collect results
                successful_operations = 0
                failed_operations = 0
                errors = []
                
                for future in concurrent.futures.as_completed(futures):
                    success, error = future.result()
                    if success:
                        successful_operations += 1
                    else:
                        failed_operations += 1
                        errors.append(error)
            
            result.metrics['concurrent_users'] = concurrent_users
            result.metrics['successful_operations'] = successful_operations
            result.metrics['failed_operations'] = failed_operations
            result.metrics['success_rate'] = (successful_operations / concurrent_users) * 100
            
            result.end(success=failed_operations == 0)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
    
    def test_memory_usage_patterns(self):
        """Test memory usage patterns under load."""
        print("\n=== Memory Usage Pattern Testing ===")
        
        result = PerformanceTestResult("memory_usage_patterns")
        result.start()
        
        try:
            memory_samples = []
            
            # Sample memory usage during operations
            for i in range(10):
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024
                
                # Perform operation
                service = OptimizedDashboardAggregationService(self.test_user)
                snapshot = service.generate_dashboard_snapshot_optimized()
                
                memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                memory_delta = memory_after - memory_before
                memory_samples.append(memory_delta)
                
                # Small delay between operations
                time.sleep(0.1)
            
            result.metrics['memory_samples'] = memory_samples
            result.metrics['avg_memory_per_operation'] = round(statistics.mean(memory_samples), 2)
            result.metrics['max_memory_per_operation'] = round(max(memory_samples), 2)
            result.metrics['min_memory_per_operation'] = round(min(memory_samples), 2)
            
            result.end(success=True)
        except Exception as e:
            result.end(success=False, error=str(e))
        
        self.results.append(result)
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        report = {
            'test_execution': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(self.results),
                'successful_tests': sum(1 for r in self.results if r.success),
                'failed_tests': sum(1 for r in self.results if not r.success)
            },
            'performance_summary': {
                'avg_response_time_ms': round(statistics.mean([r.duration_ms for r in self.results]), 2),
                'fastest_operation_ms': round(min([r.duration_ms for r in self.results]), 2),
                'slowest_operation_ms': round(max([r.duration_ms for r in self.results]), 2),
                'avg_memory_usage_mb': round(statistics.mean([r.memory_delta for r in self.results]), 2)
            },
            'test_results': [r.to_dict() for r in self.results],
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                'python_version': sys.version.split()[0]
            }
        }
        
        return report
    
    def run_all_tests(self):
        """Run the complete performance test suite."""
        print("=" * 60)
        print("SENANGKIRA PERFORMANCE TEST SUITE - SK-003")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Setup
            self.setup_test_data()
            
            # Run all performance tests
            self.test_database_query_performance()
            self.test_dashboard_performance()
            self.test_api_endpoint_performance()
            self.test_concurrent_load()
            self.test_memory_usage_patterns()
            
            # Generate report
            report = self.generate_performance_report()
            
            # Save report
            report_file = f"performance_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n{'='*60}")
            print("PERFORMANCE TEST SUITE COMPLETED")
            print(f"{'='*60}")
            print(f"Total execution time: {time.time() - start_time:.2f} seconds")
            print(f"Total tests: {len(self.results)}")
            print(f"Successful: {sum(1 for r in self.results if r.success)}")
            print(f"Failed: {sum(1 for r in self.results if not r.success)}")
            print(f"Average response time: {report['performance_summary']['avg_response_time_ms']:.2f}ms")
            print(f"Report saved to: {report_file}")
            
            return report
            
        except Exception as e:
            print(f"Performance test suite failed: {e}")
            return None


def main():
    """Main entry point for performance testing."""
    suite = SenangKiraPerformanceTestSuite()
    report = suite.run_all_tests()
    
    if report:
        print("\n=== TOP PERFORMANCE INSIGHTS ===")
        
        # Find fastest and slowest operations
        fastest = min(suite.results, key=lambda r: r.duration_ms)
        slowest = max(suite.results, key=lambda r: r.duration_ms)
        
        print(f"Fastest operation: {fastest.test_name} ({fastest.duration_ms:.2f}ms)")
        print(f"Slowest operation: {slowest.test_name} ({slowest.duration_ms:.2f}ms)")
        
        # Performance recommendations
        print("\n=== PERFORMANCE RECOMMENDATIONS ===")
        
        if slowest.duration_ms > 1000:
            print(f"⚠️  {slowest.test_name} exceeds 1 second - investigate optimization opportunities")
        
        slow_operations = [r for r in suite.results if r.duration_ms > 500]
        if slow_operations:
            print(f"⚠️  {len(slow_operations)} operations exceed 500ms threshold")
        
        memory_intensive = [r for r in suite.results if r.memory_delta > 50]
        if memory_intensive:
            print(f"💾 {len(memory_intensive)} operations use >50MB memory")
        
        failures = [r for r in suite.results if not r.success]
        if failures:
            print(f"❌ {len(failures)} test failures require investigation")
        else:
            print("✅ All performance tests passed successfully")


if __name__ == '__main__':
    main()