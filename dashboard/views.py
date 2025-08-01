"""
Dashboard views for SenangKira API.
Comprehensive dashboard endpoints with business intelligence and analytics.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List

from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from django.core.cache import cache

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from senangkira.utils.viewsets import MultiTenantViewSet
from senangkira.utils.permissions import IsOwnerOrReadOnly

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric
from .serializers import (
    DashboardSnapshotSerializer, CategoryAnalyticsSerializer, ClientAnalyticsSerializer,
    PerformanceMetricSerializer, DashboardOverviewSerializer, DashboardStatsSerializer,
    CategoryBreakdownSerializer, TrendAnalysisSerializer, DashboardFiltersSerializer,
    DashboardRefreshSerializer, KPIComparisonSerializer, ClientPerformanceSerializer,
    RevenueProjectionSerializer, DashboardExportSerializer
)
from .services import DashboardAggregationService, DashboardCacheService


class DashboardPagination(PageNumberPagination):
    """Custom pagination for dashboard endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DashboardViewSet(MultiTenantViewSet):
    """
    Main dashboard ViewSet providing comprehensive business intelligence.
    
    Endpoints:
        - GET /dashboard/ - Dashboard overview
        - GET /dashboard/stats/ - Quick statistics
        - GET /dashboard/trends/ - Trend analysis
        - GET /dashboard/breakdown/ - Category breakdown
        - POST /dashboard/refresh/ - Refresh cache
        - GET /dashboard/export/ - Export dashboard data
    """
    
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = DashboardPagination
    
    def get_queryset(self):
        """Not used - this ViewSet doesn't have a single model."""
        return DashboardSnapshot.objects.none()
    
    def get_dashboard_service(self):
        """Get dashboard aggregation service for current user."""
        return DashboardAggregationService(self.request.user)
    
    def get_cache_service(self):
        """Get dashboard cache service for current user."""
        return DashboardCacheService(self.request.user)
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        GET /api/dashboard/overview/
        
        Comprehensive dashboard overview with all key metrics.
        """
        # Get filters
        filter_serializer = DashboardFiltersSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        filters = filter_serializer.validated_data
        
        period_type = filters.get('period_type', 'monthly')
        
        # Check cache first
        cache_key = f"dashboard_overview_{request.user.id}_{period_type}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        # Get cached dashboard data
        cache_service = self.get_cache_service()
        dashboard_data = cache_service.get_cached_dashboard_data(period_type=period_type)
        
        # Prepare overview data
        snapshot = dashboard_data['snapshot']
        
        overview_data = {
            # Financial summary
            'total_revenue': snapshot.total_revenue,
            'total_expenses': snapshot.total_expenses,
            'net_profit': snapshot.net_profit,
            'profit_margin': snapshot.profit_margin,
            'outstanding_amount': snapshot.outstanding_amount,
            
            # Client metrics
            'total_clients': snapshot.total_clients,
            'new_clients': snapshot.new_clients,
            'top_clients': dashboard_data['top_clients'][:5],  # Top 5
            
            # Business metrics
            'total_invoices': snapshot.total_invoices,
            'total_quotes': snapshot.total_quotes,
            'quote_conversion_rate': snapshot.quote_conversion_rate,
            'average_invoice_value': snapshot.average_invoice_value,
            
            # Expense metrics
            'total_expense_count': snapshot.total_expense_count,
            'reimbursable_expenses': snapshot.reimbursable_expenses,
            'expense_categories': [cat for cat in dashboard_data['category_analytics'] if cat.category_type == 'expense'][:5],
            
            # Performance indicators
            'key_metrics': dashboard_data['performance_metrics'][:10],
            
            # Meta information
            'period_type': period_type,
            'snapshot_date': snapshot.snapshot_date,
            'last_updated': snapshot.updated_at
        }
        
        serializer = DashboardOverviewSerializer(overview_data)
        response_data = serializer.data
        
        # Cache for 30 minutes
        cache.set(cache_key, response_data, 1800)
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        GET /api/dashboard/stats/
        
        Quick dashboard statistics for widgets and summary displays.
        """
        # Calculate current month stats
        today = date.today()
        current_month_start = today.replace(day=1)
        
        # Previous month for comparison
        if current_month_start.month == 1:
            previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            previous_month_start = current_month_start.replace(month=current_month_start.month - 1)
        
        previous_month_end = current_month_start - timedelta(days=1)
        
        service = self.get_dashboard_service()
        
        # Current month metrics
        current_financial = service._calculate_financial_metrics(current_month_start, today)
        current_client = service._calculate_client_metrics(current_month_start, today)
        
        # Previous month metrics
        previous_financial = service._calculate_financial_metrics(previous_month_start, previous_month_end)
        
        # Calculate changes
        revenue_change = Decimal('0.00')
        profit_change = Decimal('0.00')
        expense_change = Decimal('0.00')
        
        if previous_financial['total_revenue'] > 0:
            revenue_change = ((current_financial['total_revenue'] - previous_financial['total_revenue']) / 
                            previous_financial['total_revenue']) * 100
        
        if previous_financial['net_profit'] != 0:
            profit_change = ((current_financial['net_profit'] - previous_financial['net_profit']) / 
                           abs(previous_financial['net_profit'])) * 100
        
        if previous_financial['total_expenses'] > 0:
            expense_change = ((current_financial['total_expenses'] - previous_financial['total_expenses']) / 
                            previous_financial['total_expenses']) * 100
        
        # Additional quick stats
        try:
            from invoicing.models import Invoice
            
            pending_invoices = Invoice.objects.filter(
                owner=request.user,
                status='sent'
            ).count()
            
            overdue_amount = Invoice.objects.filter(
                owner=request.user,
                status='overdue'
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
        except ImportError:
            pending_invoices = 0
            overdue_amount = Decimal('0.00')
        
        stats_data = {
            'revenue_this_month': current_financial['total_revenue'],
            'revenue_change': revenue_change,
            'profit_this_month': current_financial['net_profit'],
            'profit_change': profit_change,
            'active_clients': current_client['total_clients'],
            'pending_invoices': pending_invoices,
            'overdue_amount': overdue_amount,
            'expenses_this_month': current_financial['total_expenses'],
            'expense_change': expense_change
        }
        
        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        GET /api/dashboard/trends/
        
        Trend analysis data for charts and graphs.
        """
        period_type = request.query_params.get('period', 'monthly')
        periods = int(request.query_params.get('periods', 12))  # Default 12 periods
        
        service = self.get_dashboard_service()
        trends_data = self._calculate_trends(service, period_type, periods)
        
        serializer = TrendAnalysisSerializer({
            'period': period_type,
            'revenue_trend': trends_data['revenue'],
            'expense_trend': trends_data['expenses'],
            'profit_trend': trends_data['profit']
        })
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def breakdown(self, request):
        """
        GET /api/dashboard/breakdown/
        
        Category breakdown for pie charts and detailed analysis.
        """
        period_type = request.query_params.get('period_type', 'monthly')
        
        # Get category analytics
        analytics = CategoryAnalytics.objects.filter(
            owner=request.user,
            period_type=period_type
        ).order_by('-total_amount')
        
        serializer = CategoryBreakdownSerializer(analytics)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        POST /api/dashboard/refresh/
        
        Refresh dashboard cache with latest data.
        """
        serializer = DashboardRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        force_refresh = serializer.validated_data.get('force_refresh', False)
        
        cache_service = self.get_cache_service()
        results = cache_service.refresh_dashboard_cache(force_refresh=force_refresh)
        
        # Clear related caches
        cache_pattern = f"dashboard_*_{request.user.id}_*"
        # Note: In production, you'd use a more sophisticated cache invalidation
        
        response_data = {
            'refreshed': results['refreshed'],
            'refresh_time': results.get('refresh_time'),
            'duration_seconds': results.get('duration_seconds'),
            'results': results
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """
        GET /api/dashboard/kpis/
        
        Key Performance Indicators with comparisons.
        """
        metric_category = request.query_params.get('category')
        
        queryset = PerformanceMetric.objects.filter(owner=request.user)
        
        if metric_category:
            queryset = queryset.filter(metric_category=metric_category)
        
        metrics = queryset.order_by('-calculation_date')[:20]
        
        # Group by metric name for comparison
        kpi_comparisons = []
        processed_metrics = set()
        
        for metric in metrics:
            if metric.metric_name not in processed_metrics:
                comparison_data = {
                    'metric_name': metric.metric_name,
                    'current_period': {
                        'value': metric.current_value,
                        'period_start': metric.period_start,
                        'period_end': metric.period_end,
                        'unit': metric.unit
                    },
                    'previous_period': {
                        'value': metric.previous_value,
                        'unit': metric.unit
                    },
                    'change_amount': metric.current_value - metric.previous_value,
                    'change_percentage': metric.change_percentage,
                    'trend': 'up' if metric.is_improving else 'down' if metric.current_value < metric.previous_value else 'neutral',
                    'target_achievement': metric.target_achievement
                }
                
                kpi_comparisons.append(comparison_data)
                processed_metrics.add(metric.metric_name)
        
        serializer = KPIComparisonSerializer(kpi_comparisons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def clients(self, request):
        """
        GET /api/dashboard/clients/
        
        Client performance analysis.
        """
        period_type = request.query_params.get('period_type', 'monthly')
        risk_level = request.query_params.get('risk_level')
        
        queryset = ClientAnalytics.objects.filter(
            owner=request.user,
            period_type=period_type
        ).order_by('-total_revenue')
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ClientPerformanceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ClientPerformanceSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def projections(self, request):
        """
        GET /api/dashboard/projections/
        
        Revenue projections and forecasting.
        """
        # Simple projection based on historical data
        service = self.get_dashboard_service()
        
        # Get last 6 months of data for projection
        end_date = date.today()
        start_date = end_date - timedelta(days=180)
        
        # Calculate average monthly revenue
        snapshots = DashboardSnapshot.objects.filter(
            owner=request.user,
            period_type='monthly',
            snapshot_date__range=[start_date, end_date]
        ).order_by('snapshot_date')
        
        if not snapshots:
            return Response({
                'error': 'Insufficient historical data for projections'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        revenues = [snapshot.total_revenue for snapshot in snapshots]
        avg_revenue = sum(revenues) / len(revenues) if revenues else Decimal('0.00')
        
        # Simple trend calculation
        if len(revenues) >= 2:
            trend_factor = (revenues[-1] / revenues[0]) ** (1 / len(revenues)) if revenues[0] > 0 else Decimal('1.00')
        else:
            trend_factor = Decimal('1.00')
        
        # Project next 3 months
        projections = []
        for i in range(1, 4):
            projected_revenue = avg_revenue * (trend_factor ** i)
            confidence = max(Decimal('50.00'), Decimal('90.00') - (i * Decimal('10.00')))
            
            projections.append({
                'period': f'{(end_date + timedelta(days=30*i)).strftime("%Y-%m")}',
                'projected_revenue': projected_revenue,
                'confidence_level': confidence,
                'historical_average': avg_revenue,
                'trend_factor': trend_factor,
                'confirmed_revenue': Decimal('0.00'),  # Would come from confirmed orders
                'pipeline_revenue': projected_revenue * Decimal('0.7'),  # Estimated
                'recurring_revenue': projected_revenue * Decimal('0.3')  # Estimated
            })
        
        serializer = RevenueProjectionSerializer(projections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        GET /api/dashboard/export/
        
        Export dashboard data in various formats.
        """
        serializer = DashboardExportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        export_format = serializer.validated_data.get('export_format', 'xlsx')
        export_type = serializer.validated_data.get('export_type', 'overview')
        
        # For now, return a placeholder response
        # In production, you'd generate actual files
        response_data = {
            'export_url': f'/api/dashboard/downloads/dashboard_{export_type}_{timezone.now().strftime("%Y%m%d")}.{export_format}',
            'file_size': 1024,  # Placeholder
            'generated_at': timezone.now()
        }
        
        return Response(response_data)
    
    def _calculate_trends(self, service: DashboardAggregationService, period_type: str, periods: int) -> Dict[str, List]:
        """Calculate trend data for charts."""
        trends = {
            'revenue': [],
            'expenses': [],
            'profit': []
        }
        
        end_date = date.today()
        
        for i in range(periods):
            if period_type == 'monthly':
                period_date = end_date - timedelta(days=30 * i)
                period_start = period_date.replace(day=1)
                if period_start.month == 12:
                    period_end = period_start.replace(year=period_start.year + 1, month=1) - timedelta(days=1)
                else:
                    period_end = period_start.replace(month=period_start.month + 1) - timedelta(days=1)
            else:
                # For now, only monthly is implemented
                continue
            
            # Get financial data for this period
            financial_data = service._calculate_financial_metrics(period_start, period_end)
            
            period_label = period_date.strftime("%Y-%m")
            
            trends['revenue'].append({
                'period': period_label,
                'value': float(financial_data['total_revenue']),
                'date': period_date.isoformat()
            })
            
            trends['expenses'].append({
                'period': period_label,
                'value': float(financial_data['total_expenses']),
                'date': period_date.isoformat()
            })
            
            trends['profit'].append({
                'period': period_label,
                'value': float(financial_data['net_profit']),
                'date': period_date.isoformat()
            })
        
        # Reverse to get chronological order
        for key in trends:
            trends[key].reverse()
        
        return trends


class DashboardSnapshotViewSet(MultiTenantViewSet):
    """
    CRUD operations for dashboard snapshots.
    Primarily for administrative purposes and historical data access.
    """
    
    queryset = DashboardSnapshot.objects.all()
    serializer_class = DashboardSnapshotSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = DashboardPagination
    
    def get_queryset(self):
        """Filter snapshots by owner."""
        return DashboardSnapshot.objects.filter(owner=self.request.user).order_by('-snapshot_date')
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        POST /api/dashboard/snapshots/generate/
        
        Generate a new dashboard snapshot.
        """
        service = DashboardAggregationService(request.user)
        
        period_type = request.data.get('period_type', 'monthly')
        snapshot_date = request.data.get('snapshot_date')
        
        if snapshot_date:
            snapshot_date = date.fromisoformat(snapshot_date)
        
        snapshot = service.generate_dashboard_snapshot(
            snapshot_date=snapshot_date,
            period_type=period_type
        )
        
        serializer = self.get_serializer(snapshot)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryAnalyticsViewSet(MultiTenantViewSet):
    """CRUD operations for category analytics."""
    
    queryset = CategoryAnalytics.objects.all()
    serializer_class = CategoryAnalyticsSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = DashboardPagination
    
    def get_queryset(self):
        """Filter analytics by owner with optional filtering."""
        queryset = CategoryAnalytics.objects.filter(owner=self.request.user)
        
        category_type = self.request.query_params.get('category_type')
        period_type = self.request.query_params.get('period_type')
        
        if category_type:
            queryset = queryset.filter(category_type=category_type)
        
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        
        return queryset.order_by('-total_amount')


class ClientAnalyticsViewSet(MultiTenantViewSet):
    """CRUD operations for client analytics."""
    
    queryset = ClientAnalytics.objects.all()
    serializer_class = ClientAnalyticsSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = DashboardPagination
    
    def get_queryset(self):
        """Filter client analytics by owner with optional filtering."""
        queryset = ClientAnalytics.objects.filter(owner=self.request.user)
        
        is_active = self.request.query_params.get('is_active')
        period_type = self.request.query_params.get('period_type')
        client_id = self.request.query_params.get('client_id')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        return queryset.order_by('-total_revenue')


class PerformanceMetricViewSet(MultiTenantViewSet):
    """CRUD operations for performance metrics (KPIs)."""
    
    queryset = PerformanceMetric.objects.all()
    serializer_class = PerformanceMetricSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = DashboardPagination
    
    def get_queryset(self):
        """Filter metrics by owner with optional filtering."""
        queryset = PerformanceMetric.objects.filter(owner=self.request.user)
        
        metric_category = self.request.query_params.get('metric_category')
        metric_name = self.request.query_params.get('metric_name')
        
        if metric_category:
            queryset = queryset.filter(metric_category=metric_category)
        
        if metric_name:
            queryset = queryset.filter(metric_name__icontains=metric_name)
        
        return queryset.order_by('-calculation_date')