"""
Test utilities and helper functions for SenangKira test suite.
Provides common test operations, data generators, and assertion helpers.
"""
import json
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status


class TestDataGenerator:
    """Generate test data for various models and scenarios."""
    
    @staticmethod
    def user_data(email=None, username=None, **kwargs):
        """Generate user registration data."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'email': email or f'user_{unique_id}@example.com',
            'username': username or f'user_{unique_id}',
            'password': 'TestPass123!',
            'company_name': f'Test Company {unique_id}'
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def client_data(name=None, **kwargs):
        """Generate client creation data."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': name or f'Test Client {unique_id}',
            'email': f'client_{unique_id}@example.com',
            'phone': '+1234567890',
            'address': '123 Test Street',
            'city': 'Test City',
            'state': 'TS',
            'postal_code': '12345',
            'country': 'Test Country'
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def quote_data(client_id, title=None, **kwargs):
        """Generate quote creation data."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'client': str(client_id),
            'title': title or f'Test Quote {unique_id}',
            'description': 'Test quote description',
            'tax_rate': '0.0800',
            'quote_date': date.today().isoformat(),
            'valid_until': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Consulting Services',
                    'quantity': '10.00',
                    'unit_price': '150.00',
                    'sort_order': 0
                },
                {
                    'description': 'Development Work',
                    'quantity': '20.00',
                    'unit_price': '100.00',
                    'sort_order': 1
                }
            ]
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def invoice_data(client_id, title=None, **kwargs):
        """Generate invoice creation data."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'client': str(client_id),
            'title': title or f'Test Invoice {unique_id}',
            'description': 'Test invoice description',
            'tax_rate': '0.0800',
            'invoice_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'line_items': [
                {
                    'description': 'Professional Services',
                    'quantity': '15.00',
                    'unit_price': '120.00',
                    'sort_order': 0
                }
            ]
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def expense_data(amount=None, **kwargs):
        """Generate expense creation data."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'description': f'Test Expense {unique_id}',
            'amount': str(amount or Decimal('100.00')),
            'expense_date': date.today().isoformat(),
            'category': 'office_supplies',
            'is_reimbursable': False
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def line_items_complex():
        """Generate complex line items for testing calculations."""
        return [
            {
                'description': 'Senior Developer (Full-time)',
                'quantity': '160.00',  # 4 weeks * 40 hours
                'unit_price': '125.00',
                'sort_order': 0
            },
            {
                'description': 'UI/UX Designer (Part-time)',
                'quantity': '80.00',   # 4 weeks * 20 hours
                'unit_price': '150.00',
                'sort_order': 1
            },
            {
                'description': 'Project Management',
                'quantity': '40.00',   # 4 weeks * 10 hours
                'unit_price': '100.00',
                'sort_order': 2
            },
            {
                'description': 'Cloud Infrastructure',
                'quantity': '1.00',    # Monthly fee
                'unit_price': '500.00',
                'sort_order': 3
            }
        ]


class APITestHelpers:
    """Helper methods for API testing."""
    
    @staticmethod
    def assert_successful_response(response, expected_status=status.HTTP_200_OK):
        """Assert API response is successful."""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}. Response: {response.data}"
    
    @staticmethod
    def assert_error_response(response, expected_status=status.HTTP_400_BAD_REQUEST, error_key=None):
        """Assert API response contains expected error."""
        assert response.status_code == expected_status, \
            f"Expected status {expected_status}, got {response.status_code}. Response: {response.data}"
        
        if error_key:
            response_data = response.json() if hasattr(response, 'json') else response.data
            assert error_key in str(response_data), \
                f"Expected error key '{error_key}' not found in response: {response_data}"
    
    @staticmethod
    def assert_required_fields(response_data: Dict, required_fields: List[str]):
        """Assert response contains all required fields."""
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing from response"
    
    @staticmethod
    def assert_decimal_equal(actual, expected, places=2):
        """Assert decimal values are equal with specified precision."""
        if isinstance(actual, str):
            actual = Decimal(actual)
        if isinstance(expected, str):
            expected = Decimal(expected)
        
        assert abs(actual - expected) < Decimal(f'0.{"0" * (places-1)}1'), \
            f"Decimal values not equal: {actual} != {expected}"
    
    @staticmethod
    def assert_date_equal(actual, expected):
        """Assert date values are equal."""
        if isinstance(actual, str):
            from datetime import datetime
            actual = datetime.fromisoformat(actual.replace('Z', '+00:00')).date()
        if isinstance(expected, str):
            from datetime import datetime
            expected = datetime.fromisoformat(expected.replace('Z', '+00:00')).date()
        
        assert actual == expected, f"Dates not equal: {actual} != {expected}"


class CalculationHelpers:
    """Helper methods for testing financial calculations."""
    
    @staticmethod
    def calculate_line_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
        """Calculate line item total."""
        return quantity * unit_price
    
    @staticmethod
    def calculate_subtotal(line_items: List[Dict]) -> Decimal:
        """Calculate subtotal from line items."""
        subtotal = Decimal('0.00')
        for item in line_items:
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unit_price']))
            subtotal += quantity * unit_price
        return subtotal
    
    @staticmethod
    def calculate_tax_amount(subtotal: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate tax amount."""
        return subtotal * tax_rate
    
    @staticmethod
    def calculate_total(subtotal: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate total amount including tax."""
        tax_amount = CalculationHelpers.calculate_tax_amount(subtotal, tax_rate)
        return subtotal + tax_amount
    
    @staticmethod
    def validate_financial_calculations(response_data: Dict, line_items: List[Dict], tax_rate: Decimal):
        """Validate all financial calculations in response."""
        expected_subtotal = CalculationHelpers.calculate_subtotal(line_items)
        expected_tax = CalculationHelpers.calculate_tax_amount(expected_subtotal, tax_rate)
        expected_total = expected_subtotal + expected_tax
        
        APITestHelpers.assert_decimal_equal(response_data['subtotal'], expected_subtotal)
        APITestHelpers.assert_decimal_equal(response_data['tax_amount'], expected_tax)
        APITestHelpers.assert_decimal_equal(response_data['total_amount'], expected_total)


class FileUploadHelpers:
    """Helper methods for file upload testing."""
    
    @staticmethod
    def create_test_csv(content: str, filename: str = 'test.csv') -> SimpleUploadedFile:
        """Create test CSV file for upload."""
        return SimpleUploadedFile(
            filename,
            content.encode('utf-8'),
            content_type='text/csv'
        )
    
    @staticmethod
    def create_test_pdf(filename: str = 'test.pdf') -> SimpleUploadedFile:
        """Create test PDF file for upload."""
        # Minimal PDF content
        pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj xref 0 4 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n 0000000115 00000 n trailer<</Size 4/Root 1 0 R>>startxref 176 %%EOF'
        return SimpleUploadedFile(
            filename,
            pdf_content,
            content_type='application/pdf'
        )


class PerformanceTestHelpers:
    """Helper methods for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """Measure function execution time."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def assert_execution_time(execution_time: float, max_time: float):
        """Assert execution time is within acceptable limits."""
        assert execution_time <= max_time, \
            f"Execution time {execution_time:.3f}s exceeds maximum {max_time}s"
    
    @staticmethod
    def create_bulk_test_data(factory_func, count: int, **kwargs):
        """Create bulk test data for performance testing."""
        return [factory_func(**kwargs) for _ in range(count)]


class DatabaseTestHelpers:
    """Helper methods for database testing."""
    
    @staticmethod
    def assert_query_count(expected_count: int):
        """Context manager to assert database query count."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import TestCase
        
        class QueryCounter:
            def __enter__(self):
                self.initial_queries = len(connection.queries)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                final_queries = len(connection.queries)
                query_count = final_queries - self.initial_queries
                assert query_count <= expected_count, \
                    f"Expected at most {expected_count} queries, got {query_count}"
        
        return QueryCounter()
    
    @staticmethod
    def clear_cache():
        """Clear Django cache for testing."""
        from django.core.cache import cache
        cache.clear()


class IntegrationTestHelpers:
    """Helper methods for integration testing."""
    
    @staticmethod
    def complete_quote_workflow(api_client, quote_data):
        """Complete quote creation and approval workflow."""
        # Create quote
        response = api_client.post('/api/quotes/', quote_data, format='json')
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        quote_id = response.json()['quote']['id']
        
        # Send quote
        response = api_client.post(f'/api/quotes/{quote_id}/send/')
        APITestHelpers.assert_successful_response(response)
        
        # Approve quote
        response = api_client.post(f'/api/quotes/{quote_id}/approve/')
        APITestHelpers.assert_successful_response(response)
        
        return quote_id
    
    @staticmethod
    def complete_invoice_workflow(api_client, invoice_data):
        """Complete invoice creation and processing workflow."""
        # Create invoice
        response = api_client.post('/api/invoices/', invoice_data, format='json')
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        invoice_id = response.json()['invoice']['id']
        
        # Send invoice
        response = api_client.post(f'/api/invoices/{invoice_id}/send/')
        APITestHelpers.assert_successful_response(response)
        
        return invoice_id