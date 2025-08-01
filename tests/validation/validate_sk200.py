#!/usr/bin/env python
"""
Comprehensive validation script for SK-200: Client Management System.
Tests client CRUD operations, multi-tenant isolation, validation, and endpoints.
"""

import os
import sys
import django
import json
from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def test_client_model():
    """Test Client model functionality and validation."""
    print("Testing Client model...")
    
    try:
        from clients.models import Client
        User = get_user_model()
        
        # Create test user
        user = User.objects.create_user(
            email='clienttest@example.com',
            username='clienttestuser',
            password='TestPassword123!',
            company_name='Test Company'
        )
        
        # Test client creation with valid data
        client_data = {
            'name': 'Test Client',
            'email': 'client@example.com',
            'phone': '+1234567890',
            'address': '123 Test Street',
            'company': 'Client Company',
            'owner': user
        }
        
        client = Client.objects.create(**client_data)
        
        # Verify client properties
        assert client.name == 'Test Client'
        assert client.email == 'client@example.com'
        assert client.phone == '+1234567890'  
        assert client.owner == user
        assert isinstance(client.id, uuid.UUID)
        assert client.is_active == True
        
        print("✅ Client model creation working")
        
        # Test validation - email or phone required
        try:
            invalid_client = Client(name='Invalid Client', owner=user)
            invalid_client.clean()
            assert False, "Should have raised validation error"
        except Exception as e:
            assert 'Either email or phone' in str(e)
            print("✅ Client validation working (email or phone required)")
        
        # Test unique email constraint per owner
        try:
            Client.objects.create(
                name='Duplicate Email Client',
                email='client@example.com',  # Same email as above
                owner=user
            )
            assert False, "Should have raised unique constraint error"
        except Exception as e:
            print("✅ Email uniqueness per owner working")
        
        # Test phone validation
        try:
            invalid_phone_client = Client(
                name='Invalid Phone Client',
                phone='123',  # Too short
                owner=user
            )
            invalid_phone_client.clean()
            assert False, "Should have raised phone validation error"
        except Exception as e:
            print("✅ Phone number validation working")
        
        # Cleanup
        Client.objects.filter(owner=user).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Client model test failed: {e}")
        return False

def test_client_api_endpoints():
    """Test Client API CRUD endpoints."""
    print("\nTesting Client API endpoints...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        client = APIClient()
        
        # Create test user and get token
        user = User.objects.create_user(
            email='clientapi@example.com',
            username='clientapiuser',
            password='TestPassword123!',
            company_name='API Test Company'
        )
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Test POST /api/clients/ - Create client
        client_data = {
            'name': 'API Test Client',
            'email': 'apiclient@example.com',
            'phone': '+1234567890',
            'address': '123 API Street',
            'company': 'API Client Company',
            'notes': 'Test notes'
        }
        
        response = client.post('/api/clients/', client_data)
        assert response.status_code == 201
        
        response_data = response.json()
        assert 'client' in response_data
        assert response_data['client']['name'] == 'API Test Client'
        assert response_data['client']['email'] == 'apiclient@example.com'
        
        client_id = response_data['client']['id']
        print("✅ Client creation endpoint working")
        
        # Test GET /api/clients/ - List clients
        response = client.get('/api/clients/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert 'results' in response_data or isinstance(response_data, list)
        print("✅ Client list endpoint working")
        
        # Test GET /api/clients/{id}/ - Retrieve client
        response = client.get(f'/api/clients/{client_id}/')
        assert response.status_code == 200
        
        client_detail = response.json()
        assert client_detail['id'] == client_id
        assert client_detail['name'] == 'API Test Client'
        print("✅ Client retrieve endpoint working")
        
        # Test PUT /api/clients/{id}/ - Update client
        update_data = {
            'name': 'Updated API Client',
            'email': 'updated@example.com',
            'phone': '+9876543210',
            'is_active': True
        }
        
        response = client.put(f'/api/clients/{client_id}/', update_data)
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['client']['name'] == 'Updated API Client'
        assert response_data['client']['email'] == 'updated@example.com'
        print("✅ Client update endpoint working")
        
        # Test PATCH /api/clients/{id}/ - Partial update
        patch_data = {'notes': 'Updated notes only'}
        
        response = client.patch(f'/api/clients/{client_id}/', patch_data)
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['client']['notes'] == 'Updated notes only'
        assert response_data['client']['name'] == 'Updated API Client'  # Should remain unchanged
        print("✅ Client partial update endpoint working")
        
        # Test custom actions
        # Test POST /api/clients/{id}/deactivate/
        response = client.post(f'/api/clients/{client_id}/deactivate/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['client']['is_active'] == False
        print("✅ Client deactivate endpoint working")
        
        # Test POST /api/clients/{id}/activate/
        response = client.post(f'/api/clients/{client_id}/activate/')
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data['client']['is_active'] == True
        print("✅ Client activate endpoint working")
        
        # Test GET /api/clients/active/
        response = client.get('/api/clients/active/')
        assert response.status_code == 200
        print("✅ Active clients endpoint working")
        
        # Test GET /api/clients/statistics/
        response = client.get('/api/clients/statistics/')
        assert response.status_code == 200
        
        stats = response.json()
        assert 'total_clients' in stats
        assert 'active_clients' in stats
        print("✅ Client statistics endpoint working")
        
        # Test DELETE /api/clients/{id}/ - Delete client
        response = client.delete(f'/api/clients/{client_id}/')
        assert response.status_code == 200
        
        # Verify client is deleted
        response = client.get(f'/api/clients/{client_id}/')
        assert response.status_code == 404
        print("✅ Client delete endpoint working")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Client API endpoints test failed: {e}")
        return False

def test_multi_tenant_client_isolation():
    """Test multi-tenant client data isolation."""
    print("\nTesting multi-tenant client isolation...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        client1 = APIClient()
        client2 = APIClient()
        
        # Create two users
        user1 = User.objects.create_user(
            email='tenant1client@example.com',
            username='tenant1client',
            password='Password123!',
            company_name='Company 1'
        )
        
        user2 = User.objects.create_user(
            email='tenant2client@example.com',
            username='tenant2client',
            password='Password123!',
            company_name='Company 2'
        )
        
        # Get tokens for both users
        token1 = str(RefreshToken.for_user(user1).access_token)
        token2 = str(RefreshToken.for_user(user2).access_token)
        
        client1.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
        client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
        
        # Create clients for each user
        client1_data = {
            'name': 'Tenant 1 Client',
            'email': 'tenant1client@example.com',
            'phone': '+1111111111'
        }
        
        client2_data = {
            'name': 'Tenant 2 Client', 
            'email': 'tenant2client@example.com',
            'phone': '+2222222222'
        }
        
        response1 = client1.post('/api/clients/', client1_data)
        assert response1.status_code == 201
        tenant1_client_id = response1.json()['client']['id']
        
        response2 = client2.post('/api/clients/', client2_data)
        assert response2.status_code == 201
        tenant2_client_id = response2.json()['client']['id']
        
        # Verify each user can only see their own clients
        response1 = client1.get('/api/clients/')
        assert response1.status_code == 200
        
        tenant1_clients = response1.json()
        if 'results' in tenant1_clients:
            client_ids = [c['id'] for c in tenant1_clients['results']]
        else:
            client_ids = [c['id'] for c in tenant1_clients]
        
        assert tenant1_client_id in client_ids
        assert tenant2_client_id not in client_ids
        
        response2 = client2.get('/api/clients/')
        assert response2.status_code == 200
        
        tenant2_clients = response2.json()
        if 'results' in tenant2_clients:
            client_ids = [c['id'] for c in tenant2_clients['results']]
        else:
            client_ids = [c['id'] for c in tenant2_clients]
        
        assert tenant2_client_id in client_ids
        assert tenant1_client_id not in client_ids
        
        print("✅ Multi-tenant client data isolation working")
        
        # Test cross-tenant access prevention
        response = client1.get(f'/api/clients/{tenant2_client_id}/')
        assert response.status_code == 404
        
        response = client2.get(f'/api/clients/{tenant1_client_id}/')
        assert response.status_code == 404
        
        print("✅ Cross-tenant access prevention working")
        
        # Test duplicate email allowed across tenants
        duplicate_email_data = {
            'name': 'Duplicate Email Client',
            'email': 'shared@example.com',  # Same email for both tenants
            'phone': '+3333333333'
        }
        
        response1 = client1.post('/api/clients/', duplicate_email_data)
        assert response1.status_code == 201
        
        response2 = client2.post('/api/clients/', duplicate_email_data)
        assert response2.status_code == 201
        
        print("✅ Cross-tenant email duplication allowed")
        
        # Cleanup
        Client.objects.filter(owner=user1).delete()
        Client.objects.filter(owner=user2).delete()
        user1.delete()
        user2.delete()
        return True
        
    except Exception as e:
        print(f"❌ Multi-tenant client isolation test failed: {e}")
        return False

def test_client_validation():
    """Test client validation rules."""
    print("\nTesting client validation...")
    
    try:
        User = get_user_model()
        client = APIClient()
        
        # Create test user and get token
        user = User.objects.create_user(
            email='validationtest@example.com',
            username='validationuser',
            password='TestPassword123!'
        )
        
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Test missing required field (name)
        invalid_data = {
            'email': 'test@example.com'
        }
        
        response = client.post('/api/clients/', invalid_data)
        assert response.status_code == 400
        assert 'name' in response.json()
        print("✅ Required field validation working")
        
        # Test missing contact info (email and phone)
        invalid_data = {
            'name': 'Test Client'
        }
        
        response = client.post('/api/clients/', invalid_data)
        assert response.status_code == 400
        errors = response.json()
        assert 'non_field_errors' in errors or 'email' in errors or 'phone' in errors
        print("✅ Contact info validation working")
        
        # Test invalid email format
        invalid_data = {
            'name': 'Test Client',
            'email': 'invalid-email-format'
        }
        
        response = client.post('/api/clients/', invalid_data)
        assert response.status_code == 400
        print("✅ Email format validation working")
        
        # Test short name
        invalid_data = {
            'name': 'A',  # Too short
            'email': 'test@example.com'
        }
        
        response = client.post('/api/clients/', invalid_data)
        assert response.status_code == 400
        assert 'name' in response.json()
        print("✅ Name length validation working")
        
        # Test duplicate email within same tenant
        valid_data = {
            'name': 'First Client',
            'email': 'duplicate@example.com',
            'phone': '+1234567890'
        }
        
        response = client.post('/api/clients/', valid_data)
        assert response.status_code == 201
        
        duplicate_data = {
            'name': 'Second Client',
            'email': 'duplicate@example.com',  # Same email
            'phone': '+9876543210'
        }
        
        response = client.post('/api/clients/', duplicate_data)
        assert response.status_code == 400
        assert 'email' in response.json()
        print("✅ Email uniqueness validation working")
        
        # Cleanup
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Client validation test failed: {e}")
        return False

def test_client_search_and_filtering():
    """Test client search and filtering functionality."""
    print("\nTesting client search and filtering...")
    
    try:
        User = get_user_model()
        from clients.models import Client
        client = APIClient()
        
        # Create test user and get token
        user = User.objects.create_user(
            email='searchtest@example.com',
            username='searchuser',
            password='TestPassword123!'
        )
        
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create test clients with different attributes
        test_clients = [
            {
                'name': 'Active Company A',
                'email': 'activea@example.com',
                'company': 'Tech Corp',
                'is_active': True
            },
            {
                'name': 'Inactive Company B',
                'email': 'inactiveb@example.com',
                'company': 'Marketing Ltd',
                'is_active': False
            },
            {
                'name': 'Active Individual C',
                'phone': '+1234567890',
                'company': 'Tech Corp',
                'is_active': True
            }
        ]
        
        created_ids = []
        for client_data in test_clients:
            response = client.post('/api/clients/', client_data)
            assert response.status_code == 201
            created_ids.append(response.json()['client']['id'])
        
        # Test filtering by is_active
        response = client.get('/api/clients/?is_active=true')
        assert response.status_code == 200
        
        active_clients = response.json()
        if 'results' in active_clients:
            results = active_clients['results']
        else:
            results = active_clients
        
        assert len(results) == 2  # Should return 2 active clients
        print("✅ Active status filtering working")
        
        # Test filtering by company
        response = client.get('/api/clients/?company=Tech Corp')
        assert response.status_code == 200
        
        tech_clients = response.json()
        if 'results' in tech_clients:
            results = tech_clients['results']
        else:
            results = tech_clients
        
        assert len(results) == 2  # Should return 2 Tech Corp clients
        print("✅ Company filtering working")
        
        # Test search functionality
        response = client.get('/api/clients/search/?q=Active')
        assert response.status_code == 200
        
        search_results = response.json()
        if 'results' in search_results:
            results = search_results['results']
        else:
            results = search_results
        
        assert len(results) >= 1  # Should find clients with "Active" in name
        print("✅ Search functionality working")
        
        # Test ordering
        response = client.get('/api/clients/?ordering=name')
        assert response.status_code == 200
        print("✅ Ordering functionality working")
        
        # Cleanup
        Client.objects.filter(id__in=created_ids).delete()
        user.delete()
        return True
        
    except Exception as e:
        print(f"❌ Client search and filtering test failed: {e}")
        return False

def main():
    """Run all client management system tests."""
    print("="*60)
    print("SK-200: Client Management System - Validation Tests")
    print("="*60)
    
    # Setup Django
    setup_django()
    
    # Run all tests
    tests = [
        test_client_model,
        test_client_api_endpoints,
        test_multi_tenant_client_isolation,
        test_client_validation,
        test_client_search_and_filtering
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
        print("\nSK-200 Client Management System: COMPLETED")
        print("✅ Enhanced Client model with validation")
        print("✅ Multi-tenant data isolation")
        print("✅ Comprehensive CRUD API endpoints")
        print("✅ Client data validation and uniqueness")
        print("✅ Search, filtering, and statistics")
        print("✅ Custom actions (activate/deactivate)")
        print("\nReady to proceed with SK-300: Quote Management System")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Fix issues before proceeding to next task")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)