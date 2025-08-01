"""
Celery Monitoring and Management Tools for SenangKira Dashboard

This module provides monitoring capabilities for the Celery task system,
including real-time metrics, task tracking, and performance analysis.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from django.utils import timezone
from django.core.cache import cache
from celery import current_app

logger = logging.getLogger(__name__)

class CeleryMonitor:
    """Monitor Celery workers and tasks."""
    
    def __init__(self):
        self.app = current_app
        self.inspector = current_app.control.inspect()
        
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics about Celery workers."""
        try:
            # Get active workers
            active_workers = self.inspector.active()
            if active_workers is None:
                active_workers = {}
                
            # Get worker stats
            worker_stats = self.inspector.stats()
            if worker_stats is None:
                worker_stats = {}
                
            # Get registered tasks
            registered_tasks = self.inspector.registered()
            if registered_tasks is None:
                registered_tasks = {}
                
            # Get scheduled tasks
            scheduled_tasks = self.inspector.scheduled()
            if scheduled_tasks is None:
                scheduled_tasks = {}
                
            # Get active tasks
            active_tasks = self.inspector.active()
            if active_tasks is None:
                active_tasks = {}
                
            return {
                'workers': {
                    'count': len(active_workers),
                    'details': active_workers
                },
                'stats': worker_stats,
                'registered_tasks': registered_tasks,
                'scheduled_tasks': len(scheduled_tasks) if scheduled_tasks else 0,
                'active_tasks': len(active_tasks) if active_tasks else 0,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting worker stats: {e}")
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent task execution history."""
        try:
            # This would typically come from a result backend or custom tracking
            # For now, we'll use cache to simulate task history
            task_history_key = 'celery_task_history'
            history = cache.get(task_history_key, [])
            
            # Return last N tasks
            return history[-limit:] if history else []
            
        except Exception as e:
            logger.error(f"Error getting task history: {e}")
            return []
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about task queues."""
        try:
            # Get queue lengths
            queue_lengths = self.inspector.active_queues()
            if queue_lengths is None:
                queue_lengths = {}
                
            queue_stats = {}
            for worker, queues in queue_lengths.items():
                for queue in queues:
                    queue_name = queue['name']
                    if queue_name not in queue_stats:
                        queue_stats[queue_name] = {
                            'name': queue_name,
                            'workers': [],
                            'count': 0
                        }
                    queue_stats[queue_name]['workers'].append(worker)
                    queue_stats[queue_name]['count'] += 1
                    
            return {
                'queues': queue_stats,
                'total_queues': len(queue_stats),
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for Celery tasks."""
        try:
            # Get task history for analysis
            task_history = self.get_task_history(100)
            
            if not task_history:
                return {
                    'message': 'No task history available',
                    'timestamp': timezone.now().isoformat()
                }
            
            # Analyze task performance
            task_metrics = {}
            total_duration = 0
            successful_tasks = 0
            failed_tasks = 0
            
            for task in task_history:
                task_name = task.get('name', 'unknown')
                if task_name not in task_metrics:
                    task_metrics[task_name] = {
                        'count': 0,
                        'total_duration': 0,
                        'successful': 0,
                        'failed': 0,
                        'avg_duration': 0
                    }
                
                duration = task.get('duration', 0)
                task_metrics[task_name]['count'] += 1
                task_metrics[task_name]['total_duration'] += duration
                total_duration += duration
                
                if task.get('status') == 'success':
                    task_metrics[task_name]['successful'] += 1
                    successful_tasks += 1
                elif task.get('status') == 'failure':
                    task_metrics[task_name]['failed'] += 1
                    failed_tasks += 1
            
            # Calculate averages
            for task_name, metrics in task_metrics.items():
                if metrics['count'] > 0:
                    metrics['avg_duration'] = metrics['total_duration'] / metrics['count']
            
            overall_avg_duration = total_duration / len(task_history) if task_history else 0
            success_rate = (successful_tasks / len(task_history) * 100) if task_history else 0
            
            return {
                'task_metrics': task_metrics,
                'overall_stats': {
                    'total_tasks': len(task_history),
                    'successful_tasks': successful_tasks,
                    'failed_tasks': failed_tasks,
                    'success_rate': round(success_rate, 2),
                    'overall_avg_duration': round(overall_avg_duration, 3),
                    'total_duration': round(total_duration, 3)
                },
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            worker_stats = self.get_worker_stats()
            queue_stats = self.get_queue_stats()
            performance_metrics = self.get_performance_metrics()
            
            # Determine health status
            worker_count = worker_stats.get('workers', {}).get('count', 0)
            active_tasks = worker_stats.get('active_tasks', 0)
            success_rate = performance_metrics.get('overall_stats', {}).get('success_rate', 0)
            
            if worker_count == 0:
                health_status = 'critical'
                health_message = 'No active workers'
            elif success_rate < 80:
                health_status = 'warning'
                health_message = 'Low task success rate'
            elif active_tasks > 100:
                health_status = 'warning'
                health_message = 'High number of active tasks'
            else:
                health_status = 'healthy'
                health_message = 'System is operating normally'
            
            return {
                'status': health_status,
                'message': health_message,
                'worker_count': worker_count,
                'active_tasks': active_tasks,
                'success_rate': success_rate,
                'worker_stats': worker_stats,
                'queue_stats': queue_stats,
                'performance_metrics': performance_metrics,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                'status': 'unknown',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }

class CeleryTaskTracker:
    """Track individual task execution for monitoring and debugging."""
    
    def __init__(self):
        self.cache_key_prefix = 'celery_task_tracking'
        
    def track_task_start(self, task_id: str, task_name: str, args: tuple = (), kwargs: dict = None):
        """Track when a task starts."""
        try:
            tracking_info = {
                'task_id': task_id,
                'name': task_name,
                'args': args,
                'kwargs': kwargs or {},
                'started_at': timezone.now().isoformat(),
                'status': 'started',
                'duration': 0
            }
            
            cache_key = f"{self.cache_key_prefix}_{task_id}"
            cache.set(cache_key, tracking_info, 86400)  # Cache for 24 hours
            
            # Add to history
            self._add_to_history(tracking_info)
            
        except Exception as e:
            logger.error(f"Error tracking task start: {e}")
    
    def track_task_completion(self, task_id: str, success: bool = True, result: Any = None, error: str = None):
        """Track when a task completes."""
        try:
            cache_key = f"{self.cache_key_prefix}_{task_id}"
            tracking_info = cache.get(cache_key)
            
            if tracking_info:
                # Calculate duration
                started_at = datetime.fromisoformat(tracking_info['started_at'])
                duration = (timezone.now() - started_at).total_seconds()
                
                # Update tracking info
                tracking_info.update({
                    'completed_at': timezone.now().isoformat(),
                    'status': 'success' if success else 'failure',
                    'duration': round(duration, 3),
                    'result': result,
                    'error': error
                })
                
                # Update cache
                cache.set(cache_key, tracking_info, 86400)
                
                # Add to history
                self._add_to_history(tracking_info)
                
        except Exception as e:
            logger.error(f"Error tracking task completion: {e}")
    
    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific task."""
        try:
            cache_key = f"{self.cache_key_prefix}_{task_id}"
            return cache.get(cache_key)
        except Exception as e:
            logger.error(f"Error getting task details: {e}")
            return None
    
    def _add_to_history(self, tracking_info: Dict[str, Any]):
        """Add task tracking info to history."""
        try:
            history_key = f"{self.cache_key_prefix}_history"
            history = cache.get(history_key, [])
            
            # Add new entry
            history.append(tracking_info)
            
            # Keep only last 1000 entries
            if len(history) > 1000:
                history = history[-1000:]
            
            # Cache updated history
            cache.set(history_key, history, 86400)
            
        except Exception as e:
            logger.error(f"Error adding to history: {e}")

# Global instances
celery_monitor = CeleryMonitor()
task_tracker = CeleryTaskTracker()

# Decorator for automatic task tracking
def track_celery_task(func):
    """Decorator to automatically track Celery task execution."""
    def wrapper(*args, **kwargs):
        import uuid
        task_id = str(uuid.uuid4())
        task_name = func.__name__
        
        # Track task start
        task_tracker.track_task_start(task_id, task_name, args, kwargs)
        
        try:
            # Execute task
            result = func(*args, **kwargs)
            
            # Track successful completion
            task_tracker.track_task_completion(task_id, success=True, result=result)
            
            return result
            
        except Exception as e:
            # Track failed completion
            task_tracker.track_task_completion(task_id, success=False, error=str(e))
            raise
            
    return wrapper

# Utility functions for monitoring endpoints
def get_celery_status() -> Dict[str, Any]:
    """Get comprehensive Celery status for monitoring APIs."""
    return celery_monitor.get_system_health()

def get_recent_tasks(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent task executions."""
    return celery_monitor.get_task_history(limit)

def get_worker_information() -> Dict[str, Any]:
    """Get detailed worker information."""
    return celery_monitor.get_worker_stats()

def get_queue_information() -> Dict[str, Any]:
    """Get detailed queue information."""
    return celery_monitor.get_queue_stats()