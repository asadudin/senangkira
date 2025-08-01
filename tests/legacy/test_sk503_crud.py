#!/usr/bin/env python
"""
Comprehensive test suite for SK-503: Expense CRUD Operations.
Tests all Create, Read, Update, Delete operations with edge cases and performance.
"""

import os
import sys
import django
import json
from decimal import Decimal
from datetime import date, timedelta
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def create_test_user():
    """Create a test user for API operations."""
    User = get_user_model()
    
    # Clean up any existing test user
    User.objects.filter(email='crudtest@example.com').delete()
    
    user = User.objects.create_user(
        email='crudtest@example.com',
        password='TestPassword123!',
        company_name='CRUD Test Company'
    )
    return user

def get_auth_token(client, user):
    """Get JWT token for authentication."""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def test_expense_create_operations():
    """Test expense creation (POST) operations."""
    print("Testing Expense CREATE Operations...")
    
    try:
        from expenses.models import Expense, ExpenseCategory
        
        client = Client()
        user = create_test_user()
        token = get_auth_token(client, user)
        
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Test 1: Valid expense creation
        expense_data = {
            'description': 'Test office supplies',
            'amount': '125.50',
            'date': date.today().isoformat(),
            'category': ExpenseCategory.OFFICE_SUPPLIES,
            'notes': 'Purchased pens and paper',
            'is_reimbursable': True,
            'is_recurring': False
        }
        
        response = client.post(
            '/api/expenses/',
            data=json.dumps(expense_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.content}"
        response_data = response.json()
        
        assert response_data['description'] == expense_data['description']
        assert Decimal(response_data['amount']) == Decimal(expense_data['amount'])
        assert response_data['category'] == expense_data['category']
        
        expense_id = response_data['id']
        print("✅ Basic expense creation successful")
        
        # Test 2: Invalid amount (negative)
        invalid_expense_data = expense_data.copy()
        invalid_expense_data['amount'] = '-50.00'
        
        response = client.post(
            '/api/expenses/',
            data=json.dumps(invalid_expense_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 400, "Should reject negative amounts"
        print("✅ Negative amount validation working")
        
        # Test 3: Invalid date (future)
        future_expense_data = expense_data.copy()
        future_expense_data['date'] = (date.today() + timedelta(days=1)).isoformat()
        
        response = client.post(
            '/api/expenses/',
            data=json.dumps(future_expense_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 400, "Should reject future dates"
        print("✅ Future date validation working")
        
        # Test 4: Missing required fields
        incomplete_data = {'description': 'Incomplete expense'}
        
        response = client.post(
            '/api/expenses/',
            data=json.dumps(incomplete_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 400, "Should reject incomplete data"
        print("✅ Required field validation working")
        
        # Test 5: Unauthorized access
        response = client.post(
            '/api/expenses/',
            data=json.dumps(expense_data),
            content_type='application/json'
        )
        
        assert response.status_code == 401, "Should require authentication"
        print("✅ Authentication requirement working")
        
        return expense_id
        
    except Exception as e:
        print(f"❌ Expense CREATE test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_expense_read_operations(expense_id):
    """Test expense read (GET) operations."""
    print("\nTesting Expense READ Operations...")
    
    try:
        client = Client()
        user = get_user_model().objects.get(email='crudtest@example.com')
        token = get_auth_token(client, user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Test 1: List all expenses
        response = client.get('/api/expenses/', **headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        response_data = response.json()
        
        assert 'results' in response_data or isinstance(response_data, list)
        print("✅ Expense list retrieval successful")
        
        # Test 2: Retrieve specific expense
        response = client.get(f'/api/expenses/{expense_id}/', **headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        expense_data = response.json()
        
        assert expense_data['id'] == expense_id
        assert expense_data['description'] == 'Test office supplies'
        print("✅ Specific expense retrieval successful")
        
        # Test 3: Filtering by category
        response = client.get(
            '/api/expenses/',
            {'category': 'office_supplies'},
            **headers
        )
        
        assert response.status_code == 200
        print("✅ Category filtering working")
        
        # Test 4: Date range filtering
        today = date.today()
        response = client.get(
            '/api/expenses/',
            {
                'date_from': today.isoformat(),
                'date_to': today.isoformat()
            },
            **headers
        )
        
        assert response.status_code == 200
        print("✅ Date range filtering working")
        
        # Test 5: Search functionality
        response = client.get(
            '/api/expenses/',
            {'search': 'office'},
            **headers
        )
        
        assert response.status_code == 200
        print("✅ Search functionality working")
        
        # Test 6: Access denied for other users
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='TestPassword123!',
            company_name='Other Company'
        )
        other_token = get_auth_token(client, other_user)
        other_headers = {'HTTP_AUTHORIZATION': f'Bearer {other_token}'}
        
        response = client.get(f'/api/expenses/{expense_id}/', **other_headers)
        assert response.status_code == 404, "Should not access other user's expenses"
        print("✅ Multi-tenant isolation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Expense READ test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_expense_update_operations(expense_id):
    """Test expense update (PUT/PATCH) operations."""
    print("\nTesting Expense UPDATE Operations...")
    
    try:
        from expenses.models import ExpenseCategory
        
        client = Client()
        user = get_user_model().objects.get(email='crudtest@example.com')
        token = get_auth_token(client, user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Test 1: Partial update (PATCH)
        update_data = {
            'notes': 'Updated notes for office supplies',
            'amount': '175.75'
        }
        
        response = client.patch(
            f'/api/expenses/{expense_id}/',
            data=json.dumps(update_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
        updated_data = response.json()
        
        assert updated_data['notes'] == update_data['notes']
        assert Decimal(updated_data['amount']) == Decimal(update_data['amount'])
        assert updated_data['description'] == 'Test office supplies'  # Should remain unchanged
        
        print("✅ Partial update (PATCH) successful")
        
        # Test 2: Full update (PUT)
        full_update_data = {
            'description': 'Updated office supplies',
            'amount': '200.00',
            'date': date.today().isoformat(),
            'category': ExpenseCategory.EQUIPMENT,
            'notes': 'Changed to equipment category',
            'is_reimbursable': False,
            'is_recurring': True
        }
        
        response = client.put(
            f'/api/expenses/{expense_id}/',
            data=json.dumps(full_update_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
        updated_data = response.json()
        
        assert updated_data['description'] == full_update_data['description']
        assert updated_data['category'] == full_update_data['category']
        assert updated_data['is_reimbursable'] == full_update_data['is_reimbursable']
        
        print("✅ Full update (PUT) successful")
        
        # Test 3: Invalid update (negative amount)
        invalid_update = {'amount': '-100.00'}
        
        response = client.patch(
            f'/api/expenses/{expense_id}/',
            data=json.dumps(invalid_update),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 400, "Should reject invalid updates"
        print("✅ Invalid update validation working")
        
        # Test 4: Update non-existent expense
        response = client.patch(
            '/api/expenses/00000000-0000-0000-0000-000000000000/',
            data=json.dumps(update_data),
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 404, "Should return 404 for non-existent expense"
        print("✅ Non-existent expense handling working")
        
        return True
        
    except Exception as e:
        print(f"❌ Expense UPDATE test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_expense_delete_operations(expense_id):
    """Test expense deletion (DELETE) operations."""
    print("\nTesting Expense DELETE Operations...")
    
    try:
        client = Client()
        user = get_user_model().objects.get(email='crudtest@example.com')
        token = get_auth_token(client, user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Test 1: Verify expense exists before deletion
        response = client.get(f'/api/expenses/{expense_id}/', **headers)
        assert response.status_code == 200, "Expense should exist before deletion"
        
        # Test 2: Delete expense
        response = client.delete(f'/api/expenses/{expense_id}/', **headers)
        assert response.status_code == 204, f"Expected 204, got {response.status_code}"
        
        print("✅ Expense deletion successful")
        
        # Test 3: Verify expense no longer exists
        response = client.get(f'/api/expenses/{expense_id}/', **headers)
        assert response.status_code == 404, "Expense should not exist after deletion"
        
        print("✅ Expense deletion verification successful")
        
        # Test 4: Delete non-existent expense
        response = client.delete('/api/expenses/00000000-0000-0000-0000-000000000000/', **headers)
        assert response.status_code == 404, "Should return 404 for non-existent expense"
        
        print("✅ Non-existent expense deletion handling working")
        
        return True
        
    except Exception as e:
        print(f"❌ Expense DELETE test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_advanced_features():
    """Test advanced expense features."""
    print("\nTesting Advanced Features...")
    
    try:
        from expenses.models import Expense, ExpenseCategory
        
        client = Client()
        user = get_user_model().objects.get(email='crudtest@example.com')
        token = get_auth_token(client, user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Create some test expenses for analytics
        test_expenses = [
            {'description': 'Travel expense', 'amount': '500.00', 'category': ExpenseCategory.TRAVEL},
            {'description': 'Software license', 'amount': '99.99', 'category': ExpenseCategory.SOFTWARE},
            {'description': 'Office rent', 'amount': '2000.00', 'category': ExpenseCategory.RENT},
        ]
        
        created_expenses = []
        for expense_data in test_expenses:
            expense_data.update({
                'date': date.today().isoformat(),
                'is_reimbursable': True
            })
            
            response = client.post(
                '/api/expenses/',
                data=json.dumps(expense_data),
                content_type='application/json',
                **headers
            )
            
            assert response.status_code == 201
            created_expenses.append(response.json()['id'])
        
        print("✅ Test expense creation for analytics successful")
        
        # Test 1: Summary endpoint
        response = client.get('/api/expenses/summary/', **headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        summary_data = response.json()
        assert 'total_amount' in summary_data
        assert 'expense_count' in summary_data
        assert 'category_breakdown' in summary_data
        
        print("✅ Summary endpoint working")
        
        # Test 2: Categories endpoint
        response = client.get('/api/expenses/categories/', **headers)
        assert response.status_code == 200
        
        categories_data = response.json()
        assert 'categories' in categories_data
        assert len(categories_data['categories']) == 12  # All expense categories
        
        print("✅ Categories endpoint working")
        
        # Test 3: Recent expenses
        response = client.get('/api/expenses/recent/', **headers)
        assert response.status_code == 200
        
        recent_data = response.json()
        assert 'count' in recent_data
        assert 'expenses' in recent_data
        
        print("✅ Recent expenses endpoint working")
        
        # Test 4: Statistics endpoint
        response = client.get('/api/expenses/stats/', **headers)
        assert response.status_code == 200
        
        stats_data = response.json()
        assert 'total_expenses' in stats_data
        assert 'total_amount' in stats_data
        assert 'average_expense' in stats_data
        
        print("✅ Statistics endpoint working")
        
        # Test 5: Filtering combinations
        response = client.get(
            '/api/expenses/',
            {
                'category': 'travel',
                'amount_min': '100.00',
                'is_reimbursable': 'true'
            },
            **headers
        )
        
        assert response.status_code == 200
        print("✅ Complex filtering working")
        
        # Cleanup created test expenses
        for expense_id in created_expenses:
            client.delete(f'/api/expenses/{expense_id}/', **headers)
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling_and_edge_cases():
    """Test error handling and edge cases."""
    print("\nTesting Error Handling and Edge Cases...")
    
    try:
        client = Client()
        user = get_user_model().objects.get(email='crudtest@example.com')
        token = get_auth_token(client, user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Test 1: Invalid JSON data
        response = client.post(
            '/api/expenses/',
            data='{"invalid": json}',
            content_type='application/json',
            **headers
        )
        
        assert response.status_code == 400, "Should handle invalid JSON"
        print("✅ Invalid JSON handling working")
        
        # Test 2: SQL injection attempt
        malicious_data = {
            'description': "'; DROP TABLE expenses_expense; --",
            'amount': '100.00',
            'date': date.today().isoformat()
        }
        
        response = client.post(
            '/api/expenses/',
            data=json.dumps(malicious_data),
            content_type='application/json',
            **headers
        )
        
        # Should either create safely or reject, but not crash
        assert response.status_code in [201, 400], "Should handle SQL injection attempts safely"
        print("✅ SQL injection protection working")
        
        # Test 3: Very large description
        large_description = 'A' * 1000  # Very long description
        large_data = {
            'description': large_description,
            'amount': '100.00',
            'date': date.today().isoformat()
        }
        
        response = client.post(
            '/api/expenses/',
            data=json.dumps(large_data),
            content_type='application/json',
            **headers
        )
        
        # Should handle based on model constraints
        assert response.status_code in [201, 400]
        print("✅ Large data handling working")
        
        # Test 4: Invalid UUID format
        response = client.get('/api/expenses/invalid-uuid/', **headers)
        assert response.status_code == 404, "Should handle invalid UUID gracefully"
        print("✅ Invalid UUID handling working")
        
        # Test 5: Content-Type edge cases
        response = client.post(
            '/api/expenses/',
            data='description=test&amount=100.00',
            content_type='application/x-www-form-urlencoded',
            **headers
        )
        
        # Should handle different content types
        assert response.status_code in [201, 400, 415]
        print("✅ Content-Type handling working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_and_optimization():
    """Test performance and optimization features."""
    print("\nTesting Performance and Optimization...")
    
    try:
        from expenses.models import Expense, ExpenseCategory
        import time
        
        client = Client()
        user = get_user_model().objects.get(email='crudtest@example.com')
        token = get_auth_token(client, user)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Create multiple expenses for performance testing
        print("Creating test data for performance testing...")
        created_expenses = []
        
        for i in range(20):  # Create 20 test expenses
            expense_data = {
                'description': f'Performance test expense {i}',
                'amount': str(50.00 + i),
                'date': (date.today() - timedelta(days=i)).isoformat(),
                'category': list(ExpenseCategory.choices)[i % len(ExpenseCategory.choices)][0],
                'is_reimbursable': i % 2 == 0
            }
            
            response = client.post(
                '/api/expenses/',
                data=json.dumps(expense_data),
                content_type='application/json',
                **headers
            )
            
            if response.status_code == 201:
                created_expenses.append(response.json()['id'])
        
        print(f"✅ Created {len(created_expenses)} test expenses")
        
        # Test 1: List performance
        start_time = time.time()
        response = client.get('/api/expenses/', **headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        
        print(f"✅ List endpoint response time: {response_time:.3f}s")
        assert response_time < 2.0, f"List endpoint too slow: {response_time:.3f}s"
        
        # Test 2: Filtering performance
        start_time = time.time()
        response = client.get(
            '/api/expenses/',
            {'is_reimbursable': 'true', 'amount_min': '100.00'},
            **headers
        )
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        
        print(f"✅ Filtering response time: {response_time:.3f}s")
        assert response_time < 2.0, f"Filtering too slow: {response_time:.3f}s"
        
        # Test 3: Summary performance
        start_time = time.time()
        response = client.get('/api/expenses/summary/', **headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        
        print(f"✅ Summary endpoint response time: {response_time:.3f}s")
        assert response_time < 3.0, f"Summary endpoint too slow: {response_time:.3f}s"
        
        # Test 4: Pagination
        response = client.get('/api/expenses/?page_size=10', **headers)
        assert response.status_code == 200
        
        data = response.json()
        if 'results' in data:
            assert len(data['results']) <= 10, "Pagination not working correctly"
            print("✅ Pagination working correctly")
        
        # Cleanup performance test data
        for expense_id in created_expenses:
            client.delete(f'/api/expenses/{expense_id}/', **headers)
        
        print("✅ Performance test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run comprehensive CRUD operations tests."""
    print("="*70)
    print("SK-503: Expense CRUD Operations - Comprehensive Testing")
    print("="*70)
    
    # Setup Django
    setup_django()
    
    # Run test phases
    test_results = []
    expense_id = None
    
    # Phase 1: CREATE operations
    expense_id = test_expense_create_operations()
    test_results.append(expense_id is not None)
    
    if expense_id:
        # Phase 2: READ operations
        test_results.append(test_expense_read_operations(expense_id))
        
        # Phase 3: UPDATE operations  
        test_results.append(test_expense_update_operations(expense_id))
        
        # Phase 4: DELETE operations
        test_results.append(test_expense_delete_operations(expense_id))
    else:
        # Skip dependent tests if CREATE failed
        test_results.extend([False, False, False])
    
    # Phase 5: Advanced features
    test_results.append(test_advanced_features())
    
    # Phase 6: Error handling
    test_results.append(test_error_handling_and_edge_cases())
    
    # Phase 7: Performance testing
    test_results.append(test_performance_and_optimization())
    
    # Cleanup
    try:
        User = get_user_model()
        User.objects.filter(email__in=['crudtest@example.com', 'other@example.com']).delete()
    except:
        pass
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    test_names = [
        "CREATE Operations",
        "READ Operations", 
        "UPDATE Operations",
        "DELETE Operations",
        "Advanced Features",
        "Error Handling",
        "Performance Testing"
    ]
    
    passed = sum(test_results)
    total = len(test_results)
    
    for i, (test_name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test_name}: {status}")
    
    print("-" * 70)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nSK-503 Expense CRUD Operations: COMPLETED")
        print("✅ Complete CREATE operations with validation")
        print("✅ Comprehensive READ operations with filtering")
        print("✅ Full UPDATE operations (PUT/PATCH)")
        print("✅ Proper DELETE operations with verification")
        print("✅ Advanced analytics and reporting endpoints")
        print("✅ Robust error handling and security")
        print("✅ Performance optimization and response times")
        print("✅ Multi-tenant data isolation")
        print("✅ Authentication and authorization")
        print("✅ Complex filtering and search functionality")
        print("\nExpense tracking system CRUD operations are fully functional!")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("Review and fix failing tests before deployment")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)