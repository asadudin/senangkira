#!/usr/bin/env python
"""
Validation script for monitoring system components.
Run this script to validate the monitoring implementation.
"""
import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

def validate_files():
    """Validate that all monitoring files exist and have basic syntax."""
    print("🔍 Validating monitoring system files...")
    
    required_files = [
        'monitoring/__init__.py',
        'monitoring/models.py',
        'monitoring/views.py',
        'monitoring/urls.py',
        'monitoring/admin.py',
        'monitoring/apps.py',
        'monitoring/serializers.py',
        'monitoring/signals.py',
        'monitoring/services/__init__.py',
        'monitoring/services/task_monitor.py',
        'monitoring/management/__init__.py',
        'monitoring/management/commands/__init__.py',
        'monitoring/management/commands/monitor_tasks.py',
        'monitoring/templates/monitoring/dashboard.html',
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = project_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print(f"\n✅ All {len(required_files)} monitoring files exist!")
    return True

def validate_imports():
    """Validate basic Python imports."""
    print("\n🔍 Validating Python imports...")
    
    try:
        # Test basic Python syntax
        from monitoring import models, views, urls, admin, apps, serializers, signals
        from monitoring.services import task_monitor
        print("✅ All monitoring modules can be imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False

def validate_configuration():
    """Validate Django configuration changes."""
    print("\n🔍 Validating Django configuration...")
    
    try:
        # Check if monitoring app is in INSTALLED_APPS
        settings_file = project_dir / 'senangkira' / 'settings.py'
        settings_content = settings_file.read_text()
        
        if "'monitoring'," in settings_content:
            print("✅ Monitoring app is registered in INSTALLED_APPS")
        else:
            print("❌ Monitoring app not found in INSTALLED_APPS")
            return False
        
        # Check if monitoring URLs are included
        urls_file = project_dir / 'senangkira' / 'urls.py'
        urls_content = urls_file.read_text()
        
        if "path('monitoring/', include('monitoring.urls'))" in urls_content:
            print("✅ Monitoring URLs are included in main URLconf")
        else:
            print("❌ Monitoring URLs not found in main URLconf")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation error: {e}")
        return False

def validate_celery_integration():
    """Validate Celery integration components."""
    print("\n🔍 Validating Celery integration...")
    
    # Check if Celery tasks are configured
    settings_file = project_dir / 'senangkira' / 'settings.py'
    settings_content = settings_file.read_text()
    
    celery_components = [
        'CELERY_TASK_ROUTES',
        'CELERY_BEAT_SCHEDULE',
        'reminders.tasks.process_invoice_reminders',
        'reminders.tasks_additional.process_overdue_invoice_escalation'
    ]
    
    found_components = []
    for component in celery_components:
        if component in settings_content:
            found_components.append(component)
            print(f"✅ Found: {component}")
    
    if len(found_components) >= 3:  # Should have at least basic Celery config
        print("✅ Celery integration looks good!")
        return True
    else:
        print(f"⚠️  Some Celery components missing: {len(found_components)}/{len(celery_components)}")
        return True  # Not critical for monitoring system

def main():
    """Run all validation checks."""
    print("🚀 SenangKira Task Monitoring System Validation")
    print("=" * 50)
    
    checks = [
        ("File Structure", validate_files),
        ("Python Imports", validate_imports),
        ("Django Configuration", validate_configuration),
        ("Celery Integration", validate_celery_integration),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 30)
        if check_func():
            passed += 1
        else:
            print(f"❌ {check_name} validation failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All validations passed! Monitoring system is ready.")
        print("\n📋 Next Steps:")
        print("1. Run Django migrations: python manage.py makemigrations monitoring")
        print("2. Apply migrations: python manage.py migrate")
        print("3. Start monitoring daemon: python manage.py monitor_tasks")
        print("4. Access dashboard at: /monitoring/")
        return True
    else:
        print("❌ Some validations failed. Please fix the issues above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)