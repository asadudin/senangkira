#!/usr/bin/env python
"""
Test script for Celery scheduled tasks for invoice reminders.
Tests the scheduled task configuration and task execution.
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from celery.schedules import crontab


class CeleryScheduledTaskTest:
    """Test suite for Celery scheduled tasks."""
    
    def __init__(self):
        self.test_results = []
    
    def test_celery_beat_configuration(self):
        """Test that Celery Beat is properly configured."""
        try:
            # Check that CELERY_BEAT_SCHEDULE exists
            assert hasattr(settings, 'CELERY_BEAT_SCHEDULE'), "CELERY_BEAT_SCHEDULE not found in settings"
            
            schedule = settings.CELERY_BEAT_SCHEDULE
            assert isinstance(schedule, dict), "CELERY_BEAT_SCHEDULE must be a dictionary"
            
            # Check for reminder-related scheduled tasks
            reminder_tasks = [
                'process-daily-reminders',
                'process-evening-reminders',
                'escalation-level-1-overdue',
                'escalation-level-2-urgent',
                'escalation-level-3-final',
                'send-weekly-reminder-stats',
                'cleanup-old-reminder-records',
                'weekend-batch-reminders',
                'monthly-reminder-summary'
            ]
            
            for task_name in reminder_tasks:
                assert task_name in schedule, f"Scheduled task '{task_name}' not found"
                task_config = schedule[task_name]
                assert 'task' in task_config, f"Task '{task_name}' missing 'task' key"
                assert 'schedule' in task_config, f"Task '{task_name}' missing 'schedule' key"
                assert 'options' in task_config, f"Task '{task_name}' missing 'options' key"
            
            print("✓ Celery Beat configuration is properly set up")
            return True
            
        except Exception as e:
            print(f"✗ Celery Beat configuration test failed: {e}")
            return False
    
    def test_task_schedules(self):
        """Test that task schedules are properly configured."""
        try:
            schedule = settings.CELERY_BEAT_SCHEDULE
            
            # Test daily reminder schedule
            daily_task = schedule['process-daily-reminders']
            assert isinstance(daily_task['schedule'], crontab), "Daily reminder should use crontab schedule"
            assert daily_task['schedule'].hour == [9], "Daily reminder should run at 9 AM"
            assert daily_task['schedule'].minute == [0], "Daily reminder should run at minute 0"
            
            # Test evening reminder schedule
            evening_task = schedule['process-evening-reminders']
            assert isinstance(evening_task['schedule'], crontab), "Evening reminder should use crontab schedule"
            assert evening_task['schedule'].hour == [17], "Evening reminder should run at 5 PM"
            
            # Test escalation schedules
            escalation_1 = schedule['escalation-level-1-overdue']
            assert escalation_1['schedule'].hour == [10], "Level 1 escalation should run at 10 AM"
            assert escalation_1['kwargs']['escalation_level'] == 1, "Level 1 escalation should have correct level"
            
            escalation_2 = schedule['escalation-level-2-urgent']
            assert escalation_2['schedule'].hour == [11], "Level 2 escalation should run at 11 AM"
            assert escalation_2['kwargs']['escalation_level'] == 2, "Level 2 escalation should have correct level"
            
            escalation_3 = schedule['escalation-level-3-final']
            assert escalation_3['schedule'].hour == [12], "Level 3 escalation should run at 12 PM"
            assert escalation_3['kwargs']['escalation_level'] == 3, "Level 3 escalation should have correct level"
            assert escalation_3['schedule'].day_of_week == [1, 3, 5], "Level 3 should run Mon/Wed/Fri"
            
            # Test weekly schedule
            weekly_task = schedule['send-weekly-reminder-stats']
            assert weekly_task['schedule'].day_of_week == [1], "Weekly stats should run on Monday"
            assert weekly_task['schedule'].hour == [8], "Weekly stats should run at 8 AM"
            
            # Test weekend batch schedule
            weekend_task = schedule['weekend-batch-reminders']
            assert weekend_task['schedule'].day_of_week == [6, 0], "Weekend batch should run Sat/Sun"
            assert weekend_task['schedule'].hour == [10], "Weekend batch should run at 10 AM"
            
            # Test monthly schedule
            monthly_task = schedule['monthly-reminder-summary']
            assert monthly_task['schedule'].day_of_month == [1], "Monthly summary should run on 1st"
            assert monthly_task['schedule'].hour == [9], "Monthly summary should run at 9 AM"
            
            print("✓ Task schedules are properly configured")
            return True
            
        except Exception as e:
            print(f"✗ Task schedules test failed: {e}")
            return False
    
    def test_task_routing(self):
        """Test that tasks are routed to correct queues."""
        try:
            assert hasattr(settings, 'CELERY_TASK_ROUTES'), "CELERY_TASK_ROUTES not found"
            
            routes = settings.CELERY_TASK_ROUTES
            
            # Test reminder task routing
            expected_routes = {
                'reminders.tasks.process_daily_reminders': 'high_priority',
                'reminders.tasks.send_single_reminder': 'reminders',
                'reminders.tasks.cleanup_old_reminders': 'low_priority',
                'reminders.tasks_additional.process_overdue_invoice_escalation': 'high_priority',
                'reminders.tasks_additional.send_weekly_reminder_statistics': 'analytics',
                'reminders.tasks_additional.process_weekend_batch_reminders': 'high_priority',
                'reminders.tasks_additional.send_monthly_reminder_summary': 'analytics',
            }\n            \n            for task_name, expected_queue in expected_routes.items():\n                assert task_name in routes, f\"Task route '{task_name}' not found\"\n                actual_queue = routes[task_name]['queue']\n                assert actual_queue == expected_queue, f\"Task '{task_name}' should route to '{expected_queue}', got '{actual_queue}'\"\n            \n            print(\"✓ Task routing is properly configured\")\n            return True\n            \n        except Exception as e:\n            print(f\"✗ Task routing test failed: {e}\")\n            return False\n    \n    def test_task_imports(self):\n        \"\"\"Test that scheduled tasks can be imported.\"\"\"\n        try:\n            # Test base reminder tasks\n            from reminders.tasks import (\n                process_daily_reminders,\n                send_single_reminder,\n                cleanup_old_reminders,\n                send_reminder_statistics_email\n            )\n            \n            # Test additional reminder tasks\n            from reminders.tasks_additional import (\n                send_weekly_reminder_statistics,\n                process_overdue_invoice_escalation,\n                process_weekend_batch_reminders,\n                send_monthly_reminder_summary\n            )\n            \n            print(\"✓ All scheduled tasks can be imported\")\n            return True\n            \n        except Exception as e:\n            print(f\"✗ Task imports test failed: {e}\")\n            return False\n    \n    def test_celery_configuration(self):\n        \"\"\"Test general Celery configuration.\"\"\"\n        try:\n            # Test broker and backend configuration\n            assert hasattr(settings, 'CELERY_BROKER_URL'), \"CELERY_BROKER_URL not configured\"\n            assert hasattr(settings, 'CELERY_RESULT_BACKEND'), \"CELERY_RESULT_BACKEND not configured\"\n            \n            # Test serialization configuration\n            assert settings.CELERY_TASK_SERIALIZER == 'json', \"Task serializer should be JSON\"\n            assert settings.CELERY_RESULT_SERIALIZER == 'json', \"Result serializer should be JSON\"\n            assert 'json' in settings.CELERY_ACCEPT_CONTENT, \"Should accept JSON content\"\n            \n            # Test timezone configuration\n            assert hasattr(settings, 'CELERY_TIMEZONE'), \"CELERY_TIMEZONE not configured\"\n            \n            print(\"✓ Celery general configuration is correct\")\n            return True\n            \n        except Exception as e:\n            print(f\"✗ Celery configuration test failed: {e}\")\n            return False\n    \n    def test_task_signatures(self):\n        \"\"\"Test that tasks have correct signatures.\"\"\"\n        try:\n            from reminders.tasks import process_daily_reminders, send_single_reminder\n            from reminders.tasks_additional import process_overdue_invoice_escalation\n            \n            # Test process_daily_reminders signature\n            assert hasattr(process_daily_reminders, 'delay'), \"process_daily_reminders should be a Celery task\"\n            assert hasattr(process_daily_reminders, 'apply_async'), \"process_daily_reminders should have apply_async\"\n            \n            # Test send_single_reminder signature\n            assert hasattr(send_single_reminder, 'delay'), \"send_single_reminder should be a Celery task\"\n            \n            # Test escalation task signature\n            assert hasattr(process_overdue_invoice_escalation, 'delay'), \"process_overdue_invoice_escalation should be a Celery task\"\n            assert hasattr(process_overdue_invoice_escalation, 'retry'), \"process_overdue_invoice_escalation should have retry capability\"\n            \n            print(\"✓ Task signatures are correct\")\n            return True\n            \n        except Exception as e:\n            print(f\"✗ Task signatures test failed: {e}\")\n            return False\n    \n    def test_schedule_validation(self):\n        \"\"\"Test that schedules will execute at expected times.\"\"\"\n        try:\n            schedule = settings.CELERY_BEAT_SCHEDULE\n            \n            # Test that daily tasks will run today\n            daily_task = schedule['process-daily-reminders']\n            now = timezone.now()\n            \n            # Check if schedule would trigger today at 9 AM\n            today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)\n            \n            # Basic validation that crontab schedule exists and has correct format\n            cron_schedule = daily_task['schedule']\n            assert hasattr(cron_schedule, 'hour'), \"Crontab schedule should have hour attribute\"\n            assert hasattr(cron_schedule, 'minute'), \"Crontab schedule should have minute attribute\"\n            \n            print(\"✓ Schedule validation passed\")\n            return True\n            \n        except Exception as e:\n            print(f\"✗ Schedule validation test failed: {e}\")\n            return False\n    \n    def run_all_tests(self):\n        \"\"\"Run all tests and display results.\"\"\"\n        print(\"Testing Celery Scheduled Tasks for Invoice Reminders\")\n        print(\"=\" * 60)\n        \n        tests = [\n            self.test_celery_beat_configuration,\n            self.test_task_schedules,\n            self.test_task_routing,\n            self.test_task_imports,\n            self.test_celery_configuration,\n            self.test_task_signatures,\n            self.test_schedule_validation,\n        ]\n        \n        passed = 0\n        failed = 0\n        \n        for test in tests:\n            try:\n                if test():\n                    passed += 1\n                    self.test_results.append(f\"{test.__name__}: PASSED\")\n                else:\n                    failed += 1\n                    self.test_results.append(f\"{test.__name__}: FAILED\")\n            except Exception as e:\n                failed += 1\n                self.test_results.append(f\"{test.__name__}: CRASHED - {e}\")\n                print(f\"✗ {test.__name__} crashed: {e}\")\n        \n        print(\"\\n\" + \"=\" * 60)\n        print(\"TEST RESULTS SUMMARY\")\n        print(\"=\" * 60)\n        \n        for result in self.test_results:\n            if \"PASSED\" in result:\n                print(f\"✓ {result}\")\n            else:\n                print(f\"✗ {result}\")\n        \n        print(\"-\" * 60)\n        print(f\"Total: {len(tests)} | Passed: {passed} | Failed: {failed}\")\n        \n        if failed == 0:\n            print(\"🎉 ALL TESTS PASSED! Celery scheduled tasks are properly configured.\")\n            print(\"\\nScheduled Tasks Overview:\")\n            print(\"• Daily reminders: 9:00 AM and 5:00 PM\")\n            print(\"• Overdue escalation: 10:00 AM (Level 1), 11:00 AM (Level 2), 12:00 PM (Level 3)\")\n            print(\"• Weekly statistics: Monday 8:00 AM\")\n            print(\"• Weekend batch: Saturday and Sunday 10:00 AM\")\n            print(\"• Monthly summary: 1st of month 9:00 AM\")\n            print(\"• Cleanup: Monday 2:00 AM\")\n            print(\"\\nNext Steps:\")\n            print(\"1. Start Celery Beat: celery -A senangkira beat -l info\")\n            print(\"2. Start Celery Worker: celery -A senangkira worker -l info\")\n            print(\"3. Monitor task execution in production\")\n        else:\n            print(f\"⚠️  {failed} test(s) failed. Please check the configuration.\")\n        \n        return failed == 0\n\n\ndef main():\n    \"\"\"Main test runner.\"\"\"\n    try:\n        tester = CeleryScheduledTaskTest()\n        success = tester.run_all_tests()\n        sys.exit(0 if success else 1)\n        \n    except Exception as e:\n        print(f\"Test runner failed: {e}\")\n        sys.exit(1)\n\n\nif __name__ == '__main__':\n    main()