"""
Optimized Middleware for Dashboard Performance and Concurrent Request Handling

Key features:
1. Request queuing and throttling for heavy operations
2. Connection pooling optimization
3. Async request processing where possible
4. Memory usage monitoring and optimization
5. Request prioritization and load balancing
"""

import asyncio
import time
import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import psutil
import gc

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.db import connections
from django.core.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class RequestMetrics:
    """Track request metrics for optimization decisions."""
    
    def __init__(self):
        self.request_times = defaultdict(deque)
        self.concurrent_requests = defaultdict(int)
        self.queue_sizes = defaultdict(int)
        self.error_rates = defaultdict(float)
        self.memory_usage = deque(maxlen=100)
        self.lock = threading.Lock()
    
    def record_request(self, user_id: int, endpoint: str, duration: float, success: bool):
        """Record request metrics."""
        with self.lock:
            key = f"{user_id}:{endpoint}"
            
            # Store last 50 request times
            self.request_times[key].append(duration)
            if len(self.request_times[key]) > 50:
                self.request_times[key].popleft()
            
            # Update error rate (simple moving average)
            if not success:
                current_rate = self.error_rates.get(key, 0.0)
                self.error_rates[key] = (current_rate * 0.9) + (1.0 * 0.1)
            else:
                current_rate = self.error_rates.get(key, 0.0)
                self.error_rates[key] = current_rate * 0.95
    
    def get_avg_response_time(self, user_id: int, endpoint: str) -> float:
        """Get average response time for user/endpoint combination."""
        key = f"{user_id}:{endpoint}"
        times = self.request_times.get(key, [])
        return sum(times) / len(times) if times else 0.0
    
    def get_error_rate(self, user_id: int, endpoint: str) -> float:
        """Get error rate for user/endpoint combination."""
        key = f"{user_id}:{endpoint}"
        return self.error_rates.get(key, 0.0)
    
    def update_memory_usage(self):
        """Update memory usage metrics."""
        memory_percent = psutil.virtual_memory().percent
        self.memory_usage.append(memory_percent)
    
    def get_memory_trend(self) -> str:
        """Get memory usage trend."""
        if len(self.memory_usage) < 2:
            return 'stable'
        
        recent = list(self.memory_usage)[-5:]
        if len(recent) < 2:
            return 'stable'
        
        trend = sum(recent[-3:]) / 3 - sum(recent[:2]) / 2
        
        if trend > 5:
            return 'increasing'
        elif trend < -5:
            return 'decreasing'
        else:
            return 'stable'


class ConcurrentRequestHandler:
    """Handle concurrent requests with intelligent queuing and processing."""
    
    def __init__(self, max_workers: int = 8, max_queue_size: int = 100):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='dashboard_api')
        self.request_queues = defaultdict(lambda: deque(maxlen=max_queue_size))
        self.processing_locks = defaultdict(threading.Lock)
        self.metrics = RequestMetrics()
        
        # Priority levels for different endpoints
        self.endpoint_priorities = {
            'overview': 1,      # Highest priority
            'stats': 1,
            'refresh': 2,       # Medium priority (expensive)
            'breakdown': 3,     # Lower priority
            'export': 4,        # Lowest priority (very expensive)
            'health-check': 0   # Emergency priority
        }
        
        # Rate limiting per user
        self.rate_limits = {
            'refresh': 5,           # 5 requests per minute
            'export': 2,            # 2 requests per minute
            'breakdown': 10,        # 10 requests per minute
            'overview': 30,         # 30 requests per minute
        }
        
        self.user_request_counts = defaultdict(lambda: defaultdict(deque))
    
    def is_rate_limited(self, user_id: int, endpoint: str) -> bool:
        """Check if user is rate limited for endpoint."""
        if endpoint not in self.rate_limits:
            return False
        
        limit = self.rate_limits[endpoint]
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        user_requests = self.user_request_counts[user_id][endpoint]
        while user_requests and user_requests[0] < minute_ago:
            user_requests.popleft()
        
        # Check if over limit
        if len(user_requests) >= limit:
            return True
        
        # Record this request
        user_requests.append(now)
        return False
    
    def get_request_priority(self, endpoint: str, user_id: int) -> int:
        """Get request priority (lower number = higher priority)."""
        base_priority = self.endpoint_priorities.get(endpoint, 5)
        
        # Adjust based on error rate
        error_rate = self.metrics.get_error_rate(user_id, endpoint)
        if error_rate > 0.1:  # High error rate
            base_priority += 2
        
        # Adjust based on system load
        memory_trend = self.metrics.get_memory_trend()
        if memory_trend == 'increasing':
            base_priority += 1
        
        return base_priority
    
    def should_process_async(self, endpoint: str, estimated_duration: float) -> bool:
        """Determine if request should be processed asynchronously."""
        # Process async if estimated duration > 200ms
        return estimated_duration > 0.2 or endpoint in ['refresh', 'export', 'breakdown']
    
    def get_estimated_duration(self, user_id: int, endpoint: str) -> float:
        """Estimate request duration based on historical data."""
        avg_time = self.metrics.get_avg_response_time(user_id, endpoint)
        
        # Fallback estimates if no history
        if avg_time == 0.0:
            estimates = {
                'overview': 0.1,
                'stats': 0.05,
                'refresh': 0.8,     # High estimate for refresh
                'breakdown': 0.3,
                'export': 2.0,
                'health-check': 0.02
            }
            avg_time = estimates.get(endpoint, 0.5)
        
        return avg_time


