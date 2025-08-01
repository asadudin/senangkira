"""
Enhanced Client models for SenangKira with validation and multi-tenant support.
Maps to clients_client table in schema.sql.
"""

import uuid
import re
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


def validate_phone_number(value):
    """Validate phone number format (international format)."""
    if value:
        # Remove all non-digit characters
        digits_only = re.sub(r'[^\d]', '', value)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValidationError('Phone number must be between 10 and 15 digits.')


class Client(models.Model):
    """
    Enhanced Client model with validation and multi-tenant support.
    Maps to clients_client table in schema.sql.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Client's full name or company name"
    )
    email = models.EmailField(
        max_length=254, 
        blank=True, 
        null=True,
        help_text="Client's email address"
    )
    phone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        validators=[validate_phone_number],
        help_text="Client's phone number (international format)"
    )
    address = models.TextField(
        blank=True, 
        null=True,
        help_text="Client's full address"
    )
    company = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Client's company name (if different from name)"
    )
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Client's tax ID or business registration number"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the client"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this client is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='clients',
        help_text="The user who owns this client record"
    )
    
    class Meta:
        db_table = 'clients_client'  # Match schema.sql table name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'name']),
            models.Index(fields=['owner', 'email']),
            models.Index(fields=['owner', 'is_active']),
        ]
        constraints = [
            # Ensure email uniqueness per owner (multi-tenant)
            models.UniqueConstraint(
                fields=['owner', 'email'],
                condition=models.Q(email__isnull=False) & ~models.Q(email=''),
                name='unique_client_email_per_owner'
            )
        ]
        
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        # Ensure at least email or phone is provided
        if not self.email and not self.phone:
            raise ValidationError('Either email or phone number must be provided.')
        
        # Normalize email to lowercase
        if self.email:
            self.email = self.email.lower().strip()
        
        # Clean phone number
        if self.phone:
            self.phone = self.phone.strip()
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name} ({self.email or self.phone})"
    
    @property
    def display_contact(self):
        """Return primary contact method for display."""
        return self.email or self.phone or "No contact info"
    
    @property
    def full_address_display(self):
        """Return formatted address for display."""
        if self.address:
            return self.address.replace('\n', ', ')
        return "No address provided"