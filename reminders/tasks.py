"""
Celery tasks for email reminder processing.
Background tasks for sending reminders and managing email workflows.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import shared_task
from django.utils import timezone
from django.core.management import call_command

from .services.reminder_service import ReminderService
from .services.email_service import EmailService


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_daily_reminders(self, target_date: str = None):
    """
    Process all daily reminders for a given date.
    
    Args:
        target_date: Date string in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Dict with processing statistics
    """
    try:
        # Parse target date or use today
        if target_date:
            target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
            target_datetime = timezone.make_aware(target_datetime)
        else:
            target_datetime = timezone.now()
        
        logger.info(f"Starting daily reminder processing for {target_datetime.date()}")
        
        # Process reminders
        reminder_service = ReminderService()
        stats = reminder_service.process_daily_reminders(target_datetime)
        
        logger.info(f"Daily reminder processing complete: {stats}")
        return {
            'success': True,
            'date': target_datetime.strftime('%Y-%m-%d'),
            'stats': stats,
            'processed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Daily reminder processing failed: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)  # 1min, 2min, 4min
            logger.info(f"Retrying in {countdown} seconds...")
            raise self.retry(countdown=countdown, exc=exc)
        
        # Final failure
        return {
            'success': False,
            'error': str(exc),
            'date': target_date or timezone.now().strftime('%Y-%m-%d'),
            'processed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2)
def send_single_reminder(self, user_id: str, content_type: str, object_id: str, reminder_type: str):
    """
    Send a single reminder email.
    
    Args:
        user_id: UUID string of the user
        content_type: 'quote' or 'invoice'
        object_id: UUID string of the quote/invoice
        reminder_type: Type of reminder to send
    
    Returns:
        Dict with send result
    """
    try:
        from authentication.models import User
        from invoicing.models import Quote, Invoice
        
        # Get user
        user = User.objects.get(id=user_id)
        
        # Get content object
        if content_type == 'quote':
            content_object = Quote.objects.select_related('client').get(id=object_id)
        elif content_type == 'invoice':
            content_object = Invoice.objects.select_related('client').get(id=object_id)
        else:
            raise ValueError(f"Invalid content_type: {content_type}")
        
        # Send reminder
        email_service = EmailService()
        success = email_service.send_reminder_email(
            user=user,
            content_object=content_object,
            reminder_type=reminder_type,
            scheduled_for=timezone.now()
        )
        
        result = {
            'success': success,
            'user_email': user.email,
            'content_type': content_type,
            'object_id': object_id,
            'reminder_type': reminder_type,
            'processed_at': timezone.now().isoformat()
        }
        
        if success:
            logger.info(f"Single reminder sent successfully: {result}")
        else:
            logger.warning(f"Single reminder failed to send: {result}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Single reminder task failed: {exc}")
        
        # Retry with shorter backoff for individual emails
        if self.request.retries < self.max_retries:
            countdown = 30 * (self.request.retries + 1)  # 30s, 60s
            logger.info(f"Retrying single reminder in {countdown} seconds...")
            raise self.retry(countdown=countdown, exc=exc)
        
        return {
            'success': False,
            'error': str(exc),
            'user_id': user_id,
            'content_type': content_type,
            'object_id': object_id,
            'reminder_type': reminder_type,
            'processed_at': timezone.now().isoformat()
        }


@shared_task
def test_email_configuration():
    """
    Test email configuration and connectivity.
    
    Returns:
        Dict with test result
    """
    try:
        email_service = EmailService()
        success = email_service.test_email_configuration()
        
        return {
            'success': success,
            'message': 'Email configuration test completed',
            'tested_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Email configuration test failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'tested_at': timezone.now().isoformat()
        }


@shared_task
def generate_reminder_preview(user_id: str, days_ahead: int = 7):
    """
    Generate reminder preview for a user.
    
    Args:
        user_id: UUID string of the user
        days_ahead: Number of days to preview
    
    Returns:
        Dict with preview data
    """
    try:
        from authentication.models import User
        
        user = User.objects.get(id=user_id)
        reminder_service = ReminderService()
        
        preview = reminder_service.preview_reminders_for_user(user, days_ahead)
        
        return {
            'success': True,
            'user_email': user.email,
            'days_ahead': days_ahead,
            'preview': preview,
            'generated_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Reminder preview generation failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'user_id': user_id,
            'generated_at': timezone.now().isoformat()
        }


@shared_task
def cleanup_old_reminders(days_to_keep: int = 90):
    """
    Clean up old sent reminder records.
    
    Args:
        days_to_keep: Number of days of reminder history to keep
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        from .models import SentReminder
        
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Count records to be deleted
        old_reminders = SentReminder.objects.filter(sent_at__lt=cutoff_date)
        count_to_delete = old_reminders.count()
        
        # Delete old records
        deleted_count, _ = old_reminders.delete()
        
        logger.info(f"Cleaned up {deleted_count} old reminder records")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.strftime('%Y-%m-%d'),
            'days_kept': days_to_keep,
            'cleaned_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Reminder cleanup failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'cleaned_at': timezone.now().isoformat()
        }


@shared_task
def send_reminder_statistics_email(user_id: str, days_back: int = 30):
    """
    Send reminder statistics email to a user.
    
    Args:
        user_id: UUID string of the user
        days_back: Number of days to include in statistics
    
    Returns:
        Dict with result
    """
    try:
        from authentication.models import User
        from django.core.mail import send_mail
        from django.conf import settings
        
        user = User.objects.get(id=user_id)
        reminder_service = ReminderService()
        
        # Get statistics
        stats = reminder_service.get_reminder_statistics(user, days_back)
        
        # Build email content
        subject = f"SenangKira Reminder Statistics - {days_back} Day Summary"
        message = f"""Dear {user.get_full_name() or user.username},

Here's your reminder activity summary for the past {days_back} days:

Total Reminders Sent: {stats['total_sent']}
Successfully Delivered: {stats['delivered']}
Failed Deliveries: {stats['failed']}

Breakdown by Type:
- Quote Expiration: {stats['by_type'].get('quote_expiration', 0)}
- Invoice Due: {stats['by_type'].get('invoice_due', 0)}
- Invoice Overdue: {stats['by_type'].get('invoice_overdue', 0)}

Recent Activity:
"""
        
        for reminder in stats['recent_reminders'][:5]:  # Show last 5
            status = "✓" if reminder['delivered'] else "✗"
            message += f"  {status} {reminder['type']} - {reminder['subject']} ({reminder['sent_at']})\n"
        
        message += f"""
Best regards,
SenangKira Reminder System
"""
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        
        return {
            'success': True,
            'user_email': user.email,
            'stats': stats,
            'sent_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Statistics email failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'user_id': user_id,
            'sent_at': timezone.now().isoformat()
        }