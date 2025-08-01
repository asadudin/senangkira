"""
Dashboard aggregation services for SenangKira.
Business intelligence services that calculate KPIs and analytics data.
"""

import uuid
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from django.db import models, transaction
from django.db.models import Sum, Count, Avg, Q, F, Case, When, Value
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric

User = get_user_model()


class DashboardAggregationService:
    """
    Core service for aggregating dashboard data from all system modules.
    Calculates financial KPIs, client analytics, and performance metrics.
    """
    
    def __init__(self, owner: User):
        self.owner = owner
        
    def generate_dashboard_snapshot(
        self, 
        snapshot_date: date = None,
        period_type: str = 'monthly'
    ) -> DashboardSnapshot:
        """
        Generate comprehensive dashboard snapshot for specified period.
        
        Args:
            snapshot_date: Date for the snapshot (defaults to today)
            period_type: Period type (daily, weekly, monthly, quarterly, yearly)
            
        Returns:
            DashboardSnapshot: Generated snapshot with all KPIs
        """
        if snapshot_date is None:
            snapshot_date = date.today()
            
        # Calculate period boundaries
        period_start, period_end = self._get_period_boundaries(snapshot_date, period_type)
        
        with transaction.atomic():
            # Get or create snapshot
            snapshot, created = DashboardSnapshot.objects.get_or_create(
                owner=self.owner,
                snapshot_date=snapshot_date,
                period_type=period_type,
                defaults={}
            )
            
            # Calculate financial metrics
            financial_data = self._calculate_financial_metrics(period_start, period_end)
            
            # Calculate client metrics
            client_data = self._calculate_client_metrics(period_start, period_end)
            
            # Calculate invoice/quote metrics
            invoice_data = self._calculate_invoice_metrics(period_start, period_end)
            
            # Calculate expense metrics
            expense_data = self._calculate_expense_metrics(period_start, period_end)
            
            # Update snapshot with calculated data
            for key, value in {**financial_data, **client_data, **invoice_data, **expense_data}.items():
                setattr(snapshot, key, value)
                
            snapshot.save()
            
            return snapshot
    
    def generate_category_analytics(
        self,
        snapshot_date: date = None,
        period_type: str = 'monthly'
    ) -> List[CategoryAnalytics]:
        """
        Generate category breakdown analytics for all categories.
        
        Returns:
            List[CategoryAnalytics]: Analytics for all categories
        """
        if snapshot_date is None:
            snapshot_date = date.today()
            
        period_start, period_end = self._get_period_boundaries(snapshot_date, period_type)
        
        analytics = []
        
        with transaction.atomic():
            # Clear existing analytics for this period
            CategoryAnalytics.objects.filter(
                owner=self.owner,
                snapshot_date=snapshot_date,
                period_type=period_type
            ).delete()
            
            # Generate expense category analytics
            expense_analytics = self._generate_expense_category_analytics(
                snapshot_date, period_type, period_start, period_end
            )
            analytics.extend(expense_analytics)
            
            # Generate client category analytics
            client_analytics = self._generate_client_category_analytics(
                snapshot_date, period_type, period_start, period_end
            )
            analytics.extend(client_analytics)
            
            # Generate service category analytics
            service_analytics = self._generate_service_category_analytics(
                snapshot_date, period_type, period_start, period_end
            )
            analytics.extend(service_analytics)
            
        return analytics
    
    def generate_client_analytics(
        self,
        snapshot_date: date = None,
        period_type: str = 'monthly'
    ) -> List[ClientAnalytics]:
        """
        Generate detailed analytics for each client.
        
        Returns:
            List[ClientAnalytics]: Analytics for all clients
        """
        if snapshot_date is None:
            snapshot_date = date.today()
            
        period_start, period_end = self._get_period_boundaries(snapshot_date, period_type)
        
        try:
            from clients.models import Client
            from invoicing.models import Invoice, Quote
            
            analytics = []
            
            with transaction.atomic():
                # Clear existing client analytics for this period
                ClientAnalytics.objects.filter(
                    owner=self.owner,
                    snapshot_date=snapshot_date,
                    period_type=period_type
                ).delete()
                
                # Get all clients for this owner
                clients = Client.objects.filter(owner=self.owner)
                
                for client in clients:
                    # Calculate client metrics for the period
                    client_invoices = Invoice.objects.filter(
                        client=client,
                        owner=self.owner,
                        created_at__date__range=[period_start, period_end]
                    )
                    
                    client_quotes = Quote.objects.filter(
                        client=client,
                        owner=self.owner,
                        created_at__date__range=[period_start, period_end]
                    )
                    
                    # Calculate revenue and counts
                    total_revenue = client_invoices.aggregate(
                        total=Sum('total_amount')
                    )['total'] or Decimal('0.00')
                    
                    invoice_count = client_invoices.count()
                    quote_count = client_quotes.count()
                    
                    # Calculate outstanding amount
                    outstanding_amount = client_invoices.filter(
                        status__in=['sent', 'overdue']
                    ).aggregate(
                        total=Sum('total_amount')
                    )['total'] or Decimal('0.00')
                    
                    # Calculate payment behavior
                    paid_invoices = client_invoices.filter(status='paid')
                    average_payment_days = 0
                    payment_score = Decimal('100.00')
                    
                    if paid_invoices.exists():
                        # Calculate average payment days (simplified)
                        payment_days = []
                        for invoice in paid_invoices:
                            if invoice.due_date and invoice.updated_at:
                                days = (invoice.updated_at.date() - invoice.due_date).days
                                payment_days.append(max(0, days))
                        
                        if payment_days:
                            average_payment_days = sum(payment_days) // len(payment_days)
                            # Simple payment score: 100 - (average_days_late * 2)
                            payment_score = max(Decimal('0.00'), Decimal('100.00') - (average_payment_days * 2))
                    
                    # Get client dates
                    first_invoice = Invoice.objects.filter(
                        client=client, owner=self.owner
                    ).order_by('created_at').first()
                    
                    last_invoice = Invoice.objects.filter(
                        client=client, owner=self.owner
                    ).order_by('-created_at').first()
                    
                    # Create client analytics
                    client_analytics = ClientAnalytics.objects.create(
                        owner=self.owner,
                        client_id=client.id,
                        client_name=client.name,
                        snapshot_date=snapshot_date,
                        period_type=period_type,
                        total_revenue=total_revenue,
                        invoice_count=invoice_count,
                        quote_count=quote_count,
                        outstanding_amount=outstanding_amount,
                        average_payment_days=average_payment_days,
                        payment_score=payment_score,
                        is_active=client.is_active,
                        first_invoice_date=first_invoice.created_at.date() if first_invoice else None,
                        last_invoice_date=last_invoice.created_at.date() if last_invoice else None
                    )
                    
                    analytics.append(client_analytics)
                    
            return analytics
            
        except ImportError:
            # If clients/invoicing modules not available, return empty list
            return []
    
    def calculate_performance_metrics(
        self,
        period_start: date = None,
        period_end: date = None
    ) -> List[PerformanceMetric]:
        """
        Calculate key performance indicators (KPIs) for the business.
        
        Returns:
            List[PerformanceMetric]: Calculated KPIs
        """
        if period_end is None:
            period_end = date.today()
        if period_start is None:
            period_start = period_end - timedelta(days=30)  # Default to 30 days
            
        # Calculate previous period for comparison
        period_length = (period_end - period_start).days
        previous_start = period_start - timedelta(days=period_length)
        previous_end = period_start - timedelta(days=1)
        
        metrics = []
        
        with transaction.atomic():
            # Clear existing metrics for this period
            PerformanceMetric.objects.filter(
                owner=self.owner,
                period_start=period_start,
                period_end=period_end
            ).delete()
            
            # Financial KPIs
            financial_metrics = self._calculate_kpi_financial(
                period_start, period_end, previous_start, previous_end
            )
            metrics.extend(financial_metrics)
            
            # Operational KPIs  
            operational_metrics = self._calculate_kpi_operational(
                period_start, period_end, previous_start, previous_end
            )
            metrics.extend(operational_metrics)
            
            # Client KPIs
            client_metrics = self._calculate_kpi_client(
                period_start, period_end, previous_start, previous_end
            )
            metrics.extend(client_metrics)
            
            # Growth KPIs
            growth_metrics = self._calculate_kpi_growth(
                period_start, period_end, previous_start, previous_end
            )
            metrics.extend(growth_metrics)
            
        return metrics
    
    def _get_period_boundaries(self, snapshot_date: date, period_type: str) -> Tuple[date, date]:
        """Calculate start and end dates for the specified period."""
        if period_type == 'daily':
            return snapshot_date, snapshot_date
        elif period_type == 'weekly':
            # Start from Monday of the week
            start = snapshot_date - timedelta(days=snapshot_date.weekday())
            end = start + timedelta(days=6)
            return start, end
        elif period_type == 'monthly':
            start = snapshot_date.replace(day=1)
            # Last day of month
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1) - timedelta(days=1)
            return start, end
        elif period_type == 'quarterly':
            # Get quarter start
            quarter = (snapshot_date.month - 1) // 3 + 1
            start = snapshot_date.replace(month=(quarter - 1) * 3 + 1, day=1)
            # Quarter end
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
    
    def _calculate_financial_metrics(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Calculate financial KPIs for the period."""
        try:
            from invoicing.models import Invoice
            from expenses.models import Expense
            
            # Revenue calculation
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
            
            # Expense calculation
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
            
            # Calculate net profit
            net_profit = total_revenue - total_expenses
            
            return {
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_profit': net_profit,
                'outstanding_amount': outstanding_amount,
                'reimbursable_expenses': reimbursable_expenses,
            }
            
        except ImportError:
            # If modules not available, return zeros
            return {
                'total_revenue': Decimal('0.00'),
                'total_expenses': Decimal('0.00'),
                'net_profit': Decimal('0.00'),
                'outstanding_amount': Decimal('0.00'),
                'reimbursable_expenses': Decimal('0.00'),
            }
    
    def _calculate_client_metrics(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Calculate client-related metrics."""
        try:
            from clients.models import Client
            
            # Total active clients
            total_clients = Client.objects.filter(
                owner=self.owner,
                is_active=True
            ).count()
            
            # New clients in period
            new_clients = Client.objects.filter(
                owner=self.owner,
                created_at__date__range=[period_start, period_end]
            ).count()
            
            return {
                'total_clients': total_clients,
                'new_clients': new_clients,
            }
            
        except ImportError:
            return {
                'total_clients': 0,
                'new_clients': 0,
            }
    
    def _calculate_invoice_metrics(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Calculate invoice and quote metrics."""
        try:
            from invoicing.models import Invoice, Quote
            
            # Invoice metrics
            invoices = Invoice.objects.filter(
                owner=self.owner,
                created_at__date__range=[period_start, period_end]
            )
            
            total_invoices = invoices.count()
            average_invoice_value = invoices.aggregate(
                avg=Avg('total_amount')
            )['avg'] or Decimal('0.00')
            
            # Quote metrics
            quotes = Quote.objects.filter(
                owner=self.owner,
                created_at__date__range=[period_start, period_end]
            )
            
            total_quotes = quotes.count()
            
            # Quote conversion rate (quotes that became invoices)
            quote_conversion_rate = Decimal('0.00')
            if total_quotes > 0:
                # This is simplified - in reality you'd track quote->invoice relationships
                converted_quotes = quotes.filter(status='accepted').count()
                quote_conversion_rate = (converted_quotes / total_quotes) * 100
            
            return {
                'total_invoices': total_invoices,
                'total_quotes': total_quotes,
                'quote_conversion_rate': quote_conversion_rate,
                'average_invoice_value': average_invoice_value,
            }
            
        except ImportError:
            return {
                'total_invoices': 0,
                'total_quotes': 0,
                'quote_conversion_rate': Decimal('0.00'),
                'average_invoice_value': Decimal('0.00'),
            }
    
    def _calculate_expense_metrics(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """Calculate expense-related metrics."""
        try:
            from expenses.models import Expense
            
            expenses = Expense.objects.filter(
                owner=self.owner,
                date__range=[period_start, period_end]
            )
            
            total_expense_count = expenses.count()
            
            return {
                'total_expense_count': total_expense_count,
            }
            
        except ImportError:
            return {
                'total_expense_count': 0,
            }
    
    def _generate_expense_category_analytics(
        self, snapshot_date: date, period_type: str, 
        period_start: date, period_end: date
    ) -> List[CategoryAnalytics]:
        """Generate analytics for expense categories."""
        try:
            from expenses.models import Expense
            
            analytics = []
            
            # Get expense totals by category
            category_data = Expense.objects.filter(
                owner=self.owner,
                date__range=[period_start, period_end]
            ).values('category').annotate(
                total_amount=Sum('amount'),
                transaction_count=Count('id')
            )
            
            # Calculate total for percentage calculation
            total_expenses = sum(item['total_amount'] for item in category_data)
            
            for item in category_data:
                percentage = Decimal('0.00')
                if total_expenses > 0:
                    percentage = (item['total_amount'] / total_expenses) * 100
                
                analytics.append(CategoryAnalytics.objects.create(
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
            
            return analytics
            
        except ImportError:
            return []
    
    def _generate_client_category_analytics(
        self, snapshot_date: date, period_type: str,
        period_start: date, period_end: date
    ) -> List[CategoryAnalytics]:
        """Generate analytics for client categories."""
        try:
            from clients.models import Client
            from invoicing.models import Invoice
            
            analytics = []
            
            # Get revenue by client industry/type if available
            clients = Client.objects.filter(owner=self.owner)
            
            # Group by industry if field exists
            if hasattr(Client, 'industry'):
                industry_data = {}
                for client in clients:
                    industry = getattr(client, 'industry', 'Other')
                    if industry not in industry_data:
                        industry_data[industry] = {'total': Decimal('0.00'), 'count': 0}
                    
                    # Get invoices for this client in the period
                    client_revenue = Invoice.objects.filter(
                        client=client,
                        owner=self.owner,
                        created_at__date__range=[period_start, period_end]
                    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
                    
                    industry_data[industry]['total'] += client_revenue
                    if client_revenue > 0:
                        industry_data[industry]['count'] += 1
                
                # Calculate total for percentages
                total_revenue = sum(data['total'] for data in industry_data.values())
                
                for industry, data in industry_data.items():
                    if data['total'] > 0:
                        percentage = (data['total'] / total_revenue) * 100 if total_revenue > 0 else Decimal('0.00')
                        
                        analytics.append(CategoryAnalytics.objects.create(
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
            
            return analytics
            
        except ImportError:
            return []
    
    def _generate_service_category_analytics(
        self, snapshot_date: date, period_type: str,
        period_start: date, period_end: date
    ) -> List[CategoryAnalytics]:
        """Generate analytics for service categories."""
        try:
            from invoicing.models import Invoice, InvoiceLineItem
            
            analytics = []
            
            # Get revenue by service type from line items
            line_items = InvoiceLineItem.objects.filter(
                invoice__owner=self.owner,
                invoice__created_at__date__range=[period_start, period_end]
            ).values('description').annotate(
                total_amount=Sum(F('quantity') * F('unit_price')),
                transaction_count=Count('id')
            )
            
            # Calculate total for percentages
            total_revenue = sum(item['total_amount'] for item in line_items)
            
            for item in line_items:
                percentage = Decimal('0.00')
                if total_revenue > 0:
                    percentage = (item['total_amount'] / total_revenue) * 100
                
                analytics.append(CategoryAnalytics.objects.create(
                    owner=self.owner,
                    snapshot_date=snapshot_date,
                    period_type=period_type,
                    category_type='service',
                    category_name=item['description'][:100],  # Truncate if needed
                    category_display=item['description'][:200],
                    total_amount=item['total_amount'],
                    transaction_count=item['transaction_count'],
                    percentage_of_total=percentage
                ))
            
            return analytics
            
        except ImportError:
            return []
    
    def _calculate_kpi_financial(
        self, period_start: date, period_end: date,
        previous_start: date, previous_end: date
    ) -> List[PerformanceMetric]:
        """Calculate financial KPIs."""
        metrics = []
        
        # Current period financial data
        current_financial = self._calculate_financial_metrics(period_start, period_end)
        
        # Previous period financial data
        previous_financial = self._calculate_financial_metrics(previous_start, previous_end)
        
        # Revenue KPI
        metrics.append(PerformanceMetric.objects.create(
            owner=self.owner,
            metric_name='Total Revenue',
            metric_category='financial',
            current_value=current_financial['total_revenue'],
            previous_value=previous_financial['total_revenue'],
            unit='currency',
            period_start=period_start,
            period_end=period_end
        ))
        
        # Profit Margin KPI
        profit_margin = Decimal('0.0000')
        previous_profit_margin = Decimal('0.0000')
        
        if current_financial['total_revenue'] > 0:
            profit_margin = (current_financial['net_profit'] / current_financial['total_revenue']) * 100
        
        if previous_financial['total_revenue'] > 0:
            previous_profit_margin = (previous_financial['net_profit'] / previous_financial['total_revenue']) * 100
        
        metrics.append(PerformanceMetric.objects.create(
            owner=self.owner,
            metric_name='Profit Margin',
            metric_category='financial',
            current_value=profit_margin,
            previous_value=previous_profit_margin,
            unit='percentage',
            period_start=period_start,
            period_end=period_end,
            target_value=Decimal('20.0000')  # 20% target
        ))
        
        return metrics
    
    def _calculate_kpi_operational(
        self, period_start: date, period_end: date,
        previous_start: date, previous_end: date
    ) -> List[PerformanceMetric]:
        """Calculate operational KPIs."""
        metrics = []
        
        try:
            from invoicing.models import Invoice
            
            # Invoice processing time (simplified)
            current_invoices = Invoice.objects.filter(
                owner=self.owner,
                created_at__date__range=[period_start, period_end]
            ).count()
            
            previous_invoices = Invoice.objects.filter(
                owner=self.owner,
                created_at__date__range=[previous_start, previous_end]
            ).count()
            
            metrics.append(PerformanceMetric.objects.create(
                owner=self.owner,
                metric_name='Invoices Generated',
                metric_category='operational',
                current_value=Decimal(str(current_invoices)),
                previous_value=Decimal(str(previous_invoices)),
                unit='number',
                period_start=period_start,
                period_end=period_end
            ))
            
        except ImportError:
            pass
        
        return metrics
    
    def _calculate_kpi_client(
        self, period_start: date, period_end: date,
        previous_start: date, previous_end: date
    ) -> List[PerformanceMetric]:
        """Calculate client-related KPIs."""
        metrics = []
        
        # Current and previous client metrics
        current_client = self._calculate_client_metrics(period_start, period_end)
        previous_client = self._calculate_client_metrics(previous_start, previous_end)
        
        # Client Acquisition KPI
        metrics.append(PerformanceMetric.objects.create(
            owner=self.owner,
            metric_name='New Clients',
            metric_category='client',
            current_value=Decimal(str(current_client['new_clients'])),
            previous_value=Decimal(str(previous_client['new_clients'])),
            unit='number',
            period_start=period_start,
            period_end=period_end
        ))
        
        return metrics
    
    def _calculate_kpi_growth(
        self, period_start: date, period_end: date,
        previous_start: date, previous_end: date
    ) -> List[PerformanceMetric]:
        """Calculate growth KPIs."""
        metrics = []
        
        # Revenue Growth Rate
        current_financial = self._calculate_financial_metrics(period_start, period_end)
        previous_financial = self._calculate_financial_metrics(previous_start, previous_end)
        
        growth_rate = Decimal('0.0000')
        if previous_financial['total_revenue'] > 0:
            growth_rate = ((current_financial['total_revenue'] - previous_financial['total_revenue']) / 
                          previous_financial['total_revenue']) * 100
        
        metrics.append(PerformanceMetric.objects.create(
            owner=self.owner,
            metric_name='Revenue Growth Rate',
            metric_category='growth',
            current_value=growth_rate,
            previous_value=Decimal('0.0000'),  # Growth rate is a delta
            unit='percentage',
            period_start=period_start,
            period_end=period_end,
            target_value=Decimal('10.0000')  # 10% growth target
        ))
        
        return metrics


class DashboardCacheService:
    """
    Service for managing dashboard data caching and refresh strategies.
    Optimizes performance by pre-calculating expensive aggregations.
    """
    
    def __init__(self, owner: User):
        self.owner = owner
        self.aggregation_service = DashboardAggregationService(owner)
    
    def refresh_dashboard_cache(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Refresh dashboard cache with latest data.
        
        Args:
            force_refresh: Force refresh even if cache is recent
            
        Returns:
            Dict with refresh results and timing information
        """
        start_time = timezone.now()
        
        # Check if refresh is needed
        if not force_refresh and not self._needs_cache_refresh():
            return {
                'refreshed': False,
                'reason': 'Cache is still fresh',
                'last_refresh': self._get_last_refresh_time()
            }
        
        results = {}
        
        with transaction.atomic():
            # Refresh monthly snapshot (most common)
            monthly_snapshot = self.aggregation_service.generate_dashboard_snapshot(
                period_type='monthly'
            )
            results['monthly_snapshot'] = monthly_snapshot.id
            
            # Refresh category analytics
            category_analytics = self.aggregation_service.generate_category_analytics(
                period_type='monthly'
            )
            results['category_analytics_count'] = len(category_analytics)
            
            # Refresh client analytics
            client_analytics = self.aggregation_service.generate_client_analytics(
                period_type='monthly'
            )
            results['client_analytics_count'] = len(client_analytics)
            
            # Refresh performance metrics
            performance_metrics = self.aggregation_service.calculate_performance_metrics()
            results['performance_metrics_count'] = len(performance_metrics)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        results.update({
            'refreshed': True,
            'refresh_time': end_time,
            'duration_seconds': duration
        })
        
        return results
    
    def get_cached_dashboard_data(self, period_type: str = 'monthly') -> Dict[str, Any]:
        """
        Get cached dashboard data for display.
        
        Returns:
            Dict with all dashboard data ready for API response
        """
        today = date.today()
        
        # Get latest snapshot
        snapshot = DashboardSnapshot.objects.filter(
            owner=self.owner,
            period_type=period_type
        ).order_by('-snapshot_date').first()
        
        if not snapshot:
            # Generate if doesn't exist
            snapshot = self.aggregation_service.generate_dashboard_snapshot(period_type=period_type)
        
        # Get category analytics
        category_analytics = CategoryAnalytics.objects.filter(
            owner=self.owner,
            period_type=period_type,
            snapshot_date=snapshot.snapshot_date
        ).order_by('-total_amount')
        
        # Get client analytics
        client_analytics = ClientAnalytics.objects.filter(
            owner=self.owner,
            period_type=period_type,
            snapshot_date=snapshot.snapshot_date
        ).order_by('-total_revenue')[:10]  # Top 10 clients
        
        # Get recent performance metrics
        performance_metrics = PerformanceMetric.objects.filter(
            owner=self.owner,
            period_end=snapshot.snapshot_date
        ).order_by('-calculation_date')[:20]  # Recent metrics
        
        return {
            'snapshot': snapshot,
            'category_analytics': list(category_analytics),
            'top_clients': list(client_analytics),
            'performance_metrics': list(performance_metrics),
            'cache_info': {
                'last_updated': snapshot.updated_at,
                'period_type': period_type,
                'snapshot_date': snapshot.snapshot_date
            }
        }
    
    def _needs_cache_refresh(self) -> bool:
        """Check if cache needs to be refreshed."""
        latest_snapshot = DashboardSnapshot.objects.filter(
            owner=self.owner
        ).order_by('-updated_at').first()
        
        if not latest_snapshot:
            return True
        
        # Refresh if older than 1 hour
        threshold = timezone.now() - timedelta(hours=1)
        return latest_snapshot.updated_at < threshold
    
    def _get_last_refresh_time(self) -> Optional[datetime]:
        """Get the last cache refresh time."""
        latest_snapshot = DashboardSnapshot.objects.filter(
            owner=self.owner
        ).order_by('-updated_at').first()
        
        return latest_snapshot.updated_at if latest_snapshot else None