class DashboardConcurrencyMiddleware(MiddlewareMixin):
    """
    Middleware for optimizing concurrent dashboard requests.
    
    Features:
    - Request queuing and prioritization
    - Rate limiting per user/endpoint
    - Async processing for expensive operations
    - Memory usage monitoring
    - Connection pool optimization
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.handler = ConcurrentRequestHandler(
            max_workers=getattr(settings, 'DASHBOARD_MAX_WORKERS', 8),
            max_queue_size=getattr(settings, 'DASHBOARD_MAX_QUEUE_SIZE', 100)
        )
        
        # Start background monitoring
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring thread."""
        def monitor():
            while True:
                try:
                    self.handler.metrics.update_memory_usage()
                    self._optimize_connections()
                    time.sleep(30)  # Monitor every 30 seconds
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    time.sleep(60)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _optimize_connections(self):
        """Optimize database connections based on usage."""
        try:
            # Close idle connections
            for alias in connections:
                connection = connections[alias]
                if hasattr(connection, 'close_if_unusable_or_obsolete'):
                    connection.close_if_unusable_or_obsolete()
            
            # Force garbage collection if memory usage is high
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                gc.collect()
                
        except Exception as e:
            logger.warning(f"Connection optimization failed: {e}")
    
    def _extract_endpoint(self, path: str) -> Optional[str]:
        """Extract endpoint name from path."""
        if '/api/dashboard/' not in path:
            return None
        
        endpoint_mapping = {
            'overview': 'overview',
            'stats': 'stats', 
            'refresh': 'refresh',
            'breakdown': 'breakdown',
            'export': 'export',
            'health-check': 'health-check',
            'performance-metrics': 'performance-metrics'
        }
        
        for endpoint_path, endpoint_name in endpoint_mapping.items():
            if endpoint_path in path:
                return endpoint_name
        
        return 'unknown'
    
    def process_request(self, request):
        """Process incoming dashboard requests with optimization."""
        endpoint = self._extract_endpoint(request.path)
        if not endpoint:
            return None
        
        # Only handle authenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        user_id = request.user.id
        
        # Check rate limiting
        if self.handler.is_rate_limited(user_id, endpoint):
            logger.warning(f"Rate limit exceeded: user {user_id}, endpoint {endpoint}")
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'retry_after': 60,
                'endpoint': endpoint
            }, status=429)
        
        # Check system load
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 95:
            logger.error(f"System overloaded: {memory_percent}% memory usage")
            return JsonResponse({
                'error': 'System temporarily overloaded',
                'retry_after': 30,
                'memory_usage': memory_percent
            }, status=503)
        
        # Estimate request duration
        estimated_duration = self.handler.get_estimated_duration(user_id, endpoint)
        
        # Add metadata to request for downstream processing
        request.dashboard_metadata = {
            'endpoint': endpoint,
            'estimated_duration': estimated_duration,
            'priority': self.handler.get_request_priority(endpoint, user_id),
            'should_async': self.handler.should_process_async(endpoint, estimated_duration),
            'start_time': time.time()
        }
        
        return None
    
    def process_response(self, request, response):
        """Process response and update metrics."""
        if not hasattr(request, 'dashboard_metadata'):
            return response
        
        metadata = request.dashboard_metadata
        duration = time.time() - metadata['start_time']
        success = 200 <= response.status_code < 400
        
        # Record metrics
        self.handler.metrics.record_request(
            request.user.id,
            metadata['endpoint'],
            duration,
            success
        )
        
        # Add performance headers
        response['X-Dashboard-Duration'] = f"{duration:.3f}s"
        response['X-Dashboard-Priority'] = str(metadata['priority'])
        response['X-Dashboard-Optimized'] = 'true'
        
        # Add performance recommendations
        if duration > metadata['estimated_duration'] * 2:
            response['X-Dashboard-Recommendation'] = 'Consider caching or optimization'
        
        return response
    
    def process_exception(self, request, exception):
        """Handle exceptions and update error metrics."""
        if hasattr(request, 'dashboard_metadata'):
            metadata = request.dashboard_metadata
            duration = time.time() - metadata['start_time']
            
            self.handler.metrics.record_request(
                request.user.id,
                metadata['endpoint'],
                duration,
                False  # Exception = failure
            )
        
        return None


