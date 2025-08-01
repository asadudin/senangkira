"""
Authentication serializers for SenangKira API.
Enhanced with custom JWT claims and security validation.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
import re

User = get_user_model()


class SenangKiraTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer with additional claims for SenangKira.
    Adds company information and tenant context to tokens.
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims for multi-tenant context
        token['tenant_id'] = str(user.id)
        token['company_name'] = user.company_name or ''
        token['email'] = user.email
        token['username'] = user.username
        
        return token
    
    def validate(self, attrs):
        """Enhanced validation with security checks."""
        data = super().validate(attrs)
        
        # Add user profile data to response
        user = self.user
        data.update({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'company_name': user.company_name,
            }
        })
        
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    Enhanced user registration serializer with comprehensive validation.
    """
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password_confirm', 'company_name')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'company_name': {'required': False}
        }
    
    def validate_email(self, value):
        """Validate email format and uniqueness."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        # Additional email format validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError("Enter a valid email address.")
        
        # Check uniqueness (case-insensitive)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value.lower()  # Store emails in lowercase
    
    def validate_username(self, value):
        """Validate username format and uniqueness."""
        if not value:
            raise serializers.ValidationError("Username is required.")
        
        # Username format validation
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, and underscores.")
        
        # Check uniqueness (case-insensitive)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        return value
    
    def validate_company_name(self, value):
        """Validate company name if provided."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Company name must be at least 2 characters long.")
        
        return value.strip() if value else None
        
    def validate(self, attrs):
        """Cross-field validation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords don't match"
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create user with proper password hashing."""
        validated_data.pop('password_confirm')
        
        # Ensure email is lowercase
        validated_data['email'] = validated_data['email'].lower()
        
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Enhanced user profile serializer with validation.
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'company_name', 'company_address', 'company_logo', 'date_joined', 'last_login')
        read_only_fields = ('id', 'email', 'date_joined', 'last_login')
    
    def validate_username(self, value):
        """Validate username on update."""
        if not value:
            raise serializers.ValidationError("Username is required.")
        
        # Username format validation
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, and underscores.")
        
        # Check uniqueness (excluding current user)
        user = self.instance
        if User.objects.filter(username__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        return value
    
    def validate_company_name(self, value):
        """Validate company name."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Company name must be at least 2 characters long.")
        
        return value.strip() if value else None
    
    def validate_company_address(self, value):
        """Validate company address."""
        if value and len(value.strip()) < 5:
            raise serializers.ValidationError("Company address must be at least 5 characters long.")
        
        return value.strip() if value else None


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords don't match"
            })
        return attrs


class UserLoginActivitySerializer(serializers.Serializer):
    """
    Serializer for user login activity tracking.
    """
    login_time = serializers.DateTimeField(read_only=True)
    ip_address = serializers.IPAddressField(read_only=True)
    user_agent = serializers.CharField(read_only=True)
    success = serializers.BooleanField(read_only=True)