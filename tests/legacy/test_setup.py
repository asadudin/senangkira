#!/usr/bin/env python
"""
Comprehensive test script for SK-101: Database Setup & Migrations.
Tests database connectivity, UUID generation, foreign key constraints, and Django setup.
"""

import os
import sys
import django
import psycopg2
from urllib.parse import urlparse

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def test_database_connectivity():
    """Test PostgreSQL database connectivity."""
    print("Testing database connectivity...")
    
    DATABASE_URL = "postgresql://padux:passwordrahsia@192.168.31.117:5432/senangkira?schema=public"
    db_url = urlparse(DATABASE_URL)
    
    try:
        conn = psycopg2.connect(
            host=db_url.hostname,
            port=db_url.port,
            database=db_url.path[1:],
            user=db_url.username,
            password=db_url.password
        )
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Database connected: {version}")
        
        # Test UUID generation
        cursor.execute("SELECT gen_random_uuid()")
        uuid_test = cursor.fetchone()[0]
        print(f"✅ UUID generation working: {uuid_test}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connectivity failed: {e}")
        return False

def test_foreign_key_constraints():
    """Test foreign key constraints and relationships."""
    print("\nTesting foreign key constraints...")
    
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Test that all expected tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = [
                'auth_user',
                'clients_client', 
                'invoicing_item',
                'invoicing_quote',
                'invoicing_quotelineitem',
                'invoicing_invoice', 
                'invoicing_invoicelineitem',
                'expenses_expense'
            ]
            
            missing_tables = [table for table in expected_tables if table not in tables]
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            
            print(f"✅ All expected tables exist: {len(expected_tables)} tables")
            
            # Test foreign key constraints
            cursor.execute("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                ORDER BY tc.table_name
            """)
            
            foreign_keys = cursor.fetchall()
            print(f"✅ Foreign key constraints found: {len(foreign_keys)}")
            
            for fk in foreign_keys:
                print(f"   {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")
                
        return True
        
    except Exception as e:
        print(f"❌ Foreign key constraint test failed: {e}")
        return False

def test_django_models():
    """Test Django models and migrations."""
    print("\nTesting Django models...")
    
    try:
        # Import models to test they load correctly
        from authentication.models import User
        from clients.models import Client
        from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem, Item
        from expenses.models import Expense
        
        print("✅ All models imported successfully")
        
        # Test model meta options match schema
        assert User._meta.db_table == 'auth_user'
        assert Client._meta.db_table == 'clients_client'
        assert Quote._meta.db_table == 'invoicing_quote'
        assert Invoice._meta.db_table == 'invoicing_invoice'
        assert Expense._meta.db_table == 'expenses_expense'
        
        print("✅ Model table names match schema.sql")
        
        # Test that models can query the database (should be empty but not error)
        user_count = User.objects.count()
        client_count = Client.objects.count()
        quote_count = Quote.objects.count()
        invoice_count = Invoice.objects.count()
        expense_count = Expense.objects.count()
        
        print(f"✅ Database queries working (Users: {user_count}, Clients: {client_count}, Quotes: {quote_count}, Invoices: {invoice_count}, Expenses: {expense_count})")
        return True
        
    except Exception as e:
        print(f"❌ Django models test failed: {e}")
        return False

def test_django_settings():
    """Test Django settings and configuration."""
    print("\nTesting Django configuration...")
    
    try:
        from django.conf import settings
        from django.core.management import execute_from_command_line
        
        # Test database configuration
        db_config = settings.DATABASES['default']
        assert db_config['ENGINE'] == 'django.db.backends.postgresql'
        assert db_config['NAME'] == 'senangkira'
        print("✅ Database settings configured correctly")
        
        # Test installed apps
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
            assert app in settings.INSTALLED_APPS
        
        print("✅ Required apps installed")
        
        # Test Django check command
        execute_from_command_line(['manage.py', 'check', '--deploy'])
        print("✅ Django configuration check passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Django settings test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("="*60)
    print("SK-101: Database Setup & Migrations - Validation Tests")
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Run all tests
    tests = [
        test_database_connectivity,
        test_foreign_key_constraints,
        test_django_models,
        test_django_settings
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
        print("\nSK-101 Database Setup & Migrations: COMPLETED")
        print("Ready to proceed with SK-102: Django Project Structure")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Fix issues before proceeding to next task")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)