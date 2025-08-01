"""
URL configuration for monitoring app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TaskExecutionViewSet, SystemHealthMetricViewSet, TaskAlertViewSet,
    MonitoringAPIViewSet, MonitoringDashboardView,
    monitoring_api_health, monitoring_api_metrics
)

# API router for DRF viewsets
router = DefaultRouter()
router.register(r'tasks', TaskExecutionViewSet)
router.register(r'health-metrics', SystemHealthMetricViewSet)
router.register(r'alerts', TaskAlertViewSet)
router.register(r'monitoring', MonitoringAPIViewSet, basename='monitoring')

app_name = 'monitoring'

urlpatterns = [
    # Dashboard views
    path('', MonitoringDashboardView.as_view(), name='dashboard'),
    
    # Simple API endpoints (non-DRF)
    path('api/health/', monitoring_api_health, name='api_health'),
    path('api/metrics/', monitoring_api_metrics, name='api_metrics'),
    
    # DRF API endpoints
    path('api/', include(router.urls)),
]