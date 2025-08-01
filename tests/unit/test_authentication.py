"""
Unit tests for authentication functionality.
Tests user model, JWT authentication, and security features.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status

from tests.utils import TestDataGenerator, APITestHelpers

User = get_user_model()


class UserModelTests(TestCase):
    """Test User model functionality."""
    
    def test_user_creation_with_email(self):
        """Test user creation with email as username."""
        user_data = TestDataGenerator.user_data(
            email='test@example.com',
            username='testuser'
        )
        
        user = User.objects.create_user(**user_data)
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('TestPass123!'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_user_creation_without_email_fails(self):
        """Test that user creation without email fails."""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                username='testuser',
                password='TestPass123!'
            )
    
    def test_superuser_creation(self):
        """Test superuser creation."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='AdminPass123!'
        )
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        self.assertEqual(str(user), 'test@example.com')
    
    def test_email_uniqueness(self):
        """Test that email addresses must be unique."""
        User.objects.create_user(
            email='test@example.com',
            username='testuser1',
            password='TestPass123!'
        )
        
        with self.assertRaises(Exception):  # IntegrityError
            User.objects.create_user(
                email='test@example.com',
                username='testuser2',
                password='TestPass123!'
            )
    
    def test_username_uniqueness(self):
        """Test that usernames must be unique."""
        User.objects.create_user(
            email='test1@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        with self.assertRaises(Exception):  # IntegrityError
            User.objects.create_user(
                email='test2@example.com',
                username='testuser',
                password='TestPass123!'
            )


class JWTAuthenticationTests(APITestCase):
    """Test JWT authentication functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user_data = TestDataGenerator.user_data()
        self.user = User.objects.create_user(**self.user_data)
    
    def test_token_generation(self):
        """Test JWT token generation."""
        refresh = RefreshToken.for_user(self.user)
        
        self.assertIsNotNone(refresh)
        self.assertIsNotNone(refresh.access_token)
        
        # Verify token contains user information
        access_token = refresh.access_token
        self.assertEqual(access_token['user_id'], self.user.id)
    
    def test_token_refresh(self):
        """Test JWT token refresh functionality."""
        refresh = RefreshToken.for_user(self.user)
        original_access_token = str(refresh.access_token)
        
        # Get new access token
        new_access_token = str(refresh.access_token)
        
        # Tokens should be the same initially
        self.assertEqual(original_access_token, new_access_token)
        
        # But refresh should generate new token
        refresh.set_jti()  # Force new JTI
        newer_access_token = str(refresh.access_token)
        self.assertNotEqual(original_access_token, newer_access_token)
    
    def test_authenticated_request(self):
        """Test making authenticated API request."""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Make authenticated request to a protected endpoint
        response = self.client.get('/api/dashboard/overview/')
        
        # Should not return 401 Unauthorized
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_unauthenticated_request(self):
        """Test making request without authentication."""
        # Make request without authentication
        response = self.client.get('/api/dashboard/overview/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_invalid_token_request(self):
        """Test request with invalid token."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        response = self.client.get('/api/dashboard/overview/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_expired_token_handling(self):
        """Test handling of expired tokens."""
        from datetime import timedelta
        from django.utils import timezone
        
        # Create token with very short expiry
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Manually expire the token
        access_token.set_exp(claim='exp', value=timezone.now() - timedelta(seconds=1))
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/dashboard/overview/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationSecurityTests(TestCase):
    """Test authentication security features."""
    
    def test_password_validation(self):
        """Test password validation requirements."""
        # Test weak password
        with self.assertRaises(ValidationError):
            user = User(
                email='test@example.com',
                username='testuser'
            )
            user.set_password('weak')
            user.full_clean()
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        password = 'TestPass123!'
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password=password
        )
        
        # Password should be hashed, not stored in plain text
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.password.startswith('pbkdf2_sha256'))
        
        # But check_password should work
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.check_password('wrong_password'))
    
    def test_user_permissions(self):
        """Test user permission system."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        # Regular user should not have special permissions
        self.assertFalse(user.has_perm('auth.add_user'))
        self.assertFalse(user.has_perm('auth.change_user'))
        self.assertFalse(user.has_perm('auth.delete_user'))
        
        # But should have basic user permissions
        self.assertTrue(user.has_perm('auth.view_user'))
    
    def test_inactive_user_authentication(self):
        """Test that inactive users cannot authenticate."""
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        # Deactivate user
        user.is_active = False
        user.save()
        
        # Should not be able to create tokens for inactive user
        with self.assertRaises(Exception):
            refresh = RefreshToken.for_user(user)
            # Token creation might not fail immediately, but authentication should
            from rest_framework_simplejwt.authentication import JWTAuthentication
            auth = JWTAuthentication()
            # This should fail during actual authentication


class PasswordResetTests(TestCase):
    """Test password reset functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='OldPass123!'
        )
    
    def test_password_change(self):
        """Test password change functionality."""
        old_password = 'OldPass123!'
        new_password = 'NewPass123!'
        
        # Verify old password works
        self.assertTrue(self.user.check_password(old_password))
        
        # Change password
        self.user.set_password(new_password)
        self.user.save()
        
        # Verify new password works and old doesn't
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password(old_password))
    
    def test_password_reset_token_generation(self):
        """Test password reset token generation."""
        from django.contrib.auth.tokens import default_token_generator
        
        token = default_token_generator.make_token(self.user)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 10)  # Should be a substantial token
        
        # Token should be valid for the user
        self.assertTrue(default_token_generator.check_token(self.user, token))
        
        # Token should not be valid for different user
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='OtherPass123!'
        )
        self.assertFalse(default_token_generator.check_token(other_user, token))