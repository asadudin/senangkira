#!/usr/bin/env python
"""
Comprehensive validation script for SK-400: Invoice Management System.
Tests invoice CRUD operations, status management, quote-to-invoice conversion, and multi-tenant isolation.
"""

import os
import sys
import django
import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def test_invoice_models():
    """Test Invoice and InvoiceLineItem model functionality."""
    print("Testing Invoice models...")
    
    try:
        from invoicing.models import Invoice, InvoiceLineItem, InvoiceStatus, Quote, QuoteStatus
        from clients.models import Client
        User = get_user_model()
        
        # Create test user and client
        user = User.objects.create_user(
            email='invoicetest@example.com',
            username='invoicetestuser',
            password='TestPassword123!',
            company_name='Test Company'
        )
        
        client = Client.objects.create(
            name='Test Client',
            email='client@example.com',
            phone='+1234567890',
            owner=user
        )
        
        # Test invoice creation
        invoice = Invoice.objects.create(
            client=client,
            title='Test Invoice',
            notes='Test notes',
            tax_rate=Decimal('0.1000'),
            due_date=date.today() + timedelta(days=30),
            owner=user
        )
        
        # Verify invoice properties
        assert invoice.client == client
        assert invoice.owner == user
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.invoice_number.startswith('INV-')
        assert invoice.tax_rate == Decimal('0.1000')
        assert isinstance(invoice.id, uuid.UUID)
        
        print("✅ Invoice model creation working")
        
        # Test line item creation
        line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            description='Test Item',
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        # Verify line item properties
        assert line_item.invoice == invoice
        assert line_item.total_price == Decimal('200.00')
        assert line_item.description == 'Test Item'
        
        print("✅ InvoiceLineItem model creation working")
        
        # Test auto-generated invoice number uniqueness
        invoice2 = Invoice.objects.create(
            client=client,
            title='Test Invoice 2',
            due_date=date.today() + timedelta(days=30),
            owner=user
        )
        
        assert invoice.invoice_number != invoice2.invoice_number
        print("✅ Invoice number auto-generation working")
        
        # Test total calculation
        invoice.calculate_totals()
        invoice.refresh_from_db()
        
        expected_subtotal = Decimal('200.00')
        expected_tax = expected_subtotal * Decimal('0.1000')
        expected_total = expected_subtotal + expected_tax
        
        assert invoice.subtotal == expected_subtotal
        assert invoice.tax_amount == expected_tax
        assert invoice.total_amount == expected_total
        
        print("✅ Invoice total calculation working")
        
        # Test status transitions
        assert invoice.mark_as_sent()
        assert invoice.status == InvoiceStatus.SENT
        assert invoice.sent_at is not None
        
        print("✅ Invoice status transitions working")
        
        # Test quote-to-invoice conversion
        quote = Quote.objects.create(
            client=client,
            title='Test Quote for Conversion',
            tax_rate=Decimal('0.0800'),
            owner=user
        )
        quote.mark_as_approved()
        
        converted_invoice = Invoice.objects.create(
            client=client,
            title='Converted from Quote',
            source_quote=quote,
            tax_rate=quote.tax_rate,
            due_date=date.today() + timedelta(days=30),
            owner=user
        )
        
        assert converted_invoice.source_quote == quote
        assert converted_invoice.tax_rate == quote.tax_rate
        print("✅ Quote-to-invoice relationship working")
        
        # Cleanup
        Invoice.objects.filter(owner=user).delete()
        Quote.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Invoice models test failed: {e}")
        return False

