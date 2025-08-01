"""
Reminder service for coordinating email reminder logic.
Handles reminder scheduling, filtering, and business logic.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q

from authentication.models import User
from invoicing.models import Quote, Invoice
from ..models import EmailReminderSettings, ReminderType, ReminderTiming
from .email_service import EmailService


logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminder business logic and coordination."""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def get_users_with_reminders_enabled(self) -> List[User]:
        """Get all users who have any reminder type enabled."""
        return User.objects.filter(
            Q(email_reminder_settings__quote_expiration_enabled=True) |
            Q(email_reminder_settings__invoice_due_enabled=True) |
            Q(email_reminder_settings__invoice_overdue_enabled=True)
        ).select_related('email_reminder_settings')
    
    def get_quote_expiration_reminders(self, user: User, target_date: datetime) -> List[Dict[str, Any]]:
        """Get quotes that need expiration reminders for a user."""
        settings = EmailReminderSettings.get_or_create_for_user(user)
        
        if not settings.quote_expiration_enabled:
            return []
        
        # Calculate reminder date
        reminder_days = settings.quote_expiration_days
        reminder_date = target_date.date() + timedelta(days=reminder_days)
        
        # Find quotes expiring on the reminder date
        quotes = Quote.objects.filter(
            user=user,
            expiration_date=reminder_date,
            status__in=['draft', 'sent']  # Only active quotes
        ).select_related('client')
        
        reminders = []
        for quote in quotes:
            reminders.append({
                'user': user,
                'content_object': quote,
                'reminder_type': ReminderType.QUOTE_EXPIRATION,
                'scheduled_for': target_date,
            })
        
        return reminders
    
    def get_invoice_due_reminders(self, user: User, target_date: datetime) -> List[Dict[str, Any]]:
        """Get invoices that need due date reminders for a user."""
        settings = EmailReminderSettings.get_or_create_for_user(user)
        
        if not settings.invoice_due_enabled or not settings.invoice_due_timings:
            return []
        
        reminders = []
        reminder_days_list = settings.invoice_due_days_list
        
        for days in reminder_days_list:
            reminder_date = target_date.date() + timedelta(days=days)
            
            # Find invoices due on the reminder date
            invoices = Invoice.objects.filter(
                user=user,
                due_date=reminder_date,
                status__in=['sent', 'partial']  # Only unpaid invoices
            ).select_related('client')
            
            for invoice in invoices:
                reminders.append({
                    'user': user,
                    'content_object': invoice,
                    'reminder_type': ReminderType.INVOICE_DUE,
                    'scheduled_for': target_date,
                })
        
        return reminders
    
    def get_overdue_invoice_reminders(self, user: User, target_date: datetime) -> List[Dict[str, Any]]:
        """Get overdue invoices that need reminders for a user."""
        settings = EmailReminderSettings.get_or_create_for_user(user)
        
        if not settings.invoice_overdue_enabled:
            return []
        
        # Find overdue invoices
        overdue_invoices = Invoice.objects.filter(
            user=user,
            due_date__lt=target_date.date(),
            status__in=['sent', 'partial']  # Only unpaid invoices
        ).select_related('client')
        
        reminders = []
        for invoice in overdue_invoices:
            # Check if we should send a reminder based on interval
            if self._should_send_overdue_reminder(invoice, settings, target_date):
                reminders.append({
                    'user': user,
                    'content_object': invoice,
                    'reminder_type': ReminderType.INVOICE_OVERDUE,
                    'scheduled_for': target_date,
                })
        
        return reminders
    
    def _should_send_overdue_reminder(
        self, 
        invoice, 
        settings: EmailReminderSettings, 
        target_date: datetime
    ) -> bool:
        """Determine if an overdue reminder should be sent based on interval."""
        if settings.invoice_overdue_interval <= 0:
            # No recurring reminders
            return False
        
        # Check the last overdue reminder sent for this invoice
        from ..models import SentReminder
        last_reminder = SentReminder.objects.filter(
            user=invoice.user,
            content_type='invoice',
            object_id=invoice.id,
            reminder_type=ReminderType.INVOICE_OVERDUE,
            is_delivered=True
        ).order_by('-sent_at').first()
        
        if not last_reminder:
            # No previous reminder, send one
            return True
        
        # Check if enough time has passed since last reminder
        days_since_last = (target_date.date() - last_reminder.sent_at.date()).days
        return days_since_last >= settings.invoice_overdue_interval
    
    def get_all_reminders_for_user(self, user: User, target_date: datetime) -> List[Dict[str, Any]]:
        """Get all reminder types for a user on the target date."""
        all_reminders = []
        
        try:
            # Quote expiration reminders
            quote_reminders = self.get_quote_expiration_reminders(user, target_date)
            all_reminders.extend(quote_reminders)
            
            # Invoice due reminders
            due_reminders = self.get_invoice_due_reminders(user, target_date)
            all_reminders.extend(due_reminders)
            
            # Overdue invoice reminders
            overdue_reminders = self.get_overdue_invoice_reminders(user, target_date)
            all_reminders.extend(overdue_reminders)
            
            logger.info(f"Found {len(all_reminders)} reminders for {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to get reminders for {user.email}: {e}")
        
        return all_reminders
    
    def get_all_reminders_for_date(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Get all reminders for all users on the target date."""
        all_reminders = []
        users = self.get_users_with_reminders_enabled()
        
        logger.info(f"Processing reminders for {len(users)} users on {target_date.date()}")
        
        for user in users:
            user_reminders = self.get_all_reminders_for_user(user, target_date)
            all_reminders.extend(user_reminders)
        
        return all_reminders
    
    def process_daily_reminders(self, target_date: Optional[datetime] = None) -> Dict[str, int]:
        """Process all reminders for a given date (defaults to today)."""
        if target_date is None:
            target_date = timezone.now()
        
        logger.info(f"Processing daily reminders for {target_date.date()}")
        
        # Get all reminders for the date
        reminders = self.get_all_reminders_for_date(target_date)
        
        # Send reminders
        stats = self.email_service.send_bulk_reminders(reminders)
        
        logger.info(f"Daily reminder processing complete: {stats}")
        return stats
    
    def preview_reminders_for_user(
        self, 
        user: User, 
        days_ahead: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Preview upcoming reminders for a user (for dashboard/settings)."""
        preview = {}
        base_date = timezone.now()
        
        for day in range(days_ahead):
            target_date = base_date + timedelta(days=day)
            date_key = target_date.strftime('%Y-%m-%d')
            
            reminders = self.get_all_reminders_for_user(user, target_date)
            
            # Format for preview
            preview[date_key] = []
            for reminder in reminders:
                content = reminder['content_object']
                preview[date_key].append({
                    'type': reminder['reminder_type'],
                    'content_type': 'quote' if hasattr(content, 'quote_number') else 'invoice',
                    'number': getattr(content, 'quote_number', None) or getattr(content, 'invoice_number', None),
                    'client_name': content.client.name if hasattr(content, 'client') else 'Unknown',
                    'amount': str(content.total_amount) if hasattr(content, 'total_amount') else '0.00',
                    'due_date': content.due_date.strftime('%Y-%m-%d') if hasattr(content, 'due_date') and content.due_date else None,
                    'expiration_date': content.expiration_date.strftime('%Y-%m-%d') if hasattr(content, 'expiration_date') and content.expiration_date else None,
                })
        
        return preview
    
    def get_reminder_statistics(self, user: User, days_back: int = 30) -> Dict[str, Any]:
        """Get reminder statistics for a user."""
        from ..models import SentReminder
        
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        sent_reminders = SentReminder.objects.filter(
            user=user,
            sent_at__gte=cutoff_date
        )
        
        stats = {
            'total_sent': sent_reminders.count(),
            'delivered': sent_reminders.filter(is_delivered=True).count(),
            'failed': sent_reminders.filter(is_delivered=False).count(),
            'by_type': {},
            'recent_reminders': []
        }
        
        # Stats by reminder type
        for reminder_type, _ in ReminderType.choices:
            type_count = sent_reminders.filter(reminder_type=reminder_type).count()
            stats['by_type'][reminder_type] = type_count
        
        # Recent reminders
        recent = sent_reminders.order_by('-sent_at')[:10]
        for reminder in recent:
            stats['recent_reminders'].append({
                'type': reminder.reminder_type,
                'subject': reminder.subject,
                'sent_at': reminder.sent_at.strftime('%Y-%m-%d %H:%M'),
                'delivered': reminder.is_delivered,
            })
        
        return stats