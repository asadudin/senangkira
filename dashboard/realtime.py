"""
Real-time dashboard data aggregation with WebSocket support.
Advanced aggregation endpoint with live updates and streaming analytics.
"""

import json
import asyncio
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric
from .services import DashboardAggregationService, DashboardCacheService
from .serializers import DashboardOverviewSerializer

User = get_user_model()


@dataclass
class RealTimeMetric:
    """Real-time metric data structure."""
    name: str
    value: Decimal
    change: Decimal
    trend: str  # 'up', 'down', 'stable'
    timestamp: datetime
    confidence: float = 1.0


@dataclass
class LiveDashboardUpdate:
    """Live dashboard update structure."""
    user_id: str
    timestamp: datetime
    metrics: List[RealTimeMetric]
    alerts: List[Dict[str, Any]]
    performance_score: float


class RealTimeDashboardAggregator:
    """
    Real-time dashboard data aggregation with streaming capabilities.
    Provides live updates and instant metric calculations.
    """
    
    def __init__(self, user: User):
        self.user = user
        self.cache_key_prefix = f"realtime_dashboard_{user.id}"
        self.aggregation_service = DashboardAggregationService(user)
        
    def get_live_metrics(self) -> List[RealTimeMetric]:
        """Get current live metrics with real-time calculations."""
        metrics = []
        current_time = timezone.now()
        
        # Financial metrics
        financial_metrics = self._calculate_live_financial_metrics()
        metrics.extend(financial_metrics)
        
        # Operational metrics
        operational_metrics = self._calculate_live_operational_metrics()
        metrics.extend(operational_metrics)
        
        # Client metrics
        client_metrics = self._calculate_live_client_metrics()
        metrics.extend(client_metrics)
        
        return metrics
    
    def _calculate_live_financial_metrics(self) -> List[RealTimeMetric]:
        """Calculate real-time financial metrics."""
        metrics = []
        current_time = timezone.now()
        today = current_time.date()
        
        try:
            from expenses.models import Expense
            from invoicing.models import Invoice
            
            # Today's revenue vs yesterday
            today_revenue = Invoice.objects.filter(
                owner=self.user,
                created_at__date=today
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            yesterday_revenue = Invoice.objects.filter(
                owner=self.user,
                created_at__date=today - timedelta(days=1)
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            revenue_change = today_revenue - yesterday_revenue
            revenue_trend = 'up' if revenue_change > 0 else 'down' if revenue_change < 0 else 'stable'
            
            metrics.append(RealTimeMetric(
                name='Daily Revenue',
                value=today_revenue,
                change=revenue_change,
                trend=revenue_trend,
                timestamp=current_time,
                confidence=0.95
            ))
            
            # Today's expenses vs yesterday
            today_expenses = Expense.objects.filter(
                owner=self.user,
                date=today
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            yesterday_expenses = Expense.objects.filter(
                owner=self.user,
                date=today - timedelta(days=1)
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            expense_change = today_expenses - yesterday_expenses
            expense_trend = 'down' if expense_change > 0 else 'up' if expense_change < 0 else 'stable'  # Lower expenses are better
            
            metrics.append(RealTimeMetric(
                name='Daily Expenses',
                value=today_expenses,
                change=expense_change,
                trend=expense_trend,
                timestamp=current_time,
                confidence=0.95
            ))
            
            # Real-time profit
            daily_profit = today_revenue - today_expenses
            yesterday_profit = yesterday_revenue - yesterday_expenses
            profit_change = daily_profit - yesterday_profit
            profit_trend = 'up' if profit_change > 0 else 'down' if profit_change < 0 else 'stable'
            
            metrics.append(RealTimeMetric(
                name='Daily Profit',
                value=daily_profit,
                change=profit_change,
                trend=profit_trend,
                timestamp=current_time,
                confidence=0.90
            ))
            
        except ImportError:
            # Fallback metrics if modules not available
            pass
        
        return metrics
    
    def _calculate_live_operational_metrics(self) -> List[RealTimeMetric]:
        """Calculate real-time operational metrics."""
        metrics = []
        current_time = timezone.now()
        
        try:
            from invoicing.models import Invoice
            
            # Pending invoices count
            pending_invoices = Invoice.objects.filter(
                owner=self.user,
                status='sent'
            ).count()
            
            # Get previous count from cache for trend
            cache_key = f"{self.cache_key_prefix}_pending_invoices"
            previous_pending = cache.get(cache_key, pending_invoices)
            cache.set(cache_key, pending_invoices, 300)  # 5 minutes
            
            pending_change = pending_invoices - previous_pending
            pending_trend = 'down' if pending_change < 0 else 'up' if pending_change > 0 else 'stable'  # Less pending is better
            
            metrics.append(RealTimeMetric(
                name='Pending Invoices',
                value=Decimal(str(pending_invoices)),
                change=Decimal(str(pending_change)),
                trend=pending_trend,
                timestamp=current_time,
                confidence=1.0
            ))
            
            # Overdue invoices
            overdue_invoices = Invoice.objects.filter(
                owner=self.user,
                status='overdue'
            ).count()
            
            cache_key = f"{self.cache_key_prefix}_overdue_invoices"
            previous_overdue = cache.get(cache_key, overdue_invoices)
            cache.set(cache_key, overdue_invoices, 300)
            
            overdue_change = overdue_invoices - previous_overdue
            overdue_trend = 'down' if overdue_change < 0 else 'up' if overdue_change > 0 else 'stable'  # Less overdue is better
            
            metrics.append(RealTimeMetric(
                name='Overdue Invoices',
                value=Decimal(str(overdue_invoices)),
                change=Decimal(str(overdue_change)),
                trend=overdue_trend,
                timestamp=current_time,
                confidence=1.0
            ))
            
        except ImportError:
            pass
        
        return metrics
    
    def _calculate_live_client_metrics(self) -> List[RealTimeMetric]:
        """Calculate real-time client metrics."""
        metrics = []
        current_time = timezone.now()
        
        try:
            from clients.models import Client
            
            # Active clients count
            active_clients = Client.objects.filter(
                owner=self.user,
                is_active=True
            ).count()
            
            cache_key = f"{self.cache_key_prefix}_active_clients"
            previous_active = cache.get(cache_key, active_clients)
            cache.set(cache_key, active_clients, 900)  # 15 minutes
            
            client_change = active_clients - previous_active
            client_trend = 'up' if client_change > 0 else 'down' if client_change < 0 else 'stable'
            
            metrics.append(RealTimeMetric(
                name='Active Clients',
                value=Decimal(str(active_clients)),
                change=Decimal(str(client_change)),
                trend=client_trend,
                timestamp=current_time,
                confidence=0.98
            ))
            
        except ImportError:
            pass
        
        return metrics
    
    def generate_alerts(self, metrics: List[RealTimeMetric]) -> List[Dict[str, Any]]:
        """Generate real-time alerts based on metrics."""
        alerts = []
        
        for metric in metrics:
            # High-priority alerts
            if metric.name == 'Daily Profit' and metric.value < 0:
                alerts.append({
                    'level': 'critical',
                    'message': f'Daily profit is negative: ${metric.value}',
                    'metric': metric.name,
                    'timestamp': metric.timestamp.isoformat(),
                    'action_required': True
                })
            
            if metric.name == 'Overdue Invoices' and metric.value > 5:
                alerts.append({
                    'level': 'warning',
                    'message': f'{int(metric.value)} invoices are overdue',
                    'metric': metric.name,
                    'timestamp': metric.timestamp.isoformat(),
                    'action_required': True
                })
            
            # Positive trend alerts
            if metric.trend == 'up' and metric.name in ['Daily Revenue', 'Active Clients']:
                alerts.append({
                    'level': 'success',
                    'message': f'{metric.name} is trending up (+${metric.change})',
                    'metric': metric.name,
                    'timestamp': metric.timestamp.isoformat(),
                    'action_required': False
                })
        
        return alerts
    
    def calculate_performance_score(self, metrics: List[RealTimeMetric]) -> float:
        """Calculate overall performance score based on metrics."""
        score = 0.0
        total_weight = 0.0
        
        metric_weights = {
            'Daily Revenue': 0.3,
            'Daily Profit': 0.25,
            'Daily Expenses': 0.2,
            'Pending Invoices': 0.15,
            'Overdue Invoices': 0.1
        }
        
        for metric in metrics:
            weight = metric_weights.get(metric.name, 0.1)
            total_weight += weight
            
            # Score based on trend and change
            if metric.trend == 'up' and metric.name in ['Daily Revenue', 'Daily Profit', 'Active Clients']:
                score += weight * 1.0
            elif metric.trend == 'down' and metric.name in ['Daily Expenses', 'Pending Invoices', 'Overdue Invoices']:
                score += weight * 1.0
            elif metric.trend == 'stable':
                score += weight * 0.7
            else:
                score += weight * 0.3
        
        return (score / total_weight) * 100 if total_weight > 0 else 50.0
    
    def get_live_dashboard_update(self) -> LiveDashboardUpdate:
        """Get complete live dashboard update."""
        metrics = self.get_live_metrics()
        alerts = self.generate_alerts(metrics)
        performance_score = self.calculate_performance_score(metrics)
        
        return LiveDashboardUpdate(
            user_id=str(self.user.id),
            timestamp=timezone.now(),
            metrics=metrics,
            alerts=alerts,
            performance_score=performance_score
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def realtime_dashboard_aggregate(request):
    """
    GET /api/dashboard/realtime/aggregate/
    
    Real-time dashboard data aggregation endpoint with live metrics.
    Provides instant calculations and real-time updates.
    """
    aggregator = RealTimeDashboardAggregator(request.user)
    
    try:
        # Get live dashboard update
        dashboard_update = aggregator.get_live_dashboard_update()
        
        # Convert to serializable format
        response_data = {
            'user_id': dashboard_update.user_id,
            'timestamp': dashboard_update.timestamp.isoformat(),
            'performance_score': dashboard_update.performance_score,
            'metrics': [
                {
                    'name': metric.name,
                    'value': float(metric.value),
                    'change': float(metric.change),
                    'trend': metric.trend,
                    'timestamp': metric.timestamp.isoformat(),
                    'confidence': metric.confidence
                }
                for metric in dashboard_update.metrics
            ],
            'alerts': dashboard_update.alerts,
            'metadata': {
                'calculation_time': timezone.now().isoformat(),
                'cache_status': 'live',
                'data_freshness': 'real-time'
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to generate real-time dashboard data',
            'detail': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def streaming_dashboard_aggregate(request):
    """
    GET /api/dashboard/streaming/aggregate/
    
    Streaming dashboard data aggregation with Server-Sent Events.
    Provides continuous real-time updates.
    """
    def generate_dashboard_stream():
        """Generate streaming dashboard data."""
        aggregator = RealTimeDashboardAggregator(request.user)
        
        yield "data: " + json.dumps({"type": "connection", "message": "Dashboard stream started"}) + "\n\n"
        
        update_interval = int(request.GET.get('interval', 30))  # Default 30 seconds
        max_updates = int(request.GET.get('max_updates', 100))  # Default 100 updates
        
        for i in range(max_updates):
            try:
                # Get live dashboard update
                dashboard_update = aggregator.get_live_dashboard_update()
                
                # Convert to streaming format
                stream_data = {
                    'type': 'dashboard_update',
                    'sequence': i + 1,
                    'user_id': dashboard_update.user_id,
                    'timestamp': dashboard_update.timestamp.isoformat(),
                    'performance_score': dashboard_update.performance_score,
                    'metrics': [
                        {
                            'name': metric.name,
                            'value': float(metric.value),
                            'change': float(metric.change),
                            'trend': metric.trend,
                            'confidence': metric.confidence
                        }
                        for metric in dashboard_update.metrics
                    ],
                    'alerts': dashboard_update.alerts
                }
                
                yield "data: " + json.dumps(stream_data) + "\n\n"
                
                # Wait for next update
                import time
                time.sleep(update_interval)
                
            except Exception as e:
                error_data = {
                    'type': 'error',
                    'message': str(e),
                    'timestamp': timezone.now().isoformat()
                }
                yield "data: " + json.dumps(error_data) + "\n\n"
                break
        
        yield "data: " + json.dumps({"type": "stream_end", "message": "Dashboard stream ended"}) + "\n\n"
    
    response = StreamingHttpResponse(
        generate_dashboard_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_dashboard_recalculation(request):
    """
    POST /api/dashboard/realtime/recalculate/
    
    Trigger immediate dashboard recalculation and cache refresh.
    """
    try:
        # Force refresh dashboard cache
        cache_service = DashboardCacheService(request.user)
        refresh_results = cache_service.refresh_dashboard_cache(force_refresh=True)
        
        # Get fresh real-time metrics
        aggregator = RealTimeDashboardAggregator(request.user)
        dashboard_update = aggregator.get_live_dashboard_update()
        
        return Response({
            'success': True,
            'message': 'Dashboard recalculation completed',
            'refresh_results': refresh_results,
            'performance_score': dashboard_update.performance_score,
            'metrics_count': len(dashboard_update.metrics),
            'alerts_count': len(dashboard_update.alerts),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to recalculate dashboard',
            'detail': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_health_check(request):
    """
    GET /api/dashboard/health/
    
    Dashboard system health check and performance metrics.
    """
    try:
        start_time = timezone.now()
        
        # Test database connectivity
        snapshot_count = DashboardSnapshot.objects.filter(owner=request.user).count()
        
        # Test cache connectivity
        cache_test_key = f"health_check_{request.user.id}"
        cache.set(cache_test_key, "test", 10)
        cache_working = cache.get(cache_test_key) == "test"
        cache.delete(cache_test_key)
        
        # Test aggregation service
        aggregation_service = DashboardAggregationService(request.user)
        test_boundaries = aggregation_service._get_period_boundaries(date.today(), 'monthly')
        
        end_time = timezone.now()
        response_time = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        health_status = {
            'status': 'healthy',
            'timestamp': end_time.isoformat(),
            'response_time_ms': response_time,
            'components': {
                'database': {
                    'status': 'healthy',
                    'snapshot_count': snapshot_count
                },
                'cache': {
                    'status': 'healthy' if cache_working else 'unhealthy',
                    'working': cache_working
                },
                'aggregation_service': {
                    'status': 'healthy',
                    'period_boundaries_working': test_boundaries is not None
                }
            },
            'performance': {
                'response_time_ms': response_time,
                'target_response_time_ms': 100.0,
                'performance_grade': 'excellent' if response_time < 100 else 'good' if response_time < 500 else 'poor'
            }
        }
        
        return Response(health_status, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)