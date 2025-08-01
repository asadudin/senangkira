"""
Enhanced Client serializers for SenangKira API with validation and multi-tenant support.
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    """
    Enhanced Client serializer with comprehensive validation and multi-tenant support.
    """
    display_contact = serializers.ReadOnlyField()
    full_address_display = serializers.ReadOnlyField()
    
    class Meta:
        model = Client
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'address',
            'company',
            'tax_id',
            'notes',
            'is_active',
            'display_contact',
            'full_address_display',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'display_contact', 'full_address_display']
    
    def validate_email(self, value):
        """Validate email field with multi-tenant uniqueness check."""
        if value:
            value = value.lower().strip()
            
            # Check for uniqueness within the same owner (multi-tenant)
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                owner = request.user
                
                # For update operations, exclude the current instance
                queryset = Client.objects.filter(owner=owner, email=value)
                if self.instance:
                    queryset = queryset.exclude(pk=self.instance.pk)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "A client with this email already exists in your account."
                    )
        
        return value
    
    def validate_phone(self, value):
        """Validate phone number format."""
        if value:
            value = value.strip()
            # The model validator will handle the detailed phone validation
        return value
    
    def validate_name(self, value):
        """Validate client name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Client name cannot be empty.")
        
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Client name must be at least 2 characters long.")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        # Ensure at least email or phone is provided
        email = attrs.get('email')
        phone = attrs.get('phone')
        
        if not email and not phone:
            raise serializers.ValidationError({
                'non_field_errors': ['Either email or phone number must be provided.']
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create client with owner assignment."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        try:
            return super().create(validated_data)
        except DjangoValidationError as e:
            # Convert Django validation errors to DRF format
            raise serializers.ValidationError({'non_field_errors': [str(e)]})
    
    def update(self, instance, validated_data):
        """Update client with validation."""
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as e:
            # Convert Django validation errors to DRF format
            raise serializers.ValidationError({'non_field_errors': [str(e)]})


class ClientListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for client list views.
    """
    display_contact = serializers.ReadOnlyField()
    
    class Meta:
        model = Client
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'company',
            'display_contact',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'display_contact', 'created_at', 'updated_at']


class ClientCreateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for client creation with enhanced validation.
    """
    
    class Meta:
        model = Client
        fields = [
            'name',
            'email',
            'phone',
            'address',
            'company',
            'tax_id',
            'notes',
            'is_active',
        ]
    
    def validate_email(self, value):
        """Validate email with uniqueness check for creation."""
        if value:
            value = value.lower().strip()
            
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                owner = request.user
                
                if Client.objects.filter(owner=owner, email=value).exists():
                    raise serializers.ValidationError(
                        "A client with this email already exists in your account."
                    )
        
        return value
    
    def validate_name(self, value):
        """Validate client name for creation."""
        if not value or not value.strip():
            raise serializers.ValidationError("Client name is required.")
        
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Client name must be at least 2 characters long.")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation for creation."""
        email = attrs.get('email')
        phone = attrs.get('phone')
        
        if not email and not phone:
            raise serializers.ValidationError({
                'non_field_errors': ['Either email or phone number must be provided.']
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create client with owner assignment."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        
        try:
            client = Client.objects.create(**validated_data)
            return client
        except DjangoValidationError as e:
            raise serializers.ValidationError({'non_field_errors': [str(e)]})


class ClientUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for client updates with partial validation.
    """
    
    class Meta:
        model = Client
        fields = [
            'name',
            'email',
            'phone',
            'address',
            'company',
            'tax_id',
            'notes',
            'is_active',
        ]
    
    def validate_email(self, value):
        """Validate email with uniqueness check for updates."""
        if value:
            value = value.lower().strip()
            
            request = self.context.get('request')
            if request and hasattr(request, 'user') and self.instance:
                owner = request.user
                
                # Exclude current instance from uniqueness check
                if Client.objects.filter(owner=owner, email=value).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError(
                        "A client with this email already exists in your account."
                    )
        
        return value
    
    def validate_name(self, value):
        """Validate client name for updates."""
        if value is not None:  # Allow partial updates
            if not value or not value.strip():
                raise serializers.ValidationError("Client name cannot be empty.")
            
            value = value.strip()
            if len(value) < 2:
                raise serializers.ValidationError("Client name must be at least 2 characters long.")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation for updates."""
        # Only validate if both fields are being updated
        if 'email' in attrs and 'phone' in attrs:
            email = attrs.get('email')
            phone = attrs.get('phone')
            
            if not email and not phone:
                raise serializers.ValidationError({
                    'non_field_errors': ['Either email or phone number must be provided.']
                })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update client with validation."""
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'non_field_errors': [str(e)]})