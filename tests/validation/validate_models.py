#!/usr/bin/env python3
"""
Simple Django model validation script for SenangKira.
Validates that models match the schema.sql structure.
"""

import os
import sys
import django
from django.conf import settings

# Configure Django settings for validation
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'authentication',
            'clients',
            'invoicing',
            'expenses',
        ],
        AUTH_USER_MODEL='authentication.User',
        USE_TZ=True,
        SECRET_KEY='validation-key',
    )

django.setup()

def validate_models():
    """Validate Django models against schema.sql requirements."""
    print("🔍 Validating Django models against schema.sql...")
    
    # Import models after Django setup
    from authentication.models import User
    from clients.models import Client
    from invoicing.models import Item, Quote, QuoteLineItem, Invoice, InvoiceLineItem
    from expenses.models import Expense
    
    validation_results = []
    
    # User model validation
    print("\n📋 User Model (auth_user table):")
    user_fields = {f.name: f for f in User._meta.get_fields()}
    required_user_fields = ['id', 'email', 'password', 'company_name', 'company_address', 'company_logo']
    
    for field_name in required_user_fields:
        if field_name in user_fields:
            field = user_fields[field_name]
            print(f"  ✅ {field_name}: {field.__class__.__name__}")
        else:
            print(f"  ❌ Missing field: {field_name}")
            validation_results.append(f"User model missing field: {field_name}")
    
    # Client model validation
    print("\n👥 Client Model (clients_client table):")
    client_fields = {f.name: f for f in Client._meta.get_fields()}
    required_client_fields = ['id', 'name', 'email', 'phone', 'address', 'created_at', 'updated_at', 'owner']
    
    for field_name in required_client_fields:
        if field_name in client_fields:
            field = client_fields[field_name]
            print(f"  ✅ {field_name}: {field.__class__.__name__}")
        else:
            print(f"  ❌ Missing field: {field_name}")
            validation_results.append(f"Client model missing field: {field_name}")
    
    # Item model validation
    print("\n📦 Item Model (invoicing_item table):")
    item_fields = {f.name: f for f in Item._meta.get_fields()}
    required_item_fields = ['id', 'name', 'description', 'default_price', 'owner']
    
    for field_name in required_item_fields:
        if field_name in item_fields:
            field = item_fields[field_name]
            print(f"  ✅ {field_name}: {field.__class__.__name__}")
        else:
            print(f"  ❌ Missing field: {field_name}")
            validation_results.append(f"Item model missing field: {field_name}")
    
    # Quote model validation
    print("\n📝 Quote Model (invoicing_quote table):")
    quote_fields = {f.name: f for f in Quote._meta.get_fields()}
    required_quote_fields = ['id', 'status', 'quote_number', 'issue_date', 'total_amount', 'created_at', 'owner', 'client']
    
    for field_name in required_quote_fields:
        if field_name in quote_fields:
            field = quote_fields[field_name]
            print(f"  ✅ {field_name}: {field.__class__.__name__}")
        else:
            print(f"  ❌ Missing field: {field_name}")
            validation_results.append(f"Quote model missing field: {field_name}")
    
    # Invoice model validation  
    print("\n🧾 Invoice Model (invoicing_invoice table):")
    invoice_fields = {f.name: f for f in Invoice._meta.get_fields()}
    required_invoice_fields = ['id', 'status', 'invoice_number', 'issue_date', 'due_date', 'total_amount', 'created_at', 'owner', 'client', 'source_quote']
    
    for field_name in required_invoice_fields:
        if field_name in invoice_fields:
            field = invoice_fields[field_name]
            print(f"  ✅ {field_name}: {field.__class__.__name__}")
        else:
            print(f"  ❌ Missing field: {field_name}")
            validation_results.append(f"Invoice model missing field: {field_name}")
    
    # Expense model validation
    print("\n💰 Expense Model (expenses_expense table):")
    expense_fields = {f.name: f for f in Expense._meta.get_fields()}
    required_expense_fields = ['id', 'description', 'amount', 'date', 'receipt_image', 'created_at', 'owner']
    
    for field_name in required_expense_fields:
        if field_name in expense_fields:
            field = expense_fields[field_name]
            print(f"  ✅ {field_name}: {field.__class__.__name__}")
        else:
            print(f"  ❌ Missing field: {field_name}")
            validation_results.append(f"Expense model missing field: {field_name}")
    
    # Meta table validation
    print("\n🔗 Table Mappings:")
    expected_tables = {
        'User': 'auth_user',
        'Client': 'clients_client', 
        'Item': 'invoicing_item',
        'Quote': 'invoicing_quote',
        'QuoteLineItem': 'invoicing_quotelineitem',
        'Invoice': 'invoicing_invoice',
        'InvoiceLineItem': 'invoicing_invoicelineitem',
        'Expense': 'expenses_expense',
    }
    
    models = [User, Client, Item, Quote, QuoteLineItem, Invoice, InvoiceLineItem, Expense]
    for model in models:
        model_name = model.__name__
        expected_table = expected_tables.get(model_name)
        actual_table = model._meta.db_table
        
        if actual_table == expected_table:
            print(f"  ✅ {model_name} → {actual_table}")
        else:
            print(f"  ❌ {model_name} → {actual_table} (expected: {expected_table})")
            validation_results.append(f"{model_name} table mapping incorrect: {actual_table} vs {expected_table}")
    
    # Summary
    print(f"\n📊 Validation Summary:")
    if not validation_results:
        print("  🎉 All Django models match schema.sql structure!")
        print("  ✅ Models are ready for migrations")
        return True
    else:
        print(f"  ⚠️  Found {len(validation_results)} validation issues:")
        for issue in validation_results:
            print(f"    • {issue}")
        return False

if __name__ == '__main__':
    success = validate_models()
    sys.exit(0 if success else 1)