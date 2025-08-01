"""
Serializers for monitoring API endpoints.
"""
from rest_framework import serializers
from .models import TaskExecution, SystemHealthMetric, TaskAlert


class TaskExecutionSerializer(serializers.ModelSerializer):
    """Serializer for TaskExecution model."""
    
    duration_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = TaskExecution
        fields = [
            'id', 'task_id', 'task_name', 'queue_name', 'user',
            'priority', 'priority_display', 'status', 'status_display',
            'scheduled_at', 'started_at', 'completed_at', 'duration', 'duration_display',
            'retry_count', 'worker_name', 'result_summary', 'error_message',
            'memory_usage', 'arguments', 'keyword_arguments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_duration_display(self, obj):
        """Get human-readable duration."""
        if obj.duration:
            return f"{obj.duration:.3f}s"
        return None


class SystemHealthMetricSerializer(serializers.ModelSerializer):
    """Serializer for SystemHealthMetric model."""
    
    class Meta:
        model = SystemHealthMetric
        fields = [
            'id', 'recorded_at', 'active_workers', 'total_workers',
            'pending_tasks', 'active_tasks', 'completed_tasks_hourly',
            'failed_tasks_hourly', 'avg_task_duration', 'success_rate',
            'queue_lengths', 'metadata'
        ]
        read_only_fields = ['id', 'recorded_at']


class TaskAlertSerializer(serializers.ModelSerializer):
    """Serializer for TaskAlert model."""
    
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    is_resolved = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TaskAlert
        fields = [
            'id', 'alert_type', 'alert_type_display', 'severity', 'severity_display',
            'title', 'message', 'task_execution', 'is_resolved',
            'triggered_at', 'resolved_at', 'metadata'
        ]
        read_only_fields = ['id', 'triggered_at', 'is_resolved']


class TaskMetricsSerializer(serializers.Serializer):
    """Serializer for task metrics response."""
    
    time_period_hours = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    successful_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    success_rate = serializers.FloatField()
    duration_stats = serializers.DictField()
    task_breakdown = serializers.DictField()
    queue_breakdown = serializers.DictField()
    timestamp = serializers.DateTimeField()


class SystemHealthSerializer(serializers.Serializer):
    """Serializer for system health response."""
    
    status = serializers.CharField()
    message = serializers.CharField()
    workers = serializers.DictField()
    tasks = serializers.DictField()
    queues = serializers.DictField()
    alerts = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class PerformanceAnalyticsSerializer(serializers.Serializer):
    """Serializer for performance analytics response."""
    
    period_days = serializers.IntegerField()
    daily_trends = serializers.ListField()
    top_failing_tasks = serializers.ListField()
    slowest_tasks = serializers.ListField()
    queue_performance = serializers.ListField()
    generated_at = serializers.DateTimeField()