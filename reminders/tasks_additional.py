"""
Additional Celery tasks for enhanced email reminder functionality.
These tasks extend the base reminder system with escalation and statistics.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import shared_task
from django.utils import timezone

from .services.reminder_service import ReminderService
from .services.email_service import EmailService


logger = logging.getLogger(__name__)


@shared_task
def send_weekly_reminder_statistics():
    """
    Send weekly reminder statistics to all users with reminder activity.
    
    Returns:
        Dict with processing results
    """
    try:
        from authentication.models import User
        from .models import SentReminder
        
        # Get users who have had reminder activity in the past week
        cutoff_date = timezone.now() - timedelta(days=7)
        active_user_ids = SentReminder.objects.filter(
            sent_at__gte=cutoff_date
        ).values('user_id').distinct()
        
        users_with_activity = User.objects.filter(
            id__in=[item['user_id'] for item in active_user_ids]
        )
        
        results = {
            'total_users': users_with_activity.count(),
            'emails_sent': 0,
            'emails_failed': 0,
            'processed_at': timezone.now().isoformat()
        }
        
        # Import the task to avoid circular imports
        from .tasks import send_reminder_statistics_email
        
        # Send weekly stats to each active user
        for user in users_with_activity:
            try:
                result = send_reminder_statistics_email.delay(
                    str(user.id), 
                    days_back=7
                )
                results['emails_sent'] += 1
                logger.info(f"Weekly stats queued for {user.email}")
            except Exception as e:
                results['emails_failed'] += 1
                logger.error(f"Failed to queue weekly stats for {user.email}: {e}")
        
        logger.info(f"Weekly reminder statistics processing complete: {results}")
        return results
        
    except Exception as exc:
        logger.error(f"Weekly reminder statistics failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'processed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2)
def process_overdue_invoice_escalation(self, escalation_level: int = 1):
    """
    Process overdue invoice escalation with increasing urgency.
    
    Args:
        escalation_level: Escalation level (1=first overdue, 2=second reminder, 3=final notice)
    
    Returns:
        Dict with processing statistics
    """
    try:
        from authentication.models import User
        from invoicing.models import Invoice
        from .models import SentReminder, ReminderType
        
        logger.info(f"Starting overdue invoice escalation level {escalation_level}")
        
        # Define escalation thresholds (days overdue)
        escalation_thresholds = {
            1: 1,   # 1 day overdue - first reminder
            2: 7,   # 1 week overdue - urgent reminder
            3: 14,  # 2 weeks overdue - final notice
        }
        
        min_days_overdue = escalation_thresholds.get(escalation_level, 1)
        max_days_overdue = escalation_thresholds.get(escalation_level + 1, float('inf'))
        
        current_date = timezone.now().date()
        min_due_date = current_date - timedelta(days=max_days_overdue)
        max_due_date = current_date - timedelta(days=min_days_overdue)
        
        # Find overdue invoices in the escalation range
        overdue_invoices = Invoice.objects.filter(
            due_date__gte=min_due_date,
            due_date__lt=max_due_date,
            status__in=['sent', 'partial']  # Only unpaid invoices
        ).select_related('user', 'client')
        
        stats = {
            'escalation_level': escalation_level,
            'invoices_processed': 0,
            'reminders_sent': 0,
            'reminders_failed': 0,
            'reminders_skipped': 0,
            'processed_at': timezone.now().isoformat()
        }
        
        email_service = EmailService()
        
        for invoice in overdue_invoices:
            stats['invoices_processed'] += 1
            
            try:
                # Check if user has overdue reminders enabled
                settings_obj = getattr(invoice.user, 'email_reminder_settings', None)
                if not settings_obj or not settings_obj.invoice_overdue_enabled:
                    stats['reminders_skipped'] += 1
                    continue
                
                # Check if we should send based on interval
                if escalation_level > 1:
                    # For escalated reminders, check last sent reminder
                    last_reminder = SentReminder.objects.filter(
                        user=invoice.user,
                        content_type='invoice',
                        object_id=invoice.id,
                        reminder_type=ReminderType.INVOICE_OVERDUE,
                        is_delivered=True
                    ).order_by('-sent_at').first()
                    
                    if last_reminder:
                        days_since_last = (current_date - last_reminder.sent_at.date()).days
                        if days_since_last < (escalation_level * 3):  # Increasing intervals
                            stats['reminders_skipped'] += 1
                            continue
                
                # Send escalated reminder
                success = email_service.send_reminder_email(
                    user=invoice.user,
                    content_object=invoice,
                    reminder_type=ReminderType.INVOICE_OVERDUE,
                    scheduled_for=timezone.now(),
                    escalation_level=escalation_level,
                    days_overdue=(current_date - invoice.due_date).days
                )
                
                if success:
                    stats['reminders_sent'] += 1
                    logger.info(f"Escalation level {escalation_level} sent for invoice {invoice.invoice_number}")
                else:
                    stats['reminders_failed'] += 1
                    
            except Exception as e:
                stats['reminders_failed'] += 1
                logger.error(f"Failed to process escalation for invoice {invoice.invoice_number}: {e}")
        
        logger.info(f"Overdue invoice escalation level {escalation_level} complete: {stats}")
        return stats
        
    except Exception as exc:
        logger.error(f"Overdue invoice escalation failed: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 300 * (2 ** self.request.retries)  # 5min, 10min
            logger.info(f"Retrying escalation in {countdown} seconds...")
            raise self.retry(countdown=countdown, exc=exc)
        
        return {
            'success': False,
            'error': str(exc),
            'escalation_level': escalation_level,
            'processed_at': timezone.now().isoformat()
        }


@shared_task
def process_weekend_batch_reminders():
    """
    Process batch reminders for weekend coverage.
    Runs Saturday and Sunday to catch any missed reminders.
    
    Returns:
        Dict with processing results
    """
    try:
        logger.info("Starting weekend batch reminder processing")
        
        # Process reminders for today and yesterday
        current_date = timezone.now()
        yesterday = current_date - timedelta(days=1)
        
        reminder_service = ReminderService()
        
        # Process today's reminders
        today_stats = reminder_service.process_daily_reminders(current_date)
        
        # Process yesterday's reminders (catch any missed)
        yesterday_stats = reminder_service.process_daily_reminders(yesterday)
        
        combined_stats = {
            'today': today_stats,
            'yesterday': yesterday_stats,
            'total_sent': today_stats.get('sent', 0) + yesterday_stats.get('sent', 0),
            'total_failed': today_stats.get('failed', 0) + yesterday_stats.get('failed', 0),
            'processed_at': timezone.now().isoformat()
        }
        
        logger.info(f"Weekend batch processing complete: {combined_stats}")
        return combined_stats
        
    except Exception as exc:
        logger.error(f"Weekend batch processing failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'processed_at': timezone.now().isoformat()
        }


@shared_task
def send_monthly_reminder_summary():
    """
    Send monthly reminder summary to all active users.
    
    Returns:
        Dict with processing results
    """
    try:
        from authentication.models import User
        from .models import SentReminder
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Get users who have had reminder activity in the past month
        cutoff_date = timezone.now() - timedelta(days=30)
        active_user_ids = SentReminder.objects.filter(
            sent_at__gte=cutoff_date
        ).values('user_id').distinct()
        
        users_with_activity = User.objects.filter(
            id__in=[item['user_id'] for item in active_user_ids]
        )
        
        results = {
            'total_users': users_with_activity.count(),
            'summaries_sent': 0,
            'summaries_failed': 0,
            'processed_at': timezone.now().isoformat()
        }
        
        reminder_service = ReminderService()
        
        for user in users_with_activity:
            try:
                # Get monthly statistics
                stats = reminder_service.get_reminder_statistics(user, 30)
                
                # Build summary email
                subject = "SenangKira Monthly Reminder Summary"
                message = f"""Dear {user.get_full_name() or user.username},

