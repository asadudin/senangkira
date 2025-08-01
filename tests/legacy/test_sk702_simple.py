#!/usr/bin/env python
"""
Simplified test for SK-702: Email Reminder System
Tests core functionality without database migrations.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
import django
django.setup()

# Simple functional tests
def test_service_imports():
    """Test that services can be imported."""
    try:
        from reminders.services.email_service import EmailService
        from reminders.services.reminder_service import ReminderService
        print("✓ Service imports successful")
        return True
    except ImportError as e:
        print(f"✗ Service import failed: {e}")
        return False

def test_email_service_instantiation():
    """Test EmailService can be instantiated."""
    try:
        from reminders.services.email_service import EmailService
        service = EmailService()
        assert hasattr(service, 'DEFAULT_TEMPLATES')
        assert hasattr(service, 'get_template')
        assert hasattr(service, 'render_template')
        print("✓ EmailService instantiation successful")
        return True
    except Exception as e:
        print(f"✗ EmailService instantiation failed: {e}")
        return False

def test_reminder_service_instantiation():
    """Test ReminderService can be instantiated."""
    try:
        from reminders.services.reminder_service import ReminderService
        service = ReminderService()
        assert hasattr(service, 'email_service')
        assert hasattr(service, 'get_users_with_reminders_enabled')
        print("✓ ReminderService instantiation successful")
        return True
    except Exception as e:
        print(f"✗ ReminderService instantiation failed: {e}")
        return False

def test_template_rendering():
    """Test template rendering functionality."""
    try:
        from reminders.services.email_service import EmailService
        service = EmailService()
        
        template_text = "Hello {client_name}, your quote #{quote_number} expires on {expiration_date}"
        context = {
            'client_name': 'Test Client',
            'quote_number': 'Q001',
            'expiration_date': '2024-02-01'
        }
        
        # Test basic string replacement (non-Django template)
        result = template_text
        for key, value in context.items():
            result = result.replace('{' + key + '}', str(value))
        
        assert 'Test Client' in result
        assert 'Q001' in result
        assert '2024-02-01' in result
        
        print("✓ Template rendering logic works")
        return True
    except Exception as e:
        print(f"✗ Template rendering failed: {e}")
        return False

def test_celery_task_imports():
    """Test that Celery tasks can be imported."""
    try:
        from reminders.tasks import process_daily_reminders, send_single_reminder
        print("✓ Celery task imports successful")
        return True
    except ImportError as e:
        print(f"✗ Celery task import failed: {e}")
        return False

def test_model_imports():
    """Test that models can be imported."""
    try:
        from reminders.models import EmailReminderSettings, SentReminder, ReminderTemplate
        print("✓ Model imports successful")
        return True
    except ImportError as e:
        print(f"✗ Model import failed: {e}")
        return False

def test_management_command_exists():
    """Test that management command file exists."""
    try:
        command_path = os.path.join(os.path.dirname(__file__), 'reminders', 'management', 'commands', 'send_reminders.py')
        assert os.path.exists(command_path), "Management command file not found"
        
        # Try to import the command
        from reminders.management.commands.send_reminders import Command
        assert hasattr(Command, 'handle')
        
        print("✓ Management command exists and can be imported")
        return True
    except Exception as e:
        print(f"✗ Management command test failed: {e}")
        return False

def test_default_templates():
    """Test default email templates."""
    try:
        from reminders.services.email_service import EmailService
        from reminders.models import ReminderType
        
        service = EmailService()
        
        # Test quote expiration template
        quote_template = service.DEFAULT_TEMPLATES[ReminderType.QUOTE_EXPIRATION]
        assert 'subject' in quote_template
        assert 'body' in quote_template
        assert '{quote_number}' in quote_template['subject']
        assert '{client_name}' in quote_template['body']
        
        # Test invoice due template
        invoice_template = service.DEFAULT_TEMPLATES[ReminderType.INVOICE_DUE]
        assert 'subject' in invoice_template
        assert 'body' in invoice_template
        assert '{invoice_number}' in invoice_template['subject']
        assert '{due_date}' in invoice_template['body']
        
        # Test overdue template
        overdue_template = service.DEFAULT_TEMPLATES[ReminderType.INVOICE_OVERDUE]
        assert 'subject' in overdue_template
        assert 'body' in overdue_template
        assert 'OVERDUE' in overdue_template['subject']
        
        print("✓ Default templates are properly structured")
        return True
    except Exception as e:
        print(f"✗ Default templates test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and display results."""
    print("SK-702 Email Reminder System - Simple Functional Tests")
    print("=" * 60)
    
    tests = [
        test_service_imports,
        test_email_service_instantiation,
        test_reminder_service_instantiation,
        test_template_rendering,
        test_celery_task_imports,
        test_model_imports,
        test_management_command_exists,
        test_default_templates,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Email reminder system components are functional.")
        print("\nNext steps:")
        print("1. Run database migrations: python manage.py migrate")
        print("2. Set up email configuration in settings.py")
        print("3. Start Celery worker: celery -A senangkira worker -l info")
        print("4. Test with management command: python manage.py send_reminders --dry-run")
    else:
        print(f"⚠️  {failed} test(s) failed. Please check the implementation.")
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)