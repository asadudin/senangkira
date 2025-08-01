"""
Admin configuration for Email Reminder models.
"""
from django.contrib import admin
from .models import EmailReminderSettings, SentReminder, ReminderTemplate


@admin.register(EmailReminderSettings)
class EmailReminderSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_address', 'quote_expiration_enabled', 
                   'invoice_due_enabled', 'invoice_overdue_enabled', 'created_at')
    list_filter = ('quote_expiration_enabled', 'invoice_due_enabled', 
                  'invoice_overdue_enabled', 'created_at')
    search_fields = ('user__email', 'user__username', 'email_address')
    readonly_fields = ('created_at', 'last_updated')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'email_address')
        }),
        ('Quote Expiration Reminders', {
            'fields': ('quote_expiration_enabled', 'quote_expiration_timing')
        }),
        ('Invoice Due Date Reminders', {
            'fields': ('invoice_due_enabled', 'invoice_due_timings')
        }),
        ('Overdue Invoice Reminders', {
            'fields': ('invoice_overdue_enabled', 'invoice_overdue_interval')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SentReminder)
class SentReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'reminder_type', 'content_type', 'subject', 
                   'sent_at', 'is_delivered')
    list_filter = ('reminder_type', 'content_type', 'is_delivered', 'sent_at')
    search_fields = ('user__email', 'subject', 'content_type')
    readonly_fields = ('sent_at', 'scheduled_for')
    
    fieldsets = (
        ('Recipient', {
            'fields': ('user',)
        }),
        ('Reminder Details', {
            'fields': ('reminder_type', 'content_type', 'object_id', 'subject')
        }),
        ('Timing', {
            'fields': ('sent_at', 'scheduled_for')
        }),
        ('Delivery Status', {
            'fields': ('is_delivered', 'delivery_attempts', 'error_message')
        }),
    )


@admin.register(ReminderTemplate)
class ReminderTemplateAdmin(admin.ModelAdmin):
    list_display = ('user', 'reminder_type', 'is_active', 'created_at')
    list_filter = ('reminder_type', 'is_active', 'created_at')
    search_fields = ('user__email', 'subject_template')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Template Information', {
            'fields': ('user', 'reminder_type', 'is_active')
        }),
        ('Content', {
            'fields': ('subject_template', 'body_template')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )