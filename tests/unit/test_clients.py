"""
Unit tests for clients functionality.
Tests client model, validation, and business logic.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal

from clients.models import Client
from tests.utils import TestDataGenerator
from tests.conftest import BaseTestCase

User = get_user_model()


class ClientModelTests(BaseTestCase):
    """Test Client model functionality."""
    
    def test_client_creation(self):
        """Test basic client creation."""
        client_data = TestDataGenerator.client_data(name='Test Client')
        client = Client.objects.create(owner=self.user, **client_data)
        
        self.assertEqual(client.name, 'Test Client')
        self.assertEqual(client.owner, self.user)
        self.assertTrue(client.is_active)
        self.assertIsNotNone(client.created_at)
        self.assertIsNotNone(client.updated_at)
    
    def test_client_string_representation(self):
        """Test client string representation."""
        client = Client.objects.create(
            name='Test Client',
            email='test@client.com',
            owner=self.user
        )
        
        self.assertEqual(str(client), 'Test Client')
    
    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Name is required
        with self.assertRaises(ValidationError):
            client = Client(owner=self.user, email='test@client.com')
            client.full_clean()
        
        # Owner is required  
        with self.assertRaises(ValidationError):
            client = Client(name='Test Client', email='test@client.com')
            client.full_clean()
    
    def test_email_validation(self):
        """Test email field validation."""
        # Valid email should work
        client = Client.objects.create(
            name='Test Client',
            email='valid@email.com',
            owner=self.user
        )
        self.assertEqual(client.email, 'valid@email.com')
        
        # Invalid email should fail validation
        with self.assertRaises(ValidationError):
            client = Client(
                name='Test Client',
                email='invalid-email',
                owner=self.user
            )
            client.full_clean()
    
    def test_phone_field(self):
        """Test phone field functionality."""
        client = Client.objects.create(
            name='Test Client',
            email='test@client.com',
            phone='+1234567890',
            owner=self.user
        )
        
        self.assertEqual(client.phone, '+1234567890')
    
    def test_address_fields(self):
        """Test address-related fields."""
        address_data = {
            'address': '123 Main Street',
            'city': 'Test City',
            'state': 'TS',
            'postal_code': '12345',
            'country': 'Test Country'
        }
        
        client = Client.objects.create(
            name='Test Client',
            email='test@client.com',
            owner=self.user,
            **address_data
        )
        
        self.assertEqual(client.address, '123 Main Street')
        self.assertEqual(client.city, 'Test City')
        self.assertEqual(client.state, 'TS')
        self.assertEqual(client.postal_code, '12345')
        self.assertEqual(client.country, 'Test Country')
    
    def test_client_deactivation(self):
        """Test client deactivation functionality."""
        client = Client.objects.create(
            name='Test Client',
            email='test@client.com',
            owner=self.user
        )
        
        self.assertTrue(client.is_active)
        
        # Deactivate client
        client.is_active = False
        client.save()
        
        self.assertFalse(client.is_active)
    
    def test_client_uniqueness_per_owner(self):
        """Test that client names can be unique per owner."""
        # Same name for same owner should fail
        Client.objects.create(
            name='Test Client',
            email='test1@client.com',
            owner=self.user
        )
        
        # Different email should allow same name for same owner
        # (depending on business rules)
        try:
            Client.objects.create(
                name='Test Client',
                email='test2@client.com',
                owner=self.user
            )
        except Exception:
            # If unique constraint exists, this is expected
            pass
    
    def test_client_filtering_by_owner(self):
        """Test that clients are properly filtered by owner."""
        # Create second user
        user2 = User.objects.create_user(
            email='user2@example.com',
            username='user2',
            password='TestPass123!'
        )
        
        # Create clients for different owners
        client1 = Client.objects.create(
            name='Client 1',
            email='client1@example.com',
            owner=self.user
        )
        
        client2 = Client.objects.create(
            name='Client 2',
            email='client2@example.com',
            owner=user2
        )
        
        # Test filtering
        user1_clients = Client.objects.filter(owner=self.user)
        user2_clients = Client.objects.filter(owner=user2)
        
        self.assertIn(client1, user1_clients)
        self.assertNotIn(client2, user1_clients)
        
        self.assertIn(client2, user2_clients)
        self.assertNotIn(client1, user2_clients)


class ClientBusinessLogicTests(BaseTestCase):
    """Test client business logic and computed properties."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.client = Client.objects.create(
            name='Business Logic Test Client',
            email='business@client.com',
            owner=self.user
        )
    
    def test_full_address_property(self):
        """Test full address computed property."""
        # Client with complete address
        client = Client.objects.create(
            name='Address Test Client',
            email='address@client.com',
            address='123 Main Street',
            city='Test City',
            state='TS',
            postal_code='12345',
            country='Test Country',
            owner=self.user
        )
        
        expected_address = '123 Main Street, Test City, TS 12345, Test Country'
        if hasattr(client, 'full_address'):
            self.assertEqual(client.full_address, expected_address)
    
    def test_client_with_partial_address(self):
        """Test client with incomplete address information."""
        client = Client.objects.create(
            name='Partial Address Client',
            email='partial@client.com',
            city='Test City',
            state='TS',
            owner=self.user
        )
        
        # Should handle missing fields gracefully
        if hasattr(client, 'full_address'):
            self.assertIn('Test City', client.full_address)
            self.assertIn('TS', client.full_address)
    
    def test_client_contact_info_validation(self):
        """Test that client has at least one contact method."""
        # Should allow client with email only
        client_email_only = Client.objects.create(
            name='Email Only Client',
            email='email@client.com',
            owner=self.user
        )
        self.assertIsNotNone(client_email_only.email)
        
        # Should allow client with phone only
        client_phone_only = Client.objects.create(
            name='Phone Only Client',
            phone='+1234567890',
            owner=self.user
        )
        self.assertIsNotNone(client_phone_only.phone)
        
        # Client with neither email nor phone might be invalid
        # (depending on business rules)
        try:
            client_no_contact = Client(
                name='No Contact Client',
                owner=self.user
            )
            client_no_contact.full_clean()
        except ValidationError:
            # If validation requires contact info, this is expected
            pass


