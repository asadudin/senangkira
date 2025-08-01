"""
Dashboard models for SenangKira - Business Intelligence and Analytics.
Provides data structures for dashboard analytics and KPI caching.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


class DashboardSnapshot(models.Model):
    """
    Snapshot of dashboard data for caching and historical tracking.
    Stores pre-calculated KPIs for performance optimization.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='dashboard_snapshots',
        help_text="User who owns this dashboard snapshot"
    )
    
    # Time period
    snapshot_date = models.DateField(
        default=date.today,
        help_text="Date this snapshot represents"
    )
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly',
        help_text="Time period type for this snapshot"
    )
    
    # Financial KPIs
    total_revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total revenue for the period"
    )
    total_expenses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total expenses for the period"
    )
    net_profit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Net profit (revenue - expenses)"
    )
    outstanding_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total outstanding invoice amount"
    )
    
    # Client metrics
    total_clients = models.PositiveIntegerField(
        default=0,
        help_text="Total number of active clients"
    )
    new_clients = models.PositiveIntegerField(
        default=0,
        help_text="New clients added in this period"
    )
    
    # Invoice/Quote metrics
    total_invoices = models.PositiveIntegerField(
        default=0,
        help_text="Total invoices created in period"
    )
    total_quotes = models.PositiveIntegerField(
        default=0,
        help_text="Total quotes created in period"
    )
    quote_conversion_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Quote to invoice conversion rate percentage"
    )
    average_invoice_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Average invoice value for the period"
    )
    
    # Expense metrics
    total_expense_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of expenses in period"
    )
    reimbursable_expenses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total reimbursable expenses"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this snapshot was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this snapshot was last updated"
    )
    
    class Meta:
        ordering = ['-snapshot_date', '-created_at']
        unique_together = ['owner', 'snapshot_date', 'period_type']
        indexes = [
            models.Index(fields=['owner', 'snapshot_date']),
            models.Index(fields=['owner', 'period_type']),
            models.Index(fields=['snapshot_date']),
        ]
    
    def __str__(self):
        return f"{self.owner.email} - {self.period_type} - {self.snapshot_date}"
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.total_revenue > 0:
            return (self.net_profit / self.total_revenue) * 100
        return Decimal('0.00')
    
    @property
    def expense_ratio(self):
        """Calculate expense to revenue ratio."""
        if self.total_revenue > 0:
            return (self.total_expenses / self.total_revenue) * 100
        return Decimal('0.00')


