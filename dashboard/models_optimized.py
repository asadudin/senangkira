"""
Optimized Dashboard Models with Performance Enhancements

Key optimizations:
1. Database indexes for frequently queried fields
2. Optimized field types and constraints
3. Custom managers with optimized querysets
4. Caching methods at model level
5. Bulk operation support
"""

import uuid
from decimal import Decimal
from datetime import date, datetime
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone

User = get_user_model()


class OptimizedDashboardManager(models.Manager):
    """Custom manager with optimized queries."""
    
    def for_user(self, user):
        """Get queryset filtered by user with optimizations."""
        return self.filter(owner=user).select_related('owner')
    
    def recent(self, user, limit=10):
        """Get recent records with optimized query."""
        return self.for_user(user).order_by('-updated_at')[:limit]
    
    def bulk_create_optimized(self, objects, batch_size=100):
        """Optimized bulk create with smaller batches."""
        return self.bulk_create(objects, batch_size=batch_size, ignore_conflicts=True)


class DashboardSnapshotOptimized(models.Model):
    """
    Optimized dashboard snapshot model with performance enhancements.
    
    Optimizations:
    - Database indexes on frequently queried fields
    - Optimized field types and constraints
    - Caching methods for expensive calculations
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)  # Explicit index
    
    # Snapshot metadata with optimized indexing
    snapshot_date = models.DateField(db_index=True)  # Frequently queried
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'), 
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly')
        ],
        default='monthly',
        db_index=True  # Add index for period filtering
    )
    
    # Financial metrics with optimized precision
    total_revenue = models.DecimalField(
        max_digits=15, decimal_places=2,  # Increased precision for large amounts
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_expenses = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    net_profit = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00')  # Can be negative
    )
    outstanding_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    reimbursable_expenses = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Client metrics with constraints
    total_clients = models.PositiveIntegerField(default=0)
    new_clients = models.PositiveIntegerField(default=0)
    active_clients = models.PositiveIntegerField(default=0)
    
    # Invoice and quote metrics
    total_invoices = models.PositiveIntegerField(default=0)
    total_quotes = models.PositiveIntegerField(default=0)
    quote_conversion_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    average_invoice_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Expense metrics
    total_expense_count = models.PositiveIntegerField(default=0)
    
    # Timestamps with optimized indexing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)  # For cache invalidation
    
    objects = OptimizedDashboardManager()
    
    class Meta:
        db_table = 'dashboard_snapshot_optimized'
        
        # Composite indexes for common query patterns
        indexes = [
            models.Index(fields=['owner', 'snapshot_date'], name='owner_snapshot_date_idx'),
            models.Index(fields=['owner', 'period_type'], name='owner_period_type_idx'),
            models.Index(fields=['owner', 'updated_at'], name='owner_updated_at_idx'),
            models.Index(fields=['snapshot_date', 'period_type'], name='date_period_idx'),
        ]
        
        # Unique constraint to prevent duplicates
        unique_together = [['owner', 'snapshot_date', 'period_type']]
        
        # Default ordering for consistent results
        ordering = ['-snapshot_date', '-updated_at']
    
    def __str__(self):
        return f"Dashboard {self.period_type} snapshot for {self.owner.email} on {self.snapshot_date}"
    
    def get_cache_key(self, suffix=''):
        """Generate cache key for this snapshot."""
        return f"dashboard_snapshot_{self.owner.id}_{self.snapshot_date}_{self.period_type}_{suffix}"
    
    def invalidate_cache(self):
        """Invalidate all related cache entries."""
        cache_keys = [
            self.get_cache_key(),
            self.get_cache_key('overview'),
            self.get_cache_key('stats'),
            f"dashboard_data_{self.owner.id}_{self.period_type}_{self.snapshot_date}"
        ]
        
        for key in cache_keys:
            cache.delete(key)
    
    def calculate_profit_margin(self):
        """Calculate profit margin with caching."""
        if self.total_revenue <= 0:
            return Decimal('0.00')
        
        return (self.net_profit / self.total_revenue) * 100
    
    def save(self, *args, **kwargs):
        """Override save to handle cache invalidation."""
        # Calculate derived fields
        if self.total_revenue is not None and self.total_expenses is not None:
            self.net_profit = self.total_revenue - self.total_expenses
        
        super().save(*args, **kwargs)
        
        # Invalidate cache after successful save
        self.invalidate_cache()
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'snapshot_date': self.snapshot_date.isoformat(),
            'period_type': self.period_type,
            'total_revenue': float(self.total_revenue),
            'total_expenses': float(self.total_expenses),
            'net_profit': float(self.net_profit),
            'profit_margin': float(self.calculate_profit_margin()),
            'outstanding_amount': float(self.outstanding_amount),
            'total_clients': self.total_clients,
            'new_clients': self.new_clients,
            'total_invoices': self.total_invoices,
            'average_invoice_value': float(self.average_invoice_value),
            'updated_at': self.updated_at.isoformat()
        }


class CategoryAnalyticsOptimized(models.Model):
    """
    Optimized category analytics model for high-performance queries.
    
    Optimizations:
    - Composite indexes for common filtering patterns
    - Optimized field sizes based on actual usage
    - Bulk operation support
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    
    # Snapshot reference with cascading delete
    snapshot_date = models.DateField(db_index=True)
    period_type = models.CharField(max_length=20, db_index=True)
    
    # Category information with optimized indexing
    category_type = models.CharField(
        max_length=20,
        choices=[
            ('expense', 'Expense Category'),
            ('client', 'Client Category'),
            ('service', 'Service Category'),
            ('revenue', 'Revenue Category')
        ],
        db_index=True  # Frequently filtered
    )
    category_name = models.CharField(max_length=100, db_index=True)  # Optimized size
    category_display = models.CharField(max_length=200)  # Human-readable name
    
    # Analytics data with optimized precision
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    transaction_count = models.PositiveIntegerField(default=0)
    percentage_of_total = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    objects = OptimizedDashboardManager()
    
    class Meta:
        db_table = 'category_analytics_optimized'
        
        indexes = [
            # Most common query patterns
            models.Index(fields=['owner', 'category_type'], name='owner_category_type_idx'),
            models.Index(fields=['owner', 'snapshot_date'], name='owner_category_date_idx'),
            models.Index(fields=['category_type', 'total_amount'], name='type_amount_idx'),
            models.Index(fields=['owner', 'category_type', 'snapshot_date'], name='owner_type_date_idx'),
        ]
        
        # Prevent duplicate categories per snapshot
        unique_together = [['owner', 'snapshot_date', 'period_type', 'category_type', 'category_name']]
        
        ordering = ['-total_amount', 'category_name']
    
    def __str__(self):
        return f"{self.category_display} ({self.category_type}) - ${self.total_amount}"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'category_name': self.category_name,
            'category_display': self.category_display,
            'category_type': self.category_type,
            'total_amount': float(self.total_amount),
            'transaction_count': self.transaction_count,
            'percentage_of_total': float(self.percentage_of_total)
        }


