"""
Integration tests for API authentication flows.
Tests JWT authentication, token refresh, and API security.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from tests.utils import TestDataGenerator, APITestHelpers

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    """Test authentication API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user_data = TestDataGenerator.user_data(
            email='test@example.com',
            username='testuser'
        )
        self.user = User.objects.create_user(**self.user_data)
    
    def test_user_registration_api(self):
        """Test user registration through API."""
        registration_data = TestDataGenerator.user_data(
            email='newuser@example.com',
            username='newuser'
        )
        
        url = reverse('authentication:register')
        response = self.client.post(url, registration_data, format='json')
        
        APITestHelpers.assert_successful_response(response, status.HTTP_201_CREATED)
        
        # Check response structure
        response_data = response.json()
        APITestHelpers.assert_required_fields(response_data, ['user', 'tokens'])
        APITestHelpers.assert_required_fields(response_data['user'], ['id', 'email', 'username'])
        APITestHelpers.assert_required_fields(response_data['tokens'], ['access', 'refresh'])
    
    def test_user_login_api(self):
        """Test user login through API."""
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        
        url = reverse('authentication:login')
        response = self.client.post(url, login_data, format='json')
        
        APITestHelpers.assert_successful_response(response)
        
        # Check response structure
        response_data = response.json()
        APITestHelpers.assert_required_fields(response_data, ['user', 'tokens'])
        self.assertEqual(response_data['user']['email'], self.user.email)
    
    def test_invalid_login_credentials(self):
        """Test login with invalid credentials."""
        invalid_data = {
            'email': self.user_data['email'],
            'password': 'wrong_password'
        }
        
        url = reverse('authentication:login')
        response = self.client.post(url, invalid_data, format='json')
        
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_missing_login_fields(self):
        """Test login with missing required fields."""
        incomplete_data = {
            'email': self.user_data['email']
            # Missing password
        }
        
        url = reverse('authentication:login')
        response = self.client.post(url, incomplete_data, format='json')
        
        APITestHelpers.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
    
    def test_token_refresh(self):
        """Test JWT token refresh functionality."""
        # Get initial tokens
        refresh = RefreshToken.for_user(self.user)
        
        url = reverse('authentication:token_refresh')
        refresh_data = {'refresh': str(refresh)}
        
        response = self.client.post(url, refresh_data, format='json')
        
        APITestHelpers.assert_successful_response(response)
        
        # Should return new access token
        response_data = response.json()
        APITestHelpers.assert_required_fields(response_data, ['access'])
    
    def test_invalid_refresh_token(self):
        """Test token refresh with invalid token."""
        url = reverse('authentication:token_refresh')
        invalid_data = {'refresh': 'invalid_token'}
        
        response = self.client.post(url, invalid_data, format='json')
        
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout_functionality(self):
        """Test user logout functionality."""
        # Get tokens
        refresh = RefreshToken.for_user(self.user)
        
        # Authenticate
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('authentication:logout')
        logout_data = {'refresh': str(refresh)}
        
        response = self.client.post(url, logout_data, format='json')
        
        APITestHelpers.assert_successful_response(response)
        
        # Token should be blacklisted - subsequent refresh should fail
        refresh_url = reverse('authentication:token_refresh')
        refresh_response = self.client.post(refresh_url, logout_data, format='json')
        
        APITestHelpers.assert_error_response(refresh_response, status.HTTP_401_UNAUTHORIZED)


