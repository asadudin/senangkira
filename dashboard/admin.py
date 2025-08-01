"""
Django admin configuration for dashboard models.
Provides administrative interface for dashboard analytics.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count

from .models import DashboardSnapshot, CategoryAnalytics, ClientAnalytics, PerformanceMetric


@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(admin.ModelAdmin):
    """Admin interface for dashboard snapshots."""
    
    list_display = [
        'snapshot_date', 'period_type', 'owner', 'total_revenue', 
        'total_expenses', 'net_profit', 'profit_margin_display', 'created_at'
    ]
    list_filter = ['period_type', 'snapshot_date', 'created_at']
    search_fields = ['owner__email', 'owner__company_name']
    readonly_fields = ['profit_margin', 'expense_ratio', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'snapshot_date', 'period_type')
        }),
        ('Financial Metrics', {
            'fields': (
                'total_revenue', 'total_expenses', 'net_profit', 
                'outstanding_amount', 'reimbursable_expenses'
            )
        }),
        ('Client Metrics', {
            'fields': ('total_clients', 'new_clients')
        }),
        ('Business Metrics', {
            'fields': (
                'total_invoices', 'total_quotes', 'quote_conversion_rate',
                'average_invoice_value', 'total_expense_count'
            )
        }),
        ('Calculated Fields', {
            'fields': ('profit_margin', 'expense_ratio'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def profit_margin_display(self, obj):
        """Display profit margin with color coding."""
        margin = obj.profit_margin
        if margin >= 20:
            color = 'green'
        elif margin >= 10:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.2f}%</span>',
            color, margin
        )
    profit_margin_display.short_description = 'Profit Margin'
    profit_margin_display.admin_order_field = 'net_profit'


@admin.register(CategoryAnalytics)
class CategoryAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for category analytics."""
    
    list_display = [
        'category_display', 'category_type', 'owner', 'total_amount',
        'transaction_count', 'percentage_display', 'snapshot_date'
    ]
    list_filter = ['category_type', 'period_type', 'snapshot_date']
    search_fields = ['owner__email', 'category_name', 'category_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'snapshot_date', 'period_type')
        }),
        ('Category Details', {
            'fields': ('category_type', 'category_name', 'category_display')
        }),
        ('Analytics Data', {
            'fields': ('total_amount', 'transaction_count', 'percentage_of_total')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def percentage_display(self, obj):
        """Display percentage with formatting."""
        return f"{obj.percentage_of_total:.1f}%"
    percentage_display.short_description = 'Percentage'
    percentage_display.admin_order_field = 'percentage_of_total'


@admin.register(ClientAnalytics)
class ClientAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for client analytics."""
    
    list_display = [
        'client_name', 'owner', 'total_revenue', 'invoice_count',
        'payment_score_display', 'is_active', 'snapshot_date'
    ]
    list_filter = ['is_active', 'period_type', 'snapshot_date']
    search_fields = ['owner__email', 'client_name']
    readonly_fields = ['average_invoice_value', 'client_lifetime_value']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'client_id', 'client_name', 'snapshot_date', 'period_type')
        }),
        ('Financial Metrics', {
            'fields': (
                'total_revenue', 'outstanding_amount', 'average_invoice_value'
            )
        }),
        ('Activity Metrics', {
            'fields': ('invoice_count', 'quote_count')
        }),
        ('Payment Behavior', {
            'fields': ('average_payment_days', 'payment_score')
        }),
        ('Client Status', {
            'fields': ('is_active', 'first_invoice_date', 'last_invoice_date')
        }),
        ('Calculated Fields', {
            'fields': ('client_lifetime_value',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def payment_score_display(self, obj):
        """Display payment score with color coding."""
        score = obj.payment_score
        if score >= 85:
            color = 'green'
        elif score >= 70:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}</span>',
            color, score
        )
    payment_score_display.short_description = 'Payment Score'
    payment_score_display.admin_order_field = 'payment_score'


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    """Admin interface for performance metrics."""
    
    list_display = [
        'metric_name', 'metric_category', 'owner', 'current_value',
        'change_display', 'target_achievement_display', 'calculation_date'
    ]
    list_filter = ['metric_category', 'unit', 'calculation_date']
    search_fields = ['owner__email', 'metric_name']
    readonly_fields = ['change_percentage', 'is_improving', 'target_achievement']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'metric_name', 'metric_category', 'unit')
        }),
        ('Metric Values', {
            'fields': ('current_value', 'previous_value', 'target_value')
        }),
        ('Period Information', {
            'fields': ('calculation_date', 'period_start', 'period_end')
        }),
        ('Calculated Fields', {
            'fields': ('change_percentage', 'is_improving', 'target_achievement'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def change_display(self, obj):
        """Display change percentage with color coding."""
        change = obj.change_percentage
        if change > 0:
            color = 'green'
            symbol = '↑'
        elif change < 0:
            color = 'red'
            symbol = '↓'
        else:
            color = 'gray'
            symbol = '→'
        
        return format_html(
            '<span style="color: {};">{} {:.2f}%</span>',
            color, symbol, abs(change)
        )
    change_display.short_description = 'Change'
    change_display.admin_order_field = 'change_percentage'
    
    def target_achievement_display(self, obj):
        """Display target achievement with progress bar style."""
        achievement = obj.target_achievement
        if achievement is None:
            return 'No Target'
        
        if achievement >= 100:
            color = 'green'
        elif achievement >= 75:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, achievement
        )
    target_achievement_display.short_description = 'Target Achievement'


# Additional admin customizations
admin.site.site_header = "SenangKira Dashboard Administration"
admin.site.site_title = "Dashboard Admin"
admin.site.index_title = "Dashboard Analytics Management"