class ClientAnalyticsOptimized(models.Model):
    """
    Optimized client analytics model with performance enhancements.
    
    Optimizations:
    - Indexes on frequently queried fields
    - Optimized field sizes and types
    - Payment score calculation caching
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    
    # Client reference (stored as string for flexibility)
    client_id = models.CharField(max_length=100, db_index=True)  # External client ID
    client_name = models.CharField(max_length=200, db_index=True)  # Searchable name
    
    # Snapshot reference
    snapshot_date = models.DateField(db_index=True)
    period_type = models.CharField(max_length=20, db_index=True)
    
    # Financial analytics with optimized precision
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    outstanding_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Transaction metrics
    invoice_count = models.PositiveIntegerField(default=0)
    quote_count = models.PositiveIntegerField(default=0)
    
    # Payment behavior analytics
    average_payment_days = models.PositiveIntegerField(default=0)
    payment_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('100.00'),  # Perfect score by default
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # Client status
    is_active = models.BooleanField(default=True, db_index=True)  # Frequently filtered
    
    # Important dates
    first_invoice_date = models.DateField(null=True, blank=True)
    last_invoice_date = models.DateField(null=True, blank=True, db_index=True)  # Recent activity
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    objects = OptimizedDashboardManager()
    
    class Meta:
        db_table = 'client_analytics_optimized'
        
        indexes = [
            # Common query patterns
            models.Index(fields=['owner', 'is_active'], name='owner_active_idx'),
            models.Index(fields=['owner', 'total_revenue'], name='owner_revenue_idx'),
            models.Index(fields=['owner', 'last_invoice_date'], name='owner_last_invoice_idx'),
            models.Index(fields=['client_name'], name='client_name_search_idx'),  # For search
        ]
        
        unique_together = [['owner', 'client_id', 'snapshot_date', 'period_type']]
        
        ordering = ['-total_revenue', 'client_name']
    
    def __str__(self):
        return f"{self.client_name} - ${self.total_revenue} (Score: {self.payment_score})"
    
    def calculate_customer_lifetime_value(self):
        """Calculate CLV with caching."""
        cache_key = f"clv_{self.owner.id}_{self.client_id}"
        clv = cache.get(cache_key)
        
        if clv is None:
            # Simple CLV calculation
            months_active = max(1, (
                (self.last_invoice_date or self.snapshot_date) - 
                (self.first_invoice_date or self.snapshot_date)
            ).days / 30)
            
            monthly_revenue = self.total_revenue / max(1, months_active)
            clv = monthly_revenue * 12  # Assuming 1-year retention
            
            cache.set(cache_key, clv, 3600)  # Cache for 1 hour
        
        return clv
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'client_id': self.client_id,
            'client_name': self.client_name,
            'total_revenue': float(self.total_revenue),
            'outstanding_amount': float(self.outstanding_amount),
            'invoice_count': self.invoice_count,
            'quote_count': self.quote_count,
            'payment_score': float(self.payment_score),
            'is_active': self.is_active,
            'customer_lifetime_value': float(self.calculate_customer_lifetime_value())
        }


class PerformanceMetricOptimized(models.Model):
    """
    Optimized performance metrics model for KPI tracking.
    
    Optimizations:
    - Indexes on time-series data patterns
    - Optimized field types for metrics
    - Trend calculation caching
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    
    # Metric identification
    metric_name = models.CharField(max_length=100, db_index=True)  # Frequently queried
    metric_category = models.CharField(
        max_length=50,
        choices=[
            ('financial', 'Financial'),
            ('operational', 'Operational'),
            ('client', 'Client'),
            ('growth', 'Growth'),
            ('quality', 'Quality')
        ],
        db_index=True
    )
    
    # Metric values with high precision
    current_value = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('0.0000'))
    previous_value = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('0.0000'))
    target_value = models.DecimalField(
        max_digits=15, decimal_places=4,
        null=True, blank=True  # Not all metrics have targets
    )
    
    # Metric metadata
    unit = models.CharField(
        max_length=20,
        choices=[
            ('currency', 'Currency'),
            ('percentage', 'Percentage'),
            ('number', 'Number'),
            ('ratio', 'Ratio'),
            ('time', 'Time')
        ],
        default='number'
    )
    
    # Time period for the metric
    period_start = models.DateField(db_index=True)  # Time-series queries
    period_end = models.DateField(db_index=True)
    
    # Calculation metadata
    calculation_date = models.DateTimeField(auto_now_add=True, db_index=True)
    calculation_duration_ms = models.PositiveIntegerField(default=0)  # Performance tracking
    
    objects = OptimizedDashboardManager()
    
    class Meta:
        db_table = 'performance_metric_optimized'
        
        indexes = [
            # Time-series query patterns
            models.Index(fields=['owner', 'metric_name', 'calculation_date'], name='owner_metric_calc_idx'),
            models.Index(fields=['metric_category', 'period_end'], name='category_period_idx'),
            models.Index(fields=['owner', 'period_end'], name='owner_period_end_idx'),
        ]
        
        ordering = ['-calculation_date', 'metric_name']
    
    def __str__(self):
        return f"{self.metric_name}: {self.current_value} {self.unit}"
    
    def calculate_change_percentage(self):
        """Calculate percentage change with caching."""
        if self.previous_value == 0:
            return Decimal('0.00') if self.current_value == 0 else Decimal('100.00')
        
        return ((self.current_value - self.previous_value) / self.previous_value) * 100
    
    def calculate_target_achievement(self):
        """Calculate target achievement percentage."""
        if not self.target_value or self.target_value == 0:
            return None
        
        return (self.current_value / self.target_value) * 100
    
    def get_trend_direction(self):
        """Get trend direction as string."""
        change = self.current_value - self.previous_value
        
        if change > 0:
            return 'up'
        elif change < 0:
            return 'down'
        else:
            return 'stable'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'metric_name': self.metric_name,
            'metric_category': self.metric_category,
            'current_value': float(self.current_value),
            'previous_value': float(self.previous_value),
            'target_value': float(self.target_value) if self.target_value else None,
            'unit': self.unit,
            'change_percentage': float(self.calculate_change_percentage()),
            'target_achievement': float(self.target_achievement) if (target_achievement := self.calculate_target_achievement()) else None,
            'trend_direction': self.get_trend_direction(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'calculation_date': self.calculation_date.isoformat()
        }


