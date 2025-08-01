"""
Dashboard URLs for SenangKira API.
Dashboard analytics and business intelligence endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardViewSet, 
    DashboardSnapshotViewSet,
    CategoryAnalyticsViewSet,
    ClientAnalyticsViewSet,
    PerformanceMetricViewSet
)
from .views_celery import CeleryMonitoringViewSet
from .realtime import (
    realtime_dashboard_aggregate,
    streaming_dashboard_aggregate,
    trigger_dashboard_recalculation,
    dashboard_health_check
)

from .prometheus_exporter import prometheus_metrics

# Create router and register viewsets
router = DefaultRouter()
router.register(r'snapshots', DashboardSnapshotViewSet, basename='dashboard-snapshots')
router.register(r'categories', CategoryAnalyticsViewSet, basename='category-analytics')
router.register(r'clients', ClientAnalyticsViewSet, basename='client-analytics')
router.register(r'metrics', PerformanceMetricViewSet, basename='performance-metrics')

# Main dashboard endpoints (no prefix for clean URLs)
main_router = DefaultRouter()
main_router.register(r'', DashboardViewSet, basename='dashboard')

# Celery monitoring endpoints
celery_router = DefaultRouter()
celery_router.register(r'celery', CeleryMonitoringViewSet, basename='celery-monitoring')

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard endpoints
    # GET /api/dashboard/overview/ - Dashboard overview
    # GET /api/dashboard/stats/ - Quick statistics
    # GET /api/dashboard/trends/ - Trend analysis
    # GET /api/dashboard/breakdown/ - Category breakdown
    # POST /api/dashboard/refresh/ - Refresh cache
    # GET /api/dashboard/kpis/ - Key Performance Indicators
    # GET /api/dashboard/clients/ - Client performance analysis
    # GET /api/dashboard/projections/ - Revenue projections
    # GET /api/dashboard/export/ - Export dashboard data
    path('', include(main_router.urls)),
    
    # Celery monitoring endpoints
    # GET /api/dashboard/celery/status/ - Overall Celery system status
    # GET /api/dashboard/celery/workers/ - Worker information and statistics
    # GET /api/dashboard/celery/queues/ - Queue status and backlogs
    # GET /api/dashboard/celery/tasks/ - Recent task execution history
    # GET /api/dashboard/celery/tasks/{task_id}/ - Specific task details
    # POST /api/dashboard/celery/tasks/{task_name}/execute/ - Execute a task
    # POST /api/dashboard/celery/health_check/ - Comprehensive health check
    path('', include(celery_router.urls)),
    
    # Real-time dashboard endpoints
    path('realtime/aggregate/', realtime_dashboard_aggregate, name='realtime-aggregate'),
    path('streaming/aggregate/', streaming_dashboard_aggregate, name='streaming-aggregate'),
    path('realtime/recalculate/', trigger_dashboard_recalculation, name='trigger-recalculation'),
    path('health/', dashboard_health_check, name='dashboard-health'),
    
    # Sub-resource endpoints
    # GET /api/dashboard/snapshots/ - List snapshots
    # POST /api/dashboard/snapshots/ - Create snapshot
    # GET /api/dashboard/snapshots/{id}/ - Get specific snapshot
    # POST /api/dashboard/snapshots/generate/ - Generate new snapshot
    
    # GET /api/dashboard/categories/ - List category analytics
    # GET /api/dashboard/categories/{id}/ - Get specific category analytics
    
    # GET /api/dashboard/clients/ - List client analytics (also available on main dashboard)
    # GET /api/dashboard/clients/{id}/ - Get specific client analytics
    
    # GET /api/dashboard/metrics/ - List performance metrics
    # GET /api/dashboard/metrics/{id}/ - Get specific metric
    path('metrics/prometheus/', prometheus_metrics, name='prometheus-metrics'),
    path('', include(router.urls)),
]