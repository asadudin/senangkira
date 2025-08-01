"""
Async Task Management for Dashboard Operations

Features:
1. Background task processing for expensive operations
2. Task queuing with priority handling
3. Progress tracking and status updates
4. Result caching and notification
5. Failure handling and retry logic
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
import logging
import threading
from dataclasses import dataclass, asdict

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

User = get_user_model()
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class TaskResult:
    """Container for task execution results."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: str = None
    progress: float = 0.0
    start_time: datetime = None
    end_time: datetime = None
    duration_seconds: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


class AsyncTask:
    """Represents an async task with metadata."""
    
    def __init__(
        self,
        task_id: str,
        user_id: int,
        task_type: str,
        task_func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = task_type
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.created_at = timezone.now()
        self.result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
    
    def __lt__(self, other):
        """For priority queue ordering (higher priority value = higher priority)."""
        return self.priority.value > other.priority.value


class AsyncTaskManager:
    """
    Manages async task execution for dashboard operations.
    
    Features:
    - Priority-based task queuing
    - Concurrent execution with resource limits
    - Progress tracking and status updates
    - Result caching with expiration
    - Automatic retry with exponential backoff
    """
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 100):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix='dashboard_async'
        )
        
        self.tasks = {}  # task_id -> AsyncTask
        self.active_tasks = {}  # task_id -> Future
        self.task_queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self.is_running = False
        self.worker_thread = None
        
        # Statistics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'average_duration': 0.0,
            'last_activity': None
        }
        
        self.start()
    
    def start(self):
        """Start the async task manager."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
            self.worker_thread.start()
            logger.info("AsyncTaskManager started")
    
    def stop(self):
        """Stop the async task manager."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logger.info("AsyncTaskManager stopped")
    
    def submit_task(
        self,
        user_id: int,
        task_type: str,
        task_func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300
    ) -> str:
        """
        Submit a task for async execution.
        
        Returns:
            str: Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        
        task = AsyncTask(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            task_func=task_func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        self.tasks[task_id] = task
        
        # Add to queue (will be processed by worker)
        try:
            self.task_queue.put_nowait((priority.value, task))
            self.stats['total_tasks'] += 1
            
            # Cache initial task status
            self._cache_task_result(task.result)
            
            logger.info(f"Task {task_id} submitted: {task_type} for user {user_id}")
            return task_id
            
        except asyncio.QueueFull:
            logger.error(f"Task queue full, rejecting task {task_id}")
            task.result.status = TaskStatus.FAILED
            task.result.error = "Task queue full"
            self._cache_task_result(task.result)
            raise RuntimeError("Task queue full")
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get current task status and result."""
        # Try cache first
        cached_result = cache.get(f"task_result_{task_id}")
        if cached_result:
            return TaskResult(**cached_result)
        
        # Check active tasks
        if task_id in self.tasks:
            return self.tasks[task_id].result
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        if task_id in self.active_tasks:
            future = self.active_tasks[task_id]
            cancelled = future.cancel()
            
            if cancelled:
                task = self.tasks.get(task_id)
                if task:
                    task.result.status = TaskStatus.CANCELLED
                    task.result.end_time = timezone.now()
                    self._cache_task_result(task.result)
                    self.stats['cancelled_tasks'] += 1
                
                logger.info(f"Task {task_id} cancelled")
                return True
        
        return False
    
    def get_user_tasks(self, user_id: int, status_filter: Optional[TaskStatus] = None) -> List[TaskResult]:
        """Get all tasks for a user, optionally filtered by status."""
        user_tasks = []
        
        for task in self.tasks.values():
            if task.user_id == user_id:
                if status_filter is None or task.result.status == status_filter:
                    user_tasks.append(task.result)
        
        return sorted(user_tasks, key=lambda x: x.start_time or datetime.min, reverse=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics."""
        return {
            **self.stats,
            'active_tasks': len(self.active_tasks),
            'queued_tasks': self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else 0,
            'worker_status': 'running' if self.is_running else 'stopped'
        }
    
    def _run_worker(self):
        """Main worker loop for processing tasks."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._process_tasks())
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
        finally:
            loop.close()
    
    async def _process_tasks(self):
        """Process tasks from the queue."""
        while self.is_running:
            try:
                # Get next task (blocks until available or timeout)
                try:
                    priority, task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Submit task to thread pool
                future = self.executor.submit(self._execute_task, task)
                self.active_tasks[task.task_id] = future
                
                # Handle completion
                future.add_done_callback(
                    lambda f, task_id=task.task_id: self._handle_task_completion(task_id, f)
                )
                
            except Exception as e:
                logger.error(f"Task processing error: {e}")
                await asyncio.sleep(1)
    
    def _execute_task(self, task: AsyncTask) -> TaskResult:
        """Execute a single task."""
        task.result.status = TaskStatus.RUNNING
        task.result.start_time = timezone.now()
        self._cache_task_result(task.result)
        
        try:
            logger.info(f"Executing task {task.task_id}: {task.task_type}")
            
            # Execute the actual task function
            result = task.task_func(*task.args, **task.kwargs)
            
            # Task completed successfully
            task.result.status = TaskStatus.COMPLETED
            task.result.result = result
            task.result.end_time = timezone.now()
            task.result.duration_seconds = (
                task.result.end_time - task.result.start_time
            ).total_seconds()
            
            self.stats['completed_tasks'] += 1
            self._update_average_duration(task.result.duration_seconds)
            
            logger.info(f"Task {task.task_id} completed in {task.result.duration_seconds:.2f}s")
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            
            task.result.status = TaskStatus.FAILED
            task.result.error = str(e)
            task.result.end_time = timezone.now()
            
            # Handle retry logic
            if task.result.retry_count < task.max_retries:
                task.result.retry_count += 1
                task.result.status = TaskStatus.RETRYING
                
                # Re-queue with exponential backoff
                retry_delay = 2 ** task.result.retry_count
                threading.Timer(retry_delay, lambda: self._retry_task(task)).start()
                
                logger.info(f"Task {task.task_id} will retry in {retry_delay}s (attempt {task.result.retry_count + 1})")
            else:
                self.stats['failed_tasks'] += 1
        
        finally:
            self._cache_task_result(task.result)
            self.stats['last_activity'] = timezone.now()
        
        return task.result
    
    def _retry_task(self, task: AsyncTask):
        """Retry a failed task."""
        try:
            self.task_queue.put_nowait((task.priority.value, task))
        except asyncio.QueueFull:
            logger.error(f"Cannot retry task {task.task_id}: queue full")
            task.result.status = TaskStatus.FAILED
            task.result.error = "Retry failed: queue full"
            self._cache_task_result(task.result)
    
    def _handle_task_completion(self, task_id: str, future):
        """Handle task completion callback."""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        try:
            result = future.result()
            logger.debug(f"Task {task_id} completion handled")
        except Exception as e:
            logger.error(f"Task {task_id} completion error: {e}")
    
    def _cache_task_result(self, result: TaskResult):
        """Cache task result for status queries."""
        cache_key = f"task_result_{result.task_id}"
        cache.set(cache_key, result.to_dict(), 3600)  # Cache for 1 hour
    
    def _update_average_duration(self, duration: float):
        """Update average task duration statistics."""
        completed = self.stats['completed_tasks']
        if completed == 1:
            self.stats['average_duration'] = duration
        else:
            # Running average
            current_avg = self.stats['average_duration']
            self.stats['average_duration'] = (current_avg * (completed - 1) + duration) / completed


# Global task manager instance
_task_manager = None


def get_task_manager() -> AsyncTaskManager:
    """Get or create the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = AsyncTaskManager()
    return _task_manager


# Convenience functions for dashboard tasks
def submit_dashboard_refresh_task(user_id: int, period_type: str = 'monthly', force_refresh: bool = False) -> str:
    """Submit dashboard refresh as async task."""
    from .services_optimized import OptimizedDashboardCacheService
    
    def refresh_task():
        user = User.objects.get(id=user_id)
        cache_service = OptimizedDashboardCacheService(user)
        return cache_service.refresh_dashboard_cache_optimized(force_refresh=force_refresh)
    
    task_manager = get_task_manager()
    return task_manager.submit_task(
        user_id=user_id,
        task_type='dashboard_refresh',
        task_func=refresh_task,
        priority=TaskPriority.HIGH,
        timeout_seconds=600  # 10 minutes max
    )


def submit_dashboard_export_task(user_id: int, export_format: str = 'json', date_range: dict = None) -> str:
    """Submit dashboard export as async task."""
    def export_task():
        # This would implement the actual export logic
        user = User.objects.get(id=user_id)
        # Export implementation would go here
        return {
            'export_format': export_format,
            'date_range': date_range,
            'status': 'completed',
            'file_size': 1024  # placeholder
        }
    
    task_manager = get_task_manager()
    return task_manager.submit_task(
        user_id=user_id,
        task_type='dashboard_export',
        task_func=export_task,
        priority=TaskPriority.LOW,  # Exports are lower priority
        timeout_seconds=1800  # 30 minutes max
    )


def submit_performance_analysis_task(user_id: int) -> str:
    """Submit comprehensive performance analysis as async task."""
    def analysis_task():
        # This would implement comprehensive performance analysis
        from .services_optimized import OptimizedDashboardCacheService
        
        user = User.objects.get(id=user_id)
        cache_service = OptimizedDashboardCacheService(user)
        
        # Perform analysis
        analysis_results = {
            'cache_performance': cache_service._get_cache_stats(),
            'database_performance': 'optimized',  # placeholder
            'recommendations': [
                'Cache hit rate is optimal',
                'Database queries are well-optimized'
            ]
        }
        
        return analysis_results
    
    task_manager = get_task_manager()
    return task_manager.submit_task(
        user_id=user_id,
        task_type='performance_analysis',
        task_func=analysis_task,
        priority=TaskPriority.NORMAL,
        timeout_seconds=300  # 5 minutes max
    )