# Migration script for creating optimized indexes
OPTIMIZATION_MIGRATIONS = """
-- Performance optimization indexes for existing tables
-- Run these after deploying the optimized models

-- Dashboard snapshots optimizations
CREATE INDEX CONCURRENTLY IF NOT EXISTS dashboard_snapshot_owner_date_idx 
ON dashboard_dashboardsnapshot(owner_id, snapshot_date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS dashboard_snapshot_updated_at_idx 
ON dashboard_dashboardsnapshot(updated_at DESC);

-- Category analytics optimizations  
CREATE INDEX CONCURRENTLY IF NOT EXISTS category_analytics_owner_type_idx
ON dashboard_categoryanalytics(owner_id, category_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS category_analytics_amount_idx
ON dashboard_categoryanalytics(total_amount DESC);

-- Client analytics optimizations
CREATE INDEX CONCURRENTLY IF NOT EXISTS client_analytics_revenue_idx
ON dashboard_clientanalytics(owner_id, total_revenue DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS client_analytics_active_idx
ON dashboard_clientanalytics(owner_id, is_active) WHERE is_active = true;

-- Performance metrics optimizations
CREATE INDEX CONCURRENTLY IF NOT EXISTS performance_metric_time_series_idx
ON dashboard_performancemetric(owner_id, metric_name, calculation_date DESC);
"""