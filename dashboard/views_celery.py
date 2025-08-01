"""
Celery Monitoring API Endpoints for SenangKira Dashboard

This module provides REST API endpoints for monitoring Celery task execution,
worker status, queue health, and performance metrics.

Endpoints:
    - GET /api/dashboard/celery/status/ - Overall Celery system status
    - GET /api/dashboard/celery/workers/ - Worker information and statistics
    - GET /api/dashboard/celery/queues/ - Queue status and backlogs
    - GET /api/dashboard/celery/tasks/ - Recent task execution history
    - GET /api/dashboard/celery/tasks/{task_id}/ - Specific task details
    - POST /api/dashboard/celery/tasks/{task_name}/execute/ - Execute a task
"""

from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet

from senangkira.utils.permissions import IsOwnerOrReadOnly
from .celery_monitoring import get_celery_status, get_worker_information, get_queue_information, get_recent_tasks
from .tasks import refresh_dashboard_cache, warm_dashboard_cache, performance_analysis, export_dashboard_data, send_notification, cleanup_old_data

# Map task names to actual task functions
TASK_REGISTRY = {
    'refresh_dashboard_cache': refresh_dashboard_cache,
    'warm_dashboard_cache': warm_dashboard_cache,
    'performance_analysis': performance_analysis,
    'export_dashboard_data': export_dashboard_data,
    'send_notification': send_notification,
    'cleanup_old_data': cleanup_old_data,
}

class CeleryMonitoringViewSet(ViewSet):
    """
    ViewSet for monitoring Celery task execution and system health.
    
    Provides endpoints for:
    - System status monitoring
    - Worker and queue inspection
    - Task execution tracking
    - Manual task triggering
    """
    
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        GET /api/dashboard/celery/status/
        
        Get overall Celery system health status.
        """
        try:
            status_data = get_celery_status()
            return Response(status_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve Celery status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def workers(self, request):
        """
        GET /api/dashboard/celery/workers/
        
        Get detailed information about Celery workers.
        """
        try:
            worker_data = get_worker_information()
            return Response(worker_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve worker information: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def queues(self, request):
        """
        GET /api/dashboard/celery/queues/
        
        Get detailed information about task queues.
        """
        try:
            queue_data = get_queue_information()
            return Response(queue_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve queue information: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def tasks(self, request):
        """
        GET /api/dashboard/celery/tasks/
        
        Get recent task execution history.
        """
        try:
            limit = int(request.query_params.get('limit', 50))
            task_history = get_recent_tasks(limit)
            return Response({
                'tasks': task_history,
                'count': len(task_history)
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve task history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def task_detail(self, request, pk=None):
        """
        GET /api/dashboard/celery/tasks/{task_id}/
        
        Get detailed information about a specific task.
        """
        try:
            from .celery_monitoring import task_tracker
            task_details = task_tracker.get_task_details(pk)
            
            if task_details:
                return Response(task_details)
            else:
                return Response(
                    {'error': 'Task not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve task details: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def execute_task(self, request, pk=None):
        """
        POST /api/dashboard/celery/tasks/{task_name}/execute/
        
        Execute a specific task with optional parameters.
        """
        task_name = pk
        
        if task_name not in TASK_REGISTRY:
            return Response(
                {'error': f'Unknown task: {task_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get task parameters from request
            user_id = request.data.get('user_id')
            task_args = request.data.get('args', [])
            task_kwargs = request.data.get('kwargs', {})
            
            # Special handling for user-specific tasks
            task_func = TASK_REGISTRY[task_name]
            
            if user_id and 'user_id' not in task_kwargs:
                task_kwargs['user_id'] = user_id
            
            # Execute task asynchronously
            result = task_func.delay(*task_args, **task_kwargs)
            
            return Response({
                'task_id': result.id,
                'task_name': task_name,
                'status': 'queued',
                'message': f'Task {task_name} queued successfully'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to execute task {task_name}: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def health_check(self, request):
        """
        POST /api/dashboard/celery/health_check/
        
        Perform a comprehensive health check of the Celery system.
        """
        try:
            # Get system status
            system_status = get_celery_status()
            
            # Additional health checks could be added here
            health_report = {
                'system_status': system_status,
                'timestamp': system_status.get('timestamp'),
                'healthy': system_status.get('status') == 'healthy',
                'recommendations': []
            }
            
            # Add recommendations based on status
            if system_status.get('status') == 'warning':
                health_report['recommendations'].append('System is operating with warnings - check logs')
            elif system_status.get('status') == 'critical':
                health_report['recommendations'].append('System is in critical state - immediate attention required')
            elif system_status.get('status') == 'unknown':
                health_report['recommendations'].append('Unable to determine system status')
            
            return Response(health_report)
            
        except Exception as e:
            return Response(
                {'error': f'Health check failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )