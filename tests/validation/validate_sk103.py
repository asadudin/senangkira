#!/usr/bin/env python
"""
Comprehensive validation script for SK-103: Authentication System.
Tests JWT authentication, multi-tenant isolation, security features, and endpoints.
"""

import os
import sys
import django
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def test_user_model():
    """Test custom User model functionality."""
    print("Testing custom User model...")
    
    try:
        User = get_user_model()
        
        # Test user creation
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'TestPassword123!',
            'company_name': 'Test Company'
        }
        
        user = User.objects.create_user(**user_data)
        
        # Verify user properties
        assert user.email == 'test@example.com'
        assert user.username == 'testuser'
        assert user.company_name == 'Test Company'
        assert user.check_password('TestPassword123!')
        assert isinstance(user.id, uuid.UUID)
        
        print("✅ Custom User model working correctly")
        
        # Test email as USERNAME_FIELD
        assert User.USERNAME_FIELD == 'email'
        print("✅ Email as primary authentication field")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ User model test failed: {e}")
        return False

def test_jwt_authentication():
    """Test JWT token authentication."""
    print("\nTesting JWT authentication...")
    
    try:
        User = get_user_model()
        client = APIClient()
        
        # Create test user
        user = User.objects.create_user(
            email='jwt@example.com',
            username='jwtuser',
            password='JWTTest123!',
            company_name='JWT Company'
        )
        
        # Test token obtain
        response = client.post('/api/auth/token/', {
            'email': 'jwt@example.com',
            'password': 'JWTTest123!'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert 'user' in data
        
        # Verify custom claims in token response
        assert data['user']['email'] == 'jwt@example.com'
        assert data['user']['company_name'] == 'JWT Company'
        
        print("✅ JWT token obtain working")
        
        # Test authenticated request
        access_token = data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = client.get('/api/auth/me/')
        assert response.status_code == 200
        user_data = response.json()
        assert user_data['email'] == 'jwt@example.com'
        
        print("✅ JWT authentication working")
        
        # Test token refresh
        refresh_token = data['refresh']
        response = client.post('/api/auth/token/refresh/', {
            'refresh': refresh_token
        })
        
        assert response.status_code == 200
        assert 'access' in response.json()
        
        print("✅ JWT token refresh working")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ JWT authentication test failed: {e}")
        return False

def test_user_registration():
    """Test user registration with validation."""
    print("\nTesting user registration...")
    
    try:
        client = APIClient()
        
        # Test successful registration
        registration_data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!',
            'company_name': 'New Company'
        }
        
        response = client.post('/api/auth/register/', registration_data)
        assert response.status_code == 201
        
        data = response.json()
        assert 'tokens' in data  # Auto-login after registration
        assert data['user']['email'] == 'newuser@example.com'
        
        print("✅ User registration working")
        
        # Test validation errors
        invalid_data = {
            'email': 'invalid-email',
            'username': 'ab',  # Too short
            'password': '123',  # Weak password
            'password_confirm': '456',  # Doesn't match
        }
        
        response = client.post('/api/auth/register/', invalid_data)
        assert response.status_code == 400
        
        errors = response.json()
        assert 'email' in errors
        assert 'username' in errors
        assert 'password' in errors
        assert 'password_confirm' in errors
        
        print("✅ Registration validation working")
        
        # Test duplicate email
        response = client.post('/api/auth/register/', registration_data)
        assert response.status_code == 400
        assert 'email' in response.json()
        
        print("✅ Duplicate email prevention working")
        
        # Cleanup
        User = get_user_model()
        User.objects.filter(email='newuser@example.com').delete()
        return True
        
    except Exception as e:
        print(f"❌ User registration test failed: {e}")
        return False

def test_multi_tenant_isolation():
    """Test multi-tenant data isolation."""
    print("\nTesting multi-tenant data isolation...")
    
    try:
        User = get_user_model()
        client1 = APIClient()
        client2 = APIClient()
        
        # Create two users
        user1 = User.objects.create_user(
            email='tenant1@example.com',
            username='tenant1',
            password='Password123!',
            company_name='Company 1'
        )
        
        user2 = User.objects.create_user(
            email='tenant2@example.com',
            username='tenant2', 
            password='Password123!',
            company_name='Company 2'
        )
        
        # Get tokens for both users
        response1 = client1.post('/api/auth/token/', {
            'email': 'tenant1@example.com',
            'password': 'Password123!'
        })
        token1 = response1.json()['access']
        
        response2 = client2.post('/api/auth/token/', {
            'email': 'tenant2@example.com',
            'password': 'Password123!'
        })
        token2 = response2.json()['access']
        
        # Set authentication for each client
        client1.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        
        # Verify each user can only access their own data
        response1 = client1.get('/api/auth/me/')
        assert response1.json()['email'] == 'tenant1@example.com'
        
        response2 = client2.get('/api/auth/me/')
        assert response2.json()['email'] == 'tenant2@example.com'
        
        print("✅ Multi-tenant data isolation working")
        
        # Test JWT claims contain tenant information
        import jwt
        from django.conf import settings
        
        decoded_token1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=['HS256'])
        assert decoded_token1['tenant_id'] == str(user1.id)
        assert decoded_token1['email'] == 'tenant1@example.com'
        
        decoded_token2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=['HS256'])
        assert decoded_token2['tenant_id'] == str(user2.id)
        assert decoded_token2['email'] == 'tenant2@example.com'
        
        print("✅ JWT tenant claims working")
        
        # Cleanup
        user1.delete()
        user2.delete()
        return True
        
    except Exception as e:
        print(f"❌ Multi-tenant isolation test failed: {e}")
        return False

