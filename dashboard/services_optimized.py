"""
Optimized Dashboard Services for Performance Enhancement

Key optimizations:
1. Parallel processing for independent operations
2. Selective refresh capabilities  
3. Optimized database queries with bulk operations
4. Intelligent caching strategies
5. Background job processing for expensive operations
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from django.db import models, transaction, connection
from django.db.models import Sum, Count, Avg, Q, F, Case, When, Value, Prefetch
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import connections
import threading
import time
import logging

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric

User = get_user_model()
logger = logging.getLogger(__name__)


class OptimizedDashboardAggregationService:
    """
    High-performance dashboard aggregation service with parallel processing.
    
    Key optimizations:
    - Parallel execution of independent operations
    - Bulk database operations to reduce query count
    - Selective refresh based on data change detection
    - Optimized queries with proper joins and prefetching
    - Background processing for expensive operations
    """
    
    def __init__(self, owner: User):
        self.owner = owner
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    def generate_dashboard_snapshot_optimized(
        self, 
        snapshot_date: date = None,
        period_type: str = 'monthly',
        selective_refresh: bool = True
    ) -> DashboardSnapshot:
        """
        Optimized dashboard snapshot generation.
        
        Optimizations:
        - Single query for all financial data with joins
        - Bulk operations to reduce database round trips
        - Selective refresh based on data changes
        """
        if snapshot_date is None:
            snapshot_date = date.today()
            
        period_start, period_end = self._get_period_boundaries(snapshot_date, period_type)
        
        # Check if selective refresh is possible
        if selective_refresh:
            existing_snapshot = DashboardSnapshot.objects.filter(
                owner=self.owner,
                snapshot_date=snapshot_date,
                period_type=period_type
            ).first()
            
            if existing_snapshot and not self._data_changed_since(existing_snapshot.updated_at):
                logger.info(f"Skipping snapshot refresh - no data changes detected")
                return existing_snapshot
        
        # Optimized single-query approach for all financial data
        financial_data = self._calculate_financial_metrics_optimized(period_start, period_end)
        client_data = self._calculate_client_metrics_optimized(period_start, period_end)
        invoice_data = self._calculate_invoice_metrics_optimized(period_start, period_end)
        expense_data = self._calculate_expense_metrics_optimized(period_start, period_end)
        
        # Use update_or_create for atomic operation with minimal locking
        snapshot, created = DashboardSnapshot.objects.update_or_create(
            owner=self.owner,
            snapshot_date=snapshot_date,
            period_type=period_type,
            defaults={**financial_data, **client_data, **invoice_data, **expense_data}
        )
        
        action = "created" if created else "updated"
        logger.info(f"Dashboard snapshot {action} for {self.owner.email}: {snapshot.id}")
        
        return snapshot
    
    def generate_analytics_parallel(
        self,
        snapshot_date: date = None,
        period_type: str = 'monthly'
    ) -> Dict[str, List]:
        """
        Generate all analytics in parallel for maximum performance.
        
        Returns:
            Dict containing all analytics results
        """
        if snapshot_date is None:
            snapshot_date = date.today()
            
        period_start, period_end = self._get_period_boundaries(snapshot_date, period_type)
        
        # Submit all analytics generation to thread pool
        futures = {
            'category': self._executor.submit(
                self._generate_expense_category_analytics_optimized,
                snapshot_date, period_type, period_start, period_end
            ),
            'client': self._executor.submit(
                self._generate_client_category_analytics_optimized,
                snapshot_date, period_type, period_start, period_end
            ),
            'service': self._executor.submit(
                self._generate_service_category_analytics_optimized,
                snapshot_date, period_type, period_start, period_end
            )
        }
        
        # Collect results as they complete
        results = {}
        for category, future in futures.items():
            try:
                results[category] = future.result(timeout=30)  # 30 second timeout
                logger.info(f"Completed {category} analytics generation")
            except Exception as e:
                logger.error(f"Failed to generate {category} analytics: {e}")
                results[category] = []
        
        return results
    
    def _calculate_financial_metrics_optimized(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """
        Optimized financial metrics calculation with single query.
        
        Optimizations:
        - Single query with conditional aggregation
        - Reduced database round trips
        - Proper indexing utilization
        """
        try:
            # Single optimized query for all financial data
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        -- Revenue metrics
                        COALESCE(SUM(CASE WHEN i.created_at::date BETWEEN %s AND %s THEN i.total_amount END), 0) as total_revenue,
                        COALESCE(SUM(CASE WHEN i.created_at::date BETWEEN %s AND %s AND i.status IN ('sent', 'overdue') THEN i.total_amount END), 0) as outstanding_amount,
                        
                        -- Expense metrics  
                        COALESCE(SUM(CASE WHEN e.date BETWEEN %s AND %s THEN e.amount END), 0) as total_expenses,
                        COALESCE(SUM(CASE WHEN e.date BETWEEN %s AND %s AND e.is_billable = true THEN e.amount END), 0) as reimbursable_expenses
                    
                    FROM auth_user u
                    LEFT JOIN invoicing_invoice i ON i.owner_id = u.id
                    LEFT JOIN expenses_expense e ON e.owner_id = u.id
                    WHERE u.id = %s
                """, [period_start, period_end, period_start, period_end, 
                      period_start, period_end, period_start, period_end, self.owner.id])
                
                row = cursor.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row[0]))
                    outstanding_amount = Decimal(str(row[1]))
                    total_expenses = Decimal(str(row[2]))
                    reimbursable_expenses = Decimal(str(row[3]))
                    
                    return {
                        'total_revenue': total_revenue,
                        'total_expenses': total_expenses,
                        'net_profit': total_revenue - total_expenses,
                        'outstanding_amount': outstanding_amount,
                        'reimbursable_expenses': reimbursable_expenses,
                    }
        
        except Exception as e:
            logger.error(f"Optimized financial metrics calculation failed: {e}")
            # Fallback to original method
            return self._calculate_financial_metrics_fallback(period_start, period_end)
        
        return {
            'total_revenue': Decimal('0.00'),
            'total_expenses': Decimal('0.00'),
            'net_profit': Decimal('0.00'),
            'outstanding_amount': Decimal('0.00'),
            'reimbursable_expenses': Decimal('0.00'),
        }
    
    def _calculate_client_metrics_optimized(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Optimized client metrics with bulk query."""
        try:
            from clients.models import Client
            
            # Single query for all client metrics
            client_stats = Client.objects.filter(owner=self.owner).aggregate(
                total_clients=Count('id', filter=Q(is_active=True)),
                new_clients=Count('id', filter=Q(created_at__date__range=[period_start, period_end]))
            )
            
            return {
                'total_clients': client_stats['total_clients'] or 0,
                'new_clients': client_stats['new_clients'] or 0,
            }
            
        except ImportError:
            return {'total_clients': 0, 'new_clients': 0}
    
    def _calculate_invoice_metrics_optimized(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Optimized invoice metrics with single query."""
        try:
            from invoicing.models import Invoice, Quote
            
            # Optimized query with all metrics in one go
            date_filter = Q(created_at__date__range=[period_start, period_end])
            
            invoice_stats = Invoice.objects.filter(
                owner=self.owner
            ).filter(date_filter).aggregate(
                total_invoices=Count('id'),
                average_invoice_value=Avg('total_amount')
            )
            
            quote_stats = Quote.objects.filter(
                owner=self.owner
            ).filter(date_filter).aggregate(
                total_quotes=Count('id'),
                converted_quotes=Count('id', filter=Q(status='accepted'))
            )
            
            # Calculate conversion rate
            total_quotes = quote_stats['total_quotes'] or 0
            converted_quotes = quote_stats['converted_quotes'] or 0
            quote_conversion_rate = (converted_quotes / total_quotes * 100) if total_quotes > 0 else Decimal('0.00')
            
            return {
                'total_invoices': invoice_stats['total_invoices'] or 0,
                'total_quotes': total_quotes,
                'quote_conversion_rate': quote_conversion_rate,
                'average_invoice_value': invoice_stats['average_invoice_value'] or Decimal('0.00'),
            }
            
        except ImportError:
            return {
                'total_invoices': 0,
                'total_quotes': 0,
                'quote_conversion_rate': Decimal('0.00'),
                'average_invoice_value': Decimal('0.00'),
            }
    
    def _calculate_expense_metrics_optimized(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Optimized expense metrics."""
        try:
            from expenses.models import Expense
            
            expense_stats = Expense.objects.filter(
                owner=self.owner,
                date__range=[period_start, period_end]
            ).aggregate(
                total_expense_count=Count('id')
            )
            
            return {
                'total_expense_count': expense_stats['total_expense_count'] or 0,
            }
            
        except ImportError:
            return {'total_expense_count': 0}
    
    def _generate_expense_category_analytics_optimized(
        self, snapshot_date: date, period_type: str, 
        period_start: date, period_end: date
    ) -> List[CategoryAnalytics]:
        """Optimized expense category analytics with bulk operations."""
        try:
            from expenses.models import Expense
            
            # Clear existing records with bulk delete
            CategoryAnalytics.objects.filter(
                owner=self.owner,
                snapshot_date=snapshot_date,
                period_type=period_type,
                category_type='expense'
            ).delete()
            
            # Single query with grouping
            category_data = list(Expense.objects.filter(
                owner=self.owner,
                date__range=[period_start, period_end]
            ).values('category').annotate(
                total_amount=Sum('amount'),
                transaction_count=Count('id')
            ).order_by('-total_amount'))
            
            if not category_data:
                return []
            
            # Calculate total for percentage
            total_expenses = sum(item['total_amount'] for item in category_data)
            
            # Bulk create analytics records
            analytics_to_create = []
            for item in category_data:
                percentage = (item['total_amount'] / total_expenses * 100) if total_expenses > 0 else Decimal('0.00')
                
                analytics_to_create.append(CategoryAnalytics(
                    owner=self.owner,
                    snapshot_date=snapshot_date,
                    period_type=period_type,
                    category_type='expense',
                    category_name=item['category'],
                    category_display=item['category'].replace('_', ' ').title(),
                    total_amount=item['total_amount'],
                    transaction_count=item['transaction_count'],
                    percentage_of_total=percentage
                ))
            
            # Bulk create for performance
            created_analytics = CategoryAnalytics.objects.bulk_create(analytics_to_create)
            logger.info(f"Created {len(created_analytics)} expense category analytics")
            
            return created_analytics
            
        except ImportError:
            return []
    
    def _generate_client_category_analytics_optimized(
        self, snapshot_date: date, period_type: str,
        period_start: date, period_end: date
    ) -> List[CategoryAnalytics]:
        """Optimized client category analytics."""
        try:
            from clients.models import Client
            from invoicing.models import Invoice
            
            # Clear existing records
            CategoryAnalytics.objects.filter(
                owner=self.owner,
                snapshot_date=snapshot_date,
                period_type=period_type,
                category_type='client'
            ).delete()
            
            # Optimized query with joins
            if hasattr(Client, 'industry'):
                industry_data = {}
                
                # Single query with prefetch for better performance
                clients_with_revenue = Client.objects.filter(
                    owner=self.owner
                ).prefetch_related(
                    Prefetch(
                        'invoice_set',
                        queryset=Invoice.objects.filter(
                            created_at__date__range=[period_start, period_end]
                        ).only('total_amount'),
                        to_attr='period_invoices'
                    )
                ).only('industry')
                
                for client in clients_with_revenue:
                    industry = getattr(client, 'industry', 'Other')
                    if industry not in industry_data:
                        industry_data[industry] = {'total': Decimal('0.00'), 'count': 0}
                    
                    client_revenue = sum(
                        invoice.total_amount for invoice in client.period_invoices
                    )
                    
                    industry_data[industry]['total'] += client_revenue
                    if client_revenue > 0:
                        industry_data[industry]['count'] += 1
                
                # Bulk create analytics
                total_revenue = sum(data['total'] for data in industry_data.values())
                analytics_to_create = []
                
                for industry, data in industry_data.items():
                    if data['total'] > 0:
                        percentage = (data['total'] / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')
                        
                        analytics_to_create.append(CategoryAnalytics(
                            owner=self.owner,
                            snapshot_date=snapshot_date,
                            period_type=period_type,
                            category_type='client',
                            category_name=industry,
                            category_display=industry,
                            total_amount=data['total'],
                            transaction_count=data['count'],
                            percentage_of_total=percentage
                        ))
                
                return CategoryAnalytics.objects.bulk_create(analytics_to_create)
            
            return []
            
        except ImportError:
            return []
    
    def _generate_service_category_analytics_optimized(
        self, snapshot_date: date, period_type: str,
        period_start: date, period_end: date
    ) -> List[CategoryAnalytics]:
        """Optimized service category analytics."""
        try:
            from invoicing.models import Invoice, InvoiceLineItem
            
            # Clear existing records
            CategoryAnalytics.objects.filter(
                owner=self.owner,
                snapshot_date=snapshot_date,
                period_type=period_type,
                category_type='service'
            ).delete()
            
            # Optimized query with proper joins
            line_items_data = list(InvoiceLineItem.objects.filter(
                invoice__owner=self.owner,
                invoice__created_at__date__range=[period_start, period_end]
            ).values('description').annotate(
                total_amount=Sum(F('quantity') * F('unit_price')),
                transaction_count=Count('id')
            ).order_by('-total_amount'))
            
            if not line_items_data:
                return []
            
            # Calculate total and bulk create
            total_revenue = sum(item['total_amount'] for item in line_items_data)
            analytics_to_create = []
            
            for item in line_items_data:
                percentage = (item['total_amount'] / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')
                
                analytics_to_create.append(CategoryAnalytics(
                    owner=self.owner,
                    snapshot_date=snapshot_date,
                    period_type=period_type,
                    category_type='service',
                    category_name=item['description'][:100],
                    category_display=item['description'][:200],
                    total_amount=item['total_amount'],
                    transaction_count=item['transaction_count'],
                    percentage_of_total=percentage
                ))
            
            return CategoryAnalytics.objects.bulk_create(analytics_to_create)
            
        except ImportError:
            return []
    
    def _data_changed_since(self, timestamp: datetime) -> bool:
        """
        Check if relevant data has changed since timestamp.
        
        Uses efficient queries to detect changes without loading data.
        """
        try:
            # Check for new invoices
            from invoicing.models import Invoice
            if Invoice.objects.filter(
                owner=self.owner,
                updated_at__gt=timestamp
            ).exists():
                return True
            
            # Check for new expenses
            from expenses.models import Expense
            if Expense.objects.filter(
                owner=self.owner,
                updated_at__gt=timestamp
            ).exists():
                return True
            
            # Check for new clients
            from clients.models import Client
            if Client.objects.filter(
                owner=self.owner,
                updated_at__gt=timestamp
            ).exists():
                return True
                
        except ImportError:
            # If modules not available, assume data changed
            return True
        
        return False
    
    def _calculate_financial_metrics_fallback(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Fallback method using original approach."""
        try:
            from invoicing.models import Invoice
            from expenses.models import Expense
            
            # Original method as fallback
            invoices = Invoice.objects.filter(
                owner=self.owner,
                created_at__date__range=[period_start, period_end]
            )
            
            total_revenue = invoices.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00')
            
            outstanding_amount = invoices.filter(
                status__in=['sent', 'overdue']
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00')
            
            expenses = Expense.objects.filter(
                owner=self.owner,
                date__range=[period_start, period_end]
            )
            
            total_expenses = expenses.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            reimbursable_expenses = expenses.filter(
                is_billable=True
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            net_profit = total_revenue - total_expenses
            
            return {
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_profit': net_profit,
                'outstanding_amount': outstanding_amount,
                'reimbursable_expenses': reimbursable_expenses,
            }
            
        except ImportError:
            return {
                'total_revenue': Decimal('0.00'),
                'total_expenses': Decimal('0.00'),
                'net_profit': Decimal('0.00'),
                'outstanding_amount': Decimal('0.00'),
                'reimbursable_expenses': Decimal('0.00'),
            }
    
    def _get_period_boundaries(self, snapshot_date: date, period_type: str) -> Tuple[date, date]:
        """Calculate start and end dates for the specified period."""
        if period_type == 'daily':
            return snapshot_date, snapshot_date
        elif period_type == 'weekly':
            start = snapshot_date - timedelta(days=snapshot_date.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif period_type == 'monthly':
            start = snapshot_date.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1) - timedelta(days=1)
            return start, end
        elif period_type == 'quarterly':
            quarter = (snapshot_date.month - 1) // 3 + 1
            start = snapshot_date.replace(month=(quarter - 1) * 3 + 1, day=1)
            if quarter == 4:
                end = start.replace(year=start.year + 1, month=1) - timedelta(days=1)
            else:
                end = start.replace(month=quarter * 3 + 1) - timedelta(days=1)
            return start, end
        elif period_type == 'yearly':
            start = snapshot_date.replace(month=1, day=1)
            end = snapshot_date.replace(month=12, day=31)
            return start, end
        else:
            raise ValueError(f"Invalid period_type: {period_type}")


class OptimizedDashboardCacheService:
    """
    High-performance dashboard cache service with parallel refresh.
    
    Key optimizations:
    - Parallel processing of independent cache operations
    - Selective refresh based on data changes
    - Optimized cache key management
    - Background job integration for expensive operations
    """
    
    def __init__(self, owner: User):
        self.owner = owner
        self.aggregation_service = OptimizedDashboardAggregationService(owner)
    
    def refresh_dashboard_cache_optimized(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Optimized cache refresh with parallel processing.
        
        Key improvements:
        - Parallel execution of independent operations
        - Selective refresh based on data changes
        - Reduced database transaction time
        - Better error handling and recovery
        """
        start_time = timezone.now()
        
        # Check if refresh is needed (unless forced)
        if not force_refresh and not self._needs_cache_refresh():
            return {
                'refreshed': False,
                'reason': 'Cache is still fresh',
                'last_refresh': self._get_last_refresh_time(),
                'optimization': 'skipped_unnecessary_refresh'
            }
        
        results = {
            'optimization_applied': 'parallel_processing',
            'performance_improvements': []
        }
        
        try:
            # Step 1: Generate snapshot (this is fast with optimizations)
            snapshot_start = time.time()
            monthly_snapshot = self.aggregation_service.generate_dashboard_snapshot_optimized(
                period_type='monthly',
                selective_refresh=not force_refresh
            )
            snapshot_time = time.time() - snapshot_start
            results['monthly_snapshot'] = monthly_snapshot.id
            results['performance_improvements'].append(f'snapshot_generation: {snapshot_time:.3f}s')
            
            # Step 2: Generate all analytics in parallel (major optimization)
            analytics_start = time.time()
            analytics_results = self.aggregation_service.generate_analytics_parallel(
                period_type='monthly'
            )
            analytics_time = time.time() - analytics_start
            
            # Collect analytics results
            results['category_analytics_count'] = len(analytics_results.get('category', []))
            results['client_analytics_count'] = len(analytics_results.get('client', []))
            results['service_analytics_count'] = len(analytics_results.get('service', []))
            results['performance_improvements'].append(f'parallel_analytics: {analytics_time:.3f}s')
            
            # Step 3: Performance metrics (can be done separately if needed)
            metrics_start = time.time()
            try:
                performance_metrics = self.aggregation_service.calculate_performance_metrics()
                results['performance_metrics_count'] = len(performance_metrics)
            except Exception as e:
                logger.warning(f"Performance metrics calculation failed: {e}")
                results['performance_metrics_count'] = 0
                results['warnings'] = ['performance_metrics_failed']
            
            metrics_time = time.time() - metrics_start
            results['performance_improvements'].append(f'performance_metrics: {metrics_time:.3f}s')
            
        except Exception as e:
            logger.error(f"Optimized cache refresh failed: {e}")
            results['error'] = str(e)
            results['fallback_used'] = True
            
            # Fallback to original method if optimization fails
            return self._refresh_dashboard_cache_fallback(force_refresh)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        results.update({
            'refreshed': True,
            'refresh_time': end_time,
            'duration_seconds': duration,
            'performance_improvement': f'{duration:.3f}s total (target: <0.5s)'
        })
        
        # Log performance improvement
        logger.info(f"Optimized cache refresh completed in {duration:.3f}s")
        
        return results
    
    def _refresh_dashboard_cache_fallback(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fallback to original cache refresh method."""
        logger.info("Using fallback cache refresh method")
        
        # Import original service
        from .services import DashboardCacheService
        original_service = DashboardCacheService(self.owner)
        
        result = original_service.refresh_dashboard_cache(force_refresh=force_refresh)
        result['fallback_used'] = True
        result['optimization'] = 'fallback_to_original'
        
        return result
    
    def _needs_cache_refresh(self) -> bool:
        """Enhanced cache refresh detection."""
        latest_snapshot = DashboardSnapshot.objects.filter(
            owner=self.owner
        ).order_by('-updated_at').first()
        
        if not latest_snapshot:
            return True
        
        # More intelligent refresh logic
        threshold = timezone.now() - timedelta(minutes=30)  # Reduced from 1 hour
        
        # Check if data changed since last refresh
        if self.aggregation_service._data_changed_since(latest_snapshot.updated_at):
            return True
        
        return latest_snapshot.updated_at < threshold
    
    def _get_last_refresh_time(self) -> Optional[datetime]:
        """Get the last cache refresh time."""
        latest_snapshot = DashboardSnapshot.objects.filter(
            owner=self.owner
        ).order_by('-updated_at').first()
        
        return latest_snapshot.updated_at if latest_snapshot else None
    
    def get_cached_dashboard_data_optimized(self, period_type: str = 'monthly') -> Dict[str, Any]:
        """
        Optimized dashboard data retrieval with better caching.
        """
        today = date.today()
        
        # Try cache first
        cache_key = f"dashboard_data_{self.owner.id}_{period_type}_{today}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            cached_data['cache_hit'] = True
            return cached_data
        
        # Get latest snapshot with optimized queries
        snapshot = DashboardSnapshot.objects.filter(
            owner=self.owner,
            period_type=period_type
        ).select_related().order_by('-snapshot_date').first()
        
        if not snapshot:
            # Generate if doesn't exist
            snapshot = self.aggregation_service.generate_dashboard_snapshot_optimized(
                period_type=period_type
            )
        
        # Get analytics with optimized queries and prefetch
        category_analytics = list(CategoryAnalytics.objects.filter(
            owner=self.owner,
            period_type=period_type,
            snapshot_date=snapshot.snapshot_date
        ).order_by('-total_amount'))
        
        client_analytics = list(ClientAnalytics.objects.filter(
            owner=self.owner,
            period_type=period_type,
            snapshot_date=snapshot.snapshot_date
        ).order_by('-total_revenue')[:10])
        
        performance_metrics = list(PerformanceMetric.objects.filter(
            owner=self.owner,
            period_end=snapshot.snapshot_date
        ).order_by('-calculation_date')[:20])
        
        result = {
            'snapshot': snapshot,
            'category_analytics': category_analytics,
            'top_clients': client_analytics,
            'performance_metrics': performance_metrics,
            'cache_info': {
                'last_updated': snapshot.updated_at,
                'period_type': period_type,
                'snapshot_date': snapshot.snapshot_date,
                'optimized': True
            },
            'cache_hit': False
        }
        
        # Cache for 15 minutes
        cache.set(cache_key, result, 900)
        
        return result