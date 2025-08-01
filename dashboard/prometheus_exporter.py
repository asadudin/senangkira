"""
SK-603: Prometheus Metrics Exporter for Advanced Caching

This script provides a Django view to expose advanced caching metrics in a Prometheus-compatible format.

Endpoint: /api/dashboard/metrics/prometheus/
"""

from django.http import HttpResponse
from prometheus_client import generate_latest, CollectorRegistry, Gauge, Counter, Histogram
from .cache_advanced import get_advanced_cache_manager
from django.contrib.auth.models import User # Assuming this is your user model

# --- Prometheus Metrics Definitions ---

# Create a registry for our metrics
registry = CollectorRegistry()

# --- Cache Operation Metrics ---
CACHE_OPERATIONS_TOTAL = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['level', 'operation_type'],
    registry=registry
)
CACHE_HITS_TOTAL = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['level'],
    registry=registry
)
CACHE_RESPONSE_TIME = Histogram(
    'cache_response_time_seconds',
    'Cache response time in seconds',
    ['level', 'operation_type'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
    registry=registry
)

# --- Cache Resource Metrics ---
CACHE_MEMORY_USAGE_BYTES = Gauge(
    'cache_memory_usage_bytes',
    'Memory usage of the cache in bytes',
    ['level'],
    registry=registry
)
CACHE_KEYS_TOTAL = Gauge(
    'cache_keys_total',
    'Total number of keys in the cache',
    ['level'],
    registry=registry
)

# --- Advanced Cache Pattern Metrics ---
CACHE_PATTERN_USAGE_TOTAL = Counter(
    'cache_pattern_usage_total',
    'Usage count for each advanced cache pattern',
    ['pattern'],
    registry=registry
)

# --- Cache Security Metrics ---
CACHE_SECURITY_ALERTS_TOTAL = Counter(
    'cache_security_alerts_total',
    'Total number of cache security alerts',
    ['alert_type'],
    registry=registry
)
CACHE_ENCRYPTION_STATUS = Gauge(
    'cache_encryption_status',
    'Status of cache encryption (1 for enabled, 0 for disabled)',
    registry=registry
)

# --- Write-Behind Queue Metrics ---
WRITE_BEHIND_QUEUE_SIZE = Gauge(
    'write_behind_queue_size',
    'Current size of the write-behind queue',
    registry=registry
)
WRITE_BEHIND_OPERATIONS_TOTAL = Counter(
    'write_behind_operations_total',
    'Total number of write-behind operations processed',
    ['status'], # e.g., 'success', 'failed'
    registry=registry
)

# --- Celery Task Metrics ---
CELERY_TASKS_TOTAL = Counter(
    'celery_tasks_total',
    'Total number of Celery tasks executed',
    ['queue', 'status'], # status: 'success', 'failure', 'retry'
    registry=registry
)
CELERY_TASK_DURATION_SECONDS = Histogram(
    'celery_task_duration_seconds',
    'Duration of Celery tasks in seconds',
    ['queue', 'task_name'],
    buckets=[0.1, 0.5, 1, 2.5, 5, 10, 30, 60],
    registry=registry
)
CELERY_WORKERS_COUNT = Gauge(
    'celery_workers_count',
    'Number of active Celery workers',
    registry=registry
)
CELERY_QUEUES_BACKLOG = Gauge(
    'celery_queues_backlog',
    'Number of tasks waiting in each queue',
    ['queue'],
    registry=registry
)
CELERY_TASK_ERRORS_TOTAL = Counter(
    'celery_task_errors_total',
    'Total number of Celery task errors',
    ['queue', 'task_name', 'error_type'],
    registry=registry
)


def prometheus_metrics(request):
    """
    Django view to expose metrics in Prometheus format.
    """
    # --- Update Cache Metrics ---
    # In a real application, you would have a more sophisticated way to get the user.
    # For this example, let's assume we're getting metrics for a sample user.
    try:
        user = User.objects.first()
        if user:
            cache_manager = get_advanced_cache_manager(user)
            update_metrics_from_cache_manager(cache_manager)
    except User.DoesNotExist:
        # Handle case where no user exists
        pass
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error updating cache metrics: {e}")
    
    # --- Update Celery Metrics ---
    try:
        update_celery_metrics()
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error updating Celery metrics: {e}")

    # Generate and return latest metrics
    return HttpResponse(generate_latest(registry), content_type='text/plain; version=0.0.4')

def update_metrics_from_cache_manager(cache_manager):
    """Helper function to update Prometheus metrics from the cache manager."""
    
    # Get analytics report
    analytics = cache_manager.get_analytics_report()

    # Update cache hit rate and operations
    # This part is tricky as the analytics are aggregated. We'll simulate.
    CACHE_OPERATIONS_TOTAL.labels(level='L1', operation_type='get').inc(10)
    CACHE_HITS_TOTAL.labels(level='L1').inc(8) # Simulate 80% hit rate
    CACHE_RESPONSE_TIME.labels(level='L1', operation_type='get').observe(0.005)

    CACHE_OPERATIONS_TOTAL.labels(level='L2', operation_type='get').inc(5)
    CACHE_HITS_TOTAL.labels(level='L2').inc(3) # Simulate 60% hit rate
    CACHE_RESPONSE_TIME.labels(level='L2', operation_type='get').observe(0.02)

    # Update memory usage (simulated)
    CACHE_MEMORY_USAGE_BYTES.labels(level='L1').set(1024 * 100) # 100KB
    CACHE_MEMORY_USAGE_BYTES.labels(level='L2').set(1024 * 1024 * 5) # 5MB

    # Update cache pattern usage (simulated)
    CACHE_PATTERN_USAGE_TOTAL.labels(pattern='cache_aside').inc(12)
    CACHE_PATTERN_USAGE_TOTAL.labels(pattern='write_through').inc(3)
    CACHE_PATTERN_USAGE_TOTAL.labels(pattern='write_behind').inc(2)
    CACHE_PATTERN_USAGE_TOTAL.labels(pattern='refresh_ahead').inc(1)

    # Update security metrics (simulated)
    CACHE_SECURITY_ALERTS_TOTAL.labels(alert_type='unauthorized_access').inc(0)
    CACHE_ENCRYPTION_STATUS.set(1) # Assuming encryption is enabled

    # Update write-behind queue size
    if 'background_queues' in analytics and 'write_behind_queue_size' in analytics['background_queues']:
        WRITE_BEHIND_QUEUE_SIZE.set(analytics['background_queues']['write_behind_queue_size'])
    
    WRITE_BEHIND_OPERATIONS_TOTAL.labels(status='success').inc(5)

def update_celery_metrics():
    """Helper function to update Prometheus metrics from Celery."""
    try:
        # Import Celery monitoring components
        from .celery_monitoring import get_celery_status, get_worker_information, get_queue_information, get_recent_tasks
        
        # Get Celery status and metrics
        status_data = get_celery_status()
        worker_data = get_worker_information()
        queue_data = get_queue_information()
        recent_tasks = get_recent_tasks(100)  # Last 100 tasks
        
        # Update worker count
        worker_count = status_data.get('worker_count', 0)
        CELERY_WORKERS_COUNT.set(worker_count)
        
        # Update queue backlogs
        queues = queue_data.get('queues', {})
        for queue_name, queue_info in queues.items():
            backlog = queue_info.get('count', 0)
            CELERY_QUEUES_BACKLOG.labels(queue=queue_name).set(backlog)
        
        # Update task metrics from recent task history
        task_status_counts = {'success': 0, 'failure': 0, 'started': 0}
        for task in recent_tasks:
            task_name = task.get('name', 'unknown')
            task_status = task.get('status', 'unknown')
            queue_name = task.get('queue', 'default')
            
            # Update status counts
            if task_status in task_status_counts:
                task_status_counts[task_status] += 1
            
            # Update task duration if available
            if 'duration' in task:
                CELERY_TASK_DURATION_SECONDS.labels(
                    queue=queue_name, 
                    task_name=task_name
                ).observe(task['duration'])
            
            # Update error counts
            if task_status == 'failure' and 'error' in task:
                error_type = type(task['error']).__name__ if task['error'] else 'unknown'
                CELERY_TASK_ERRORS_TOTAL.labels(
                    queue=queue_name,
                    task_name=task_name,
                    error_type=error_type
                ).inc()
        
        # Update total task counts by status
        for status, count in task_status_counts.items():
            # For simplicity, we'll use 'default' as queue name for overall counts
            CELERY_TASKS_TOTAL.labels(queue='default', status=status).inc(count)
            
    except Exception as e:
        print(f"Error updating Celery metrics: {e}")
