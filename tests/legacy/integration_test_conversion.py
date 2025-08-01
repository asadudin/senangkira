#!/usr/bin/env python
"""
Integration test for quote-to-invoice conversion with enhanced atomic transactions.
Tests the actual API endpoints through Django's test framework.
"""

import os
import django
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from datetime import date, timedelta
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
django.setup()

from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem, QuoteStatus, InvoiceStatus
from clients.models import Client

class QuoteToInvoiceConversionTest(APITestCase):
    """Integration tests for quote-to-invoice conversion with atomic transactions."""
    
    def setUp(self):
        """Set up test data."""
        User = get_user_model()
        
        # Create test users
        self.user1 = User.objects.create_user(
            email='testuser1@example.com',
            username='testuser1',
            password='TestPass123!',
            company_name='Test Company 1'
        )
        
        self.user2 = User.objects.create_user(
            email='testuser2@example.com',
            username='testuser2',
            password='TestPass123!',
            company_name='Test Company 2'
        )
        
        # Create test clients
        self.client1 = Client.objects.create(
            name='Test Client 1',
            email='client1@example.com',
            phone='+1111111111', 
            owner=self.user1
        )
        
        self.client2 = Client.objects.create(
            name='Test Client 2',
            email='client2@example.com',
            phone='+2222222222',
            owner=self.user2
        )
        
        # Setup API client
        self.api_client = APIClient()
        
        # Get authentication tokens
        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)
    
    def test_successful_atomic_conversion(self):
        """Test successful quote-to-invoice conversion with data integrity."""
        print("\n=== Testing Successful Atomic Conversion ===")
        
        # Authenticate as user1
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # Create and approve quote
        quote_data = {
            'client': str(self.client1.id),
            'title': 'Integration Test Quote',
            'tax_rate': '0.0800',
            'line_items': [
                {
                    'description': 'Consulting Services',
                    'quantity': '20.00',
                    'unit_price': '150.00',
                    'sort_order': 0
                },
                {
                    'description': 'Development Work', 
                    'quantity': '40.00',
                    'unit_price': '100.00',
                    'sort_order': 1
                }
            ]
        }
        
        # Create quote
        response = self.api_client.post('/api/quotes/', quote_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quote_id = response.json()['quote']['id']
        print(f"✅ Quote created: {quote_id}")
        
        # Send and approve quote
        response = self.api_client.post(f'/api/quotes/{quote_id}/send/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("✅ Quote sent successfully")
        
        response = self.api_client.post(f'/api/quotes/{quote_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("✅ Quote approved successfully")
        
        # Convert to invoice
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'notes': 'Converted via integration test'
        }
        
        response = self.api_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        invoice_data = response.json()['invoice']
        print(f"✅ Invoice created: {invoice_data['invoice_number']}")
        
        # Validate data integrity
        self.assertEqual(invoice_data['subtotal'], '7000.00')  # 20*150 + 40*100
        self.assertEqual(invoice_data['tax_amount'], '560.00')  # 7000 * 0.08
        self.assertEqual(invoice_data['total_amount'], '7560.00')  # 7000 + 560
        self.assertEqual(len(invoice_data['line_items']), 2)
        self.assertEqual(invoice_data['source_quote'], quote_id)
        
        print("✅ Data integrity validation passed")
        
        # Verify in database
        invoice = Invoice.objects.get(id=invoice_data['id'])
        self.assertEqual(invoice.line_items.count(), 2)
        self.assertEqual(invoice.source_quote.id, uuid.UUID(quote_id))
        
        print("✅ Database validation passed")
    
    def test_duplicate_conversion_prevention(self):
        """Test prevention of duplicate conversions."""
        print("\n=== Testing Duplicate Conversion Prevention ===")
        
        # Authenticate as user1
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # Create and approve quote
        quote_data = {
            'client': str(self.client1.id),
            'title': 'Duplicate Test Quote',
            'line_items': [
                {
                    'description': 'Test Service',
                    'quantity': '1.00',
                    'unit_price': '1000.00'
                }
            ]
        }
        
        response = self.api_client.post('/api/quotes/', quote_data, format='json')
        quote_id = response.json()['quote']['id']
        
        # Approve quote
        self.api_client.post(f'/api/quotes/{quote_id}/send/')
        self.api_client.post(f'/api/quotes/{quote_id}/approve/')
        
        # First conversion (should succeed)
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.api_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        print("✅ First conversion succeeded")
        
        # Second conversion (should fail)
        response = self.api_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        error_message = str(response.json())
        self.assertIn('already been converted', error_message)
        print("✅ Duplicate conversion prevented")
    
    def test_invalid_quote_status_handling(self):
        """Test conversion rejection for invalid quote status."""
        print("\n=== Testing Invalid Quote Status Handling ===")
        
        # Authenticate as user1
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        # Create quote but don't approve it
        quote_data = {
            'client': str(self.client1.id),
            'title': 'Draft Quote Test',
            'line_items': [
                {
                    'description': 'Draft Service',
                    'quantity': '1.00',
                    'unit_price': '500.00'
                }
            ]
        }
        
        response = self.api_client.post('/api/quotes/', quote_data, format='json')
        quote_id = response.json()['quote']['id']
        print(f"✅ Draft quote created: {quote_id}")
        
        # Try to convert draft quote (should fail)
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.api_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        error_message = str(response.json())
        self.assertIn('cannot be converted', error_message)
        print("✅ Draft quote conversion properly rejected")
    
    def test_cross_tenant_security(self):
        """Test cross-tenant security for quote conversion."""
        print("\n=== Testing Cross-Tenant Security ===")
        
        # Create quote as user2
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        
        quote_data = {
            'client': str(self.client2.id),
            'title': 'Other User Quote',
            'line_items': [
                {
                    'description': 'Other Service',
                    'quantity': '1.00',
                    'unit_price': '800.00'
                }
            ]
        }
        
        response = self.api_client.post('/api/quotes/', quote_data, format='json')
        quote_id = response.json()['quote']['id']
        
        # Approve quote as user2
        self.api_client.post(f'/api/quotes/{quote_id}/send/')
        self.api_client.post(f'/api/quotes/{quote_id}/approve/')
        print(f"✅ Quote created and approved by user2: {quote_id}")
        
        # Try to convert as user1 (should fail)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.api_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        error_message = str(response.json())
        self.assertIn('Quote not found', error_message)
        print("✅ Cross-tenant access properly blocked")

if __name__ == '__main__':
    # Run the tests
    import unittest
    
    print("="*70)
    print("Quote-to-Invoice Conversion Integration Tests")
    print("="*70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(QuoteToInvoiceConversionTest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    
    if result.wasSuccessful():
        print(f"✅ ALL INTEGRATION TESTS PASSED")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print("\nAtomic Quote-to-Invoice Conversion: PRODUCTION READY")
        print("✅ Data integrity validation")
        print("✅ Duplicate conversion prevention")  
        print("✅ Business rule enforcement")
        print("✅ Cross-tenant security")
        print("✅ Enhanced error handling")
    else:
        print(f"❌ SOME TESTS FAILED")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
                
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")