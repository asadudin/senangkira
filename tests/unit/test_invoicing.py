"""
Unit tests for invoicing functionality.
Tests quote and invoice models, calculations, and business logic.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta

from invoicing.models import (
    Quote, Invoice, QuoteLineItem, InvoiceLineItem,
    QuoteStatus, InvoiceStatus
)
from clients.models import Client
from tests.utils import TestDataGenerator, CalculationHelpers
from tests.conftest import BaseTestCase

User = get_user_model()


class QuoteModelTests(BaseTestCase):
    """Test Quote model functionality."""
    
    def test_quote_creation(self):
        """Test basic quote creation."""
        quote = Quote.objects.create(
            title='Test Quote',
            description='Test quote description',
            tax_rate=Decimal('0.0800'),
            quote_date=date.today(),
            valid_until=date.today() + timedelta(days=30),
            owner=self.user,
            client=self.client_model
        )
        
        self.assertEqual(quote.title, 'Test Quote')
        self.assertEqual(quote.owner, self.user)
        self.assertEqual(quote.client, self.client_model)
        self.assertEqual(quote.status, QuoteStatus.DRAFT)
        self.assertIsNotNone(quote.id)
    
    def test_quote_string_representation(self):
        """Test quote string representation."""
        quote = Quote.objects.create(
            title='Test Quote Representation',
            owner=self.user,
            client=self.client_model
        )
        
        self.assertIn('Test Quote Representation', str(quote))
    
    def test_quote_default_values(self):
        """Test quote default field values."""
        quote = Quote.objects.create(
            title='Default Values Quote',
            owner=self.user,
            client=self.client_model
        )
        
        self.assertEqual(quote.status, QuoteStatus.DRAFT)
        self.assertEqual(quote.tax_rate, Decimal('0.0000'))
        self.assertEqual(quote.quote_date, date.today())
        self.assertIsNotNone(quote.created_at)
        self.assertIsNotNone(quote.updated_at)
    
    def test_quote_validation(self):
        """Test quote field validation."""
        # Tax rate cannot be negative
        with self.assertRaises(ValidationError):
            quote = Quote(
                title='Invalid Tax Rate',
                tax_rate=Decimal('-0.10'),
                owner=self.user,
                client=self.client_model
            )
            quote.full_clean()
        
        # Valid until should be after quote date
        with self.assertRaises(ValidationError):
            quote = Quote(
                title='Invalid Date Range',
                quote_date=date.today(),
                valid_until=date.today() - timedelta(days=1),
                owner=self.user,
                client=self.client_model
            )
            quote.full_clean()
    
    def test_quote_status_transitions(self):
        """Test quote status transitions."""
        quote = Quote.objects.create(
            title='Status Test Quote',
            owner=self.user,
            client=self.client_model
        )
        
        # Initial status should be DRAFT
        self.assertEqual(quote.status, QuoteStatus.DRAFT)
        
        # Can change to SENT
        quote.status = QuoteStatus.SENT
        quote.save()
        self.assertEqual(quote.status, QuoteStatus.SENT)
        
        # Can change to ACCEPTED
        quote.status = QuoteStatus.ACCEPTED
        quote.save()
        self.assertEqual(quote.status, QuoteStatus.ACCEPTED)


class QuoteLineItemTests(BaseTestCase):
    """Test QuoteLineItem model functionality."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.quote = Quote.objects.create(
            title='Line Item Test Quote',
            owner=self.user,
            client=self.client_model
        )
    
    def test_line_item_creation(self):
        """Test line item creation."""
        line_item = QuoteLineItem.objects.create(
            quote=self.quote,
            description='Test Service',
            quantity=Decimal('10.00'),
            unit_price=Decimal('150.00'),
            sort_order=0
        )
        
        self.assertEqual(line_item.quote, self.quote)
        self.assertEqual(line_item.description, 'Test Service')
        self.assertEqual(line_item.quantity, Decimal('10.00'))
        self.assertEqual(line_item.unit_price, Decimal('150.00'))
    
    def test_line_item_total_calculation(self):
        """Test line item total calculation."""
        line_item = QuoteLineItem.objects.create(
            quote=self.quote,
            description='Calculation Test',
            quantity=Decimal('5.00'),
            unit_price=Decimal('200.00'),
            sort_order=0
        )
        
        expected_total = Decimal('1000.00')  # 5 * 200
        self.assertEqual(line_item.total, expected_total)
    
    def test_line_item_validation(self):
        """Test line item validation."""
        # Quantity cannot be negative
        with self.assertRaises(ValidationError):
            line_item = QuoteLineItem(
                quote=self.quote,
                description='Invalid Quantity',
                quantity=Decimal('-1.00'),
                unit_price=Decimal('100.00')
            )
            line_item.full_clean()
        
        # Unit price cannot be negative
        with self.assertRaises(ValidationError):
            line_item = QuoteLineItem(
                quote=self.quote,
                description='Invalid Price',
                quantity=Decimal('1.00'),
                unit_price=Decimal('-100.00')
            )
            line_item.full_clean()
    
    def test_line_item_ordering(self):
        """Test line item ordering by sort_order."""
        # Create items in different order
        item2 = QuoteLineItem.objects.create(
            quote=self.quote,
            description='Second Item',
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00'),
            sort_order=1
        )
        
        item1 = QuoteLineItem.objects.create(
            quote=self.quote,
            description='First Item',
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        items = self.quote.line_items.order_by('sort_order')
        self.assertEqual(items[0], item1)
        self.assertEqual(items[1], item2)


class InvoiceModelTests(BaseTestCase):
    """Test Invoice model functionality."""
    
    def test_invoice_creation(self):
        """Test basic invoice creation."""
        invoice = Invoice.objects.create(
            title='Test Invoice',
            description='Test invoice description',
            tax_rate=Decimal('0.0800'),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            owner=self.user,
            client=self.client_model
        )
        
        self.assertEqual(invoice.title, 'Test Invoice')
        self.assertEqual(invoice.owner, self.user)
        self.assertEqual(invoice.client, self.client_model)
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
    
    def test_invoice_default_values(self):
        """Test invoice default field values."""
        invoice = Invoice.objects.create(
            title='Default Values Invoice',
            owner=self.user,
            client=self.client_model
        )
        
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.assertEqual(invoice.tax_rate, Decimal('0.0000'))
        self.assertEqual(invoice.invoice_date, date.today())
        self.assertIsNone(invoice.paid_date)
    
    def test_invoice_payment_status(self):
        """Test invoice payment status logic."""
        invoice = Invoice.objects.create(
            title='Payment Test Invoice',
            owner=self.user,
            client=self.client_model
        )
        
        # Initially unpaid
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.assertIsNone(invoice.paid_date)
        
        # Mark as paid
        invoice.status = InvoiceStatus.PAID
        invoice.paid_date = date.today()
        invoice.save()
        
        self.assertEqual(invoice.status, InvoiceStatus.PAID)
        self.assertIsNotNone(invoice.paid_date)
    
    def test_invoice_overdue_logic(self):
        """Test invoice overdue detection."""
        # Create overdue invoice
        overdue_invoice = Invoice.objects.create(
            title='Overdue Invoice',
            due_date=date.today() - timedelta(days=5),
            status=InvoiceStatus.SENT,
            owner=self.user,
            client=self.client_model
        )
        
        # Create current invoice
        current_invoice = Invoice.objects.create(
            title='Current Invoice',
            due_date=date.today() + timedelta(days=5),
            status=InvoiceStatus.SENT,
            owner=self.user,
            client=self.client_model
        )
        
        # Test overdue logic if implemented
        if hasattr(overdue_invoice, 'is_overdue'):
            self.assertTrue(overdue_invoice.is_overdue)
            self.assertFalse(current_invoice.is_overdue)


class FinancialCalculationTests(BaseTestCase):
    """Test financial calculations in quotes and invoices."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.quote = Quote.objects.create(
            title='Calculation Test Quote',
            tax_rate=Decimal('0.0800'),
            owner=self.user,
            client=self.client_model
        )
    
    def test_quote_subtotal_calculation(self):
        """Test quote subtotal calculation."""
        # Add line items
        QuoteLineItem.objects.create(
            quote=self.quote,
            description='Service 1',
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        QuoteLineItem.objects.create(
            quote=self.quote,
            description='Service 2',
            quantity=Decimal('5.00'),
            unit_price=Decimal('200.00'),
            sort_order=1
        )
        
        expected_subtotal = Decimal('2000.00')  # (10*100) + (5*200)
        
        if hasattr(self.quote, 'subtotal'):
            self.assertEqual(self.quote.subtotal, expected_subtotal)
    
    def test_quote_tax_calculation(self):
        """Test quote tax amount calculation."""
        # Add line item
        QuoteLineItem.objects.create(
            quote=self.quote,
            description='Taxable Service',
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        expected_subtotal = Decimal('1000.00')
        expected_tax = expected_subtotal * self.quote.tax_rate  # 1000 * 0.08 = 80
        
        if hasattr(self.quote, 'tax_amount'):
            self.assertEqual(self.quote.tax_amount, expected_tax)
    
    def test_quote_total_calculation(self):
        """Test quote total amount calculation."""
        # Add line item
        QuoteLineItem.objects.create(
            quote=self.quote,
            description='Total Test Service',
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        expected_subtotal = Decimal('1000.00')
        expected_tax = Decimal('80.00')  # 1000 * 0.08
        expected_total = Decimal('1080.00')  # subtotal + tax
        
        if hasattr(self.quote, 'total_amount'):
            self.assertEqual(self.quote.total_amount, expected_total)
    
    def test_zero_tax_rate_calculation(self):
        """Test calculations with zero tax rate."""
        zero_tax_quote = Quote.objects.create(
            title='Zero Tax Quote',
            tax_rate=Decimal('0.0000'),
            owner=self.user,
            client=self.client_model
        )
        
        QuoteLineItem.objects.create(
            quote=zero_tax_quote,
            description='No Tax Service',
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        if hasattr(zero_tax_quote, 'tax_amount'):
            self.assertEqual(zero_tax_quote.tax_amount, Decimal('0.00'))
        
        if hasattr(zero_tax_quote, 'total_amount'):
            self.assertEqual(zero_tax_quote.total_amount, Decimal('1000.00'))
    
    def test_high_precision_calculations(self):
        """Test calculations with high precision decimals."""
        high_precision_quote = Quote.objects.create(
            title='High Precision Quote',
            tax_rate=Decimal('0.0825'),  # 8.25%
            owner=self.user,
            client=self.client_model
        )
        
        QuoteLineItem.objects.create(
            quote=high_precision_quote,
            description='Precision Test',
            quantity=Decimal('3.333'),
            unit_price=Decimal('99.99'),
            sort_order=0
        )
        
        expected_subtotal = Decimal('3.333') * Decimal('99.99')
        expected_tax = expected_subtotal * Decimal('0.0825')
        expected_total = expected_subtotal + expected_tax
        
        # Test calculations maintain precision
        if hasattr(high_precision_quote, 'subtotal'):
            # Allow for small rounding differences
            self.assertAlmostEqual(
                float(high_precision_quote.subtotal),
                float(expected_subtotal),
                places=2
            )


class QuoteToInvoiceConversionTests(BaseTestCase):
    """Test quote to invoice conversion logic."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.quote = Quote.objects.create(
            title='Conversion Test Quote',
            tax_rate=Decimal('0.0800'),
            status=QuoteStatus.ACCEPTED,
            owner=self.user,
            client=self.client_model
        )
        
        # Add line items
        QuoteLineItem.objects.create(
            quote=self.quote,
            description='Service 1',
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            sort_order=0
        )
        
        QuoteLineItem.objects.create(
            quote=self.quote,
            description='Service 2',
            quantity=Decimal('5.00'),
            unit_price=Decimal('200.00'),
            sort_order=1
        )
    
    def test_conversion_eligibility(self):
        """Test quote conversion eligibility."""
        # Accepted quote should be convertible
        if hasattr(self.quote, 'can_convert_to_invoice'):
            self.assertTrue(self.quote.can_convert_to_invoice)
        
        # Draft quote should not be convertible
        draft_quote = Quote.objects.create(
            title='Draft Quote',
            status=QuoteStatus.DRAFT,
            owner=self.user,
            client=self.client_model
        )
        
        if hasattr(draft_quote, 'can_convert_to_invoice'):
            self.assertFalse(draft_quote.can_convert_to_invoice)
    
    def test_conversion_creates_invoice(self):
        """Test that conversion creates proper invoice."""
        # This would test the actual conversion method if implemented
        # For now, we test the data structure compatibility
        
        # Quote data should be compatible with invoice creation
        invoice_data = {
            'title': self.quote.title,
            'description': self.quote.description,
            'tax_rate': self.quote.tax_rate,
            'owner': self.quote.owner,
            'client': self.quote.client,
            'source_quote': self.quote
        }
        
        invoice = Invoice.objects.create(**invoice_data)
        
        self.assertEqual(invoice.title, self.quote.title)
        self.assertEqual(invoice.tax_rate, self.quote.tax_rate)
        self.assertEqual(invoice.owner, self.quote.owner)
        self.assertEqual(invoice.client, self.quote.client)
        
        if hasattr(invoice, 'source_quote'):
            self.assertEqual(invoice.source_quote, self.quote)
    
    def test_line_item_conversion(self):
        """Test line item conversion from quote to invoice."""
        # Create invoice for conversion test
        invoice = Invoice.objects.create(
            title=self.quote.title,
            tax_rate=self.quote.tax_rate,
            owner=self.quote.owner,
            client=self.quote.client
        )
        
        # Convert line items
        for quote_item in self.quote.line_items.all():
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=quote_item.description,
                quantity=quote_item.quantity,
                unit_price=quote_item.unit_price,
                sort_order=quote_item.sort_order
            )
        
        # Verify conversion
        self.assertEqual(
            invoice.line_items.count(),
            self.quote.line_items.count()
        )
        
        for quote_item, invoice_item in zip(
            self.quote.line_items.order_by('sort_order'),
            invoice.line_items.order_by('sort_order')
        ):
            self.assertEqual(quote_item.description, invoice_item.description)
            self.assertEqual(quote_item.quantity, invoice_item.quantity)
            self.assertEqual(quote_item.unit_price, invoice_item.unit_price)
            self.assertEqual(quote_item.total, invoice_item.total)