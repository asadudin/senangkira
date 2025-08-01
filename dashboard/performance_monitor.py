"""
Real-time Performance Monitoring for Dashboard Optimizations

Monitors the performance improvements implemented in SK-602 and provides
real-time metrics, alerts, and optimization recommendations.

Features:
- Real-time performance tracking
- Automatic performance degradation detection
- Optimization recommendations
- Performance trend analysis
- Alert system for performance issues
"""

import time
import statistics
import threading
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import psutil
import json
from dataclasses import dataclass, asdict

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Container for performance metrics."""
    timestamp: datetime
    operation: str
    duration_ms: float
    memory_usage_mb: float
    cache_hit: bool
    user_id: Optional[int] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


class PerformanceThresholds:
    """Performance thresholds for monitoring and alerting."""
    
    # Response time thresholds (milliseconds)
    DASHBOARD_REFRESH_WARNING = 400.0
    DASHBOARD_REFRESH_CRITICAL = 600.0
    
    API_ENDPOINT_WARNING = 200.0
    API_ENDPOINT_CRITICAL = 500.0
    
    DATABASE_QUERY_WARNING = 100.0
    DATABASE_QUERY_CRITICAL = 300.0
    
    # Cache performance thresholds
    CACHE_HIT_RATE_WARNING = 70.0  # Below 70%
    CACHE_HIT_RATE_CRITICAL = 50.0  # Below 50%
    
    # Memory usage thresholds (MB)
    MEMORY_USAGE_WARNING = 100.0
    MEMORY_USAGE_CRITICAL = 200.0
    
    # System resource thresholds
    CPU_USAGE_WARNING = 70.0  # Percentage
    CPU_USAGE_CRITICAL = 85.0
    
    MEMORY_SYSTEM_WARNING = 80.0  # Percentage
    MEMORY_SYSTEM_CRITICAL = 90.0


class PerformanceMonitor:
    """
    Real-time performance monitoring system.
    
    Tracks performance metrics, detects degradation, and provides
    optimization recommendations.
    """
    
    def __init__(self, window_size: int = 100, monitoring_interval: int = 30):
        self.window_size = window_size
        self.monitoring_interval = monitoring_interval
        
        # Metric storage (sliding windows)
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))
        self.system_metrics = deque(maxlen=window_size)
        
        # Performance tracking
        self.performance_trends = defaultdict(list)
        self.alerts = deque(maxlen=50)  # Last 50 alerts
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'total_errors': 0,
            'average_response_time': 0.0,
            'cache_hit_rate': 0.0,
            'uptime_start': timezone.now()
        }
        
        self.thresholds = PerformanceThresholds()
    
    def start_monitoring(self):
        """Start real-time performance monitoring."""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        # Store metric
        self.metrics[metric.operation].append(metric)
        
        # Update statistics
        self.stats['total_requests'] += 1
        if metric.error:
            self.stats['total_errors'] += 1
        
        # Update average response time (running average)
        current_avg = self.stats['average_response_time']
        total_requests = self.stats['total_requests']
        self.stats['average_response_time'] = (
            (current_avg * (total_requests - 1) + metric.duration_ms) / total_requests
        )
        
        # Update cache hit rate
        if metric.operation in self.metrics:
            recent_metrics = list(self.metrics[metric.operation])[-20:]  # Last 20 requests
            cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
            self.stats['cache_hit_rate'] = (cache_hits / len(recent_metrics)) * 100 if recent_metrics else 0
        
        # Check for alerts
        self._check_performance_alerts(metric)
        
        # Cache the metric for external access
        cache.set(f"perf_metric_{metric.operation}_latest", metric.to_dict(), 300)
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Analyze performance trends
                self._analyze_trends()
                
                # Check system resource alerts
                self._check_system_alerts()
                
                # Update cached statistics
                self._update_cached_stats()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)  # Brief pause before retrying
    
    def _collect_system_metrics(self):
        """Collect system-level performance metrics."""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Database connection stats
            db_connections = len(connection.queries) if hasattr(connection, 'queries') else 0
            
            system_metric = {
                'timestamp': timezone.now(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / 1024 / 1024,
                'db_connections': db_connections
            }
            
            self.system_metrics.append(system_metric)
            
        except Exception as e:
            logger.warning(f"System metrics collection failed: {e}")
    
    def _analyze_trends(self):
        """Analyze performance trends and detect degradation."""
        for operation, metrics in self.metrics.items():
            if len(metrics) < 10:  # Need at least 10 data points
                continue
            
            recent_metrics = list(metrics)[-10:]  # Last 10 requests
            older_metrics = list(metrics)[-20:-10] if len(metrics) >= 20 else []
            
            if not older_metrics:
                continue
            
            # Calculate trend
            recent_avg = statistics.mean(m.duration_ms for m in recent_metrics)
            older_avg = statistics.mean(m.duration_ms for m in older_metrics)
            
            trend_change = ((recent_avg - older_avg) / older_avg) * 100
            
            # Store trend
            trend_data = {
                'timestamp': timezone.now(),
                'operation': operation,
                'trend_change_percent': trend_change,
                'recent_avg_ms': recent_avg,
                'older_avg_ms': older_avg
            }
            
            self.performance_trends[operation].append(trend_data)
            
            # Alert on significant degradation
            if trend_change > 25:  # 25% slower
                self._create_alert(
                    level='warning',
                    message=f"Performance degradation detected in {operation}: {trend_change:.1f}% slower",
                    details=trend_data
                )
    
    def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check metric against thresholds and create alerts."""
        operation = metric.operation
        duration = metric.duration_ms
        
        # Dashboard refresh alerts (critical optimization)
        if 'refresh' in operation.lower():
            if duration > self.thresholds.DASHBOARD_REFRESH_CRITICAL:
                self._create_alert(
                    level='critical',
                    message=f"Dashboard refresh critically slow: {duration:.1f}ms (target: <500ms)",
                    details=metric.to_dict()
                )
            elif duration > self.thresholds.DASHBOARD_REFRESH_WARNING:
                self._create_alert(
                    level='warning',
                    message=f"Dashboard refresh performance degraded: {duration:.1f}ms",
                    details=metric.to_dict()
                )
        
        # General API endpoint alerts
        elif 'api' in operation.lower() or 'endpoint' in operation.lower():
            if duration > self.thresholds.API_ENDPOINT_CRITICAL:
                self._create_alert(
                    level='critical',
                    message=f"API endpoint critically slow: {operation} {duration:.1f}ms",
                    details=metric.to_dict()
                )
            elif duration > self.thresholds.API_ENDPOINT_WARNING:
                self._create_alert(
                    level='warning',
                    message=f"API endpoint slow: {operation} {duration:.1f}ms",
                    details=metric.to_dict()
                )
        
        # Database query alerts
        elif 'db' in operation.lower() or 'query' in operation.lower():
            if duration > self.thresholds.DATABASE_QUERY_CRITICAL:
                self._create_alert(
                    level='critical',
                    message=f"Database query critically slow: {operation} {duration:.1f}ms",
                    details=metric.to_dict()
                )
            elif duration > self.thresholds.DATABASE_QUERY_WARNING:
                self._create_alert(
                    level='warning',
                    message=f"Database query slow: {operation} {duration:.1f}ms",
                    details=metric.to_dict()
                )
        
        # Memory usage alerts
        if metric.memory_usage_mb > self.thresholds.MEMORY_USAGE_CRITICAL:
            self._create_alert(
                level='critical',
                message=f"High memory usage: {metric.memory_usage_mb:.1f}MB in {operation}",
                details=metric.to_dict()
            )
        elif metric.memory_usage_mb > self.thresholds.MEMORY_USAGE_WARNING:
            self._create_alert(
                level='warning',
                message=f"Elevated memory usage: {metric.memory_usage_mb:.1f}MB in {operation}",
                details=metric.to_dict()
            )
    
    def _check_system_alerts(self):
        """Check system-level metrics for alerts."""
        if not self.system_metrics:
            return
        
        latest = self.system_metrics[-1]
        
        # CPU usage alerts
        if latest['cpu_percent'] > self.thresholds.CPU_USAGE_CRITICAL:
            self._create_alert(
                level='critical',
                message=f"Critical CPU usage: {latest['cpu_percent']:.1f}%",
                details=latest
            )
        elif latest['cpu_percent'] > self.thresholds.CPU_USAGE_WARNING:
            self._create_alert(
                level='warning',
                message=f"High CPU usage: {latest['cpu_percent']:.1f}%",
                details=latest
            )
        
        # Memory usage alerts
        if latest['memory_percent'] > self.thresholds.MEMORY_SYSTEM_CRITICAL:
            self._create_alert(
                level='critical',
                message=f"Critical system memory usage: {latest['memory_percent']:.1f}%",
                details=latest
            )
        elif latest['memory_percent'] > self.thresholds.MEMORY_SYSTEM_WARNING:
            self._create_alert(
                level='warning',
                message=f"High system memory usage: {latest['memory_percent']:.1f}%",
                details=latest
            )
    
    def _create_alert(self, level: str, message: str, details: Dict[str, Any]):
        """Create a performance alert."""
        alert = {
            'timestamp': timezone.now(),
            'level': level,
            'message': message,
            'details': details,
            'id': f"{level}_{int(time.time())}"
        }
        
        self.alerts.append(alert)
        
        # Log alert
        if level == 'critical':
            logger.error(f"CRITICAL PERFORMANCE ALERT: {message}")
        elif level == 'warning':
            logger.warning(f"PERFORMANCE WARNING: {message}")
        else:
            logger.info(f"PERFORMANCE INFO: {message}")
        
        # Cache for external access
        cache.set(f"perf_alert_{alert['id']}", alert, 3600)
    
    def _update_cached_stats(self):
        """Update cached performance statistics."""
        stats_summary = {
            **self.stats,
            'uptime_seconds': (timezone.now() - self.stats['uptime_start']).total_seconds(),
            'recent_alerts': len([a for a in self.alerts if 
                                (timezone.now() - a['timestamp']).total_seconds() < 3600]),
            'monitoring_active': self.is_monitoring,
            'last_updated': timezone.now().isoformat()
        }
        
        cache.set('dashboard_performance_stats', stats_summary, 300)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'statistics': self.stats.copy(),
            'recent_alerts': [
                {**alert, 'timestamp': alert['timestamp'].isoformat()}
                for alert in list(self.alerts)[-10:]  # Last 10 alerts
            ],
            'operation_performance': {},
            'system_status': 'unknown',
            'recommendations': []
        }
        
        # Add performance data for each operation
        for operation, metrics in self.metrics.items():
            if metrics:
                recent_metrics = list(metrics)[-10:]
                response_times = [m.duration_ms for m in recent_metrics]
                
                summary['operation_performance'][operation] = {
                    'average_response_time_ms': statistics.mean(response_times),
                    'median_response_time_ms': statistics.median(response_times),
                    'max_response_time_ms': max(response_times),
                    'min_response_time_ms': min(response_times),
                    'sample_size': len(response_times),
                    'cache_hit_rate': (sum(1 for m in recent_metrics if m.cache_hit) / len(recent_metrics)) * 100,
                    'error_rate': (sum(1 for m in recent_metrics if m.error) / len(recent_metrics)) * 100
                }
        
        # Determine system status
        critical_alerts = [a for a in self.alerts if a['level'] == 'critical' and 
                          (timezone.now() - a['timestamp']).total_seconds() < 3600]
        warning_alerts = [a for a in self.alerts if a['level'] == 'warning' and 
                         (timezone.now() - a['timestamp']).total_seconds() < 3600]
        
        if critical_alerts:
            summary['system_status'] = 'critical'
        elif warning_alerts:
            summary['system_status'] = 'warning'
        else:
            summary['system_status'] = 'healthy'
        
        # Generate recommendations
        summary['recommendations'] = self._generate_recommendations()
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Check dashboard refresh performance
        if 'dashboard_refresh' in self.metrics:
            refresh_metrics = list(self.metrics['dashboard_refresh'])[-10:]
            if refresh_metrics:
                avg_time = statistics.mean(m.duration_ms for m in refresh_metrics)
                if avg_time > 500:
                    recommendations.append(
                        "Dashboard refresh exceeds 500ms target - consider cache warming or query optimization"
                    )
        
        # Check cache hit rates
        low_cache_operations = []
        for operation, metrics in self.metrics.items():
            recent_metrics = list(metrics)[-10:]
            if recent_metrics:
                cache_hit_rate = (sum(1 for m in recent_metrics if m.cache_hit) / len(recent_metrics)) * 100
                if cache_hit_rate < 70:
                    low_cache_operations.append(operation)
        
        if low_cache_operations:
            recommendations.append(
                f"Low cache hit rates detected in: {', '.join(low_cache_operations)} - review caching strategy"
            )
        
        # Check system resources
        if self.system_metrics:
            latest_system = self.system_metrics[-1]
            if latest_system['memory_percent'] > 80:
                recommendations.append("High system memory usage - consider memory optimization")
            if latest_system['cpu_percent'] > 70:
                recommendations.append("High CPU usage - consider load balancing or optimization")
        
        # Check error rates
        high_error_operations = []
        for operation, metrics in self.metrics.items():
            recent_metrics = list(metrics)[-10:]
            if recent_metrics:
                error_rate = (sum(1 for m in recent_metrics if m.error) / len(recent_metrics)) * 100
                if error_rate > 5:  # More than 5% error rate
                    high_error_operations.append(operation)
        
        if high_error_operations:
            recommendations.append(
                f"High error rates in: {', '.join(high_error_operations)} - investigate and fix issues"
            )
        
        if not recommendations:
            recommendations.append("Performance is within acceptable ranges - continue monitoring")
        
        return recommendations