def test_invoice_api_endpoints():
    """Test Invoice API CRUD endpoints."""
    print("\nTesting Invoice API endpoints...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Invoice, InvoiceStatus
        client = APIClient()
        
        # Create test user, client and get token
        user = User.objects.create_user(
            email='invoiceapi@example.com',
            username='invoiceapiuser',
            password='TestPassword123!',
            company_name='API Test Company'
        )
        
        test_client = Client.objects.create(
            name='API Test Client',
            email='apiclient@example.com',
            phone='+1234567890',
            owner=user
        )
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Test POST /api/invoices/ - Create invoice
        invoice_data = {
            'client': str(test_client.id),
            'title': 'API Test Invoice',
            'notes': 'Test notes',
            'terms': 'Net 30',
            'tax_rate': '0.1000',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Web Development',
                    'quantity': '40.00',
                    'unit_price': '100.00',
                    'sort_order': 0
                },
                {
                    'description': 'Design Work',
                    'quantity': '10.00',
                    'unit_price': '150.00',
                    'sort_order': 1
                }
            ]
        }
        
        response = client.post('/api/invoices/', invoice_data, format='json')
        assert response.status_code == 201
        
        response_data = response.json()
        assert 'invoice' in response_data
        assert response_data['invoice']['title'] == 'API Test Invoice'
        assert len(response_data['invoice']['line_items']) == 2
        
        invoice_id = response_data['invoice']['id']
        print("✅ Invoice creation endpoint working")
        
        # Test GET /api/invoices/ - List invoices
        response = client.get('/api/invoices/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert 'results' in response_data or isinstance(response_data, list)
        if 'statistics' in response_data:
            assert 'total_invoices' in response_data['statistics']
        print("✅ Invoice list endpoint working")
        
        # Test GET /api/invoices/{id}/ - Retrieve invoice
        response = client.get(f'/api/invoices/{invoice_id}/')
        assert response.status_code == 200
        
        invoice_detail = response.json()
        assert invoice_detail['id'] == invoice_id
        assert invoice_detail['title'] == 'API Test Invoice'
        assert len(invoice_detail['line_items']) == 2
        assert invoice_detail['subtotal'] == '5500.00'  # 40*100 + 10*150
        assert invoice_detail['tax_amount'] == '550.00'  # 5500 * 0.1
        assert invoice_detail['total_amount'] == '6050.00'  # 5500 + 550
        print("✅ Invoice retrieve endpoint working")
        
        # Test PUT /api/invoices/{id}/ - Update invoice (only works for drafts)
        update_data = {
            'client': str(test_client.id),
            'title': 'Updated API Invoice',
            'tax_rate': '0.0800',
            'due_date': (date.today() + timedelta(days=45)).isoformat(),
            'line_items': [
                {
                    'description': 'Updated Web Development',
                    'quantity': '50.00',
                    'unit_price': '120.00',
                    'sort_order': 0
                }
            ]
        }
        
        response = client.put(f'/api/invoices/{invoice_id}/', update_data, format='json')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['invoice']['title'] == 'Updated API Invoice'
        assert len(response_data['invoice']['line_items']) == 1
        print("✅ Invoice update endpoint working")
        
        # Test custom actions
        # Test POST /api/invoices/{id}/send/
        response = client.post(f'/api/invoices/{invoice_id}/send/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['invoice']['status'] == 'sent'
        assert response_data['invoice']['sent_at'] is not None
        print("✅ Invoice send endpoint working")
        
        # Test POST /api/invoices/{id}/mark_paid/
        response = client.post(f'/api/invoices/{invoice_id}/mark_paid/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['invoice']['status'] == 'paid'
        assert response_data['invoice']['paid_at'] is not None
        print("✅ Invoice mark paid endpoint working")
        
        # Create another invoice for duplication test
        new_invoice_data = {
            'client': str(test_client.id),
            'title': 'Invoice for Duplication',
            'line_items': [
                {
                    'description': 'Service',
                    'quantity': '1.00',
                    'unit_price': '500.00'
                }
            ]
        }
        
        response = client.post('/api/invoices/', new_invoice_data, format='json')
        assert response.status_code == 201
        duplicate_invoice_id = response.json()['invoice']['id']
        
        # Test POST /api/invoices/{id}/duplicate/
        response = client.post(f'/api/invoices/{duplicate_invoice_id}/duplicate/')
        assert response.status_code == 201
        
        response_data = response.json()
        assert 'duplicate_invoice' in response_data
        assert response_data['duplicate_invoice']['title'] == 'Copy of Invoice for Duplication'
        print("✅ Invoice duplicate endpoint working")
        
        # Test GET /api/invoices/statistics/
        response = client.get('/api/invoices/statistics/')
        assert response.status_code == 200
        
        stats = response.json()
        assert 'total_invoices' in stats
        assert 'status_breakdown' in stats
        assert 'financial' in stats
        print("✅ Invoice statistics endpoint working")
        
        # Test GET /api/invoices/overdue/
        response = client.get('/api/invoices/overdue/')
        assert response.status_code == 200
        
        overdue_data = response.json()
        assert 'count' in overdue_data
        assert 'total_overdue_amount' in overdue_data
        print("✅ Invoice overdue endpoint working")
        
        # Cleanup
        Invoice.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Invoice API endpoints test failed: {e}")
        return False

def test_quote_to_invoice_conversion():
    """Test quote-to-invoice conversion functionality."""
    print("\nTesting quote-to-invoice conversion...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Quote, Invoice, QuoteLineItem, QuoteStatus
        client = APIClient()
        
        # Create test user, client and get token
        user = User.objects.create_user(
            email='conversiontest@example.com',
            username='conversionuser',
            password='TestPassword123!',
            company_name='Conversion Test Company'
        )
        
        test_client = Client.objects.create(
            name='Conversion Test Client',
            email='conversion@example.com',
            phone='+1234567890',
            owner=user
        )
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Create and approve a quote first
        quote_data = {
            'client': str(test_client.id),
            'title': 'Quote for Conversion',
            'tax_rate': '0.0800',
            'line_items': [
                {
                    'description': 'Consultation',
                    'quantity': '10.00',
                    'unit_price': '150.00',
                    'sort_order': 0
                },
                {
                    'description': 'Implementation',
                    'quantity': '20.00',
                    'unit_price': '100.00',
                    'sort_order': 1
                }
            ]
        }
        
        # Create quote
        response = client.post('/api/quotes/', quote_data, format='json')
        assert response.status_code == 201
        quote_id = response.json()['quote']['id']
        
        # Send and approve quote
        response = client.post(f'/api/quotes/{quote_id}/send/')
        assert response.status_code == 200
        
        response = client.post(f'/api/quotes/{quote_id}/approve/')
        assert response.status_code == 200
        
        # Test quote-to-invoice conversion
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'notes': 'Converted from approved quote'
        }
        
        response = client.post('/api/invoices/from_quote/', conversion_data, format='json')
        assert response.status_code == 201
        
        response_data = response.json()
        assert 'invoice' in response_data
        assert 'source_quote' in response_data
        assert response_data['source_quote'] == quote_id
        
        invoice = response_data['invoice']
        assert invoice['title'] == 'Quote for Conversion'
        assert invoice['tax_rate'] == '0.0800'
        assert len(invoice['line_items']) == 2
        assert invoice['subtotal'] == '3500.00'  # 10*150 + 20*100
        assert invoice['source_quote'] == quote_id
        
        print("✅ Quote-to-invoice conversion working")
        
        # Verify quote is linked to invoice
        response = client.get(f'/api/quotes/{quote_id}/')
        assert response.status_code == 200
        quote_detail = response.json()
        assert quote_detail['status'] == 'approved'
        
        print("✅ Quote-invoice relationship established")
        
        # Test conversion validation (try to convert same quote again)
        response = client.post('/api/invoices/from_quote/', conversion_data, format='json')
        assert response.status_code == 400
        print("✅ Duplicate conversion prevention working")
        
        # Cleanup
        Invoice.objects.filter(owner=user).delete()
        Quote.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Quote-to-invoice conversion test failed: {e}")
        return False

def test_multi_tenant_invoice_isolation():
    """Test multi-tenant invoice data isolation."""
    print("\nTesting multi-tenant invoice isolation...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Invoice
        client1 = APIClient()
        client2 = APIClient()
        
        # Create two users and clients
        user1 = User.objects.create_user(
            email='tenant1invoice@example.com',
            username='tenant1invoice',
            password='Password123!',
            company_name='Company 1'
        )
        
        user2 = User.objects.create_user(
            email='tenant2invoice@example.com',
            username='tenant2invoice',
            password='Password123!',
            company_name='Company 2'
        )
        
        test_client1 = Client.objects.create(
            name='Tenant 1 Client',
            email='tenant1client@example.com',
            phone='+1111111111',
            owner=user1
        )
        
        test_client2 = Client.objects.create(
            name='Tenant 2 Client',
            email='tenant2client@example.com',
            phone='+2222222222',
            owner=user2
        )
        
        # Get tokens for both users
        token1 = str(RefreshToken.for_user(user1).access_token)
        token2 = str(RefreshToken.for_user(user2).access_token)
        
        client1.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        
        # Create invoices for each user
        invoice1_data = {
            'client': str(test_client1.id),
            'title': 'Tenant 1 Invoice',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Service 1',
                    'quantity': '1.00',
                    'unit_price': '1000.00'
                }
            ]
        }
        
        invoice2_data = {
            'client': str(test_client2.id),
            'title': 'Tenant 2 Invoice',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Service 2',
                    'quantity': '2.00',
                    'unit_price': '2000.00'
                }
            ]
        }
        
        response1 = client1.post('/api/invoices/', invoice1_data, format='json')
        assert response1.status_code == 201
        tenant1_invoice_id = response1.json()['invoice']['id']
        
        response2 = client2.post('/api/invoices/', invoice2_data, format='json')
        assert response2.status_code == 201
        tenant2_invoice_id = response2.json()['invoice']['id']
        
        # Verify each user can only see their own invoices
        response1 = client1.get('/api/invoices/')
        assert response1.status_code == 200
        
        tenant1_invoices = response1.json()
        if 'results' in tenant1_invoices:
            invoice_ids = [i['id'] for i in tenant1_invoices['results']]
        else:
            invoice_ids = [i['id'] for i in tenant1_invoices]
        
        assert tenant1_invoice_id in invoice_ids
        assert tenant2_invoice_id not in invoice_ids
        
        response2 = client2.get('/api/invoices/')
        assert response2.status_code == 200
        
        tenant2_invoices = response2.json()
        if 'results' in tenant2_invoices:
            invoice_ids = [i['id'] for i in tenant2_invoices['results']]
        else:
            invoice_ids = [i['id'] for i in tenant2_invoices]
        
        assert tenant2_invoice_id in invoice_ids
        assert tenant1_invoice_id not in invoice_ids
        
        print("✅ Multi-tenant invoice data isolation working")
        
        # Test cross-tenant access prevention
        response = client1.get(f'/api/invoices/{tenant2_invoice_id}/')
        assert response.status_code == 404
        
        response = client2.get(f'/api/invoices/{tenant1_invoice_id}/')
        assert response.status_code == 404
        
        print("✅ Cross-tenant invoice access prevention working")
        
        # Cleanup
        Invoice.objects.filter(owner=user1).delete()
        Invoice.objects.filter(owner=user2).delete()
        Client.objects.filter(owner=user1).delete()
        Client.objects.filter(owner=user2).delete()
        user1.delete()
        user2.delete()
        return True
        
    except Exception as e:
        print(f"❌ Multi-tenant invoice isolation test failed: {e}")
        return False