Your monthly reminder summary for SenangKira:

📊 Monthly Statistics:
• Total Reminders Sent: {stats['total_sent']}
• Successfully Delivered: {stats['delivered']}
• Delivery Rate: {(stats['delivered']/stats['total_sent']*100) if stats['total_sent'] > 0 else 0:.1f}%

📈 Breakdown by Type:
• Quote Expiration Reminders: {stats['by_type'].get('quote_expiration', 0)}
• Invoice Due Reminders: {stats['by_type'].get('invoice_due', 0)}
• Overdue Invoice Reminders: {stats['by_type'].get('invoice_overdue', 0)}

🎯 Performance Insights:
This month, your reminder system helped ensure timely communication with clients,
potentially improving payment collection and quote response rates.

💡 Tips for Better Results:
1. Review reminder timing settings if needed
2. Customize email templates for better client engagement
3. Monitor overdue patterns to adjust payment terms

Best regards,
SenangKira Team
"""
                
                # Send monthly summary
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
                
                results['summaries_sent'] += 1
                logger.info(f"Monthly summary sent to {user.email}")
                
            except Exception as e:
                results['summaries_failed'] += 1
                logger.error(f"Failed to send monthly summary to {user.email}: {e}")
        
        logger.info(f"Monthly reminder summary processing complete: {results}")
        return results
        
    except Exception as exc:
        logger.error(f"Monthly reminder summary failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'processed_at': timezone.now().isoformat()
        }