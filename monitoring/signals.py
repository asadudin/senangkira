"""
Celery task monitoring signals.
Automatically track task lifecycle events.
"""
import logging
from typing import Any, Dict

from celery import signals
from django.utils import timezone

from .services.task_monitor import task_monitoring_service

logger = logging.getLogger(__name__)


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal."""
    try:
        # Get task information
        task_name = task.name if task else sender
        queue_name = getattr(task, 'queue', 'default') if task else 'default'
        
        # Update task to started status
        task_monitoring_service.update_task_started(
            task_id=task_id,
            worker_name=kwds.get('worker', {}).get('hostname', '')
        )
        
        logger.debug(f"Task started: {task_name} ({task_id})")
        
    except Exception as e:
        logger.error(f"Error in task prerun handler: {e}")


@signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None,
                        retval=None, state=None, **kwds):
    """Handle task postrun signal."""
    try:
        # Determine success based on state
        success = state == 'SUCCESS'
        
        # Get error information from kwargs if available
        error = None
        if not success and 'einfo' in kwds:
            error = kwds['einfo']
        
        # Update task completion status
        task_monitoring_service.update_task_completed(
            task_id=task_id,
            success=success,
            result=retval,
            error=error
        )
        
        logger.debug(f"Task completed: {task.name if task else sender} ({task_id}) - {state}")
        
    except Exception as e:
        logger.error(f"Error in task postrun handler: {e}")


@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """Handle task retry signal."""
    try:
        # Update retry count
        task_monitoring_service.update_task_retry(task_id=task_id)
        
        logger.debug(f"Task retry: {sender} ({task_id}) - {reason}")
        
    except Exception as e:
        logger.error(f"Error in task retry handler: {e}")


@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Handle task failure signal."""
    try:
        # Update task with failure information
        task_monitoring_service.update_task_completed(
            task_id=task_id,
            success=False,
            error=exception
        )
        
        logger.warning(f"Task failed: {sender} ({task_id}) - {exception}")
        
    except Exception as e:
        logger.error(f"Error in task failure handler: {e}")


@signals.task_revoked.connect
def task_revoked_handler(sender=None, task_id=None, reason=None, **kwds):
    """Handle task revoked signal."""
    try:
        logger.info(f"Task revoked: {sender} ({task_id}) - {reason}")
        
    except Exception as e:
        logger.error(f"Error in task revoked handler: {e}")