"""
Serializers for expense management with receipt image handling.
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from .models import Expense, ExpenseAttachment, ExpenseCategory
from .services import ReceiptImageService

User = get_user_model()


class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for expense attachments with file handling.
    """
    
    file_size_mb = serializers.ReadOnlyField()
    image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpenseAttachment
        fields = [
            'id', 'file_name', 'file_size', 'file_size_mb',
            'content_type', 'uploaded_at', 'image_url', 'thumbnail_url'
        ]
        read_only_fields = ['id', 'uploaded_at', 'file_size', 'content_type']
    
    def get_image_url(self, obj):
        """Get URL for the main image."""
        service = ReceiptImageService()
        return service.get_image_url(obj, thumbnail=False)
    
    def get_thumbnail_url(self, obj):
        """Get URL for the thumbnail image."""
        service = ReceiptImageService()
        return service.get_image_url(obj, thumbnail=True)


class ExpenseSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for expense management with comprehensive validation.
    """
    
    # Read-only fields
    owner = serializers.StringRelatedField(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    is_recent = serializers.ReadOnlyField()
    age_in_days = serializers.ReadOnlyField()
    attachments = ExpenseAttachmentSerializer(many=True, read_only=True)
    attachment_count = serializers.SerializerMethodField()
    
    # File upload fields (write-only)
    receipt_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="List of receipt image files to upload"
    )
    
    class Meta:
        model = Expense
        fields = [
            'id', 'description', 'amount', 'date', 'category', 'category_display',
            'notes', 'is_reimbursable', 'is_recurring', 'receipt_image',
            'owner', 'created_at', 'updated_at', 'is_recent', 'age_in_days',
            'attachments', 'attachment_count', 'receipt_files'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
        
    def get_attachment_count(self, obj):
        """Get the number of attachments."""
        return obj.attachments.count()
    
    def validate_amount(self, value):
        """Validate expense amount with enhanced business rules."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
            
        if value > Decimal('99999999.99'):
            raise serializers.ValidationError("Amount is too large")
            
        return value
    
    def validate_date(self, value):
        """Validate expense date with business rules."""
        today = date.today()
        
        # Cannot be in the future
        if value > today:
            raise serializers.ValidationError("Expense date cannot be in the future")
            
        # Cannot be too far in the past (more than 10 years)
        max_past_date = today - timedelta(days=3650)  # ~10 years
        if value < max_past_date:
            raise serializers.ValidationError("Expense date is too far in the past")
            
        return value
    
    def validate(self, attrs):
        """Perform cross-field validation."""
        # Category-specific amount validation
        category = attrs.get('category')
        amount = attrs.get('amount')
        
        if category and amount:
            # Travel expenses over $10,000 need special approval
            if category == ExpenseCategory.TRAVEL and amount > Decimal('10000.00'):
                raise serializers.ValidationError({
                    'amount': 'Travel expenses over $10,000 require special approval'
                })
            
            # Meal expenses over $500 need justification
            if category == ExpenseCategory.MEALS and amount > Decimal('500.00'):
                notes = attrs.get('notes', '').strip()
                if not notes:
                    raise serializers.ValidationError({
                        'notes': 'Meal expenses over $500 require justification in notes'
                    })
            
            # Office supplies over $1000 should be categorized as equipment
            if (category == ExpenseCategory.OFFICE_SUPPLIES and 
                amount > Decimal('1000.00')):
                raise serializers.ValidationError({
                    'category': 'Expenses over $1000 should be categorized as Equipment'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create expense with receipt file handling."""
        receipt_files = validated_data.pop('receipt_files', [])
        
        # Create the expense
        expense = super().create(validated_data)
        
        # Handle receipt file uploads
        if receipt_files:
            try:
                service = ReceiptImageService()
                
                # Process each uploaded file
                for receipt_file in receipt_files:
                    # Read file content
                    file_content = receipt_file.read()
                    
                    # Save the receipt image
                    service.save_receipt_image(
                        expense=expense,
                        file_content=file_content,
                        original_filename=receipt_file.name
                    )
                    
            except Exception as e:
                # If file processing fails, delete the expense and re-raise
                expense.delete()
                raise serializers.ValidationError(f"Receipt processing failed: {str(e)}")
        
        return expense
    
    def update(self, instance, validated_data):
        """Update expense with optional new receipt files."""
        receipt_files = validated_data.pop('receipt_files', [])
        
        # Update the expense
        expense = super().update(instance, validated_data)
        
        # Handle new receipt file uploads
        if receipt_files:
            try:
                service = ReceiptImageService()
                
                # Process each uploaded file
                for receipt_file in receipt_files:
                    # Read file content
                    file_content = receipt_file.read()
                    
                    # Save the receipt image
                    service.save_receipt_image(
                        expense=expense,
                        file_content=file_content,
                        original_filename=receipt_file.name
                    )
                    
            except Exception as e:
                raise serializers.ValidationError(f"Receipt processing failed: {str(e)}")
        
        return expense


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for expense creation via API.
    """
    
    class Meta:
        model = Expense
        fields = [
            'description', 'amount', 'date', 'category',
            'notes', 'is_reimbursable', 'is_recurring'
        ]
    
    def validate_amount(self, value):
        """Validate expense amount."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value
    
    def validate_date(self, value):
        """Validate expense date."""
        today = date.today()
        if value > today:
            raise serializers.ValidationError("Expense date cannot be in the future")
        return value


class ExpenseListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for expense list views.
    """
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    attachment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Expense
        fields = [
            'id', 'description', 'amount', 'date', 'category', 'category_display',
            'is_reimbursable', 'is_recent', 'attachment_count', 'created_at'
        ]
    
    def get_attachment_count(self, obj):
        """Get the number of attachments efficiently."""
        # Use prefetch_related in the view to avoid N+1 queries
        return getattr(obj, 'attachment_count', obj.attachments.count())


class ReceiptUploadSerializer(serializers.Serializer):
    """
    Dedicated serializer for receipt file uploads.
    """
    
    expense_id = serializers.UUIDField(help_text="ID of the expense to attach receipts to")
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=5,  # Maximum 5 files per upload
        help_text="Receipt image files (max 5 files, 10MB each)"
    )
    
    def validate_expense_id(self, value):
        """Validate that the expense exists and user has access."""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
            
        try:
            expense = Expense.objects.get(id=value, owner=request.user)
            return value
        except Expense.DoesNotExist:
            raise serializers.ValidationError("Expense not found or access denied")
    
    def validate_files(self, files):
        """Validate uploaded files."""
        if len(files) > 5:
            raise serializers.ValidationError("Maximum 5 files allowed per upload")
            
        service = ReceiptImageService()
        
        for file in files:
            # Check file size
            if file.size > service.MAX_FILE_SIZE:
                size_mb = file.size / (1024 * 1024)
                raise serializers.ValidationError(
                    f"File '{file.name}' is too large: {size_mb:.1f}MB (max: 10MB)"
                )
            
            # Check file extension
            import os
            file_ext = os.path.splitext(file.name.lower())[1]
            if file_ext not in service.SUPPORTED_EXTENSIONS:
                raise serializers.ValidationError(
                    f"File '{file.name}' has unsupported format: {file_ext}"
                )
        
        return files
    
    def create(self, validated_data):
        """Process receipt uploads."""
        expense_id = validated_data['expense_id']
        files = validated_data['files']
        
        # Get the expense
        request = self.context.get('request')
        expense = Expense.objects.get(id=expense_id, owner=request.user)
        
        # Process files
        service = ReceiptImageService()
        attachments = []
        
        try:
            for file in files:
                file_content = file.read()
                attachment = service.save_receipt_image(
                    expense=expense,
                    file_content=file_content,
                    original_filename=file.name
                )
                attachments.append(attachment)
            
            return {
                'expense_id': expense_id,
                'uploaded_count': len(attachments),
                'attachments': attachments
            }
            
        except Exception as e:
            # Clean up any successfully uploaded files
            for attachment in attachments:
                try:
                    service.delete_receipt_image(attachment)
                    attachment.delete()
                except:
                    pass
            
            raise serializers.ValidationError(f"Upload failed: {str(e)}")


class ExpenseSummarySerializer(serializers.Serializer):
    """
    Serializer for expense summary and analytics data.
    """
    
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_count = serializers.IntegerField()
    average_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    category_breakdown = serializers.ListField(
        child=serializers.DictField()
    )
    
    monthly_trend = serializers.ListField(
        child=serializers.DictField()
    )
    
    period = serializers.DictField()