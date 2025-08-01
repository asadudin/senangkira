"""
Email Reminder models for SenangKira.
Provides configuration and tracking for automated email reminders.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from invoicing.models import Quote, Invoice

User = get_user_model()


class ReminderType(models.TextChoices):
    """Types of reminders that can be sent."""
    QUOTE_EXPIRATION = 'quote_expiration', 'Quote Expiration'
    INVOICE_DUE = 'invoice_due', 'Invoice Due Date'
    INVOICE_OVERDUE = 'invoice_overdue', 'Invoice Overdue'


class ReminderTiming(models.TextChoices):
    """Timing options for when reminders should be sent."""
    ONE_DAY = '1_day', '1 Day'
    THREE_DAYS = '3_days', '3 Days'
    SEVEN_DAYS = '7_days', '7 Days'
    FOURTEEN_DAYS = '14_days', '14 Days'


class EmailReminderSettings(models.Model):
    """
    User-configurable settings for email reminders.
    Allows users to customize when and how they receive reminders.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='email_reminder_settings',
        help_text="User these settings belong to"
    )
    
    # Quote expiration reminders
    quote_expiration_enabled = models.BooleanField(
        default=True,
        help_text="Send reminders for quote expirations"
    )
    quote_expiration_timing = models.CharField(
        max_length=20,
        choices=ReminderTiming.choices,
        default=ReminderTiming.THREE_DAYS,
        help_text="When to send quote expiration reminders"
    )
    
    # Invoice due date reminders
    invoice_due_enabled = models.BooleanField(
        default=True,
        help_text="Send reminders for invoice due dates"
    )
    invoice_due_timings = models.JSONField(
        default=list,
        help_text="List of timing options for invoice due date reminders (e.g., ['3_days', '1_day'])"
    )
    
    # Overdue invoice reminders
    invoice_overdue_enabled = models.BooleanField(
        default=True,
        help_text="Send reminders for overdue invoices"
    )
    invoice_overdue_interval = models.IntegerField(
        default=3,
        help_text="Days between overdue reminders (0 for no recurring reminders)"
    )
    
    # General settings
    email_address = models.EmailField(
        help_text="Email address to send reminders to (defaults to user's email)"
    )
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reminders_settings'
        verbose_name = 'Email Reminder Settings'
        verbose_name_plural = 'Email Reminder Settings'
    
    def __str__(self):
        return f"Reminder settings for {self.user.email}"
    
    def save(self, *args, **kwargs):
        """Set default email address if not provided."""
        if not self.email_address:
            self.email_address = self.user.email
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create reminder settings for a user."""
        settings, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'email_address': user.email,
                'invoice_due_timings': [ReminderTiming.THREE_DAYS, ReminderTiming.ONE_DAY]
            }
        )
        return settings
    
    @property
    def quote_expiration_days(self):
        """Get the number of days before expiration for quote reminders."""
        timing_map = {
            ReminderTiming.ONE_DAY: 1,
            ReminderTiming.THREE_DAYS: 3,
            ReminderTiming.SEVEN_DAYS: 7,
            ReminderTiming.FOURTEEN_DAYS: 14,
        }
        return timing_map.get(self.quote_expiration_timing, 3)
    
    @property
    def invoice_due_days_list(self):
        """Get list of days before due date for invoice reminders."""
        timing_map = {
            ReminderTiming.ONE_DAY: 1,
            ReminderTiming.THREE_DAYS: 3,
            ReminderTiming.SEVEN_DAYS: 7,
            ReminderTiming.FOURTEEN_DAYS: 14,
        }
        return [timing_map.get(timing, 3) for timing in self.invoice_due_timings]


class SentReminder(models.Model):
    """
    Track sent reminders to prevent duplicates and provide audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_reminders',
        help_text="User this reminder was sent to"
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=ReminderType.choices,
        help_text="Type of reminder sent"
    )
    
    # Reference to the item this reminder is about
    content_type = models.CharField(
        max_length=20,
        choices=[
            ('quote', 'Quote'),
            ('invoice', 'Invoice'),
        ],
        help_text="Type of content this reminder is for"
    )
    object_id = models.UUIDField(help_text="ID of the quote or invoice")
    
    # Reminder details
    subject = models.CharField(max_length=200, help_text="Email subject")
    sent_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(
        help_text="When this reminder was originally scheduled for"
    )
    
    # Tracking
    is_delivered = models.BooleanField(default=False)
    delivery_attempts = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'reminders_sent'
        ordering = ['-sent_at']
        unique_together = ['user', 'content_type', 'object_id', 'reminder_type', 'scheduled_for']
        indexes = [
            models.Index(fields=['user', 'sent_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['reminder_type']),
            models.Index(fields=['scheduled_for']),
        ]
        verbose_name = 'Sent Reminder'
        verbose_name_plural = 'Sent Reminders'
    
    def __str__(self):
        return f"{self.reminder_type} reminder to {self.user.email} on {self.sent_at.strftime('%Y-%m-%d')}"
    
    @property
    def content_object(self):
        """Get the actual quote or invoice object this reminder is for."""
        if self.content_type == 'quote':
            try:
                return Quote.objects.get(id=self.object_id)
            except Quote.DoesNotExist:
                return None
        elif self.content_type == 'invoice':
            try:
                return Invoice.objects.get(id=self.object_id)
            except Invoice.DoesNotExist:
                return None
        return None


class ReminderTemplate(models.Model):
    """
    Customizable email templates for different reminder types.
    Allows users to customize the content of their reminders.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reminder_templates',
        help_text="User this template belongs to (null for system default)"
    )
    
    reminder_type = models.CharField(
        max_length=20,
        choices=ReminderType.choices,
        help_text="Type of reminder this template is for"
    )
    
    # Template content
    subject_template = models.CharField(
        max_length=200,
        help_text="Template for email subject (supports placeholders)"
    )
    body_template = models.TextField(
        help_text="Template for email body (supports placeholders)"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reminders_templates'
        unique_together = ['user', 'reminder_type']
        indexes = [
            models.Index(fields=['user', 'reminder_type']),
            models.Index(fields=['reminder_type']),
        ]
        verbose_name = 'Reminder Template'
        verbose_name_plural = 'Reminder Templates'
    
    def __str__(self):
        return f"{self.reminder_type} template for {self.user.email}"
    
    @classmethod
    def get_template_for_user(cls, user, reminder_type):
        """Get template for user, falling back to system default."""
        try:
            return cls.objects.get(user=user, reminder_type=reminder_type, is_active=True)
        except cls.DoesNotExist:
            # Return system default template (would be implemented separately)
            return None