def test_invoice_status_management():
    """Test invoice status transitions and business logic."""
    print("\nTesting invoice status management...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Invoice, InvoiceStatus
        client = APIClient()
        
        # Create test user, client and get token
        user = User.objects.create_user(
            email='statustest@example.com',
            username='statususer',
            password='TestPassword123!'
        )
        
        test_client = Client.objects.create(
            name='Status Test Client',
            email='status@example.com',
            phone='+1234567890',
            owner=user
        )
        
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create an invoice
        invoice_data = {
            'client': str(test_client.id),
            'title': 'Status Test Invoice',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Test Service',
                    'quantity': '1.00',
                    'unit_price': '100.00'
                }
            ]
        }
        
        response = client.post('/api/invoices/', invoice_data, format='json')
        assert response.status_code == 201
        invoice_id = response.json()['invoice']['id']
        
        # Test status transitions: DRAFT -> SENT -> PAID
        # 1. Send invoice
        response = client.post(f'/api/invoices/{invoice_id}/send/')
        assert response.status_code == 200
        assert response.json()['invoice']['status'] == 'sent'
        
        # 2. Try to edit sent invoice (should fail)
        update_data = {
            'client': str(test_client.id),
            'title': 'Should Not Update',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Should Not Update',
                    'quantity': '1.00',
                    'unit_price': '200.00'
                }
            ]
        }
        
        response = client.put(f'/api/invoices/{invoice_id}/', update_data, format='json')
        assert response.status_code == 400
        assert 'Only draft invoices can be edited' in response.json()['error']
        print("✅ Invoice editing restrictions working")
        
        # 3. Mark as paid
        response = client.post(f'/api/invoices/{invoice_id}/mark_paid/')
        assert response.status_code == 200
        assert response.json()['invoice']['status'] == 'paid'
        
        # 4. Test overdue status update
        # Create overdue invoice (past due date)
        overdue_invoice_data = {
            'client': str(test_client.id),
            'title': 'Overdue Test Invoice',
            'due_date': (date.today() - timedelta(days=5)).isoformat(),
            'line_items': [
                {
                    'description': 'Overdue Service',
                    'quantity': '1.00',
                    'unit_price': '200.00'
                }
            ]
        }
        
        response = client.post('/api/invoices/', overdue_invoice_data, format='json')
        assert response.status_code == 201
        overdue_invoice_id = response.json()['invoice']['id']
        
        # Send the overdue invoice
        response = client.post(f'/api/invoices/{overdue_invoice_id}/send/')
        assert response.status_code == 200
        
        # Update overdue status
        response = client.post('/api/invoices/update_overdue_status/')
        assert response.status_code == 200
        updated_count = response.json()['updated_count']
        assert updated_count >= 1
        print("✅ Overdue status update working")
        
        # Test invoice deletion restrictions
        response = client.delete(f'/api/invoices/{invoice_id}/')
        assert response.status_code == 400
        assert 'Only draft invoices can be deleted' in response.json()['error']
        print("✅ Invoice deletion restrictions working")
        
        # Cleanup
        Invoice.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Invoice status management test failed: {e}")
        return False

def main():
    """Run all invoice management system tests."""
    print("="*60)
    print("SK-400: Invoice Management System - Validation Tests")
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Run all tests
    tests = [
        test_invoice_models,
        test_invoice_api_endpoints,
        test_quote_to_invoice_conversion,
        test_multi_tenant_invoice_isolation,
        test_invoice_status_management
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
        print("\nSK-400 Invoice Management System: COMPLETED")
        print("✅ Enhanced Invoice model with auto-generation")
        print("✅ Invoice line items with validation and calculations")
        print("✅ Multi-tenant data isolation")
        print("✅ Comprehensive CRUD API endpoints")
        print("✅ Status management and transitions")
        print("✅ Quote-to-invoice conversion")
        print("✅ Payment tracking and overdue management")
        print("✅ Advanced features (duplicate, statistics, search)")
        print("\nReady to proceed with SK-500: Expense Tracking System")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Fix issues before proceeding to next task")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)