"""
Django admin configuration for monitoring models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import TaskExecution, SystemHealthMetric, TaskAlert


@admin.register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    """Admin interface for TaskExecution model."""
    
    list_display = [
        'task_name', 'task_id_short', 'status', 'priority', 'queue_name',
        'duration_display', 'retry_count', 'scheduled_at', 'completed_at'
    ]
    list_filter = ['status', 'priority', 'queue_name', 'task_name', 'created_at']
    search_fields = ['task_id', 'task_name', 'worker_name']
    readonly_fields = [
        'task_id', 'created_at', 'updated_at', 'duration', 'started_at',
        'completed_at', 'error_traceback_display'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_id', 'task_name', 'queue_name', 'priority', 'status')
        }),
        ('Execution Details', {
            'fields': ('user', 'worker_name', 'retry_count', 'arguments', 'keyword_arguments')
        }),
        ('Timing', {
            'fields': ('scheduled_at', 'started_at', 'completed_at', 'duration')
        }),
        ('Results', {
            'fields': ('result_summary', 'error_message', 'error_traceback_display', 'memory_usage')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def task_id_short(self, obj):
        """Display shortened task ID."""
        return obj.task_id[:8] + '...' if len(obj.task_id) > 8 else obj.task_id
    task_id_short.short_description = 'Task ID'
    
    def duration_display(self, obj):
        """Display formatted duration."""
        if obj.duration:
            return f"{obj.duration:.3f}s"
        return "-"
    duration_display.short_description = 'Duration'
    duration_display.admin_order_field = 'duration'
    
    def error_traceback_display(self, obj):
        """Display formatted error traceback."""
        if obj.error_traceback:
            return format_html('<pre style="white-space: pre-wrap;">{}</pre>', obj.error_traceback)
        return "-"
    error_traceback_display.short_description = 'Error Traceback'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(SystemHealthMetric)
class SystemHealthMetricAdmin(admin.ModelAdmin):
    """Admin interface for SystemHealthMetric model."""
    
    list_display = [
        'recorded_at', 'active_workers', 'total_workers', 'pending_tasks',
        'active_tasks', 'success_rate_display', 'avg_duration_display'
    ]
    list_filter = ['recorded_at', 'active_workers', 'success_rate']
    readonly_fields = ['id', 'recorded_at']
    ordering = ['-recorded_at']
    date_hierarchy = 'recorded_at'
    
    fieldsets = (
        ('Workers', {
            'fields': ('active_workers', 'total_workers')
        }),
        ('Tasks', {
            'fields': ('pending_tasks', 'active_tasks', 'completed_tasks_hourly', 'failed_tasks_hourly')
        }),
        ('Performance', {
            'fields': ('avg_task_duration', 'success_rate', 'queue_lengths')
        }),
        ('Metadata', {
            'fields': ('recorded_at', 'metadata'),
            'classes': ('collapse',)
        })
    )
    
    def success_rate_display(self, obj):
        """Display formatted success rate."""
        if obj.success_rate is not None:
            return f"{obj.success_rate:.1f}%"
        return "-"
    success_rate_display.short_description = 'Success Rate'
    success_rate_display.admin_order_field = 'success_rate'
    
    def avg_duration_display(self, obj):
        """Display formatted average duration."""
        if obj.avg_task_duration:
            return f"{obj.avg_task_duration:.3f}s"
        return "-"
    avg_duration_display.short_description = 'Avg Duration'
    avg_duration_display.admin_order_field = 'avg_task_duration'


@admin.register(TaskAlert)
class TaskAlertAdmin(admin.ModelAdmin):
    """Admin interface for TaskAlert model."""
    
    list_display = [
        'title', 'alert_type', 'severity', 'is_resolved_display',
        'triggered_at', 'resolved_at'
    ]
    list_filter = ['alert_type', 'severity', 'resolved_at', 'triggered_at']
    search_fields = ['title', 'message']
    readonly_fields = ['id', 'triggered_at', 'is_resolved']
    ordering = ['-triggered_at']
    date_hierarchy = 'triggered_at'
    actions = ['mark_resolved']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_type', 'severity', 'title', 'message')
        }),
        ('Related Task', {
            'fields': ('task_execution',)
        }),
        ('Resolution', {
            'fields': ('resolved_at',)
        }),
        ('Metadata', {
            'fields': ('triggered_at', 'metadata'),
            'classes': ('collapse',)
        })
    )
    
    def is_resolved_display(self, obj):
        """Display resolution status with color coding."""
        if obj.is_resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Active</span>')
    is_resolved_display.short_description = 'Status'
    is_resolved_display.admin_order_field = 'resolved_at'
    
    def mark_resolved(self, request, queryset):
        """Admin action to mark alerts as resolved."""
        count = 0
        for alert in queryset.filter(resolved_at__isnull=True):
            alert.resolve()
            count += 1
        
        self.message_user(request, f'Marked {count} alert(s) as resolved.')
    mark_resolved.short_description = 'Mark selected alerts as resolved'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('task_execution')