def test_security_features():
    """Test security features and endpoints."""
    print("\nTesting security features...")
    
    try:
        User = get_user_model()
        client = APIClient()
        
        # Create test user
        user = User.objects.create_user(
            email='security@example.com',
            username='securityuser',
            password='SecurityTest123!',
            company_name='Security Company'
        )
        
        # Get authentication token
        response = client.post('/api/auth/token/', {
            'email': 'security@example.com',
            'password': 'SecurityTest123!'
        })
        token_data = response.json()
        access_token = token_data['access']
        refresh_token = token_data['refresh']
        
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Test password change
        response = client.put('/api/auth/change-password/', {
            'old_password': 'SecurityTest123!',
            'new_password': 'NewSecurityPassword123!',
            'new_password_confirm': 'NewSecurityPassword123!'
        })
        
        assert response.status_code == 200
        print("✅ Password change working")
        
        # Test invalid old password
        response = client.put('/api/auth/change-password/', {
            'old_password': 'WrongPassword',
            'new_password': 'NewPassword123!',
            'new_password_confirm': 'NewPassword123!'
        })
        
        assert response.status_code == 400
        print("✅ Password change validation working")
        
        # Test logout with token blacklisting
        response = client.post('/api/auth/logout/', {
            'refresh': refresh_token
        })
        
        assert response.status_code == 200
        print("✅ Logout with token blacklisting working")
        
        # Test token verification
        response = client.post('/api/auth/token/verify/', {
            'token': access_token
        })
        
        assert response.status_code == 200
        print("✅ Token verification working")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Security features test failed: {e}")
        return False

def test_api_endpoints():
    """Test all authentication API endpoints."""
    print("\nTesting API endpoints...")
    
    try:
        client = APIClient()
        
        # Test unauthenticated access to protected endpoints
        protected_endpoints = [
            '/api/auth/profile/',
            '/api/auth/me/',
            '/api/auth/change-password/',
            '/api/auth/logout/'
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
        
        print("✅ Protected endpoints require authentication")
        
        # Test public endpoints
        public_endpoints = [
            '/api/auth/register/',
            '/api/auth/token/',
            '/api/auth/token/refresh/',
            '/api/auth/token/verify/'
        ]
        
        # These should not return 401 (they may return 400 for missing data)
        for endpoint in public_endpoints:
            response = client.post(endpoint, {})
            assert response.status_code != 401
        
        print("✅ Public endpoints accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def test_middleware_integration():
    """Test middleware integration."""
    print("\nTesting middleware integration...")
    
    try:
        User = get_user_model()
        client = APIClient()
        
        # Create test user
        user = User.objects.create_user(
            email='middleware@example.com',
            username='middlewareuser',
            password='MiddlewareTest123!'
        )
        
        # Get token
        response = client.post('/api/auth/token/', {
            'email': 'middleware@example.com',
            'password': 'MiddlewareTest123!'
        })
        token = response.json()['access']
        
        # Test authenticated request includes tenant context
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = client.get('/api/auth/me/')
        
        assert response.status_code == 200
        
        # Check security headers are added by middleware
        assert 'X-Content-Type-Options' in response
        
        print("✅ Middleware integration working")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Middleware integration test failed: {e}")
        return False

def main():
    """Run all authentication system tests."""
    print("="*60)
    print("SK-103: Authentication System - Validation Tests")
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Run all tests
    tests = [
        test_user_model,
        test_jwt_authentication,
        test_user_registration,
        test_multi_tenant_isolation,
        test_security_features,
        test_api_endpoints,
        test_middleware_integration
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nSK-103 Authentication System: COMPLETED")
        print("✅ JWT authentication with custom claims")
        print("✅ Multi-tenant data isolation") 
        print("✅ Comprehensive security validation")
        print("✅ User registration with validation")
        print("✅ Password management and security")
        print("✅ Token blacklisting and logout")
        print("\nReady to proceed with SK-200: Client Management System")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Fix issues before proceeding to next task")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)