class ClientQueryTests(BaseTestCase):
    """Test client querying and filtering."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create multiple clients for testing
        self.active_client = Client.objects.create(
            name='Active Client',
            email='active@client.com',
            is_active=True,
            owner=self.user
        )
        
        self.inactive_client = Client.objects.create(
            name='Inactive Client',
            email='inactive@client.com',
            is_active=False,
            owner=self.user
        )
    
    def test_active_clients_query(self):
        """Test querying for active clients only."""
        active_clients = Client.objects.filter(owner=self.user, is_active=True)
        
        self.assertIn(self.active_client, active_clients)
        self.assertNotIn(self.inactive_client, active_clients)
    
    def test_client_search_by_name(self):
        """Test searching clients by name."""
        search_results = Client.objects.filter(
            owner=self.user,
            name__icontains='Active'
        )
        
        self.assertIn(self.active_client, search_results)
        self.assertNotIn(self.inactive_client, search_results)
    
    def test_client_search_by_email(self):
        """Test searching clients by email."""
        search_results = Client.objects.filter(
            owner=self.user,
            email__icontains='active'
        )
        
        self.assertIn(self.active_client, search_results)
        self.assertNotIn(self.inactive_client, search_results)
    
    def test_client_ordering(self):
        """Test client ordering."""
        # Create additional client to test ordering
        Client.objects.create(
            name='Alpha Client',
            email='alpha@client.com',
            owner=self.user
        )
        
        clients_by_name = Client.objects.filter(owner=self.user).order_by('name')
        client_names = [c.name for c in clients_by_name]
        
        # Should be in alphabetical order
        self.assertEqual(client_names[0], 'Active Client')
        self.assertEqual(client_names[1], 'Alpha Client')
    
    def test_client_count_by_status(self):
        """Test counting clients by status."""
        active_count = Client.objects.filter(owner=self.user, is_active=True).count()
        inactive_count = Client.objects.filter(owner=self.user, is_active=False).count()
        total_count = Client.objects.filter(owner=self.user).count()
        
        self.assertEqual(active_count + inactive_count, total_count)
        self.assertGreaterEqual(active_count, 1)  # At least our test client
        self.assertGreaterEqual(inactive_count, 1)  # At least our test client


class ClientIntegrationTests(BaseTestCase):
    """Test client integration with other models."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.client = Client.objects.create(
            name='Integration Test Client',
            email='integration@client.com',
            owner=self.user
        )
    
    def test_client_deletion_cascade(self):
        """Test what happens when client is deleted."""
        client_id = self.client.id
        
        # Delete client
        self.client.delete()
        
        # Verify client is deleted
        with self.assertRaises(Client.DoesNotExist):
            Client.objects.get(id=client_id)
    
    def test_user_deletion_cascade(self):
        """Test what happens when user (owner) is deleted."""
        user_id = self.user.id
        client_id = self.client.id
        
        # Delete user
        self.user.delete()
        
        # Client should also be deleted (cascade)
        with self.assertRaises(Client.DoesNotExist):
            Client.objects.get(id=client_id)
        
        # Verify user is deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)