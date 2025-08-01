"""
Authentication models for SenangKira.
Custom User model with company profile fields to match schema.sql.
"""

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Maps to auth_user table in schema.sql with company profile fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=254)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    company_address = models.TextField(blank=True, null=True)
    company_logo = models.CharField(max_length=255, blank=True, null=True)  # File path
    
    # Override username field to use email as primary identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # Keep username as required for Django admin
    
    class Meta:
        db_table = 'auth_user'  # Match schema.sql table name
        
    def __str__(self):
        return self.email