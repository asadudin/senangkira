"""
Enhanced Invoicing models for SenangKira with validation, auto-generation, and comprehensive features.
Maps to invoicing tables in schema.sql.
"""

import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db import models, transaction
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from clients.models import Client


class QuoteStatus(models.TextChoices):
    """Enhanced quote status choices with lifecycle management."""
    DRAFT = 'draft', 'Draft'
    SENT = 'sent', 'Sent'
    APPROVED = 'approved', 'Approved'
    DECLINED = 'declined', 'Declined'
    EXPIRED = 'expired', 'Expired'


class InvoiceStatus(models.TextChoices):
    """Enhanced invoice status choices with lifecycle management."""
    DRAFT = 'draft', 'Draft'
    SENT = 'sent', 'Sent'
    VIEWED = 'viewed', 'Viewed'
    PAID = 'paid', 'Paid'
    OVERDUE = 'overdue', 'Overdue'
    CANCELLED = 'cancelled', 'Cancelled'


def generate_quote_number(owner):
    """Generate unique quote number for owner."""
    today = date.today()
    prefix = f"QT-{today.year}-"
    
    # Get the last quote number for this owner and year
    last_quote = Quote.objects.filter(
        owner=owner,
        quote_number__startswith=prefix
    ).order_by('-quote_number').first()
    
    if last_quote:
        try:
            last_number = int(last_quote.quote_number.split('-')[-1])
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1
    
    return f"{prefix}{next_number:04d}"


def generate_invoice_number(owner):
    """Generate unique invoice number for owner."""
    today = date.today()
    prefix = f"INV-{today.year}-"
    
    # Get the last invoice number for this owner and year
    last_invoice = Invoice.objects.filter(
        owner=owner,
        invoice_number__startswith=prefix
    ).order_by('-invoice_number').first()
    
    if last_invoice:
        try:
            last_number = int(last_invoice.invoice_number.split('-')[-1])
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1
    
    return f"{prefix}{next_number:04d}"


