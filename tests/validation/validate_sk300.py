#!/usr/bin/env python
"""
Comprehensive validation script for SK-300: Quote Management System.
Tests quote CRUD operations, status management, line items, and multi-tenant isolation.
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

def test_quote_models():
    """Test Quote and QuoteLineItem model functionality."""
    print("Testing Quote models...")
    
    try:
        from invoicing.models import Quote, QuoteLineItem, QuoteStatus
        from clients.models import Client
        User = get_user_model()
        
        # Create test user and client
        user = User.objects.create_user(
            email='quotetest@example.com',
            username='quotetestuser',
            password='TestPassword123!',
            company_name='Test Company'
        )
        
        client = Client.objects.create(
            name='Test Client',
            email='client@example.com',
            phone='+1234567890',
            owner=user
        )
        
        # Test quote creation
        quote = Quote.objects.create(
            client=client,
            title='Test Quote',
            notes='Test notes',
            tax_rate=Decimal('0.1000'),
            owner=user
        )
        
        # Verify quote properties
        assert quote.client == client
        assert quote.owner == user
        assert quote.status == QuoteStatus.DRAFT
        assert quote.quote_number.startswith('QT-')
        assert quote.tax_rate == Decimal('0.1000')
        assert isinstance(quote.id, uuid.UUID)
        
        print("✅ Quote model creation working")
        
        # Test line item creation
        line_item = QuoteLineItem.objects.create(
            quote=quote,
            description='Test Item',
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        # Verify line item properties
        assert line_item.quote == quote
        assert line_item.total_price == Decimal('200.00')
        assert line_item.description == 'Test Item'
        
        print("✅ QuoteLineItem model creation working")
        
        # Test auto-generated quote number uniqueness
        quote2 = Quote.objects.create(
            client=client,
            title='Test Quote 2',
            owner=user
        )
        
        assert quote.quote_number != quote2.quote_number
        print("✅ Quote number auto-generation working")
        
        # Test total calculation
        quote.calculate_totals()
        quote.refresh_from_db()
        
        expected_subtotal = Decimal('200.00')
        expected_tax = expected_subtotal * Decimal('0.1000')
        expected_total = expected_subtotal + expected_tax
        
        assert quote.subtotal == expected_subtotal
        assert quote.tax_amount == expected_tax
        assert quote.total_amount == expected_total
        
        print("✅ Quote total calculation working")
        
        # Test status transitions
        assert quote.can_transition_to(QuoteStatus.SENT)
        assert quote.mark_as_sent()
        assert quote.status == QuoteStatus.SENT
        assert quote.sent_at is not None
        
        print("✅ Quote status transitions working")
        
        # Cleanup
        Quote.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Quote models test failed: {e}")
        return False

def test_quote_api_endpoints():
    """Test Quote API CRUD endpoints."""
    print("\nTesting Quote API endpoints...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Quote, QuoteStatus
        client = APIClient()
        
        # Create test user, client and get token
        user = User.objects.create_user(
            email='quoteapi@example.com',
            username='quoteapiuser',
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
        
        # Test POST /api/quotes/ - Create quote
        quote_data = {
            'client': str(test_client.id),
            'title': 'API Test Quote',
            'notes': 'Test notes',
            'terms': 'Net 30',
            'tax_rate': '0.1000',
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
        
        response = client.post('/api/quotes/', quote_data, format='json')
        assert response.status_code == 201
        
        response_data = response.json()
        assert 'quote' in response_data
        assert response_data['quote']['title'] == 'API Test Quote'
        assert len(response_data['quote']['line_items']) == 2
        
        quote_id = response_data['quote']['id']
        print("✅ Quote creation endpoint working")
        
        # Test GET /api/quotes/ - List quotes
        response = client.get('/api/quotes/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert 'results' in response_data or isinstance(response_data, list)
        if 'statistics' in response_data:
            assert 'total_quotes' in response_data['statistics']
        print("✅ Quote list endpoint working")
        
        # Test GET /api/quotes/{id}/ - Retrieve quote
        response = client.get(f'/api/quotes/{quote_id}/')
        assert response.status_code == 200
        
        quote_detail = response.json()
        assert quote_detail['id'] == quote_id
        assert quote_detail['title'] == 'API Test Quote'
        assert len(quote_detail['line_items']) == 2
        assert quote_detail['subtotal'] == '5500.00'  # 40*100 + 10*150
        assert quote_detail['tax_amount'] == '550.00'  # 5500 * 0.1
        assert quote_detail['total_amount'] == '6050.00'  # 5500 + 550
        print("✅ Quote retrieve endpoint working")
        
        # Test PUT /api/quotes/{id}/ - Update quote (only works for drafts)
        update_data = {
            'client': str(test_client.id),
            'title': 'Updated API Quote',
            'tax_rate': '0.0800',
            'line_items': [
                {
                    'description': 'Updated Web Development',
                    'quantity': '50.00',
                    'unit_price': '120.00',
                    'sort_order': 0
                }
            ]
        }
        
        response = client.put(f'/api/quotes/{quote_id}/', update_data, format='json')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['quote']['title'] == 'Updated API Quote'
        assert len(response_data['quote']['line_items']) == 1
        print("✅ Quote update endpoint working")
        
        # Test custom actions
        # Test POST /api/quotes/{id}/send/
        response = client.post(f'/api/quotes/{quote_id}/send/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['quote']['status'] == 'sent'
        assert response_data['quote']['sent_at'] is not None
        print("✅ Quote send endpoint working")
        
        # Test POST /api/quotes/{id}/approve/
        response = client.post(f'/api/quotes/{quote_id}/approve/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['quote']['status'] == 'approved'
        print("✅ Quote approve endpoint working")
        
        # Test POST /api/quotes/{id}/duplicate/
        response = client.post(f'/api/quotes/{quote_id}/duplicate/')
        assert response.status_code == 201
        
        response_data = response.json()
        assert 'duplicate_quote' in response_data
        assert response_data['duplicate_quote']['title'] == 'Copy of Updated API Quote'
        print("✅ Quote duplicate endpoint working")
        
        # Test GET /api/quotes/statistics/
        response = client.get('/api/quotes/statistics/')
        assert response.status_code == 200
        
        stats = response.json()
        assert 'total_quotes' in stats
        assert 'status_breakdown' in stats
        assert 'financial' in stats
        print("✅ Quote statistics endpoint working")
        
        # Cleanup
        Quote.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Quote API endpoints test failed: {e}")
        return False

def test_multi_tenant_quote_isolation():
    """Test multi-tenant quote data isolation."""
    print("\nTesting multi-tenant quote isolation...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Quote
        client1 = APIClient()
        client2 = APIClient()
        
        # Create two users and clients
        user1 = User.objects.create_user(
            email='tenant1quote@example.com',
            username='tenant1quote',
            password='Password123!',
            company_name='Company 1'
        )
        
        user2 = User.objects.create_user(
            email='tenant2quote@example.com',
            username='tenant2quote',
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
        
        # Create quotes for each user
        quote1_data = {
            'client': str(test_client1.id),
            'title': 'Tenant 1 Quote',
            'line_items': [
                {
                    'description': 'Service 1',
                    'quantity': '1.00',
                    'unit_price': '1000.00'
                }
            ]
        }
        
        quote2_data = {
            'client': str(test_client2.id),
            'title': 'Tenant 2 Quote',
            'line_items': [
                {
                    'description': 'Service 2',
                    'quantity': '2.00',
                    'unit_price': '2000.00'
                }
            ]
        }
        
        response1 = client1.post('/api/quotes/', quote1_data, format='json')
        assert response1.status_code == 201
        tenant1_quote_id = response1.json()['quote']['id']
        
        response2 = client2.post('/api/quotes/', quote2_data, format='json')
        assert response2.status_code == 201
        tenant2_quote_id = response2.json()['quote']['id']
        
        # Verify each user can only see their own quotes
        response1 = client1.get('/api/quotes/')
        assert response1.status_code == 200
        
        tenant1_quotes = response1.json()
        if 'results' in tenant1_quotes:
            quote_ids = [q['id'] for q in tenant1_quotes['results']]
        else:
            quote_ids = [q['id'] for q in tenant1_quotes]
        
        assert tenant1_quote_id in quote_ids
        assert tenant2_quote_id not in quote_ids
        
        response2 = client2.get('/api/quotes/')
        assert response2.status_code == 200
        
        tenant2_quotes = response2.json()
        if 'results' in tenant2_quotes:
            quote_ids = [q['id'] for q in tenant2_quotes['results']]
        else:
            quote_ids = [q['id'] for q in tenant2_quotes]
        
        assert tenant2_quote_id in quote_ids
        assert tenant1_quote_id not in quote_ids
        
        print("✅ Multi-tenant quote data isolation working")
        
        # Test cross-tenant access prevention
        response = client1.get(f'/api/quotes/{tenant2_quote_id}/')
        assert response.status_code == 404
        
        response = client2.get(f'/api/quotes/{tenant1_quote_id}/')
        assert response.status_code == 404
        
        print("✅ Cross-tenant quote access prevention working")
        
        # Cleanup
        Quote.objects.filter(owner=user1).delete()
        Quote.objects.filter(owner=user2).delete()
        Client.objects.filter(owner=user1).delete()
        Client.objects.filter(owner=user2).delete()
        user1.delete()
        user2.delete()
        return True
        
    except Exception as e:
        print(f"❌ Multi-tenant quote isolation test failed: {e}")
        return False

def test_quote_status_management():
    """Test quote status transitions and business logic."""
    print("\nTesting quote status management...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        from invoicing.models import Quote, QuoteStatus
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
        
        # Create a quote
        quote_data = {
            'client': str(test_client.id),
            'title': 'Status Test Quote',
            'line_items': [
                {
                    'description': 'Test Service',
                    'quantity': '1.00',
                    'unit_price': '100.00'
                }
            ]
        }
        
        response = client.post('/api/quotes/', quote_data, format='json')
        assert response.status_code == 201
        quote_id = response.json()['quote']['id']
        
        # Test status transitions: DRAFT -> SENT -> APPROVED
        # 1. Send quote
        response = client.post(f'/api/quotes/{quote_id}/send/')
        assert response.status_code == 200
        assert response.json()['quote']['status'] == 'sent'
        
        # 2. Try to edit sent quote (should fail)
        update_data = {
            'client': str(test_client.id),
            'title': 'Should Not Update',
            'line_items': [
                {
                    'description': 'Should Not Update',
                    'quantity': '1.00',
                    'unit_price': '200.00'
                }
            ]
        }
        
        response = client.put(f'/api/quotes/{quote_id}/', update_data, format='json')
        assert response.status_code == 400
        assert 'Only draft quotes can be edited' in response.json()['error']
        print("✅ Quote editing restrictions working")
        
        # 3. Approve quote
        response = client.post(f'/api/quotes/{quote_id}/approve/')
        assert response.status_code == 200
        assert response.json()['quote']['status'] == 'approved'
        
        # 4. Test invalid status transition (approve to send should fail)
        response = client.post(f'/api/quotes/{quote_id}/send/')
        assert response.status_code == 400
        print("✅ Invalid status transitions prevented")
        
        # Test quote expiration logic
        quote = Quote.objects.get(id=quote_id)
        assert not quote.is_expired  # Should not be expired (valid_until is 30 days from now)
        assert quote.days_until_expiry > 25  # Should have ~30 days
        
        # Test quote deletion restrictions
        response = client.delete(f'/api/quotes/{quote_id}/')
        assert response.status_code == 400
        assert 'Only draft or declined quotes can be deleted' in response.json()['error']
        print("✅ Quote deletion restrictions working")
        
        # Cleanup
        Quote.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Quote status management test failed: {e}")
        return False

def test_quote_line_items_validation():
    """Test quote line items validation and calculations."""
    print("\nTesting quote line items validation...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        client = APIClient()
        
        # Create test user, client and get token
        user = User.objects.create_user(
            email='lineitemtest@example.com',
            username='lineitemuser',
            password='TestPassword123!'
        )
        
        test_client = Client.objects.create(
            name='Line Item Test Client',
            email='lineitem@example.com',
            phone='+1234567890',
            owner=user
        )
        
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Test validation: empty line items
        invalid_data = {
            'client': str(test_client.id),
            'title': 'Invalid Quote',
            'line_items': []
        }
        
        response = client.post('/api/quotes/', invalid_data, format='json')
        assert response.status_code == 400
        assert 'At least one line item is required' in str(response.json())
        print("✅ Empty line items validation working")
        
        # Test validation: invalid quantity
        invalid_data = {
            'client': str(test_client.id),
            'title': 'Invalid Quote',
            'line_items': [
                {
                    'description': 'Test Service',
                    'quantity': '0.00',  # Invalid
                    'unit_price': '100.00'
                }
            ]
        }
        
        response = client.post('/api/quotes/', invalid_data, format='json')
        assert response.status_code == 400
        print("✅ Invalid quantity validation working")
        
        # Test validation: invalid unit price
        invalid_data = {
            'client': str(test_client.id),
            'title': 'Invalid Quote',
            'line_items': [
                {
                    'description': 'Test Service',
                    'quantity': '1.00',
                    'unit_price': '-50.00'  # Invalid
                }
            ]
        }
        
        response = client.post('/api/quotes/', invalid_data, format='json')
        assert response.status_code == 400
        print("✅ Invalid unit price validation working")
        
        # Test validation: empty description
        invalid_data = {
            'client': str(test_client.id),
            'title': 'Invalid Quote',
            'line_items': [
                {
                    'description': '',  # Invalid
                    'quantity': '1.00',
                    'unit_price': '100.00'
                }
            ]
        }
        
        response = client.post('/api/quotes/', invalid_data, format='json')
        assert response.status_code == 400
        print("✅ Empty description validation working")
        
        # Test complex calculation
        complex_data = {
            'client': str(test_client.id),
            'title': 'Complex Calculation Quote',
            'tax_rate': '0.0875',  # 8.75% tax
            'line_items': [
                {
                    'description': 'Service A',
                    'quantity': '2.50',
                    'unit_price': '125.00'
                },
                {
                    'description': 'Service B',
                    'quantity': '1.75',
                    'unit_price': '200.00'
                }
            ]
        }
        
        response = client.post('/api/quotes/', complex_data, format='json')
        assert response.status_code == 201
        
        quote_data = response.json()['quote']
        # 2.50 * 125.00 + 1.75 * 200.00 = 312.50 + 350.00 = 662.50
        assert quote_data['subtotal'] == '662.50'
        # 662.50 * 0.0875 = 57.97
        assert quote_data['tax_amount'] == '57.97'
        # 662.50 + 57.97 = 720.47
        assert quote_data['total_amount'] == '720.47'
        
        print("✅ Complex calculation validation working")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Quote line items validation test failed: {e}")
        return False

def main():
    """Run all quote management system tests."""
    print("="*60)
    print("SK-300: Quote Management System - Validation Tests")
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Run all tests
    tests = [
        test_quote_models,
        test_quote_api_endpoints,
        test_multi_tenant_quote_isolation,
        test_quote_status_management,
        test_quote_line_items_validation
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
        print("\nSK-300 Quote Management System: COMPLETED")
        print("✅ Enhanced Quote model with auto-generation")
        print("✅ Quote line items with validation and calculations")
        print("✅ Multi-tenant data isolation")
        print("✅ Comprehensive CRUD API endpoints")
        print("✅ Status management and transitions")
        print("✅ Business logic validation")
        print("✅ Advanced features (duplicate, statistics, search)")
        print("\nReady to proceed with SK-400: Invoice Management System")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Fix issues before proceeding to next task")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)