"""
Dashboard serializers for SenangKira API.
Handles serialization of dashboard analytics and KPI data.
"""

from rest_framework import serializers
from decimal import Decimal
from datetime import date
from typing import Dict, Any

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric


class DashboardSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for dashboard snapshot data."""
    
    profit_margin = serializers.ReadOnlyField()
    expense_ratio = serializers.ReadOnlyField()
    
    class Meta:
        model = DashboardSnapshot
        fields = [
            'id', 'snapshot_date', 'period_type',
            'total_revenue', 'total_expenses', 'net_profit', 'outstanding_amount',
            'total_clients', 'new_clients',
            'total_invoices', 'total_quotes', 'quote_conversion_rate', 'average_invoice_value',
            'total_expense_count', 'reimbursable_expenses',
            'profit_margin', 'expense_ratio',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategoryAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for category analytics data."""
    
    class Meta:
        model = CategoryAnalytics
        fields = [
            'id', 'snapshot_date', 'period_type',
            'category_type', 'category_name', 'category_display',
            'total_amount', 'transaction_count', 'percentage_of_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClientAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for client analytics data."""
    
    average_invoice_value = serializers.ReadOnlyField()
    client_lifetime_value = serializers.ReadOnlyField()
    
    class Meta:
        model = ClientAnalytics
        fields = [
            'id', 'client_id', 'client_name', 'snapshot_date', 'period_type',
            'total_revenue', 'invoice_count', 'quote_count', 'outstanding_amount',
            'average_payment_days', 'payment_score',
            'is_active', 'first_invoice_date', 'last_invoice_date',
            'average_invoice_value', 'client_lifetime_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceMetricSerializer(serializers.ModelSerializer):
    """Serializer for performance metrics (KPIs)."""
    
    change_percentage = serializers.ReadOnlyField()
    is_improving = serializers.ReadOnlyField()
    target_achievement = serializers.ReadOnlyField()
    
    class Meta:
        model = PerformanceMetric
        fields = [
            'id', 'metric_name', 'metric_category',
            'current_value', 'previous_value', 'target_value',
            'unit', 'calculation_date', 'period_start', 'period_end',
            'change_percentage', 'is_improving', 'target_achievement',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardOverviewSerializer(serializers.Serializer):
    """Comprehensive dashboard overview serializer."""
    
    # Financial summary
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Client metrics
    total_clients = serializers.IntegerField()
    new_clients = serializers.IntegerField()
    top_clients = ClientAnalyticsSerializer(many=True, read_only=True)
    
    # Business metrics
    total_invoices = serializers.IntegerField()
    total_quotes = serializers.IntegerField()
    quote_conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_invoice_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Expense metrics
    total_expense_count = serializers.IntegerField()
    reimbursable_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_categories = CategoryAnalyticsSerializer(many=True, read_only=True)
    
    # Performance indicators
    key_metrics = PerformanceMetricSerializer(many=True, read_only=True)
    
    # Meta information
    period_type = serializers.CharField()
    snapshot_date = serializers.DateField()
    last_updated = serializers.DateTimeField()


class DashboardStatsSerializer(serializers.Serializer):
    """Quick dashboard statistics serializer."""
    
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_change = serializers.DecimalField(max_digits=5, decimal_places=2)
    profit_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_change = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    active_clients = serializers.IntegerField()
    pending_invoices = serializers.IntegerField()
    overdue_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    expenses_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_change = serializers.DecimalField(max_digits=5, decimal_places=2)


class CategoryBreakdownSerializer(serializers.Serializer):
    """Category breakdown with charts data."""
    
    expense_categories = serializers.ListField(
        child=serializers.DictField(),
        help_text="Expense category breakdown for charts"
    )
    revenue_categories = serializers.ListField(
        child=serializers.DictField(),
        help_text="Revenue category breakdown for charts"
    )
    
    def to_representation(self, instance):
        """Custom representation for chart-friendly data."""
        if isinstance(instance, list):
            # Group by category type
            expense_cats = []
            revenue_cats = []
            
            for item in instance:
                chart_data = {
                    'name': item.category_display,
                    'value': float(item.total_amount),
                    'percentage': float(item.percentage_of_total),
                    'count': item.transaction_count
                }
                
                if item.category_type == 'expense':
                    expense_cats.append(chart_data)
                elif item.category_type in ['client', 'service']:
                    revenue_cats.append(chart_data)
            
            return {
                'expense_categories': expense_cats,
                'revenue_categories': revenue_cats
            }
        
        return super().to_representation(instance)


class TrendAnalysisSerializer(serializers.Serializer):
    """Trend analysis data for charts."""
    
    period = serializers.CharField()
    revenue_trend = serializers.ListField(
        child=serializers.DictField(),
        help_text="Revenue trend data points"
    )
    expense_trend = serializers.ListField(
        child=serializers.DictField(),
        help_text="Expense trend data points"
    )
    profit_trend = serializers.ListField(
        child=serializers.DictField(),
        help_text="Profit trend data points"
    )


class DashboardFiltersSerializer(serializers.Serializer):
    """Serializer for dashboard filter parameters."""
    
    period_type = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly', 'quarterly', 'yearly'],
        default='monthly'
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    client_id = serializers.UUIDField(required=False)
    category_type = serializers.ChoiceField(
        choices=['expense', 'client', 'service'],
        required=False
    )
    metric_category = serializers.ChoiceField(
        choices=['financial', 'operational', 'client', 'growth'],
        required=False
    )
    
    def validate(self, data):
        """Validate filter parameters."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("start_date must be before end_date")
        
        return data


class DashboardRefreshSerializer(serializers.Serializer):
    """Serializer for dashboard cache refresh operations."""
    
    force_refresh = serializers.BooleanField(default=False)
    refresh_types = serializers.MultipleChoiceField(
        choices=['snapshots', 'analytics', 'metrics', 'all'],
        default=['all']
    )
    
    # Read-only response fields
    refreshed = serializers.BooleanField(read_only=True)
    refresh_time = serializers.DateTimeField(read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    results = serializers.DictField(read_only=True)


class KPIComparisonSerializer(serializers.Serializer):
    """KPI comparison between periods."""
    
    metric_name = serializers.CharField()
    current_period = serializers.DictField()
    previous_period = serializers.DictField()
    change_amount = serializers.DecimalField(max_digits=15, decimal_places=4)
    change_percentage = serializers.DecimalField(max_digits=8, decimal_places=4)
    trend = serializers.ChoiceField(choices=['up', 'down', 'neutral'])
    target_achievement = serializers.DecimalField(max_digits=8, decimal_places=4, allow_null=True)


class ClientPerformanceSerializer(serializers.Serializer):
    """Client performance analysis."""
    
    client_id = serializers.UUIDField()
    client_name = serializers.CharField()
    
    # Financial metrics
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_invoice_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Behavioral metrics
    payment_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_payment_days = serializers.IntegerField()
    
    # Activity metrics
    invoice_count = serializers.IntegerField()
    quote_count = serializers.IntegerField()
    
    # Status
    is_active = serializers.BooleanField()
    risk_level = serializers.ChoiceField(
        choices=['low', 'medium', 'high'],
        help_text="Payment risk assessment"
    )
    
    def to_representation(self, instance):
        """Add calculated risk level."""
        data = super().to_representation(instance)
        
        # Calculate risk level based on payment score and outstanding amount
        payment_score = float(data['payment_score'])
        outstanding = float(data['outstanding_amount'])
        
        if payment_score < 70 or outstanding > 10000:
            risk_level = 'high'
        elif payment_score < 85 or outstanding > 5000:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        data['risk_level'] = risk_level
        return data


class RevenueProjectionSerializer(serializers.Serializer):
    """Revenue projection and forecasting."""
    
    period = serializers.CharField()
    projected_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    confidence_level = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Historical basis
    historical_average = serializers.DecimalField(max_digits=12, decimal_places=2)
    trend_factor = serializers.DecimalField(max_digits=8, decimal_places=4)
    
    # Breakdown
    confirmed_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    pipeline_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    recurring_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class DashboardExportSerializer(serializers.Serializer):
    """Dashboard data export configuration."""
    
    export_format = serializers.ChoiceField(
        choices=['csv', 'xlsx', 'pdf'],
        default='xlsx'
    )
    export_type = serializers.ChoiceField(
        choices=['overview', 'detailed', 'financial', 'clients', 'analytics'],
        default='overview'
    )
    period_type = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'yearly'],
        default='monthly'
    )
    include_charts = serializers.BooleanField(default=True)
    
    # Response fields
    export_url = serializers.URLField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    generated_at = serializers.DateTimeField(read_only=True)