class Item(models.Model):
    """
    Enhanced reusable items/services for quick entry with validation.
    Maps to invoicing_item table in schema.sql.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Item or service name"
    )
    description = models.TextField(
        blank=True, 
        null=True,
        help_text="Detailed description of the item/service"
    )
    default_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Default price for this item"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this item is available for use"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The user who owns this item"
    )
    
    class Meta:
        db_table = 'invoicing_item'
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner', 'name']),
            models.Index(fields=['owner', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='unique_item_name_per_owner'
            )
        ]
        
    def clean(self):
        """Validate item fields."""
        super().clean()
        if self.name:
            self.name = self.name.strip()
        if self.default_price and self.default_price <= 0:
            raise ValidationError('Price must be greater than zero.')
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name} (${self.default_price})"


class Quote(models.Model):
    """
    Enhanced Quote model with auto-generation, validation, and status management.
    Maps to invoicing_quote table in schema.sql.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=QuoteStatus.choices,
        default=QuoteStatus.DRAFT,
        help_text="Current status of the quote"
    )
    quote_number = models.CharField(
        max_length=50,
        help_text="Auto-generated quote number"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional title for the quote"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes for the quote"
    )
    terms = models.TextField(
        blank=True,
        null=True,
        help_text="Terms and conditions for the quote"
    )
    issue_date = models.DateField(
        auto_now_add=True,
        help_text="Date when the quote was created"
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Quote expiration date"
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount of the quote (auto-calculated)"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Subtotal before tax (auto-calculated)"
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Tax rate as decimal (e.g., 0.1000 for 10%)"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tax amount (auto-calculated)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the quote was sent to client"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quotes',
        help_text="The user who owns this quote"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.RESTRICT,
        related_name='quotes',
        help_text="The client this quote is for"
    )
    
    class Meta:
        db_table = 'invoicing_quote'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['owner', 'client']),
            models.Index(fields=['owner', 'quote_number']),
            models.Index(fields=['valid_until']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'quote_number'],
                name='unique_quote_number_per_owner'
            )
        ]
    
    def clean(self):
        """Validate quote fields."""
        super().clean()
        
        # Validate tax rate
        if self.tax_rate and (self.tax_rate < 0 or self.tax_rate > 1):
            raise ValidationError('Tax rate must be between 0 and 1 (0-100%)')
        
        # Validate valid_until date
        if self.valid_until and self.valid_until < self.issue_date:
            raise ValidationError('Valid until date cannot be before issue date')
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate quote number and calculate totals."""
        # Generate quote number if not set
        if not self.quote_number:
            self.quote_number = generate_quote_number(self.owner)
        
        # Set default valid_until if not set (30 days from issue date)
        if not self.valid_until:
            self.valid_until = self.issue_date + timedelta(days=30)
        
        # Validate before saving
        self.clean()
        
        super().save(*args, **kwargs)
        
        # Recalculate totals after saving (in case line items changed)
        self.calculate_totals()
    
    def calculate_totals(self):
        """Calculate and update quote totals based on line items."""
        line_items = self.line_items.all()
        
        # Calculate subtotal
        subtotal = sum(item.total_price for item in line_items)
        
        # Calculate tax
        tax_amount = subtotal * self.tax_rate
        
        # Calculate total
        total_amount = subtotal + tax_amount
        
        # Round to 2 decimal places
        self.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.tax_amount = tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_amount = total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Update without triggering save recursion
        Quote.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
            updated_at=timezone.now()
        )
    
    def can_transition_to(self, new_status):
        """Check if quote can transition to new status."""
        valid_transitions = {
            QuoteStatus.DRAFT: [QuoteStatus.SENT, QuoteStatus.DECLINED],
            QuoteStatus.SENT: [QuoteStatus.APPROVED, QuoteStatus.DECLINED, QuoteStatus.EXPIRED],
            QuoteStatus.APPROVED: [QuoteStatus.DECLINED],  # Can decline even after approval
            QuoteStatus.DECLINED: [],  # Terminal state
            QuoteStatus.EXPIRED: [QuoteStatus.SENT],  # Can resend expired quote
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def mark_as_sent(self):
        """Mark quote as sent and update sent_at timestamp."""
        if self.can_transition_to(QuoteStatus.SENT):
            self.status = QuoteStatus.SENT
            self.sent_at = timezone.now()
            self.save(update_fields=['status', 'sent_at', 'updated_at'])
            return True
        return False
    
    def mark_as_approved(self):
        """Mark quote as approved."""
        if self.can_transition_to(QuoteStatus.APPROVED):
            self.status = QuoteStatus.APPROVED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def mark_as_declined(self):
        """Mark quote as declined."""
        if self.can_transition_to(QuoteStatus.DECLINED):
            self.status = QuoteStatus.DECLINED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    @property
    def is_expired(self):
        """Check if quote has expired."""
        return self.valid_until and date.today() > self.valid_until
    
    @property
    def days_until_expiry(self):
        """Get days until quote expires."""
        if self.valid_until:
            delta = self.valid_until - date.today()
            return delta.days
        return None
    
    @property
    def can_be_converted_to_invoice(self):
        """Check if quote can be converted to invoice."""
        return self.status == QuoteStatus.APPROVED and not hasattr(self, 'invoice')
        
    def __str__(self):
        return f"Quote {self.quote_number} - {self.client.name}"


class QuoteLineItem(models.Model):
    """
    Enhanced line items for quotes with validation and calculations.
    Maps to invoicing_quotelineitem table in schema.sql.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField(
        help_text="Description of the item or service"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity of items"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order of line items in the quote"
    )
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name='line_items',
        help_text="The quote this line item belongs to"
    )
    
    class Meta:
        db_table = 'invoicing_quotelineitem'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['quote', 'sort_order']),
        ]
    
    def clean(self):
        """Validate line item fields."""
        super().clean()
        
        if self.quantity and self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')
        
        if self.unit_price and self.unit_price <= 0:
            raise ValidationError('Unit price must be greater than zero.')
        
        if self.description:
            self.description = self.description.strip()
    
    def save(self, *args, **kwargs):
        """Override save to validate and update quote totals."""
        self.clean()
        super().save(*args, **kwargs)
        
        # Update quote totals when line item changes
        if self.quote_id:
            self.quote.calculate_totals()
    
    def delete(self, *args, **kwargs):
        """Override delete to update quote totals."""
        quote = self.quote
        super().delete(*args, **kwargs)
        
        # Update quote totals after deletion
        quote.calculate_totals()
        
    @property
    def total_price(self):
        """Calculate total price for this line item."""
        return (self.quantity * self.unit_price).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    def __str__(self):
        return f"{self.description} (${self.total_price})"


