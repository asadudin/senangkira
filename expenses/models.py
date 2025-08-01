"""
Enhanced Expense models for SenangKira with comprehensive validation and business logic.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ExpenseCategory(models.TextChoices):
    """Standard expense categories for business expenses."""
    OFFICE_SUPPLIES = 'office_supplies', 'Office Supplies'
    TRAVEL = 'travel', 'Travel & Transportation'
    MEALS = 'meals', 'Meals & Entertainment'
    UTILITIES = 'utilities', 'Utilities'
    RENT = 'rent', 'Rent & Facilities'
    MARKETING = 'marketing', 'Marketing & Advertising'
    SOFTWARE = 'software', 'Software & Subscriptions'
    EQUIPMENT = 'equipment', 'Equipment & Hardware'
    PROFESSIONAL = 'professional', 'Professional Services'
    INSURANCE = 'insurance', 'Insurance'
    TAXES = 'taxes', 'Taxes & Fees'
    OTHER = 'other', 'Other'


class Expense(models.Model):
    """
    Enhanced Expense model for tracking business expenses with comprehensive validation.
    
    Features:
    - Multi-tenant data isolation
    - Comprehensive date and amount validation
    - Expense categorization
    - Receipt image handling
    - Business logic validation
    - Audit trail
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the expense"
    )
    
    description = models.CharField(
        max_length=500,
        help_text="Description of the expense"
    )
    
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01'), message="Expense amount must be positive"),
            MaxValueValidator(Decimal('99999999.99'), message="Expense amount too large")
        ],
        help_text="Expense amount (must be positive)"
    )
    
    date = models.DateField(
        help_text="Date when the expense occurred"
    )
    
    category = models.CharField(
        max_length=50,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER,
        help_text="Category of the expense"
    )
    
    receipt_image = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Path to receipt image file"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the expense"
    )
    
    is_reimbursable = models.BooleanField(
        default=True,
        help_text="Whether this expense is reimbursable"
    )
    
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this is a recurring expense"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the expense record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the expense record was last updated"
    )
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses',
        help_text="The user who owns this expense"
    )
    
    class Meta:
        db_table = 'expenses_expense'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['owner', 'date'], name='expenses_owner_date_idx'),
            models.Index(fields=['owner', 'category'], name='expenses_owner_category_idx'),
            models.Index(fields=['owner', 'amount'], name='expenses_owner_amount_idx'),
            models.Index(fields=['date'], name='expenses_date_idx'),
            models.Index(fields=['category'], name='expenses_category_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='expense_amount_positive'
            ),
        ]
    
    def __str__(self):
        return f"{self.description} - ${self.amount} ({self.date})"
    
    def clean(self):
        """Custom validation for the expense model."""
        super().clean()
        
        # Validate date is not in the future
        if self.date and self.date > date.today():
            raise ValidationError({
                'date': 'Expense date cannot be in the future.'
            })
        
        # Validate date is not too far in the past (e.g., more than 10 years)
        if self.date and self.date < date.today() - timedelta(days=3650):
            raise ValidationError({
                'date': 'Expense date cannot be more than 10 years in the past.'
            })
        
        # Validate amount is positive
        if self.amount and self.amount <= 0:
            raise ValidationError({
                'amount': 'Expense amount must be positive.'
            })
        
        # Validate description is not empty
        if not self.description or not self.description.strip():
            raise ValidationError({
                'description': 'Expense description cannot be empty.'
            })
        
        # Category-specific validation
        if self.category == ExpenseCategory.TRAVEL and self.amount > Decimal('10000.00'):
            raise ValidationError({
                'amount': 'Travel expenses over $10,000 require additional approval.'
            })
        
        if self.category == ExpenseCategory.MEALS and self.amount > Decimal('500.00'):
            raise ValidationError({
                'amount': 'Meal expenses over $500 require additional approval.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to run full validation."""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Log expense creation/update for audit trail
        action = 'updated' if self.pk else 'created'
        logger.info(
            f"Expense {action}: {self.id} | Owner: {self.owner.email} | "
            f"Amount: ${self.amount} | Category: {self.category} | Date: {self.date}"
        )
    
    @property
    def category_display(self):
        """Get the display name for the category."""
        return self.get_category_display()
    
    @property
    def is_recent(self):
        """Check if expense is from the last 30 days."""
        return self.date >= date.today() - timedelta(days=30)
    
    @property
    def age_in_days(self):
        """Get age of expense in days."""
        return (date.today() - self.date).days
    
    def get_absolute_url(self):
        """Get the absolute URL for this expense."""
        return f"/expenses/{self.id}/"
    
    @classmethod
    def get_total_for_period(cls, owner, start_date, end_date):
        """Get total expenses for a specific period and owner."""
        return cls.objects.filter(
            owner=owner,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @classmethod
    def get_monthly_total(cls, owner, year, month):
        """Get total expenses for a specific month."""
        from calendar import monthrange
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        return cls.get_total_for_period(owner, start_date, end_date)
    
    @classmethod
    def get_category_breakdown(cls, owner, start_date=None, end_date=None):
        """Get expense breakdown by category."""
        queryset = cls.objects.filter(owner=owner)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.values('category').annotate(
            total=models.Sum('amount'),
            count=models.Count('id')
        ).order_by('-total')


class ExpenseAttachment(models.Model):
    """
    Model for storing multiple attachments per expense (receipts, invoices, etc.).
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text="The expense this attachment belongs to"
    )
    
    file_path = models.CharField(
        max_length=500,
        help_text="Path to the attachment file"
    )
    
    file_name = models.CharField(
        max_length=255,
        help_text="Original name of the file"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="Size of the file in bytes"
    )
    
    content_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )
    
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the attachment was uploaded"
    )
    
    class Meta:
        db_table = 'expenses_attachment'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} for {self.expense}"
    
    @property
    def file_size_mb(self):
        """Get file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)
    
    def clean(self):
        """Validate attachment."""
        super().clean()
        
        # Validate file size (max 10MB)
        if self.file_size > 10 * 1024 * 1024:
            raise ValidationError({
                'file_size': 'File size cannot exceed 10MB.'
            })
        
        # Validate content type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain'
        ]
        
        if self.content_type not in allowed_types:
            raise ValidationError({
                'content_type': f'File type {self.content_type} is not allowed.'
            })