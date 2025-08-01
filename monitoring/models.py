"""
Task Monitoring Models for SenangKira.
Comprehensive tracking and monitoring of task execution, performance, and health.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class TaskExecutionStatus(models.TextChoices):
    """Status choices for task execution."""
    PENDING = 'pending', 'Pending'
    STARTED = 'started', 'Started'
    SUCCESS = 'success', 'Success'
    FAILURE = 'failure', 'Failure'
    RETRY = 'retry', 'Retry'
    REVOKED = 'revoked', 'Revoked'


class TaskPriority(models.TextChoices):
    """Priority levels for tasks."""
    LOW = 'low', 'Low'
    NORMAL = 'normal', 'Normal'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class TaskExecution(models.Model):
    """
    Track individual task executions with comprehensive metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Task identification
    task_id = models.CharField(max_length=255, unique=True, help_text="Celery task ID")
    task_name = models.CharField(max_length=255, help_text="Name of the executed task")
    queue_name = models.CharField(max_length=100, default='default', help_text="Queue name")
    
    # User context
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_executions',
        help_text="User who triggered the task (if applicable)"
    )
    
    # Execution details
    status = models.CharField(
        max_length=20,
        choices=TaskExecutionStatus.choices,
        default=TaskExecutionStatus.PENDING,
        help_text="Current task status"
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.NORMAL,
        help_text="Task priority level"
    )
    
    # Timing information
    scheduled_at = models.DateTimeField(help_text="When task was scheduled")
    started_at = models.DateTimeField(null=True, blank=True, help_text="When task execution started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When task completed")
    
    # Performance metrics
    duration = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Task execution duration in seconds"
    )
    retry_count = models.IntegerField(default=0, help_text="Number of retry attempts")
    memory_usage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Peak memory usage in MB"
    )
    
    # Result and error tracking
    result_summary = models.TextField(blank=True, help_text="Summary of task result")
    error_message = models.TextField(blank=True, help_text="Error message if task failed")
    error_traceback = models.TextField(blank=True, help_text="Full error traceback")
    
    # Additional metadata
    worker_name = models.CharField(max_length=255, blank=True, help_text="Worker that executed the task")
    arguments = models.JSONField(default=dict, help_text="Task arguments")
    keyword_arguments = models.JSONField(default=dict, help_text="Task keyword arguments")
    
    # System metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'monitoring_task_execution'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['task_name', 'status']),
            models.Index(fields=['user', 'scheduled_at']),
            models.Index(fields=['queue_name', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['priority', 'scheduled_at']),
        ]
        verbose_name = 'Task Execution'
        verbose_name_plural = 'Task Executions'
    
    def __str__(self):
        return f"{self.task_name} ({self.task_id[:8]}...)"
    
    @property
    def is_completed(self):
        """Check if task has completed (success or failure)."""
        return self.status in [TaskExecutionStatus.SUCCESS, TaskExecutionStatus.FAILURE]
    
    @property
    def execution_time_display(self):
        """Human-readable execution time."""
        if self.duration is None:
            return "N/A"
        
        if self.duration < 1:
            return f"{self.duration * 1000:.0f}ms"
        elif self.duration < 60:
            return f"{self.duration:.2f}s"
        else:
            minutes = int(self.duration // 60)
            seconds = self.duration % 60
            return f"{minutes}m {seconds:.1f}s"
    
    def mark_started(self, worker_name: str = ""):
        """Mark task as started."""
        self.status = TaskExecutionStatus.STARTED
        self.started_at = timezone.now()
        self.worker_name = worker_name
        self.save(update_fields=['status', 'started_at', 'worker_name', 'updated_at'])
    
    def mark_completed(self, success: bool, result_summary: str = "", error_message: str = "", 
                      error_traceback: str = "", memory_usage: float = None):
        """Mark task as completed with results."""
        self.status = TaskExecutionStatus.SUCCESS if success else TaskExecutionStatus.FAILURE
        self.completed_at = timezone.now()
        self.result_summary = result_summary
        self.error_message = error_message
        self.error_traceback = error_traceback
        
        if memory_usage is not None:
            self.memory_usage = memory_usage
        
        # Calculate duration
        if self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()
        
        self.save(update_fields=[
            'status', 'completed_at', 'result_summary', 'error_message', 
            'error_traceback', 'duration', 'memory_usage', 'updated_at'
        ])
    
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.status = TaskExecutionStatus.RETRY
        self.save(update_fields=['retry_count', 'status', 'updated_at'])


class SystemHealthMetric(models.Model):
    """
    Track system-wide health metrics over time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Timestamp
    recorded_at = models.DateTimeField(default=timezone.now, help_text="When metrics were recorded")
    
    # Worker metrics
    active_workers = models.IntegerField(default=0, help_text="Number of active workers")
    total_workers = models.IntegerField(default=0, help_text="Total number of workers")
    
    # Task metrics
    pending_tasks = models.IntegerField(default=0, help_text="Number of pending tasks")
    active_tasks = models.IntegerField(default=0, help_text="Number of active tasks")
    completed_tasks_hourly = models.IntegerField(default=0, help_text="Tasks completed in last hour")
    failed_tasks_hourly = models.IntegerField(default=0, help_text="Tasks failed in last hour")
    
    # Performance metrics
    avg_task_duration = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Average task duration in seconds (last hour)"
    )
    success_rate = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Task success rate percentage (last hour)"
    )
    
    # System resource metrics
    cpu_usage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="CPU usage percentage"
    )
    memory_usage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Memory usage in MB"
    )
    
    # Queue metrics
    queue_lengths = models.JSONField(
        default=dict,
        help_text="Length of each queue (queue_name: length)"
    )
    
    class Meta:
        db_table = 'monitoring_system_health'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['recorded_at']),
            models.Index(fields=['success_rate', 'recorded_at']),
        ]
        verbose_name = 'System Health Metric'
        verbose_name_plural = 'System Health Metrics'
    
    def __str__(self):
        return f"Health metrics at {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def health_status(self):
        """Determine overall health status based on metrics."""
        if self.active_workers == 0:
            return 'critical'
        elif self.success_rate < 80:
            return 'warning'
        elif self.pending_tasks > 100:
            return 'warning'
        elif self.avg_task_duration and self.avg_task_duration > 300:  # > 5 minutes
            return 'warning'
        else:
            return 'healthy'


class TaskAlert(models.Model):
    """
    Track alerts generated by the monitoring system.
    """
    ALERT_TYPES = [
        ('task_failure', 'Task Failure'),
        ('high_failure_rate', 'High Failure Rate'),
        ('worker_down', 'Worker Down'),
        ('queue_backlog', 'Queue Backlog'),
        ('slow_tasks', 'Slow Tasks'),
        ('system_overload', 'System Overload'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Alert details
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, help_text="Type of alert")
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, help_text="Alert severity")
    title = models.CharField(max_length=255, help_text="Alert title")
    message = models.TextField(help_text="Detailed alert message")
    
    # Context
    task_execution = models.ForeignKey(
        TaskExecution,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        help_text="Related task execution (if applicable)"
    )
    
    # Timing
    triggered_at = models.DateTimeField(default=timezone.now, help_text="When alert was triggered")
    acknowledged_at = models.DateTimeField(null=True, blank=True, help_text="When alert was acknowledged")
    resolved_at = models.DateTimeField(null=True, blank=True, help_text="When alert was resolved")
    
    # User tracking
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        help_text="User who acknowledged the alert"
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, help_text="Additional alert metadata")
    notification_sent = models.BooleanField(default=False, help_text="Whether notification was sent")
    
    class Meta:
        db_table = 'monitoring_task_alert'
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['triggered_at', 'acknowledged_at']),
            models.Index(fields=['severity', 'triggered_at']),
        ]
        verbose_name = 'Task Alert'
        verbose_name_plural = 'Task Alerts'
    
    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"
    
    @property
    def is_active(self):
        """Check if alert is still active (not resolved)."""
        return self.resolved_at is None
    
    @property
    def is_acknowledged(self):
        """Check if alert has been acknowledged."""
        return self.acknowledged_at is not None
    
    @property
    def is_resolved(self):
        """Check if alert has been resolved."""
        return self.resolved_at is not None
    
    def acknowledge(self, user: User):
        """Acknowledge the alert."""
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save(update_fields=['acknowledged_at', 'acknowledged_by'])
    
    def resolve(self):
        """Mark alert as resolved."""
        self.resolved_at = timezone.now()
        self.save(update_fields=['resolved_at'])