class Invoice(models.Model):
    """
    Enhanced Invoice model with auto-generation, validation, and status management.
    Maps to invoicing_invoice table in schema.sql.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        help_text="Current status of the invoice"
    )
    invoice_number = models.CharField(
        max_length=50,
        help_text="Auto-generated invoice number"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional title for the invoice"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes for the invoice"
    )
    terms = models.TextField(
        blank=True,
        null=True,
        help_text="Payment terms and conditions"
    )
    issue_date = models.DateField(
        auto_now_add=True,
        help_text="Date when the invoice was issued"
    )
    due_date = models.DateField(
        help_text="Payment due date"
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount of the invoice (auto-calculated)"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Subtotal before tax (auto-calculated)"
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Tax rate as decimal (e.g., 0.1000 for 10%)"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tax amount (auto-calculated)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invoice was sent to client"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invoice was marked as paid"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="The user who owns this invoice"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.RESTRICT,
        related_name='invoices',
        help_text="The client this invoice is for"
    )
    source_quote = models.OneToOneField(
        Quote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        help_text="The quote this invoice was created from (optional)"
    )
    
    class Meta:
        db_table = 'invoicing_invoice'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['owner', 'client']),
            models.Index(fields=['owner', 'invoice_number']),
            models.Index(fields=['due_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'invoice_number'],
                name='unique_invoice_number_per_owner'
            )
        ]
    
    def clean(self):
        """Validate invoice fields."""
        super().clean()
        
        # Validate tax rate
        if self.tax_rate and (self.tax_rate < 0 or self.tax_rate > 1):
            raise ValidationError('Tax rate must be between 0 and 1 (0-100%)')
        
        # Validate due date
        if self.due_date and self.due_date < self.issue_date:
            raise ValidationError('Due date cannot be before issue date')
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate invoice number and set defaults."""
        # Generate invoice number if not set
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number(self.owner)
        
        # Set default due date if not set (30 days from issue date)
        if not self.due_date:
            self.due_date = self.issue_date + timedelta(days=30)
        
        # Validate before saving
        self.clean()
        
        super().save(*args, **kwargs)
        
        # Recalculate totals after saving (in case line items changed)
        self.calculate_totals()
    
    def calculate_totals(self):
        """Calculate and update invoice totals based on line items."""
        line_items = self.line_items.all()
        
        # Calculate subtotal
        subtotal = sum(item.total_price for item in line_items)
        
        # Calculate tax
        tax_amount = subtotal * self.tax_rate
        
        # Calculate total
        total_amount = subtotal + tax_amount
        
        # Round to 2 decimal places
        self.subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.tax_amount = tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_amount = total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Update without triggering save recursion
        Invoice.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
            updated_at=timezone.now()
        )
    
    def can_transition_to(self, new_status):
        """Check if invoice can transition to new status."""
        valid_transitions = {
            InvoiceStatus.DRAFT: [InvoiceStatus.SENT, InvoiceStatus.CANCELLED],
            InvoiceStatus.SENT: [InvoiceStatus.VIEWED, InvoiceStatus.PAID, InvoiceStatus.OVERDUE, InvoiceStatus.CANCELLED],
            InvoiceStatus.VIEWED: [InvoiceStatus.PAID, InvoiceStatus.OVERDUE, InvoiceStatus.CANCELLED],
            InvoiceStatus.PAID: [],  # Terminal state
            InvoiceStatus.OVERDUE: [InvoiceStatus.PAID, InvoiceStatus.CANCELLED],
            InvoiceStatus.CANCELLED: [],  # Terminal state
        }
        
        return new_status in valid_transitions.get(self.status, [])
    
    def mark_as_sent(self):
        """Mark invoice as sent and update sent_at timestamp."""
        if self.can_transition_to(InvoiceStatus.SENT):
            self.status = InvoiceStatus.SENT
            self.sent_at = timezone.now()
            self.save(update_fields=['status', 'sent_at', 'updated_at'])
            return True
        return False
    
    def mark_as_paid(self):
        """Mark invoice as paid and update paid_at timestamp."""
        if self.can_transition_to(InvoiceStatus.PAID):
            self.status = InvoiceStatus.PAID
            self.paid_at = timezone.now()
            self.save(update_fields=['status', 'paid_at', 'updated_at'])
            return True
        return False
    
    def mark_as_cancelled(self):
        """Mark invoice as cancelled."""
        if self.can_transition_to(InvoiceStatus.CANCELLED):
            self.status = InvoiceStatus.CANCELLED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        return (
            self.status not in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED] and
            date.today() > self.due_date
        )
    
    @property
    def days_until_due(self):
        """Get days until invoice is due."""
        delta = self.due_date - date.today()
        return delta.days
    
    @property
    def days_overdue(self):
        """Get days overdue (negative if not overdue)."""
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0
        
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.name}"


class InvoiceLineItem(models.Model):
    """
    Enhanced line items for invoices with validation and calculations.
    Maps to invoicing_invoicelineitem table in schema.sql.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField(
        help_text="Description of the item or service"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity of items"
    )
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order of line items in the invoice"
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='line_items',
        help_text="The invoice this line item belongs to"
    )
    
    class Meta:
        db_table = 'invoicing_invoicelineitem'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['invoice', 'sort_order']),
        ]
    
    def clean(self):
        """Validate line item fields."""
        super().clean()
        
        if self.quantity and self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')
        
        if self.unit_price and self.unit_price <= 0:
            raise ValidationError('Unit price must be greater than zero.')
        
        if self.description:
            self.description = self.description.strip()
    
    def save(self, *args, **kwargs):
        """Override save to validate and update invoice totals."""
        self.clean()
        super().save(*args, **kwargs)
        
        # Update invoice totals when line item changes
        if self.invoice_id:
            self.invoice.calculate_totals()
    
    def delete(self, *args, **kwargs):
        """Override delete to update invoice totals."""
        invoice = self.invoice
        super().delete(*args, **kwargs)
        
        # Update invoice totals after deletion
        invoice.calculate_totals()
        
    @property
    def total_price(self):
        """Calculate total price for this line item."""
        return (self.quantity * self.unit_price).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    def __str__(self):
        return f"{self.description} (${self.total_price})"