# Global monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        _performance_monitor.start_monitoring()
    return _performance_monitor


# Decorator for automatic performance monitoring
def monitor_performance(operation_name: str):
    """Decorator to automatically monitor function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                duration_ms = (end_time - start_time) * 1000
                memory_usage = end_memory - start_memory
                
                # Determine cache hit (simplified)
                cache_hit = hasattr(func, '_cache_hit') or 'cache' in operation_name.lower()
                
                # Extract user ID if available
                user_id = None
                if args and hasattr(args[0], 'user'):
                    user_id = getattr(args[0].user, 'id', None)
                
                metric = PerformanceMetric(
                    timestamp=timezone.now(),
                    operation=operation_name,
                    duration_ms=duration_ms,
                    memory_usage_mb=memory_usage,
                    cache_hit=cache_hit,
                    user_id=user_id,
                    error=error
                )
                
                monitor.record_metric(metric)
        
        return wrapper
    return decorator


# Convenience functions
def record_dashboard_refresh(duration_ms: float, cache_hit: bool = False, user_id: int = None, error: str = None):
    """Record dashboard refresh performance metric."""
    monitor = get_performance_monitor()
    metric = PerformanceMetric(
        timestamp=timezone.now(),
        operation='dashboard_refresh',
        duration_ms=duration_ms,
        memory_usage_mb=0.0,  # Not measured in this context
        cache_hit=cache_hit,
        user_id=user_id,
        error=error
    )
    monitor.record_metric(metric)


def get_performance_status() -> Dict[str, Any]:
    """Get current performance status."""
    monitor = get_performance_monitor()
    return monitor.get_performance_summary()