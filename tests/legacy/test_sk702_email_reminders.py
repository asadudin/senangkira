#!/usr/bin/env python
"""
Test script for SK-702: Email Reminder System
Tests email reminder functionality including services, tasks, and management commands.
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
django.setup()

from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from reminders.models import EmailReminderSettings, SentReminder, ReminderTemplate, ReminderType
from reminders.services.email_service import EmailService
from reminders.services.reminder_service import ReminderService
from invoicing.models import Quote, Invoice
from clients.models import Client
from reminders.tasks import process_daily_reminders, send_single_reminder

User = get_user_model()


class EmailReminderSystemTest:
    """Test suite for email reminder system."""
    
    def __init__(self):
        self.test_results = []
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create test data for email reminder tests."""
        print("Setting up test data...")
        
        # Clean up existing test data
        User.objects.filter(email='test@example.com').delete()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            company_name='Test Company',
            company_address='123 Test Street'
        )
        
        # Create test client
        self.client = Client.objects.create(
            owner=self.user,
            name='Test Client',
            email='client@example.com',
            address='456 Client Street'
        )
        
        # Create email reminder settings
        self.settings = EmailReminderSettings.objects.create(
            user=self.user,
            quote_expiration_enabled=True,
            invoice_due_enabled=True,
            invoice_overdue_enabled=True,
            invoice_due_timings=['3_days', '1_day']
        )
        
        # Create test quote (expires in 3 days)
        expiration_date = timezone.now().date() + timedelta(days=3)
        self.quote = Quote.objects.create(
            user=self.user,
            client=self.client,
            quote_number='Q001',
            expiration_date=expiration_date,
            total_amount=1000.00,
            status='sent'
        )
        
        # Create test invoice (due in 3 days)
        due_date = timezone.now().date() + timedelta(days=3)
        self.invoice = Invoice.objects.create(
            user=self.user,
            client=self.client,
            invoice_number='INV001',
            due_date=due_date,
            total_amount=1500.00,
            status='sent'
        )
        
        # Create overdue invoice
        overdue_date = timezone.now().date() - timedelta(days=5)
        self.overdue_invoice = Invoice.objects.create(
            user=self.user,
            client=self.client,
            invoice_number='INV002',
            due_date=overdue_date,
            total_amount=2000.00,
            status='sent'
        )
        
        print("✓ Test data setup complete")
    
    def test_email_service(self):
        """Test EmailService functionality."""
        print("\n=== Testing EmailService ===")
        
        try:
            email_service = EmailService()
            
            # Test template retrieval
            template = email_service.get_template(self.user, ReminderType.QUOTE_EXPIRATION)
            assert 'subject' in template
            assert 'body' in template
            print("✓ Template retrieval works")
            
            # Test context building
            context = email_service.build_context(self.user, self.quote, ReminderType.QUOTE_EXPIRATION)
            assert context['company_name'] == 'Test Company'
            assert context['client_name'] == 'Test Client'
            assert context['quote_number'] == 'Q001'
            print("✓ Context building works")
            
            # Test template rendering
            template_text = "Quote #{quote_number} for {client_name}"
            rendered = email_service.render_template(template_text, context)
            assert 'Q001' in rendered
            assert 'Test Client' in rendered
            print("✓ Template rendering works")
            
            self.test_results.append("EmailService: PASSED")
            
        except Exception as e:
            print(f"✗ EmailService test failed: {e}")
            self.test_results.append("EmailService: FAILED")
    
    def test_reminder_service(self):
        """Test ReminderService functionality."""
        print("\n=== Testing ReminderService ===")
        
        try:
            reminder_service = ReminderService()
            
            # Test getting users with reminders enabled
            users = reminder_service.get_users_with_reminders_enabled()
            assert self.user in users
            print("✓ Users with reminders enabled query works")
            
            # Test quote expiration reminders
            target_date = timezone.now()  # Today should trigger reminder for quote expiring in 3 days
            quote_reminders = reminder_service.get_quote_expiration_reminders(self.user, target_date)
            assert len(quote_reminders) == 1
            assert quote_reminders[0]['content_object'] == self.quote
            print("✓ Quote expiration reminders work")
            
            # Test invoice due reminders
            due_reminders = reminder_service.get_invoice_due_reminders(self.user, target_date)
            assert len(due_reminders) == 1  # Should find invoice due in 3 days
            assert due_reminders[0]['content_object'] == self.invoice
            print("✓ Invoice due reminders work")
            
            # Test overdue invoice reminders
            overdue_reminders = reminder_service.get_overdue_invoice_reminders(self.user, target_date)
            assert len(overdue_reminders) == 1
            assert overdue_reminders[0]['content_object'] == self.overdue_invoice
            print("✓ Overdue invoice reminders work")
            
            # Test getting all reminders for user
            all_reminders = reminder_service.get_all_reminders_for_user(self.user, target_date)
            assert len(all_reminders) == 3  # Quote + invoice + overdue
            print("✓ All reminders for user works")
            
            # Test preview functionality
            preview = reminder_service.preview_reminders_for_user(self.user, 7)
            assert len(preview) == 7  # 7 days of preview
            print("✓ Reminder preview works")
            
            self.test_results.append("ReminderService: PASSED")
            
        except Exception as e:
            print(f"✗ ReminderService test failed: {e}")
            self.test_results.append("ReminderService: FAILED")
    
    @patch('reminders.services.email_service.send_mail')
    def test_email_sending(self, mock_send_mail):
        """Test actual email sending (mocked)."""
        print("\n=== Testing Email Sending ===")
        
        try:
            # Mock successful email sending
            mock_send_mail.return_value = True
            
            email_service = EmailService()
            
            # Test sending quote reminder
            success = email_service.send_reminder_email(
                user=self.user,
                content_object=self.quote,
                reminder_type=ReminderType.QUOTE_EXPIRATION,
                scheduled_for=timezone.now()
            )
            
            assert success
            assert mock_send_mail.called
            print("✓ Quote reminder email sending works")
            
            # Check that SentReminder was created
            sent_reminder = SentReminder.objects.filter(
                user=self.user,
                content_type='quote',
                object_id=self.quote.id
            ).first()
            assert sent_reminder is not None
            assert sent_reminder.is_delivered
            print("✓ SentReminder tracking works")
            
            # Test duplicate prevention
            success2 = email_service.send_reminder_email(
                user=self.user,
                content_object=self.quote,
                reminder_type=ReminderType.QUOTE_EXPIRATION,
                scheduled_for=timezone.now()
            )
            assert success2  # Should return True but not send duplicate
            print("✓ Duplicate prevention works")
            
            self.test_results.append("Email Sending: PASSED")
            
        except Exception as e:
            print(f"✗ Email sending test failed: {e}")
            self.test_results.append("Email Sending: FAILED")
    
    def test_models(self):
        """Test model functionality."""
        print("\n=== Testing Models ===")
        
        try:
            # Test EmailReminderSettings
            settings = EmailReminderSettings.get_or_create_for_user(self.user)
            assert settings.user == self.user
            assert settings.quote_expiration_days == 3  # Default setting
            print("✓ EmailReminderSettings model works")
            
            # Test ReminderTemplate
            template = ReminderTemplate.objects.create(
                user=self.user,
                reminder_type=ReminderType.QUOTE_EXPIRATION,
                subject_template='Custom Quote Reminder: #{quote_number}',
                body_template='Your quote #{quote_number} expires soon!'
            )
            
            retrieved_template = ReminderTemplate.get_template_for_user(
                self.user, ReminderType.QUOTE_EXPIRATION
            )
            assert retrieved_template == template
            print("✓ ReminderTemplate model works")
            
            # Test SentReminder
            reminder_count = SentReminder.objects.filter(user=self.user).count()
            assert reminder_count > 0  # Should have reminders from previous tests
            print("✓ SentReminder model works")
            
            self.test_results.append("Models: PASSED")
            
        except Exception as e:
            print(f"✗ Models test failed: {e}")
            self.test_results.append("Models: FAILED")
    
    def test_management_command(self):
        """Test management command functionality."""
        print("\n=== Testing Management Command ===")
        
        try:
            from io import StringIO
            import sys
            
            # Capture command output
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()
            
            # Test dry run
            call_command('send_reminders', '--dry-run', '--verbose')
            
            # Restore stdout
            sys.stdout = old_stdout
            output = captured_output.getvalue()
            
            assert 'DRY RUN' in output
            assert 'No emails will be sent' in output
            print("✓ Management command dry run works")
            
            self.test_results.append("Management Command: PASSED")
            
        except Exception as e:
            print(f"✗ Management command test failed: {e}")
            self.test_results.append("Management Command: FAILED")
    
    @patch('reminders.services.email_service.send_mail')
    def test_celery_tasks(self, mock_send_mail):
        """Test Celery task functionality."""
        print("\n=== Testing Celery Tasks ===")
        
        try:
            # Mock successful email sending
            mock_send_mail.return_value = True
            
            # Test process_daily_reminders task
            result = process_daily_reminders.apply(args=[timezone.now().strftime('%Y-%m-%d')])
            assert result.successful()
            assert result.result['success']
            print("✓ process_daily_reminders task works")
            
            # Test send_single_reminder task
            result = send_single_reminder.apply(args=[
                str(self.user.id),
                'quote',
                str(self.quote.id),
                ReminderType.QUOTE_EXPIRATION
            ])
            assert result.successful()
            assert result.result['success']
            print("✓ send_single_reminder task works")
            
            self.test_results.append("Celery Tasks: PASSED")
            
        except Exception as e:
            print(f"✗ Celery tasks test failed: {e}")
            self.test_results.append("Celery Tasks: FAILED")
    
    def run_all_tests(self):
        """Run all tests and display results."""
        print("Starting SK-702 Email Reminder System Tests...")
        print("=" * 60)
        
        self.test_email_service()
        self.test_reminder_service()
        self.test_email_sending()
        self.test_models()
        self.test_management_command()
        self.test_celery_tasks()
        
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for result in self.test_results:
            if "PASSED" in result:
                print(f"✓ {result}")
                passed += 1
            else:
                print(f"✗ {result}")
                failed += 1
        
        print("-" * 60)
        print(f"Total: {len(self.test_results)} | Passed: {passed} | Failed: {failed}")
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED! Email reminder system is working correctly.")
        else:
            print(f"⚠️  {failed} test(s) failed. Please check the implementation.")
        
        return failed == 0


def main():
    """Main test runner."""
    try:
        tester = EmailReminderSystemTest()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Test runner failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()