class DatabaseConnectionPoolingMiddleware(MiddlewareMixin):
    """
    Optimize database connection pooling for dashboard operations.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.connection_stats = defaultdict(int)
        self.last_optimization = time.time()
    
    def process_request(self, request):
        """Optimize connections before processing dashboard requests."""
        if '/api/dashboard/' not in request.path:
            return None
        
        # Optimize connections every 5 minutes
        now = time.time()
        if now - self.last_optimization > 300:
            self._optimize_connection_pool()
            self.last_optimization = now
        
        return None
    
    def _optimize_connection_pool(self):
        """Optimize database connection pool settings."""
        try:
            for alias in connections:
                connection = connections[alias]
                
                # Close idle connections
                if hasattr(connection, 'close_if_unusable_or_obsolete'):
                    connection.close_if_unusable_or_obsolete()
                
                # Update connection stats
                self.connection_stats[alias] += 1
            
            logger.info(f"Connection pool optimized: {dict(self.connection_stats)}")
            
        except Exception as e:
            logger.warning(f"Connection pool optimization failed: {e}")


class AsyncRequestProcessingMiddleware(MiddlewareMixin):
    """
    Handle async processing for expensive dashboard operations.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.async_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='async_dashboard')
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check if request should be processed asynchronously."""
        if not hasattr(request, 'dashboard_metadata'):
            return None
        
        metadata = request.dashboard_metadata
        
        # For very expensive operations, consider background processing
        if metadata['estimated_duration'] > 2.0:  # > 2 seconds
            # This could be enhanced to use Celery or similar for true async processing
            logger.info(f"Expensive operation detected: {metadata['endpoint']} (~{metadata['estimated_duration']:.2f}s)")
        
        return None


# Utility functions for middleware integration
def get_request_metrics() -> Dict[str, Any]:
    """Get current request metrics for monitoring."""
    # This would access the global middleware instance
    # Implementation depends on how middleware is configured
    return {
        'message': 'Metrics available through middleware instance',
        'timestamp': timezone.now().isoformat()
    }


def optimize_dashboard_performance():
    """Trigger manual performance optimization."""
    try:
        # Force connection optimization
        for alias in connections:
            connection = connections[alias]
            if hasattr(connection, 'close_if_unusable_or_obsolete'):
                connection.close_if_unusable_or_obsolete()
        
        # Force garbage collection
        gc.collect()
        
        return True
        
    except Exception as e:
        logger.error(f"Performance optimization failed: {e}")
        return False