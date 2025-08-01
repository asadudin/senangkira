"""
Task Monitoring Service for SenangKira.
Comprehensive task tracking, metrics collection, and alerting system.
"""
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max, Min
from django.core.cache import cache
from celery import current_app
from celery.app.control import Inspect

from ..models import TaskExecution, SystemHealthMetric, TaskAlert, TaskExecutionStatus, TaskPriority


logger = logging.getLogger(__name__)


class TaskMonitoringService:
    """Service for comprehensive task monitoring and tracking."""
    
    def __init__(self):
        self.app = current_app
        self.inspector = Inspect(app=current_app)
        self.cache_timeout = 300  # 5 minutes
    
    def track_task_execution(self, task_id: str, task_name: str, queue_name: str = 'default',
                           user=None, priority: str = TaskPriority.NORMAL, 
                           args: tuple = (), kwargs: dict = None) -> TaskExecution:
        """Track a new task execution."""
        try:
            task_execution = TaskExecution.objects.create(
                task_id=task_id,
                task_name=task_name,
                queue_name=queue_name,
                user=user,
                priority=priority,
                status=TaskExecutionStatus.PENDING,
                scheduled_at=timezone.now(),
                arguments=list(args) if args else [],
                keyword_arguments=kwargs or {}
            )
            
            logger.info(f"Tracking task execution: {task_name} ({task_id})")
            return task_execution
            
        except Exception as e:
            logger.error(f"Failed to track task execution {task_id}: {e}")
            raise
    
    def update_task_started(self, task_id: str, worker_name: str = "") -> bool:
        """Update task status to started."""
        try:
            task_execution = TaskExecution.objects.get(task_id=task_id)
            task_execution.mark_started(worker_name)
            
            logger.debug(f"Task started: {task_id}")
            return True
            
        except TaskExecution.DoesNotExist:
            logger.warning(f"Task execution not found for started task: {task_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update task started {task_id}: {e}")
            return False
    
    def update_task_completed(self, task_id: str, success: bool, result: Any = None, 
                            error: Exception = None, memory_usage: float = None) -> bool:
        """Update task status to completed."""
        try:
            task_execution = TaskExecution.objects.get(task_id=task_id)
            
            # Prepare result and error information
            result_summary = ""
            error_message = ""
            error_traceback = ""
            
            if success and result is not None:
                result_summary = str(result)[:1000]  # Limit summary length
            elif not success and error:
                error_message = str(error)[:1000]
                error_traceback = traceback.format_exc()[:5000]
            
            task_execution.mark_completed(
                success=success,
                result_summary=result_summary,
                error_message=error_message,
                error_traceback=error_traceback,
                memory_usage=memory_usage
            )
            
            # Check for alerting conditions
            if not success:
                self._check_failure_alerts(task_execution)
            
            logger.debug(f"Task completed: {task_id} (success: {success})")
            return True
            
        except TaskExecution.DoesNotExist:
            logger.warning(f"Task execution not found for completed task: {task_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update task completed {task_id}: {e}")
            return False
    
    def update_task_retry(self, task_id: str) -> bool:
        """Update task retry count."""
        try:
            task_execution = TaskExecution.objects.get(task_id=task_id)
            task_execution.increment_retry()
            
            # Check if retry count is high
            if task_execution.retry_count >= 3:
                self._create_alert(
                    alert_type='task_failure',
                    severity='warning',
                    title=f'High retry count for task {task_execution.task_name}',
                    message=f'Task {task_id} has been retried {task_execution.retry_count} times',
                    task_execution=task_execution
                )
            
            logger.debug(f"Task retry: {task_id} (attempt {task_execution.retry_count})")
            return True
            
        except TaskExecution.DoesNotExist:
            logger.warning(f"Task execution not found for retry task: {task_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update task retry {task_id}: {e}")
            return False
    
    def get_task_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive task metrics for the specified time period."""
        try:
            cutoff_time = timezone.now() - timedelta(hours=hours)
            
            # Get task executions in time period
            executions = TaskExecution.objects.filter(scheduled_at__gte=cutoff_time)
            
            # Basic counts
            total_tasks = executions.count()
            completed_tasks = executions.filter(status__in=[TaskExecutionStatus.SUCCESS, TaskExecutionStatus.FAILURE]).count()
            successful_tasks = executions.filter(status=TaskExecutionStatus.SUCCESS).count()
            failed_tasks = executions.filter(status=TaskExecutionStatus.FAILURE).count()
            pending_tasks = executions.filter(status=TaskExecutionStatus.PENDING).count()
            active_tasks = executions.filter(status=TaskExecutionStatus.STARTED).count()
            
            # Success rate
            success_rate = (successful_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
            
            # Duration statistics
            completed_with_duration = executions.filter(duration__isnull=False)
            duration_stats = completed_with_duration.aggregate(
                avg_duration=Avg('duration'),
                min_duration=Min('duration'),
                max_duration=Max('duration')
            )
            
            # Task breakdown by name
            task_breakdown = {}
            task_stats = executions.values('task_name').annotate(
                total=Count('id'),
                successful=Count('id', filter=Q(status=TaskExecutionStatus.SUCCESS)),
                failed=Count('id', filter=Q(status=TaskExecutionStatus.FAILURE)),
                avg_duration=Avg('duration', filter=Q(duration__isnull=False))
            )
            
            for stat in task_stats:
                task_name = stat['task_name']
                task_breakdown[task_name] = {
                    'total': stat['total'],
                    'successful': stat['successful'],
                    'failed': stat['failed'],
                    'success_rate': (stat['successful'] / stat['total'] * 100) if stat['total'] > 0 else 0,
                    'avg_duration': round(stat['avg_duration'], 3) if stat['avg_duration'] else None
                }
            
            # Queue breakdown
            queue_breakdown = {}
            queue_stats = executions.values('queue_name').annotate(
                total=Count('id'),
                successful=Count('id', filter=Q(status=TaskExecutionStatus.SUCCESS)),
                failed=Count('id', filter=Q(status=TaskExecutionStatus.FAILURE))
            )
            
            for stat in queue_stats:
                queue_name = stat['queue_name']
                queue_breakdown[queue_name] = {
                    'total': stat['total'],
                    'successful': stat['successful'],
                    'failed': stat['failed'],
                    'success_rate': (stat['successful'] / stat['total'] * 100) if stat['total'] > 0 else 0
                }
            
            return {
                'time_period_hours': hours,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'pending_tasks': pending_tasks,
                'active_tasks': active_tasks,
                'success_rate': round(success_rate, 2),
                'duration_stats': {
                    'avg_duration': round(duration_stats['avg_duration'], 3) if duration_stats['avg_duration'] else None,
                    'min_duration': round(duration_stats['min_duration'], 3) if duration_stats['min_duration'] else None,
                    'max_duration': round(duration_stats['max_duration'], 3) if duration_stats['max_duration'] else None
                },
                'task_breakdown': task_breakdown,
                'queue_breakdown': queue_breakdown,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get task metrics: {e}")
            return {'error': str(e), 'timestamp': timezone.now().isoformat()}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        try:
            # Check cache first
            cache_key = 'system_health_status'
            cached_health = cache.get(cache_key)
            if cached_health:
                return cached_health
            
            # Get Celery worker information
            worker_info = self._get_worker_information()
            
            # Get recent task metrics
            recent_metrics = self.get_task_metrics(hours=1)
            
            # Get current queue lengths
            queue_info = self._get_queue_information()
            
            # Determine overall health status
            health_status = self._calculate_health_status(worker_info, recent_metrics, queue_info)
            
            health_data = {
                'status': health_status['status'],
                'message': health_status['message'],
                'workers': {
                    'active': worker_info.get('active_workers', 0),
                    'total': worker_info.get('total_workers', 0)
                },
                'tasks': {
                    'pending': recent_metrics.get('pending_tasks', 0),
                    'active': recent_metrics.get('active_tasks', 0),
                    'success_rate': recent_metrics.get('success_rate', 0)
                },
                'queues': queue_info,
                'alerts': self._get_active_alerts_count(),
                'timestamp': timezone.now().isoformat()
            }
            
            # Cache for 1 minute
            cache.set(cache_key, health_data, 60)
            
            return health_data
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                'status': 'unknown',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def record_system_metrics(self) -> SystemHealthMetric:
        """Record current system metrics."""
        try:
            # Get worker information
            worker_info = self._get_worker_information()
            
            # Get task metrics for last hour
            task_metrics = self.get_task_metrics(hours=1)
            
            # Get queue information
            queue_info = self._get_queue_information()
            
            # Create health metric record
            health_metric = SystemHealthMetric.objects.create(
                active_workers=worker_info.get('active_workers', 0),
                total_workers=worker_info.get('total_workers', 0),
                pending_tasks=task_metrics.get('pending_tasks', 0),
                active_tasks=task_metrics.get('active_tasks', 0),
                completed_tasks_hourly=task_metrics.get('completed_tasks', 0),
                failed_tasks_hourly=task_metrics.get('failed_tasks', 0),
                avg_task_duration=task_metrics.get('duration_stats', {}).get('avg_duration'),
                success_rate=task_metrics.get('success_rate', 0),
                queue_lengths=queue_info
            )
            
            logger.info(f"Recorded system health metrics: {health_metric.id}")
            return health_metric
            
        except Exception as e:
            logger.error(f"Failed to record system metrics: {e}")
            raise
    
    def get_performance_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get detailed performance analytics."""
        try:
            cutoff_time = timezone.now() - timedelta(days=days)
            
            # Get task executions
            executions = TaskExecution.objects.filter(scheduled_at__gte=cutoff_time)
            
            # Performance trends (daily breakdown)
            daily_stats = []
            for i in range(days):
                day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                day_executions = executions.filter(scheduled_at__gte=day_start, scheduled_at__lt=day_end)
                
                total = day_executions.count()
                successful = day_executions.filter(status=TaskExecutionStatus.SUCCESS).count()
                failed = day_executions.filter(status=TaskExecutionStatus.FAILURE).count()
                
                daily_stats.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'total_tasks': total,
                    'successful_tasks': successful,
                    'failed_tasks': failed,
                    'success_rate': (successful / total * 100) if total > 0 else 0
                })
            
            # Top failing tasks
            failing_tasks = executions.filter(status=TaskExecutionStatus.FAILURE).values('task_name').annotate(
                failure_count=Count('id')
            ).order_by('-failure_count')[:10]
            
            # Slowest tasks
            slow_tasks = executions.filter(duration__isnull=False).values('task_name').annotate(
                avg_duration=Avg('duration'),
                max_duration=Max('duration')
            ).order_by('-avg_duration')[:10]
            
            # Queue performance
            queue_performance = executions.values('queue_name').annotate(
                total=Count('id'),
                avg_duration=Avg('duration', filter=Q(duration__isnull=False)),
                success_rate=Count('id', filter=Q(status=TaskExecutionStatus.SUCCESS)) * 100.0 / Count('id')
            ).order_by('-total')
            
            return {
                'period_days': days,
                'daily_trends': daily_stats,
                'top_failing_tasks': list(failing_tasks),
                'slowest_tasks': list(slow_tasks),
                'queue_performance': list(queue_performance),
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance analytics: {e}")
            return {'error': str(e), 'generated_at': timezone.now().isoformat()}
    
    def _get_worker_information(self) -> Dict[str, Any]:
        """Get information about Celery workers."""
        try:
            active = self.inspector.active()
            registered = self.inspector.registered()
            stats = self.inspector.stats()
            
            active_workers = len(active) if active else 0
            total_workers = len(stats) if stats else active_workers
            
            return {
                'active_workers': active_workers,
                'total_workers': total_workers,
                'worker_details': {
                    'active': active or {},
                    'registered': registered or {},
                    'stats': stats or {}
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to get worker information: {e}")
            return {'active_workers': 0, 'total_workers': 0, 'worker_details': {}}
    
    def _get_queue_information(self) -> Dict[str, int]:
        """Get information about task queues."""
        try:
            active_queues = self.inspector.active_queues()
            if not active_queues:
                return {}
            
            queue_lengths = {}
            for worker, queues in active_queues.items():
                for queue in queues:
                    queue_name = queue['name']
                    if queue_name not in queue_lengths:
                        queue_lengths[queue_name] = 0
                    # Note: Celery doesn't provide queue length directly
                    # This would need to be implemented with Redis/broker inspection
                    queue_lengths[queue_name] += 1
            
            return queue_lengths
            
        except Exception as e:
            logger.warning(f"Failed to get queue information: {e}")
            return {}
    
    def _calculate_health_status(self, worker_info: Dict, task_metrics: Dict, queue_info: Dict) -> Dict[str, str]:
        """Calculate overall system health status."""
        active_workers = worker_info.get('active_workers', 0)
        success_rate = task_metrics.get('success_rate', 0)
        pending_tasks = task_metrics.get('pending_tasks', 0)
        
        if active_workers == 0:
            return {'status': 'critical', 'message': 'No active workers available'}
        elif success_rate < 70:
            return {'status': 'critical', 'message': f'Very low success rate: {success_rate:.1f}%'}
        elif success_rate < 85:
            return {'status': 'warning', 'message': f'Low success rate: {success_rate:.1f}%'}
        elif pending_tasks > 100:
            return {'status': 'warning', 'message': f'High task backlog: {pending_tasks} pending'}
        else:
            return {'status': 'healthy', 'message': 'System operating normally'}
    
    def _get_active_alerts_count(self) -> int:
        """Get count of active alerts."""
        return TaskAlert.objects.filter(resolved_at__isnull=True).count()
    
    def _check_failure_alerts(self, task_execution: TaskExecution):
        """Check if task failure should trigger alerts."""
        try:
            # Check for high failure rate in recent tasks of same type
            recent_time = timezone.now() - timedelta(hours=1)
            recent_executions = TaskExecution.objects.filter(
                task_name=task_execution.task_name,
                scheduled_at__gte=recent_time,
                status__in=[TaskExecutionStatus.SUCCESS, TaskExecutionStatus.FAILURE]
            )
            
            total_recent = recent_executions.count()
            failed_recent = recent_executions.filter(status=TaskExecutionStatus.FAILURE).count()
            
            if total_recent >= 5 and failed_recent / total_recent > 0.5:  # >50% failure rate
                self._create_alert(
                    alert_type='high_failure_rate',
                    severity='error',
                    title=f'High failure rate for {task_execution.task_name}',
                    message=f'Task {task_execution.task_name} has {failed_recent}/{total_recent} failures in the last hour',
                    task_execution=task_execution
                )
            
        except Exception as e:
            logger.error(f"Failed to check failure alerts: {e}")
    
    def _create_alert(self, alert_type: str, severity: str, title: str, message: str, 
                     task_execution: TaskExecution = None, metadata: Dict = None):
        """Create a new alert."""
        try:
            alert = TaskAlert.objects.create(
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                task_execution=task_execution,
                metadata=metadata or {}
            )
            
            logger.warning(f"Alert created: {alert.title}")
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None


# Global service instance
task_monitoring_service = TaskMonitoringService()