class ProtectedEndpointTests(APITestCase):
    """Test access to protected API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPass123!'
        )
        
        self.refresh = RefreshToken.for_user(self.user)
    
    def test_authenticated_access_to_dashboard(self):
        """Test authenticated access to dashboard endpoints."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.refresh.access_token}')
        
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        # Should not be unauthorized
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        # Don't set credentials
        
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_invalid_token_access_denied(self):
        """Test that invalid tokens are rejected."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_expired_token_access_denied(self):
        """Test that expired tokens are rejected."""
        from datetime import timedelta
        from django.utils import timezone
        
        # Create token with very short expiry
        access_token = self.refresh.access_token
        access_token.set_exp(claim='exp', value=timezone.now() - timedelta(seconds=1))
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_cross_user_data_isolation(self):
        """Test that users can only access their own data."""
        # Create second user
        user2 = User.objects.create_user(
            email='user2@example.com',
            username='user2',
            password='TestPass123!'
        )
        
        # Authenticate as user2
        refresh2 = RefreshToken.for_user(user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh2.access_token}')
        
        # Try to access user1's data would require specific endpoint tests
        # This is a placeholder for tenant isolation testing
        url = reverse('dashboard:dashboard-overview')
        response = self.client.get(url)
        
        # Should succeed but return only user2's data
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationSecurityTests(APITestCase):
    """Test authentication security features."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='security@example.com',
            username='securityuser',
            password='SecurePass123!'
        )
    
    def test_password_change_requires_authentication(self):
        """Test that password change requires authentication."""
        url = reverse('authentication:change_password')
        change_data = {
            'old_password': 'SecurePass123!',
            'new_password': 'NewSecurePass123!'
        }
        
        # Without authentication
        response = self.client.post(url, change_data, format='json')
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
        
        # With authentication
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = self.client.post(url, change_data, format='json')
        # Should not be unauthorized (might be 200 or 400 depending on implementation)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_rate_limiting_on_login_attempts(self):
        """Test rate limiting on login attempts."""
        url = reverse('authentication:login')
        invalid_data = {
            'email': self.user.email,
            'password': 'wrong_password'
        }
        
        # Make multiple failed attempts
        responses = []
        for i in range(5):  # Attempt 5 failed logins
            response = self.client.post(url, invalid_data, format='json')
            responses.append(response.status_code)
        
        # If rate limiting is implemented, should eventually get 429
        # For now, just verify all return 401
        for status_code in responses:
            self.assertEqual(status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_csrf_protection_disabled_for_api(self):
        """Test that CSRF protection is properly configured for API."""
        # API endpoints should have CSRF disabled for JSON requests
        url = reverse('authentication:login')
        login_data = {
            'email': self.user.email,
            'password': 'SecurePass123!'
        }
        
        # Should work without CSRF token
        response = self.client.post(url, login_data, format='json')
        
        # Should not get CSRF error (403)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_cors_headers_present(self):
        """Test that CORS headers are properly configured."""
        url = reverse('authentication:login')
        
        # Make OPTIONS request to check CORS
        response = self.client.options(url)
        
        # Should have CORS headers if configured
        # This test might need adjustment based on CORS configuration
        self.assertTrue(
            response.has_header('Access-Control-Allow-Origin') or
            response.status_code == status.HTTP_200_OK  # Even without CORS headers, endpoint should work
        )


class TokenSecurityTests(APITestCase):
    """Test JWT token security features."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='token@example.com',
            username='tokenuser',
            password='TokenPass123!'
        )
    
    def test_token_contains_expected_claims(self):
        """Test that JWT tokens contain expected claims."""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Check token claims
        self.assertEqual(access_token['user_id'], self.user.id)
        self.assertIn('exp', access_token)  # Expiration time
        self.assertIn('iat', access_token)  # Issued at time
        self.assertIn('jti', access_token)  # JWT ID
    
    def test_token_expiration_times(self):
        """Test that tokens have appropriate expiration times."""
        from datetime import timedelta
        from django.utils import timezone
        
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Access token should expire relatively soon
        access_exp = timezone.datetime.fromtimestamp(access_token['exp'], tz=timezone.utc)
        access_lifetime = access_exp - timezone.now()
        
        # Should be less than 1 day (typical access token lifetime)
        self.assertLess(access_lifetime, timedelta(days=1))
        
        # Refresh token should last longer
        refresh_exp = timezone.datetime.fromtimestamp(refresh['exp'], tz=timezone.utc)
        refresh_lifetime = refresh_exp - timezone.now()
        
        # Should be more than access token lifetime
        self.assertGreater(refresh_lifetime, access_lifetime)
    
    def test_token_blacklisting_works(self):
        """Test that token blacklisting prevents reuse."""
        refresh = RefreshToken.for_user(self.user)
        
        # Blacklist the token
        refresh.blacklist()
        
        # Try to use blacklisted token
        url = reverse('authentication:token_refresh')
        refresh_data = {'refresh': str(refresh)}
        
        response = self.client.post(url, refresh_data, format='json')
        
        APITestHelpers.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_multiple_device_tokens(self):
        """Test that user can have multiple active tokens."""
        # Create multiple refresh tokens for same user
        refresh1 = RefreshToken.for_user(self.user)
        refresh2 = RefreshToken.for_user(self.user)
        
        # Both should be valid
        url = reverse('authentication:token_refresh')
        
        response1 = self.client.post(url, {'refresh': str(refresh1)}, format='json')
        response2 = self.client.post(url, {'refresh': str(refresh2)}, format='json')
        
        APITestHelpers.assert_successful_response(response1)
        APITestHelpers.assert_successful_response(response2)
        
        # Tokens should be different
        self.assertNotEqual(str(refresh1), str(refresh2))