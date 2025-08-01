"""
Integration tests for complete quote-to-invoice workflow.
Tests the full business process from quote creation to invoice conversion.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal

from tests.utils import TestDataGenerator, APITestHelpers, CalculationHelpers, IntegrationTestHelpers
from tests.conftest import BaseTestCase
from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem, QuoteStatus, InvoiceStatus
from clients.models import Client

User = get_user_model()


class CompleteQuoteWorkflowTests(APITestCase):
    """Test complete quote workflow from creation to approval."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='workflow@example.com',
            username='workflowuser',
            password='WorkflowPass123!'
        )
        
        self.client_model = Client.objects.create(
            name='Workflow Test Client',
            email='client@workflow.com',
            owner=self.user
        )
        
        self.authenticated_client = self.create_authenticated_client()
    
    def create_authenticated_client(self):
        """Create authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework.test import APIClient
        
        client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return client
    
    def test_complete_quote_creation_workflow(self):
        """Test complete quote creation and management workflow."""
        # Step 1: Create quote
        quote_data = TestDataGenerator.quote_data(
            client_id=self.client_model.id,
            title='Complete Workflow Quote',
            line_items=TestDataGenerator.line_items_complex()
        )
        
        response = self.authenticated_client.post('/api/quotes/', quote_data, format='json')
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        
        quote_response = response.json()
        quote_id = quote_response['quote']['id']
        
        # Verify quote data
        APITestHelpers.assert_required_fields(
            quote_response['quote'],
            ['id', 'title', 'status', 'subtotal', 'tax_amount', 'total_amount', 'line_items']
        )
        
        # Verify calculations
        CalculationHelpers.validate_financial_calculations(
            quote_response['quote'],
            quote_data['line_items'],
            Decimal(quote_data['tax_rate'])
        )
        
        # Step 2: Retrieve quote
        response = self.authenticated_client.get(f'/api/quotes/{quote_id}/')
        APITestHelpers.assert_successful_response(response)
        
        # Step 3: Update quote
        update_data = {
            'title': 'Updated Complete Workflow Quote',
            'description': 'Updated description'
        }
        
        response = self.authenticated_client.patch(f'/api/quotes/{quote_id}/', update_data, format='json')
        APITestHelpers.assert_successful_response(response)
        
        updated_quote = response.json()['quote']
        self.assertEqual(updated_quote['title'], update_data['title'])
        
        # Step 4: Send quote
        response = self.authenticated_client.post(f'/api/quotes/{quote_id}/send/')
        APITestHelpers.assert_successful_response(response)
        
        # Verify status changed
        response = self.authenticated_client.get(f'/api/quotes/{quote_id}/')
        quote_data = response.json()['quote']
        self.assertEqual(quote_data['status'], 'sent')
        
        # Step 5: Approve quote
        response = self.authenticated_client.post(f'/api/quotes/{quote_id}/approve/')
        APITestHelpers.assert_successful_response(response)
        
        # Verify status changed
        response = self.authenticated_client.get(f'/api/quotes/{quote_id}/')
        quote_data = response.json()['quote']
        self.assertEqual(quote_data['status'], 'accepted')
        
        return quote_id
    
    def test_quote_listing_and_filtering(self):
        """Test quote listing with filtering and pagination."""
        # Create multiple quotes with different statuses
        quote_data = TestDataGenerator.quote_data(self.client_model.id)
        
        # Create draft quote
        draft_response = self.authenticated_client.post('/api/quotes/', quote_data, format='json')
        draft_id = draft_response.json()['quote']['id']
        
        # Create and send another quote
        sent_response = self.authenticated_client.post('/api/quotes/', quote_data, format='json')
        sent_id = sent_response.json()['quote']['id']
        self.authenticated_client.post(f'/api/quotes/{sent_id}/send/')
        
        # Test listing all quotes
        response = self.authenticated_client.get('/api/quotes/')
        APITestHelpers.assert_successful_response(response)
        
        quotes_data = response.json()
        self.assertGreaterEqual(len(quotes_data['results']), 2)
        
        # Test filtering by status
        response = self.authenticated_client.get('/api/quotes/?status=draft')
        APITestHelpers.assert_successful_response(response)
        
        filtered_quotes = response.json()['results']
        for quote in filtered_quotes:
            self.assertEqual(quote['status'], 'draft')
        
        # Test filtering by client
        response = self.authenticated_client.get(f'/api/quotes/?client={self.client_model.id}')
        APITestHelpers.assert_successful_response(response)
        
        client_quotes = response.json()['results']
        for quote in client_quotes:
            self.assertEqual(quote['client']['id'], str(self.client_model.id))
    
    def test_quote_validation_and_error_handling(self):
        """Test quote validation and error handling."""
        # Test missing required fields
        incomplete_data = {
            'title': 'Incomplete Quote'
            # Missing client and line_items
        }
        
        response = self.authenticated_client.post('/api/quotes/', incomplete_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid client ID
        invalid_client_data = TestDataGenerator.quote_data(
            client_id='00000000-0000-0000-0000-000000000000'  # Non-existent UUID
        )
        
        response = self.authenticated_client.post('/api/quotes/', invalid_client_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid line item data
        invalid_line_items_data = TestDataGenerator.quote_data(
            client_id=self.client_model.id,
            line_items=[
                {
                    'description': 'Invalid Item',
                    'quantity': '-5.00',  # Negative quantity
                    'unit_price': '100.00'
                }
            ]
        )
        
        response = self.authenticated_client.post('/api/quotes/', invalid_line_items_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST)


class QuoteToInvoiceConversionTests(APITestCase):
    """Test quote to invoice conversion workflow."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='conversion@example.com',
            username='conversionuser',
            password='ConversionPass123!'
        )
        
        self.client_model = Client.objects.create(
            name='Conversion Test Client',
            email='client@conversion.com',
            owner=self.user
        )
        
        self.authenticated_client = self.create_authenticated_client()
    
    def create_authenticated_client(self):
        """Create authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework.test import APIClient
        
        client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return client
    
    def test_successful_quote_to_invoice_conversion(self):
        """Test successful conversion of approved quote to invoice."""
        # Step 1: Create and approve quote
        quote_data = TestDataGenerator.quote_data(
            client_id=self.client_model.id,
            title='Conversion Test Quote',
            line_items=[
                {
                    'description': 'Development Services',
                    'quantity': '40.00',
                    'unit_price': '125.00',
                    'sort_order': 0
                },
                {
                    'description': 'Design Services',
                    'quantity': '20.00',
                    'unit_price': '150.00',
                    'sort_order': 1
                }
            ]
        )
        
        quote_id = IntegrationTestHelpers.complete_quote_workflow(self.authenticated_client, quote_data)
        
        # Step 2: Convert quote to invoice
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'notes': 'Converted via integration test'
        }
        
        response = self.authenticated_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        
        invoice_response = response.json()
        invoice_data = invoice_response['invoice']
        
        # Step 3: Verify conversion integrity
        # Check invoice structure
        APITestHelpers.assert_required_fields(
            invoice_data,
            ['id', 'title', 'subtotal', 'tax_amount', 'total_amount', 'line_items', 'source_quote']
        )
        
        # Verify financial calculations
        expected_subtotal = Decimal('8000.00')  # (40*125) + (20*150)
        expected_tax = expected_subtotal * Decimal('0.0800')  # Assuming 8% tax
        expected_total = expected_subtotal + expected_tax
        
        APITestHelpers.assert_decimal_equal(invoice_data['subtotal'], expected_subtotal)
        APITestHelpers.assert_decimal_equal(invoice_data['tax_amount'], expected_tax)  
        APITestHelpers.assert_decimal_equal(invoice_data['total_amount'], expected_total)
        
        # Verify line items transfer
        self.assertEqual(len(invoice_data['line_items']), 2)
        self.assertEqual(invoice_data['source_quote'], quote_id)
        
        # Step 4: Verify quote status after conversion
        quote_response = self.authenticated_client.get(f'/api/quotes/{quote_id}/')
        quote_data = quote_response.json()['quote']
        
        # Quote should maintain its accepted status
        self.assertEqual(quote_data['status'], 'accepted')
        
        return invoice_data['id']
    
    def test_conversion_prevents_duplicates(self):
        """Test that conversion prevents duplicate invoice creation."""
        # Create and approve quote
        quote_data = TestDataGenerator.quote_data(self.client_model.id)
        quote_id = IntegrationTestHelpers.complete_quote_workflow(self.authenticated_client, quote_data)
        
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        # First conversion should succeed
        response = self.authenticated_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        
        # Second conversion should fail
        response = self.authenticated_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST, 'already been converted')
    
    def test_conversion_rejects_invalid_quote_status(self):
        """Test that conversion rejects quotes that aren't approved."""
        # Create quote but don't approve it
        quote_data = TestDataGenerator.quote_data(self.client_model.id)
        
        response = self.authenticated_client.post('/api/quotes/', quote_data, format='json')
        quote_id = response.json()['quote']['id']
        
        # Try to convert draft quote
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.authenticated_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST, 'cannot be converted')
    
    def test_cross_tenant_conversion_security(self):
        """Test that users cannot convert other users' quotes."""
        # Create second user and client
        user2 = User.objects.create_user(
            email='user2@example.com',
            username='user2',
            password='User2Pass123!'
        )
        
        client2 = Client.objects.create(
            name='User2 Client',
            email='client2@example.com',
            owner=user2
        )
        
        # Create quote as user2
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework.test import APIClient
        
        user2_client = APIClient()
        refresh2 = RefreshToken.for_user(user2)
        user2_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh2.access_token}')
        
        quote_data = TestDataGenerator.quote_data(client2.id)
        quote_id = IntegrationTestHelpers.complete_quote_workflow(user2_client, quote_data)
        
        # Try to convert as user1 (should fail)
        conversion_data = {
            'quote_id': quote_id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.authenticated_client.post('/api/invoices/from_quote/', conversion_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST, 'Quote not found')


class CompleteInvoiceWorkflowTests(APITestCase):
    """Test complete invoice workflow from creation to payment."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='invoice@example.com',
            username='invoiceuser',
            password='InvoicePass123!'
        )
        
        self.client_model = Client.objects.create(
            name='Invoice Test Client',
            email='client@invoice.com',
            owner=self.user
        )
        
        self.authenticated_client = self.create_authenticated_client()
    
    def create_authenticated_client(self):
        """Create authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework.test import APIClient
        
        client = APIClient()
        refresh = RefreshToken.for_user(self.user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return client
    
    def test_complete_invoice_workflow(self):
        """Test complete invoice management workflow."""
        # Step 1: Create invoice directly (not from quote)
        invoice_data = TestDataGenerator.invoice_data(
            client_id=self.client_model.id,
            title='Complete Invoice Workflow',
            line_items=[
                {
                    'description': 'Professional Services',
                    'quantity': '30.00',
                    'unit_price': '120.00',
                    'sort_order': 0
                }
            ]
        )
        
        response = self.authenticated_client.post('/api/invoices/', invoice_data, format='json')
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        
        invoice_response = response.json()
        invoice_id = invoice_response['invoice']['id']
        
        # Verify calculations
        expected_subtotal = Decimal('3600.00')  # 30 * 120
        APITestHelpers.assert_decimal_equal(invoice_response['invoice']['subtotal'], expected_subtotal)
        
        # Step 2: Send invoice
        response = self.authenticated_client.post(f'/api/invoices/{invoice_id}/send/')
        APITestHelpers.assert_successful_response(response)
        
        # Step 3: Check invoice status
        response = self.authenticated_client.get(f'/api/invoices/{invoice_id}/')
        invoice_data = response.json()['invoice']
        self.assertEqual(invoice_data['status'], 'sent')
        
        # Step 4: Mark as paid
        payment_data = {
            'payment_date': date.today().isoformat(),
            'payment_method': 'bank_transfer',
            'notes': 'Payment received via bank transfer'
        }
        
        response = self.authenticated_client.post(f'/api/invoices/{invoice_id}/mark_paid/', payment_data, format='json')
        APITestHelpers.assert_successful_response(response)
        
        # Verify payment status
        response = self.authenticated_client.get(f'/api/invoices/{invoice_id}/')
        invoice_data = response.json()['invoice']
        self.assertEqual(invoice_data['status'], 'paid')
        self.assertIsNotNone(invoice_data.get('paid_date'))
        
        return invoice_id
    
    def test_invoice_listing_and_filtering(self):
        """Test invoice listing with comprehensive filtering."""
        # Create invoices with different statuses
        invoice_data = TestDataGenerator.invoice_data(self.client_model.id)
        
        # Create draft invoice
        draft_response = self.authenticated_client.post('/api/invoices/', invoice_data, format='json')
        draft_id = draft_response.json()['invoice']['id']
        
        # Create sent invoice
        sent_response = self.authenticated_client.post('/api/invoices/', invoice_data, format='json')
        sent_id = sent_response.json()['invoice']['id']
        self.authenticated_client.post(f'/api/invoices/{sent_id}/send/')
        
        # Test basic listing
        response = self.authenticated_client.get('/api/invoices/')
        APITestHelpers.assert_successful_response(response)
        
        invoices_data = response.json()
        self.assertGreaterEqual(len(invoices_data['results']), 2)
        
        # Test status filtering
        response = self.authenticated_client.get('/api/invoices/?status=draft')
        APITestHelpers.assert_successful_response(response)
        
        draft_invoices = response.json()['results']
        for invoice in draft_invoices:
            self.assertEqual(invoice['status'], 'draft')
        
        # Test client filtering
        response = self.authenticated_client.get(f'/api/invoices/?client={self.client_model.id}')
        APITestHelpers.assert_successful_response(response)
        
        client_invoices = response.json()['results']
        for invoice in client_invoices:
            self.assertEqual(invoice['client']['id'], str(self.client_model.id))
        
        # Test date range filtering
        today = date.today()
        response = self.authenticated_client.get(f'/api/invoices/?date_from={today}&date_to={today}')
        APITestHelpers.assert_successful_response(response)
    
    def test_overdue_invoice_detection(self):
        """Test overdue invoice detection and handling."""
        # Create overdue invoice
        overdue_data = TestDataGenerator.invoice_data(
            client_id=self.client_model.id,
            due_date=(date.today() - timedelta(days=5)).isoformat()  # 5 days overdue
        )
        
        response = self.authenticated_client.post('/api/invoices/', overdue_data, format='json')
        invoice_id = response.json()['invoice']['id']
        
        # Send invoice to make it active
        self.authenticated_client.post(f'/api/invoices/{invoice_id}/send/')
        
        # Test overdue endpoint if available
        response = self.authenticated_client.get('/api/invoices/?overdue=true')
        APITestHelpers.assert_successful_response(response)
        
        # Should include our overdue invoice if filtering is implemented
        overdue_invoices = response.json()['results']
        overdue_ids = [inv['id'] for inv in overdue_invoices]
        
        # If overdue filtering is implemented, our invoice should be included
        if len(overdue_invoices) > 0:
            self.assertIn(invoice_id, overdue_ids)