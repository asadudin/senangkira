"""
API views for task monitoring system.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .models import TaskExecution, SystemHealthMetric, TaskAlert
from .serializers import (
    TaskExecutionSerializer, SystemHealthMetricSerializer, TaskAlertSerializer,
    TaskMetricsSerializer, SystemHealthSerializer, PerformanceAnalyticsSerializer
)
from .services.task_monitor import task_monitoring_service


class TaskExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for TaskExecution model."""
    
    queryset = TaskExecution.objects.all().order_by('-created_at')
    serializer_class = TaskExecutionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['task_name', 'status', 'queue_name', 'priority']
    search_fields = ['task_name', 'task_id', 'worker_name']
    ordering_fields = ['created_at', 'scheduled_at', 'duration', 'retry_count']


class SystemHealthMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SystemHealthMetric model."""
    
    queryset = SystemHealthMetric.objects.all().order_by('-recorded_at')
    serializer_class = SystemHealthMetricSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['recorded_at', 'success_rate', 'active_workers']


class TaskAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for TaskAlert model."""
    
    queryset = TaskAlert.objects.all().order_by('-triggered_at')
    serializer_class = TaskAlertSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['alert_type', 'severity', 'resolved_at']
    search_fields = ['title', 'message']
    ordering_fields = ['triggered_at', 'severity']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark alert as resolved."""
        alert = self.get_object()
        alert.resolve()
        return Response({'status': 'resolved'})
    
    @action(detail=False)
    def active(self, request):
        """Get active (unresolved) alerts."""
        queryset = self.get_queryset().filter(resolved_at__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MonitoringAPIViewSet(viewsets.ViewSet):
    """API endpoints for monitoring data."""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """Get task metrics for specified time period."""
        hours = int(request.query_params.get('hours', 24))
        metrics = task_monitoring_service.get_task_metrics(hours=hours)
        serializer = TaskMetricsSerializer(data=metrics)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """Get current system health status."""
        health = task_monitoring_service.get_system_health()
        serializer = SystemHealthSerializer(data=health)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get performance analytics."""
        days = int(request.query_params.get('days', 7))
        analytics = task_monitoring_service.get_performance_analytics(days=days)
        serializer = PerformanceAnalyticsSerializer(data=analytics)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def record_metrics(self, request):
        """Manually trigger metrics recording."""
        try:
            metric = task_monitoring_service.record_system_metrics()
            serializer = SystemHealthMetricSerializer(metric)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(login_required, name='dispatch')
class MonitoringDashboardView(TemplateView):
    """Main monitoring dashboard view."""
    
    template_name = 'monitoring/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get basic system health
        try:
            health = task_monitoring_service.get_system_health()
            metrics = task_monitoring_service.get_task_metrics(hours=24)
            active_alerts = TaskAlert.objects.filter(resolved_at__isnull=True).count()
            
            context.update({
                'system_health': health,
                'task_metrics': metrics,
                'active_alerts': active_alerts,
            })
        except Exception as e:
            context['error'] = str(e)
        
        return context


@login_required
def monitoring_api_health(request):
    """Simple health check endpoint."""
    try:
        health = task_monitoring_service.get_system_health()
        return JsonResponse(health)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def monitoring_api_metrics(request):
    """Simple metrics endpoint."""
    try:
        hours = int(request.GET.get('hours', 24))
        metrics = task_monitoring_service.get_task_metrics(hours=hours)
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)