class CategoryAnalytics(models.Model):
    """
    Analytics data for expense and revenue categories.
    Provides breakdown by category for detailed insights.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='category_analytics',
        help_text="User who owns this category analytics"
    )
    
    # Period information
    snapshot_date = models.DateField(
        default=date.today,
        help_text="Date this analytics represents"
    )
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )
    
    # Category information
    category_type = models.CharField(
        max_length=20,
        choices=[
            ('expense', 'Expense Category'),
            ('client', 'Client Category'),
            ('service', 'Service Category'),
        ]
    )
    category_name = models.CharField(
        max_length=100,
        help_text="Name of the category"
    )
    category_display = models.CharField(
        max_length=200,
        help_text="Display name for the category"
    )
    
    # Analytics data
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total amount for this category"
    )
    transaction_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of transactions in this category"
    )
    percentage_of_total = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Percentage of total amount"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_amount', 'category_name']
        unique_together = ['owner', 'snapshot_date', 'period_type', 'category_type', 'category_name']
        indexes = [
            models.Index(fields=['owner', 'category_type']),
            models.Index(fields=['snapshot_date', 'category_type']),
        ]
    
    def __str__(self):
        return f"{self.owner.email} - {self.category_name} - {self.snapshot_date}"


class ClientAnalytics(models.Model):
    """
    Analytics data for individual clients.
    Tracks client performance and payment behavior.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='client_analytics',
        help_text="User who owns this client analytics"
    )
    
    # Client reference (we don't want foreign key to avoid cascading issues)
    client_id = models.UUIDField(help_text="Reference to client ID")
    client_name = models.CharField(
        max_length=200,
        help_text="Client name for reference"
    )
    
    # Period information
    snapshot_date = models.DateField(default=date.today)
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )
    
    # Client metrics
    total_revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total revenue from this client"
    )
    invoice_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of invoices for this client"
    )
    quote_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of quotes for this client"
    )
    outstanding_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Outstanding amount from this client"
    )
    
    # Payment behavior
    average_payment_days = models.PositiveIntegerField(
        default=0,
        help_text="Average days to payment"
    )
    payment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('100.00'),
        help_text="Payment reliability score (0-100)"
    )
    
    # Client status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether client is currently active"
    )
    first_invoice_date = models.DateField(
        null=True, blank=True,
        help_text="Date of first invoice to this client"
    )
    last_invoice_date = models.DateField(
        null=True, blank=True,
        help_text="Date of most recent invoice"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-total_revenue', 'client_name']
        unique_together = ['owner', 'client_id', 'snapshot_date', 'period_type']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['client_id']),
            models.Index(fields=['snapshot_date']),
            models.Index(fields=['total_revenue']),
        ]
    
    def __str__(self):
        return f"{self.client_name} - {self.snapshot_date}"
    
    @property
    def average_invoice_value(self):
        """Calculate average invoice value for this client."""
        if self.invoice_count > 0:
            return self.total_revenue / self.invoice_count
        return Decimal('0.00')
    
    @property
    def client_lifetime_value(self):
        """Estimate client lifetime value."""
        if self.first_invoice_date and self.last_invoice_date:
            days_active = (self.last_invoice_date - self.first_invoice_date).days
            if days_active > 0:
                monthly_revenue = self.total_revenue / (days_active / 30)
                # Estimate 2 years lifetime
                return monthly_revenue * 24
        return self.total_revenue


class PerformanceMetric(models.Model):
    """
    Key Performance Indicators (KPIs) tracking.
    Stores calculated business metrics for dashboard display.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='performance_metrics'
    )
    
    # Metric identification
    metric_name = models.CharField(
        max_length=100,
        help_text="Name of the performance metric"
    )
    metric_category = models.CharField(
        max_length=50,
        choices=[
            ('financial', 'Financial'),
            ('operational', 'Operational'),
            ('client', 'Client'),
            ('growth', 'Growth'),
        ]
    )
    
    # Metric data
    current_value = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        help_text="Current metric value"
    )
    previous_value = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        default=Decimal('0.0000'),
        help_text="Previous period value for comparison"
    )
    target_value = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        null=True, blank=True,
        help_text="Target value for this metric"
    )
    
    # Metric metadata
    unit = models.CharField(
        max_length=20,
        default='number',
        choices=[
            ('currency', 'Currency'),
            ('percentage', 'Percentage'),
            ('number', 'Number'),
            ('days', 'Days'),
        ]
    )
    calculation_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this metric was calculated"
    )
    period_start = models.DateField(help_text="Start date of measurement period")
    period_end = models.DateField(help_text="End date of measurement period")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-calculation_date', 'metric_category', 'metric_name']
        unique_together = ['owner', 'metric_name', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['owner', 'metric_category']),
            models.Index(fields=['metric_name']),
            models.Index(fields=['calculation_date']),
        ]
    
    def __str__(self):
        return f"{self.owner.email} - {self.metric_name}"
    
    @property
    def change_percentage(self):
        """Calculate percentage change from previous value."""
        if self.previous_value > 0:
            return ((self.current_value - self.previous_value) / self.previous_value) * 100
        return Decimal('0.0000')
    
    @property
    def is_improving(self):
        """Determine if metric is improving (higher is better for most metrics)."""
        return self.current_value > self.previous_value
    
    @property
    def target_achievement(self):
        """Calculate percentage of target achieved."""
        if self.target_value and self.target_value > 0:
            return (self.current_value / self.target_value) * 100
        return None