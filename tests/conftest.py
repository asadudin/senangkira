"""
Pytest configuration and shared fixtures for SenangKira test suite.
Provides reusable test data, authentication, and test utilities.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from clients.models import Client
from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem
from expenses.models import Expense, ExpenseCategory
from dashboard.models import DashboardSnapshot

User = get_user_model()


@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    def create_user(email=None, username=None, company_name=None):
        if not email:
            unique_id = str(uuid.uuid4())[:8]
            email = f'testuser_{unique_id}@example.com'
            username = f'testuser_{unique_id}'
        
        return User.objects.create_user(
            email=email,
            username=username or email.split('@')[0],
            password='TestPass123!',
            company_name=company_name or f'Test Company {username}'
        )
    return create_user


@pytest.fixture
def test_user(user_factory):
    """Primary test user."""
    return user_factory(
        email='testuser@example.com',
        username='testuser',
        company_name='Test Company'
    )


@pytest.fixture
def secondary_user(user_factory):
    """Secondary test user for multi-tenant testing."""
    return user_factory(
        email='testuser2@example.com', 
        username='testuser2',
        company_name='Test Company 2'
    )


@pytest.fixture
def client_factory():
    """Factory for creating test clients."""
    def create_client(owner, name=None, **kwargs):
        defaults = {
            'name': name or f'Test Client {str(uuid.uuid4())[:8]}',
            'email': f'client_{str(uuid.uuid4())[:8]}@example.com',
            'phone': '+1234567890',
            'address': '123 Test Street',
            'city': 'Test City',
            'state': 'TS',
            'postal_code': '12345',
            'country': 'Test Country',
            'owner': owner
        }
        defaults.update(kwargs)
        return Client.objects.create(**defaults)
    return create_client


@pytest.fixture
def test_client(test_user, client_factory):
    """Primary test client."""
    return client_factory(
        owner=test_user,
        name='Primary Test Client',
        email='primary@testclient.com'
    )


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, test_user):
    """API client authenticated with JWT token."""
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def quote_factory():
    """Factory for creating test quotes."""
    def create_quote(owner, client, **kwargs):
        defaults = {
            'title': f'Test Quote {str(uuid.uuid4())[:8]}',
            'description': 'Test quote description',
            'tax_rate': Decimal('0.0800'),
            'quote_date': date.today(),
            'valid_until': date.today() + timedelta(days=30),
            'owner': owner,
            'client': client
        }
        defaults.update(kwargs)
        
        quote = Quote.objects.create(**defaults)
        
        # Add default line items if not provided
        if 'line_items' not in kwargs:
            QuoteLineItem.objects.create(
                quote=quote,
                description='Consulting Services',
                quantity=Decimal('10.00'),
                unit_price=Decimal('150.00'),
                sort_order=0
            )
            QuoteLineItem.objects.create(
                quote=quote,
                description='Development Work',
                quantity=Decimal('20.00'),
                unit_price=Decimal('100.00'),
                sort_order=1
            )
        
        return quote
    return create_quote


@pytest.fixture
def invoice_factory():
    """Factory for creating test invoices."""
    def create_invoice(owner, client, **kwargs):
        defaults = {
            'title': f'Test Invoice {str(uuid.uuid4())[:8]}',
            'description': 'Test invoice description',
            'tax_rate': Decimal('0.0800'),
            'invoice_date': date.today(),
            'due_date': date.today() + timedelta(days=30),
            'owner': owner,
            'client': client
        }
        defaults.update(kwargs)
        
        invoice = Invoice.objects.create(**defaults)
        
        # Add default line items if not provided
        if 'line_items' not in kwargs:
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description='Professional Services',
                quantity=Decimal('15.00'),
                unit_price=Decimal('120.00'),
                sort_order=0
            )
        
        return invoice
    return create_invoice


@pytest.fixture
def expense_factory():
    """Factory for creating test expenses."""
    def create_expense(owner, **kwargs):
        # Create category if needed
        category, created = ExpenseCategory.objects.get_or_create(
            name='office_supplies',
            defaults={
                'display_name': 'Office Supplies',
                'description': 'Office supplies and equipment',
                'owner': owner
            }
        )
        
        defaults = {
            'description': f'Test Expense {str(uuid.uuid4())[:8]}',
            'amount': Decimal('100.00'),
            'expense_date': date.today(),
            'category': category,
            'owner': owner,
            'is_reimbursable': False
        }
        defaults.update(kwargs)
        
        return Expense.objects.create(**defaults)
    return create_expense


@pytest.fixture
def dashboard_snapshot_factory():
    """Factory for creating dashboard snapshots."""
    def create_snapshot(owner, **kwargs):
        defaults = {
            'snapshot_date': date.today(),
            'period_type': 'monthly',
            'total_revenue': Decimal('10000.00'),
            'total_expenses': Decimal('7000.00'),
            'net_profit': Decimal('3000.00'),
            'outstanding_amount': Decimal('2000.00'),
            'reimbursable_expenses': Decimal('500.00'),
            'total_clients': 15,
            'new_clients': 3,
            'total_invoices': 25,
            'total_quotes': 30,
            'owner': owner
        }
        defaults.update(kwargs)
        
        return DashboardSnapshot.objects.create(**defaults)
    return create_snapshot


@pytest.fixture
def sample_line_items():
    """Sample line items data for testing."""
    return [
        {
            'description': 'Web Development',
            'quantity': '40.00',
            'unit_price': '125.00',
            'sort_order': 0
        },
        {
            'description': 'UI/UX Design',
            'quantity': '20.00',
            'unit_price': '150.00',
            'sort_order': 1
        },
        {
            'description': 'Project Management',
            'quantity': '10.00',
            'unit_price': '100.00',
            'sort_order': 2
        }
    ]


@pytest.fixture(scope='session')
def test_database_setup():
    """Setup test database with initial data."""
    # This fixture can be used for one-time database setup
    # if needed for integration tests
    pass


class BaseTestCase(TransactionTestCase):
    """Base test case with common setup and utilities."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None  # Show full diff in assertions
    
    def setUp(self):
        """Common setup for all test cases."""
        super().setUp()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            username='testuser',
            password='TestPass123!',
            company_name='Test Company'
        )
        
        self.client_model = Client.objects.create(
            name='Test Client',
            email='client@example.com',
            phone='+1234567890',
            owner=self.user
        )
    
    def create_authenticated_client(self, user=None):
        """Create authenticated API client."""
        user = user or self.user
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return client
    
    def assert_response_success(self, response, expected_status=200):
        """Assert API response is successful."""
        self.assertEqual(response.status_code, expected_status)
        
    def assert_response_error(self, response, expected_status=400):
        """Assert API response contains expected error."""
        self.assertEqual(response.status_code, expected_status)
        self.assertIn('error', response.json() or response.data)


# Mark as pytest configuration
pytest_plugins = []