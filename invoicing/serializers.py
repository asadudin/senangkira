"""
Enhanced serializers for SenangKira invoicing system with nested relationships and validation.
"""

from rest_framework import serializers
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
import logging

from clients.serializers import ClientListSerializer
from .models import (
    Item, Quote, QuoteLineItem, Invoice, InvoiceLineItem,
    QuoteStatus, InvoiceStatus
)

# Initialize logger for audit trail
logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    """Serializer for reusable items/services."""
    
    class Meta:
        model = Item
        fields = [
            'id', 'name', 'description', 'default_price', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate item name uniqueness per owner."""
        if not value or not value.strip():
            raise serializers.ValidationError("Item name cannot be empty.")
        
        value = value.strip()
        request = self.context.get('request')
        
        if request and hasattr(request, 'user'):
            owner = request.user
            
            # Check for uniqueness within the same owner
            queryset = Item.objects.filter(owner=owner, name=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    "An item with this name already exists in your account."
                )
        
        return value
    
    def validate_default_price(self, value):
        """Validate default price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value
    
    def create(self, validated_data):
        """Create item with owner assignment."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        try:
            return super().create(validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'non_field_errors': [str(e)]})


class QuoteLineItemSerializer(serializers.ModelSerializer):
    """Serializer for quote line items with automatic total calculation."""
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = QuoteLineItem
        fields = [
            'id', 'description', 'quantity', 'unit_price', 'sort_order', 'total_price'
        ]
        read_only_fields = ['id', 'total_price']
    
    def validate_quantity(self, value):
        """Validate quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value
    
    def validate_unit_price(self, value):
        """Validate unit price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than zero.")
        return value
    
    def validate_description(self, value):
        """Validate description is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()


class QuoteSerializer(serializers.ModelSerializer):
    """
    Comprehensive Quote serializer with nested line items and client information.
    """
    line_items = QuoteLineItemSerializer(many=True, required=False)
    client_details = ClientListSerializer(source='client', read_only=True)
    
    # Read-only calculated fields
    subtotal = serializers.ReadOnlyField()
    tax_amount = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    can_be_converted_to_invoice = serializers.ReadOnlyField()
    
    # Status display
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Quote
        fields = [
            'id', 'status', 'status_display', 'quote_number', 'title', 'notes', 'terms',
            'issue_date', 'valid_until', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount',
            'created_at', 'updated_at', 'sent_at', 'client', 'client_details',
            'line_items', 'is_expired', 'days_until_expiry', 'can_be_converted_to_invoice'
        ]
        read_only_fields = [
            'id', 'quote_number', 'issue_date', 'subtotal', 'tax_amount', 'total_amount',
            'created_at', 'updated_at', 'sent_at', 'is_expired', 'days_until_expiry',
            'can_be_converted_to_invoice', 'status_display'
        ]
    
    def validate_tax_rate(self, value):
        """Validate tax rate is between 0 and 1."""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Tax rate must be between 0 and 1 (0-100%).")
        return value
    
    def validate_client(self, value):
        """Validate client belongs to the current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if value.owner != request.user:
                raise serializers.ValidationError("Invalid client selected.")
        return value
    
    def validate_valid_until(self, value):
        """Validate valid_until is not in the past."""
        if value and hasattr(self, 'initial_data'):
            # For updates, we need to check against issue_date
            if self.instance and value < self.instance.issue_date:
                raise serializers.ValidationError("Valid until date cannot be before issue date.")
        return value
    
    def validate_line_items(self, value):
        """Validate that at least one line item is provided."""
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create quote with nested line items."""
        line_items_data = validated_data.pop('line_items', [])
        
        # Set owner
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        # Create quote
        quote = Quote.objects.create(**validated_data)
        
        # Create line items
        for i, line_item_data in enumerate(line_items_data):
            line_item_data['sort_order'] = i
            line_item_data['quote'] = quote
            QuoteLineItem.objects.create(**line_item_data)
        
        # Calculate totals
        quote.calculate_totals()
        
        return quote
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update quote with nested line items."""
        line_items_data = validated_data.pop('line_items', None)
        
        # Update quote fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update line items if provided
        if line_items_data is not None:
            # Delete existing line items
            instance.line_items.all().delete()
            
            # Create new line items
            for i, line_item_data in enumerate(line_items_data):
                line_item_data['sort_order'] = i
                line_item_data['quote'] = instance
                QuoteLineItem.objects.create(**line_item_data)
        
        # Recalculate totals
        instance.calculate_totals()
        
        return instance


class QuoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for quote list views."""
    client_name = serializers.CharField(source='client.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    line_items_count = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Quote
        fields = [
            'id', 'status', 'status_display', 'quote_number', 'title',
            'issue_date', 'valid_until', 'total_amount', 'client', 'client_name',
            'line_items_count', 'is_expired', 'created_at'
        ]
        read_only_fields = [
            'id', 'quote_number', 'issue_date', 'total_amount', 'created_at',
            'client_name', 'line_items_count', 'is_expired', 'status_display'
        ]
    
    def get_line_items_count(self, obj):
        """Get count of line items."""
        return obj.line_items.count()


class QuoteCreateSerializer(serializers.ModelSerializer):
    """Specialized serializer for quote creation."""
    line_items = QuoteLineItemSerializer(many=True, required=True)
    
    class Meta:
        model = Quote
        fields = [
            'client', 'title', 'notes', 'terms', 'valid_until', 'tax_rate', 'line_items'
        ]
    
    def validate_client(self, value):
        """Validate client belongs to current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if value.owner != request.user:
                raise serializers.ValidationError("Invalid client selected.")
        return value
    
    def validate_line_items(self, value):
        """Validate line items data."""
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        
        for item in value:
            if not item.get('description', '').strip():
                raise serializers.ValidationError("All line items must have a description.")
            if item.get('quantity', 0) <= 0:
                raise serializers.ValidationError("All line items must have quantity > 0.")
            if item.get('unit_price', 0) <= 0:
                raise serializers.ValidationError("All line items must have unit_price > 0.")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create quote with line items."""
        line_items_data = validated_data.pop('line_items')
        
        # Set owner
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        # Create quote
        quote = Quote.objects.create(**validated_data)
        
        # Create line items
        for i, line_item_data in enumerate(line_items_data):
            line_item_data['sort_order'] = i
            QuoteLineItem.objects.create(quote=quote, **line_item_data)
        
        return quote


class QuoteStatusSerializer(serializers.Serializer):
    """Serializer for quote status transitions."""
    status = serializers.ChoiceField(choices=QuoteStatus.choices)
    
    def validate_status(self, value):
        """Validate status transition is allowed."""
        quote = self.context.get('quote')
        if quote and not quote.can_transition_to(value):
            current_status = quote.get_status_display()
            new_status = dict(QuoteStatus.choices)[value]
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {new_status}."
            )
        return value


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items with automatic total calculation."""
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = InvoiceLineItem
        fields = [
            'id', 'description', 'quantity', 'unit_price', 'sort_order', 'total_price'
        ]
        read_only_fields = ['id', 'total_price']
    
    def validate_quantity(self, value):
        """Validate quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value
    
    def validate_unit_price(self, value):
        """Validate unit price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Unit price must be greater than zero.")
        return value
    
    def validate_description(self, value):
        """Validate description is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Comprehensive Invoice serializer with nested line items and client information.
    """
    line_items = InvoiceLineItemSerializer(many=True, required=False)
    client_details = ClientListSerializer(source='client', read_only=True)
    
    # Read-only calculated fields
    subtotal = serializers.ReadOnlyField()
    tax_amount = serializers.ReadOnlyField()
    total_amount = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    days_overdue = serializers.ReadOnlyField()
    
    # Status display
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'status', 'status_display', 'invoice_number', 'title', 'notes', 'terms',
            'issue_date', 'due_date', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount',
            'created_at', 'updated_at', 'sent_at', 'paid_at', 'client', 'client_details',
            'source_quote', 'line_items', 'is_overdue', 'days_until_due', 'days_overdue'
        ]
        read_only_fields = [
            'id', 'invoice_number', 'issue_date', 'subtotal', 'tax_amount', 'total_amount',
            'created_at', 'updated_at', 'sent_at', 'paid_at', 'is_overdue', 'days_until_due',
            'days_overdue', 'status_display'
        ]
    
    def validate_tax_rate(self, value):
        """Validate tax rate is between 0 and 1."""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Tax rate must be between 0 and 1 (0-100%).")
        return value
    
    def validate_client(self, value):
        """Validate client belongs to the current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if value.owner != request.user:
                raise serializers.ValidationError("Invalid client selected.")
        return value
    
    def validate_source_quote(self, value):
        """Validate source quote belongs to current user and client."""
        if value:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                if value.owner != request.user:
                    raise serializers.ValidationError("Invalid quote selected.")
                
                # Check if quote client matches invoice client
                client = self.initial_data.get('client')
                if client and str(value.client.id) != str(client):
                    raise serializers.ValidationError("Quote client must match invoice client.")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create invoice with nested line items."""
        line_items_data = validated_data.pop('line_items', [])
        
        # Set owner
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        # Create invoice
        invoice = Invoice.objects.create(**validated_data)
        
        # Create line items
        for i, line_item_data in enumerate(line_items_data):
            line_item_data['sort_order'] = i
            line_item_data['invoice'] = invoice
            InvoiceLineItem.objects.create(**line_item_data)
        
        # Calculate totals
        invoice.calculate_totals()
        
        return invoice
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update invoice with nested line items."""
        line_items_data = validated_data.pop('line_items', None)
        
        # Update invoice fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update line items if provided
        if line_items_data is not None:
            # Delete existing line items
            instance.line_items.all().delete()
            
            # Create new line items
            for i, line_item_data in enumerate(line_items_data):
                line_item_data['sort_order'] = i
                line_item_data['invoice'] = instance
                InvoiceLineItem.objects.create(**line_item_data)
        
        # Recalculate totals
        instance.calculate_totals()
        
        return instance


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for invoice list views."""
    client_name = serializers.CharField(source='client.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    line_items_count = serializers.SerializerMethodField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'status', 'status_display', 'invoice_number', 'title',
            'issue_date', 'due_date', 'total_amount', 'client', 'client_name',
            'line_items_count', 'is_overdue', 'created_at'
        ]
        read_only_fields = [
            'id', 'invoice_number', 'issue_date', 'total_amount', 'created_at',
            'client_name', 'line_items_count', 'is_overdue', 'status_display'
        ]
    
    def get_line_items_count(self, obj):
        """Get count of line items."""
        return obj.line_items.count()


class InvoiceFromQuoteSerializer(serializers.Serializer):
    """Serializer for creating invoices from quotes."""
    quote_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    terms = serializers.CharField(required=False, allow_blank=True)
    due_date = serializers.DateField(required=False)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=4, required=False)
    
    def validate_quote_id(self, value):
        """Validate quote exists and belongs to current user."""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Authentication required.")
        
        try:
            quote = Quote.objects.get(id=value, owner=request.user)
        except Quote.DoesNotExist:
            raise serializers.ValidationError("Quote not found.")
        
        if not quote.can_be_converted_to_invoice:
            raise serializers.ValidationError("Quote cannot be converted to invoice.")
        
        return value
    
    def create(self, validated_data):
        """Create invoice from quote with enhanced atomic transaction safety."""
        quote_id = validated_data.pop('quote_id')
        request = self.context.get('request')
        
        try:
            # Start atomic transaction with enhanced safety measures
            with transaction.atomic():
                # Use select_for_update to prevent concurrent conversions
                quote = Quote.objects.select_for_update().get(
                    id=quote_id, 
                    owner=request.user
                )
                
                # Enhanced validation: Check if quote has already been converted
                if hasattr(quote, 'invoice') and quote.invoice:
                    raise serializers.ValidationError(
                        f"Quote {quote.quote_number} has already been converted to invoice {quote.invoice.invoice_number}."
                    )
                
                # Verify quote is still in valid state for conversion
                if not quote.can_be_converted_to_invoice:
                    raise serializers.ValidationError(
                        f"Quote {quote.quote_number} cannot be converted. Status: {quote.get_status_display()}"
                    )
                
                # Pre-conversion validation: Ensure line items exist
                line_items_count = quote.line_items.count()
                if line_items_count == 0:
                    raise serializers.ValidationError(
                        f"Quote {quote.quote_number} has no line items and cannot be converted."
                    )
                
                # Calculate expected totals for integrity check
                expected_subtotal = sum(
                    item.quantity * item.unit_price 
                    for item in quote.line_items.all()
                )
                
                # Prepare invoice data with enhanced validation
                invoice_data = {
                    'client': quote.client,
                    'title': validated_data.get('title', quote.title),
                    'notes': validated_data.get('notes', quote.notes),
                    'terms': validated_data.get('terms', quote.terms),
                    'due_date': validated_data.get('due_date'),
                    'tax_rate': validated_data.get('tax_rate', quote.tax_rate),
                    'source_quote': quote,
                    'owner': request.user,
                }
                
                # Set default due date if not provided (30 days from today)
                if not invoice_data['due_date']:
                    from datetime import date, timedelta
                    invoice_data['due_date'] = date.today() + timedelta(days=30)
                
                # Create invoice with atomic safety
                invoice = Invoice.objects.create(**invoice_data)
                
                # Copy line items with integrity validation
                copied_items = []
                total_copied_value = Decimal('0.00')
                
                for quote_item in quote.line_items.all().order_by('sort_order'):
                    invoice_line_item = InvoiceLineItem.objects.create(
                        invoice=invoice,
                        description=quote_item.description,
                        quantity=quote_item.quantity,
                        unit_price=quote_item.unit_price,
                        sort_order=quote_item.sort_order
                    )
                    copied_items.append(invoice_line_item)
                    total_copied_value += invoice_line_item.total_price
                
                # Validate data integrity: Ensure copied totals match
                if total_copied_value != expected_subtotal:
                    raise serializers.ValidationError(
                        f"Data integrity error: Expected subtotal {expected_subtotal}, "
                        f"but copied {total_copied_value}. Transaction rolled back."
                    )
                
                # Calculate and validate invoice totals
                invoice.calculate_totals()
                invoice.refresh_from_db()
                
                # Final integrity check
                if invoice.subtotal != expected_subtotal:
                    raise serializers.ValidationError(
                        f"Final validation failed: Invoice subtotal {invoice.subtotal} "
                        f"does not match expected {expected_subtotal}. Transaction rolled back."
                    )
                
                # Verify line items count matches
                if invoice.line_items.count() != line_items_count:
                    raise serializers.ValidationError(
                        f"Line item count mismatch: Expected {line_items_count}, "
                        f"got {invoice.line_items.count()}. Transaction rolled back."
                    )
                
                # Log successful conversion for audit trail
                logger.info(
                    f"Quote-to-Invoice conversion successful: "
                    f"Quote {quote.quote_number} -> Invoice {invoice.invoice_number} "
                    f"| Amount: {invoice.total_amount} | Items: {line_items_count} "
                    f"| User: {request.user.email}"
                )
                
                return invoice
                
        except Quote.DoesNotExist:
            raise serializers.ValidationError("Quote not found or access denied.")
        except Exception as e:
            # Log the error for debugging
            logger.error(
                f"Quote-to-Invoice conversion failed: Quote ID {quote_id} "
                f"| User: {request.user.email if request and hasattr(request, 'user') else 'Unknown'} "
                f"| Error: {str(e)}"
            )
            # Re-raise the exception to ensure transaction rollback
            if isinstance(e, serializers.ValidationError):
                raise
            else:
                raise serializers.ValidationError(
                    f"Conversion failed due to unexpected error: {str(e)}"
                )