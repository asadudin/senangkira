#!/usr/bin/env python
"""
Validation script for SK-102: Django Project Structure.
Tests project structure, URL routing, middleware, and infrastructure components.
"""

import os
import sys
import django
from pathlib import Path

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def test_project_structure():
    """Test Django project structure and app organization."""
    print("Testing Django project structure...")
    
    # Check required directories exist
    base_dir = Path(__file__).parent
    required_dirs = [
        'senangkira',
        'authentication',
        'clients', 
        'invoicing',
        'expenses',
        'dashboard',
        'docs'
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not (base_dir / dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    print(f"✅ All required directories exist: {len(required_dirs)} apps + project")
    
    # Check app structure
    apps = ['authentication', 'clients', 'invoicing', 'expenses', 'dashboard']
    required_files = ['__init__.py', 'apps.py', 'models.py']
    
    for app in apps:
        app_path = base_dir / app
        for file_name in required_files:
            if not (app_path / file_name).exists():
                print(f"❌ Missing {file_name} in {app} app")
                return False
    
    print("✅ All apps have required structure")
    
    # Check infrastructure components
    infra_components = [
        'senangkira/middleware/__init__.py',
        'senangkira/middleware/tenant_isolation.py',
        'senangkira/permissions/__init__.py', 
        'senangkira/permissions/base.py',
        'senangkira/utils/__init__.py',
        'senangkira/utils/views.py',
        'senangkira/utils/serializers.py',
        'senangkira/views.py'
    ]
    
    missing_components = []
    for component in infra_components:
        if not (base_dir / component).exists():
            missing_components.append(component)
    
    if missing_components:
        print(f"❌ Missing infrastructure components: {missing_components}")
        return False
    
    print("✅ All infrastructure components exist")
    return True

def test_url_routing():
    """Test URL routing configuration."""
    print("\nTesting URL routing...")
    
    try:
        from django.urls import reverse, resolve
        from django.test import Client
        from django.conf import settings
        
        # Test main project URLs
        client = Client()
        
        # Test API root
        response = client.get('/api/')
        if response.status_code != 200:
            print(f"❌ API root endpoint failed: {response.status_code}")
            return False
        
        # Test health check
        response = client.get('/api/health/')
        if response.status_code != 200:
            print(f"❌ Health check endpoint failed: {response.status_code}")
            return False
        
        print("✅ Main API endpoints working")
        
        # Test URL patterns are properly configured
        expected_patterns = [
            'api-root',
            'health-check',
        ]
        
        for pattern_name in expected_patterns:
            try:
                url = reverse(pattern_name)
                print(f"  ✅ {pattern_name}: {url}")
            except Exception as e:
                print(f"❌ URL pattern {pattern_name} not found: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ URL routing test failed: {e}")
        return False

def test_middleware_configuration():
    """Test middleware configuration."""
    print("\nTesting middleware configuration...")
    
    try:
        from django.conf import settings
        
        # Check custom middleware is installed
        expected_middleware = [
            'senangkira.middleware.tenant_isolation.TenantIsolationMiddleware',
            'senangkira.middleware.tenant_isolation.APIResponseMiddleware'
        ]
        
        for middleware in expected_middleware:
            if middleware not in settings.MIDDLEWARE:
                print(f"❌ Missing middleware: {middleware}")
                return False
        
        print("✅ Custom middleware configured")
        
        # Test middleware functionality
        from django.test import RequestFactory
        from senangkira.middleware.tenant_isolation import TenantIsolationMiddleware, APIResponseMiddleware
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        
        # Test tenant isolation middleware
        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse("OK")
        
        tenant_middleware = TenantIsolationMiddleware(get_response)
        response = tenant_middleware(request)
        
        if not hasattr(request, 'tenant_id'):
            print("❌ Tenant isolation middleware not adding tenant_id")
            return False
        
        print("✅ Tenant isolation middleware working")
        
        # Test API response middleware
        api_middleware = APIResponseMiddleware(get_response)
        response = api_middleware(request)
        
        if 'X-Content-Type-Options' not in response:
            print("❌ API response middleware not adding security headers")
            return False
        
        print("✅ API response middleware working")
        return True
        
    except Exception as e:
        print(f"❌ Middleware test failed: {e}")
        return False

def test_permissions_and_utils():
    """Test custom permissions and utility classes."""
    print("\nTesting permissions and utilities...")
    
    try:
        # Test permissions import
        from senangkira.permissions.base import IsOwner, IsOwnerOrReadOnly, IsTenantOwner
        print("✅ Custom permissions imported successfully")
        
        # Test utility views
        from senangkira.utils.views import TenantViewSetMixin, BaseAPIViewSet
        print("✅ Utility views imported successfully")
        
        # Test utility serializers
        from senangkira.utils.serializers import BaseModelSerializer, TimestampedSerializer
        print("✅ Utility serializers imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Permissions and utilities test failed: {e}")
        return False

def test_settings_configuration():
    """Test Django settings configuration."""
    print("\nTesting Django settings...")
    
    try:
        from django.conf import settings
        
        # Check required apps are installed
        required_apps = [
            'rest_framework',
            'rest_framework_simplejwt', 
            'corsheaders',
            'authentication',
            'clients',
            'invoicing',
            'expenses',
            'dashboard'
        ]
        
        for app in required_apps:
            if app not in settings.INSTALLED_APPS:
                print(f"❌ Missing app in INSTALLED_APPS: {app}")
                return False
        
        print("✅ All required apps installed")
        
        # Check database configuration
        db_config = settings.DATABASES['default']
        if db_config['ENGINE'] != 'django.db.backends.postgresql':
            print("❌ PostgreSQL not configured")
            return False
        
        print("✅ PostgreSQL database configured")
        
        # Check REST framework configuration
        if 'DEFAULT_AUTHENTICATION_CLASSES' not in settings.REST_FRAMEWORK:
            print("❌ REST framework authentication not configured")
            return False
        
        print("✅ REST framework configured")
        
        # Check JWT configuration
        if not hasattr(settings, 'SIMPLE_JWT'):
            print("❌ JWT configuration missing")
            return False
        
        print("✅ JWT configuration present")
        
        return True
        
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False

def test_django_check():
    """Run Django's built-in check command."""
    print("\nRunning Django system checks...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Capture stdout to prevent cluttering output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            execute_from_command_line(['manage.py', 'check'])
        
        output = f.getvalue()
        if 'System check identified no issues' in output or not output.strip():
            print("✅ Django system check passed")
            return True
        else:
            print(f"❌ Django system check failed: {output}")
            return False
            
    except SystemExit as e:
        if e.code == 0:
            print("✅ Django system check passed")
            return True
        else:
            print(f"❌ Django system check failed with code: {e.code}")
            return False
    except Exception as e:
        print(f"❌ Django system check failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("="*60)
    print("SK-102: Django Project Structure - Validation Tests")  
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Run all tests
    tests = [
        test_project_structure,
        test_url_routing,
        test_middleware_configuration,
        test_permissions_and_utils,
        test_settings_configuration,
        test_django_check
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nSK-102 Django Project Structure: COMPLETED")
        print("Ready to proceed with SK-103: Authentication System")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Fix issues before proceeding to next task")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)