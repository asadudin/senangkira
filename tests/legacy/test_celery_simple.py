#!/usr/bin/env python
"""
Simple test for Celery scheduled task configuration.
Tests the basic configuration without running into syntax issues.
"""
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
import django
django.setup()

from django.conf import settings


def test_celery_beat_exists():
    """Test that Celery Beat configuration exists."""
    try:
        assert hasattr(settings, 'CELERY_BEAT_SCHEDULE')
        print("✓ CELERY_BEAT_SCHEDULE exists")
        return True
    except Exception as e:
        print(f"✗ CELERY_BEAT_SCHEDULE test failed: {e}")
        return False


def test_reminder_tasks_exist():
    """Test that reminder tasks are in the schedule."""
    try:
        schedule = settings.CELERY_BEAT_SCHEDULE
        
        expected_tasks = [
            'process-daily-reminders',
            'process-evening-reminders', 
            'escalation-level-1-overdue',
            'escalation-level-2-urgent',
            'escalation-level-3-final',
            'send-weekly-reminder-stats'
        ]
        
        for task in expected_tasks:
            assert task in schedule, f"Task {task} not found"
        
        print("✓ All expected reminder tasks are configured")
        return True
    except Exception as e:
        print(f"✗ Reminder tasks test failed: {e}")
        return False


def test_task_imports():
    """Test that tasks can be imported."""
    try:
        from reminders.tasks import process_daily_reminders
        from reminders.tasks_additional import process_overdue_invoice_escalation
        print("✓ Tasks can be imported successfully")
        return True
    except Exception as e:
        print(f"✗ Task import test failed: {e}")
        return False


def test_celery_config():
    """Test basic Celery configuration."""
    try:
        assert hasattr(settings, 'CELERY_BROKER_URL')
        assert hasattr(settings, 'CELERY_RESULT_BACKEND')
        assert hasattr(settings, 'CELERY_TASK_ROUTES')
        print("✓ Basic Celery configuration exists")
        return True
    except Exception as e:
        print(f"✗ Celery config test failed: {e}")
        return False


def run_tests():
    """Run all tests."""
    print("Simple Celery Scheduled Task Configuration Test")
    print("=" * 50)
    
    tests = [
        test_celery_beat_exists,
        test_reminder_tasks_exist,
        test_task_imports,
        test_celery_config,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Celery scheduled tasks are configured.")
        
        # Show configured tasks
        schedule = settings.CELERY_BEAT_SCHEDULE
        print("\nConfigured scheduled tasks:")
        for task_name, config in schedule.items():
            if 'reminder' in task_name or 'escalation' in task_name:
                print(f"  • {task_name}: {config['task']}")
    else:
        print("❌ Some tests failed.")
    
    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)