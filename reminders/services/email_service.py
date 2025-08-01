"""
Email service for sending reminder emails.
Handles template rendering, email composition, and delivery.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.core.mail import send_mail
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone

from ..models import ReminderTemplate, SentReminder, ReminderType


logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending reminder emails with template support."""
    
    DEFAULT_TEMPLATES = {
        ReminderType.QUOTE_EXPIRATION: {
            'subject': 'Quote #{quote_number} expires in {days_until_expiration} days',
            'body': '''Dear {client_name},

This is a friendly reminder that your quote #{quote_number} will expire in {days_until_expiration} days on {expiration_date}.

Quote Details:
- Quote Number: #{quote_number}
- Amount: ${total_amount}
- Expiration Date: {expiration_date}

To accept this quote, please contact us at your earliest convenience.

Best regards,
{company_name}
{company_address}'''
        },
        ReminderType.INVOICE_DUE: {
            'subject': 'Invoice #{invoice_number} is due in {days_until_due} days',
            'body': '''Dear {client_name},

This is a reminder that your invoice #{invoice_number} is due in {days_until_due} days on {due_date}.

Invoice Details:
- Invoice Number: #{invoice_number}
- Amount Due: ${total_amount}
- Due Date: {due_date}

Please ensure payment is made by the due date to avoid any late fees.

Best regards,
{company_name}
{company_address}'''
        },
        ReminderType.INVOICE_OVERDUE: {
            'subject': 'OVERDUE: Invoice #{invoice_number} - Payment Required',
            'body': '''Dear {client_name},

This invoice is now overdue and requires immediate attention.

Invoice Details:
- Invoice Number: #{invoice_number}
- Amount Due: ${total_amount}
- Original Due Date: {due_date}
- Days Overdue: {days_overdue}

Please contact us immediately to arrange payment or discuss payment options.

Best regards,
{company_name}
{company_address}'''
        }
    }
    
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
    
    def get_template(self, user, reminder_type: str) -> Dict[str, str]:
        """Get email template for user, falling back to default."""
        try:
            template = ReminderTemplate.get_template_for_user(user, reminder_type)
            if template:
                return {
                    'subject': template.subject_template,
                    'body': template.body_template
                }
        except Exception as e:
            logger.warning(f"Failed to get custom template for {user.email}: {e}")
        
        # Return default template
        return self.DEFAULT_TEMPLATES.get(reminder_type, {
            'subject': 'Reminder from {company_name}',
            'body': 'This is a reminder from {company_name}.'
        })
    
    def render_template(self, template_text: str, context: Dict[str, Any]) -> str:
        """Render Django template with context."""
        try:
            template = Template(template_text)
            return template.render(Context(context))
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            return template_text  # Return original if rendering fails
    
    def build_context(self, user, content_object, reminder_type: str, **kwargs) -> Dict[str, Any]:
        """Build template context from user, content object, and additional data."""
        context = {
            'user_name': user.get_full_name() or user.username,
            'user_email': user.email,
            'company_name': user.company_name or 'Your Company',
            'company_address': user.company_address or '',
            'reminder_type': reminder_type,
            'current_date': timezone.now().strftime('%B %d, %Y'),
        }
        
        # Add content-specific context
        if hasattr(content_object, 'client'):
            context.update({
                'client_name': content_object.client.name,
                'client_email': content_object.client.email,
            })
        
        if hasattr(content_object, 'quote_number'):
            # Quote context
            context.update({
                'quote_number': content_object.quote_number,
                'total_amount': str(content_object.total_amount),
                'expiration_date': content_object.expiration_date.strftime('%B %d, %Y') if content_object.expiration_date else 'N/A',
            })
            
            if content_object.expiration_date:
                days_until = (content_object.expiration_date - timezone.now().date()).days
                context['days_until_expiration'] = max(0, days_until)
        
        elif hasattr(content_object, 'invoice_number'):
            # Invoice context
            context.update({
                'invoice_number': content_object.invoice_number,
                'total_amount': str(content_object.total_amount),
                'due_date': content_object.due_date.strftime('%B %d, %Y') if content_object.due_date else 'N/A',
            })
            
            if content_object.due_date:
                days_until = (content_object.due_date - timezone.now().date()).days
                context['days_until_due'] = days_until
                context['days_overdue'] = max(0, -days_until)
        
        # Add any additional context
        context.update(kwargs)
        
        return context
    
    def send_reminder_email(
        self,
        user,
        content_object,
        reminder_type: str,
        scheduled_for: datetime,
        **kwargs
    ) -> bool:
        """Send a reminder email and track it."""
        try:
            # Check if already sent
            content_type = 'quote' if hasattr(content_object, 'quote_number') else 'invoice'
            existing_reminder = SentReminder.objects.filter(
                user=user,
                content_type=content_type,
                object_id=content_object.id,
                reminder_type=reminder_type,
                scheduled_for__date=scheduled_for.date()
            ).first()
            
            if existing_reminder:
                logger.info(f"Reminder already sent: {existing_reminder}")
                return True
            
            # Get template and build context
            template = self.get_template(user, reminder_type)
            context = self.build_context(user, content_object, reminder_type, **kwargs)
            
            # Render email content
            subject = self.render_template(template['subject'], context)
            body = self.render_template(template['body'], context)
            
            # Get recipient email from user settings or user email
            settings_obj = getattr(user, 'email_reminder_settings', None)
            recipient_email = settings_obj.email_address if settings_obj else user.email
            
            # Create reminder record
            sent_reminder = SentReminder.objects.create(
                user=user,
                reminder_type=reminder_type,
                content_type=content_type,
                object_id=content_object.id,
                subject=subject[:200],  # Truncate to fit field
                scheduled_for=scheduled_for
            )
            
            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=self.from_email,
                    recipient_list=[recipient_email],
                    fail_silently=False
                )
                
                sent_reminder.is_delivered = True
                sent_reminder.delivery_attempts = 1
                sent_reminder.save()
                
                logger.info(f"Reminder email sent successfully to {recipient_email}")
                return True
                
            except Exception as e:
                sent_reminder.delivery_attempts = 1
                sent_reminder.error_message = str(e)
                sent_reminder.save()
                
                logger.error(f"Failed to send email to {recipient_email}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process reminder email: {e}")
            return False
    
    def send_bulk_reminders(self, reminders_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Send multiple reminder emails and return stats."""
        stats = {'sent': 0, 'failed': 0, 'skipped': 0}
        
        for reminder_data in reminders_data:
            try:
                success = self.send_reminder_email(**reminder_data)
                if success:
                    stats['sent'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"Failed to process bulk reminder: {e}")
                stats['failed'] += 1
        
        return stats
    
    def test_email_configuration(self) -> bool:
        """Test email configuration by sending a test email."""
        try:
            send_mail(
                subject='SenangKira Email Configuration Test',
                message='This is a test email to verify email configuration.',
                from_email=self.from_email,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=False
            )
            return True
        except Exception as e:
            logger.error(f"Email configuration test failed: {e}")
            return False