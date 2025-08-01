"""
Test data factories for creating consistent test objects.
Provides factory classes for generating test data with realistic values.
"""
import factory
from factory import SubFactory, LazyAttribute, Sequence
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from datetime import date, timedelta
import uuid

from django.contrib.auth import get_user_model
from clients.models import Client
from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem
from expenses.models import Expense

User = get_user_model()
fake = Faker()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
    
    email = Sequence(lambda n: f'user{n}@senangkira.com')
    username = Sequence(lambda n: f'testuser{n}')
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    password = factory.PostGenerationMethodCall('set_password', 'TestPass123!')
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        """Handle many-to-many groups relationship."""
        if not create:
            return
        if extracted:
            for group in extracted:
                self.groups.add(group)


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""
    
    email = Sequence(lambda n: f'admin{n}@senangkira.com')
    username = Sequence(lambda n: f'admin{n}')
    is_staff = True
    is_superuser = True


class ClientFactory(DjangoModelFactory):
    """Factory for creating test clients."""
    
    class Meta:
        model = Client
    
    name = factory.LazyFunction(fake.company)
    email = factory.LazyAttribute(lambda obj: f'contact@{obj.name.lower().replace(" ", "")}.com')
    phone = factory.LazyFunction(fake.phone_number)
    address = factory.LazyFunction(fake.street_address)
    city = factory.LazyFunction(fake.city)
    state = factory.LazyFunction(fake.state_abbr)
    postal_code = factory.LazyFunction(fake.zipcode)
    country = 'USA'
    owner = SubFactory(UserFactory)
    
    @factory.lazy_attribute
    def email(self):
        """Generate realistic email based on company name."""
        company_name = self.name.lower().replace(' ', '').replace(',', '').replace('.', '')
        return f'contact@{company_name}.com'


class QuoteFactory(DjangoModelFactory):
    """Factory for creating test quotes."""
    
    class Meta:
        model = Quote
    
    title = factory.LazyFunction(lambda: fake.catch_phrase())
    description = factory.LazyFunction(fake.text)
    status = 'draft'
    tax_rate = Decimal('0.08')
    notes = factory.LazyFunction(fake.sentence)
    valid_until = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    owner = SubFactory(UserFactory)
    client = SubFactory(ClientFactory, owner=factory.SelfAttribute('..owner'))


class QuoteLineItemFactory(DjangoModelFactory):
    """Factory for creating quote line items."""
    
    class Meta:
        model = QuoteLineItem
    
    quote = SubFactory(QuoteFactory)
    description = factory.LazyFunction(fake.catch_phrase)
    quantity = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=1, max=100))))
    unit_price = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=50, max=500))))
    sort_order = Sequence(lambda n: n)


class InvoiceFactory(DjangoModelFactory):
    """Factory for creating test invoices."""
    
    class Meta:
        model = Invoice
    
    title = factory.LazyFunction(lambda: fake.catch_phrase())
    description = factory.LazyFunction(fake.text)
    status = 'draft'
    tax_rate = Decimal('0.08')
    due_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    notes = factory.LazyFunction(fake.sentence)
    owner = SubFactory(UserFactory)
    client = SubFactory(ClientFactory, owner=factory.SelfAttribute('..owner'))
    source_quote = None


class InvoiceLineItemFactory(DjangoModelFactory):
    """Factory for creating invoice line items."""
    
    class Meta:
        model = InvoiceLineItem
    
    invoice = SubFactory(InvoiceFactory)
    description = factory.LazyFunction(fake.catch_phrase)
    quantity = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=1, max=100))))
    unit_price = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=50, max=500))))
    sort_order = Sequence(lambda n: n)


class ExpenseFactory(DjangoModelFactory):
    """Factory for creating test expenses."""
    
    class Meta:
        model = Expense
    
    description = factory.LazyFunction(fake.catch_phrase)
    amount = factory.LazyFunction(lambda: Decimal(str(fake.random_int(min=10, max=1000))))
    date = factory.LazyFunction(fake.date_this_year)
    category = factory.Iterator(['software', 'hardware', 'travel', 'meals', 'marketing', 'office'])
    receipt_url = factory.LazyFunction(lambda: f'https://example.com/receipt_{uuid.uuid4().hex[:8]}.pdf')
    owner = SubFactory(UserFactory)


# Specialized factories for specific test scenarios

class QuoteWithLineItemsFactory(QuoteFactory):
    """Factory for quotes with predefined line items."""
    
    @factory.post_generation
    def line_items(self, create, extracted, **kwargs):
        """Create line items for the quote."""
        if not create:
            return
        
        if extracted:
            # Use provided line items
            for i, item_data in enumerate(extracted):
                QuoteLineItemFactory(
                    quote=self,
                    description=item_data.get('description', fake.catch_phrase()),
                    quantity=Decimal(str(item_data.get('quantity', 10))),
                    unit_price=Decimal(str(item_data.get('unit_price', 100))),
                    sort_order=i
                )
        else:
            # Create default line items
            QuoteLineItemFactory.create_batch(3, quote=self)


class InvoiceWithLineItemsFactory(InvoiceFactory):
    """Factory for invoices with predefined line items."""
    
    @factory.post_generation
    def line_items(self, create, extracted, **kwargs):
        """Create line items for the invoice."""
        if not create:
            return
        
        if extracted:
            # Use provided line items
            for i, item_data in enumerate(extracted):
                InvoiceLineItemFactory(
                    invoice=self,
                    description=item_data.get('description', fake.catch_phrase()),
                    quantity=Decimal(str(item_data.get('quantity', 10))),
                    unit_price=Decimal(str(item_data.get('unit_price', 100))),
                    sort_order=i
                )
        else:
            # Create default line items
            InvoiceLineItemFactory.create_batch(3, invoice=self)


class SentQuoteFactory(QuoteFactory):
    """Factory for quotes in sent status."""
    status = 'sent'


class AcceptedQuoteFactory(QuoteFactory):
    """Factory for quotes in accepted status."""
    status = 'accepted'


class SentInvoiceFactory(InvoiceFactory):
    """Factory for invoices in sent status."""
    status = 'sent'


class PaidInvoiceFactory(InvoiceFactory):
    """Factory for invoices in paid status."""
    status = 'paid'
    paid_date = factory.LazyFunction(lambda: date.today() - timedelta(days=5))
    payment_method = 'bank_transfer'


class OverdueInvoiceFactory(InvoiceFactory):
    """Factory for overdue invoices."""
    status = 'sent'
    due_date = factory.LazyFunction(lambda: date.today() - timedelta(days=10))


# Batch creation helpers

def create_test_users(count=5):
    """Create multiple test users."""
    return UserFactory.create_batch(count)


def create_test_clients(owner=None, count=5):
    """Create multiple test clients."""
    if owner:
        return ClientFactory.create_batch(count, owner=owner)
    return ClientFactory.create_batch(count)


def create_test_quotes(owner=None, client=None, count=5):
    """Create multiple test quotes."""
    kwargs = {}
    if owner:
        kwargs['owner'] = owner
    if client:
        kwargs['client'] = client
    return QuoteWithLineItemsFactory.create_batch(count, **kwargs)


def create_test_invoices(owner=None, client=None, count=5):
    """Create multiple test invoices."""
    kwargs = {}
    if owner:
        kwargs['owner'] = owner
    if client:
        kwargs['client'] = client
    return InvoiceWithLineItemsFactory.create_batch(count, **kwargs)


def create_test_expenses(owner=None, count=5):
    """Create multiple test expenses."""
    kwargs = {}
    if owner:
        kwargs['owner'] = owner
    return ExpenseFactory.create_batch(count, **kwargs)


# Realistic scenario factories

def create_complete_business_scenario(user=None):
    """
    Create a complete business scenario with user, clients, quotes, invoices, and expenses.
    Returns a dictionary with all created objects.
    """
    if not user:
        user = UserFactory()
    
    # Create clients
    clients = ClientFactory.create_batch(3, owner=user)
    
    # Create quotes in various statuses
    draft_quotes = QuoteWithLineItemsFactory.create_batch(2, owner=user, client=clients[0])
    sent_quotes = SentQuoteFactory.create_batch(2, owner=user, client=clients[1])
    accepted_quotes = AcceptedQuoteFactory.create_batch(1, owner=user, client=clients[2])
    
    # Create invoices in various statuses
    draft_invoices = InvoiceWithLineItemsFactory.create_batch(1, owner=user, client=clients[0])
    sent_invoices = SentInvoiceFactory.create_batch(2, owner=user, client=clients[1])
    paid_invoices = PaidInvoiceFactory.create_batch(1, owner=user, client=clients[2])
    overdue_invoices = OverdueInvoiceFactory.create_batch(1, owner=user, client=clients[0])
    
    # Create expenses
    expenses = ExpenseFactory.create_batch(5, owner=user)
    
    return {
        'user': user,
        'clients': clients,
        'quotes': {
            'draft': draft_quotes,
            'sent': sent_quotes,
            'accepted': accepted_quotes
        },
        'invoices': {
            'draft': draft_invoices,
            'sent': sent_invoices,
            'paid': paid_invoices,
            'overdue': overdue_invoices
        },
        'expenses': expenses
    }


def create_quote_to_invoice_scenario():
    """
    Create scenario for testing quote-to-invoice conversion.
    Returns quote ready for conversion and related objects.
    """
    user = UserFactory()
    client = ClientFactory(owner=user)
    
    # Create accepted quote
    quote = AcceptedQuoteFactory(owner=user, client=client, title='Quote for Conversion')
    QuoteLineItemFactory.create_batch(3, quote=quote)
    
    return {
        'user': user,
        'client': client,
        'quote': quote
    }


def create_financial_reporting_scenario():
    """
    Create scenario for testing financial reporting.
    Returns objects with known financial values for testing calculations.
    """
    user = UserFactory()
    client = ClientFactory(owner=user)
    
    # Create paid invoices with known amounts
    paid_invoice_1 = PaidInvoiceFactory(
        owner=user,
        client=client,
        title='Paid Invoice 1',
        tax_rate=Decimal('0.08')
    )
    InvoiceLineItemFactory(
        invoice=paid_invoice_1,
        description='Service 1',
        quantity=Decimal('10'),
        unit_price=Decimal('100'),
        sort_order=0
    )
    
    paid_invoice_2 = PaidInvoiceFactory(
        owner=user,
        client=client,
        title='Paid Invoice 2',
        tax_rate=Decimal('0.08')
    )
    InvoiceLineItemFactory(
        invoice=paid_invoice_2,
        description='Service 2',
        quantity=Decimal('20'),
        unit_price=Decimal('50'),
        sort_order=0
    )
    
    # Create expenses with known amounts
    expense_1 = ExpenseFactory(
        owner=user,
        description='Software License',
        amount=Decimal('200'),
        category='software'
    )
    
    expense_2 = ExpenseFactory(
        owner=user,
        description='Office Supplies',
        amount=Decimal('150'),
        category='office'
    )
    
    return {
        'user': user,
        'client': client,
        'paid_invoices': [paid_invoice_1, paid_invoice_2],
        'expenses': [expense_1, expense_2],
        'expected_revenue': Decimal('2160.00'),  # (1000 + 1000) * 1.08
        'expected_expenses': Decimal('350.00'),   # 200 + 150
        'expected_profit': Decimal('1810.00')     # 2160 - 350
    }


# Performance testing factories

def create_large_dataset(users=10, clients_per_user=5, quotes_per_client=3, invoices_per_client=2):
    """
    Create large dataset for performance testing.
    Returns dictionary with counts and sample objects.
    """
    users = UserFactory.create_batch(users)
    total_clients = 0
    total_quotes = 0
    total_invoices = 0
    
    for user in users:
        clients = ClientFactory.create_batch(clients_per_user, owner=user)
        total_clients += len(clients)
        
        for client in clients:
            quotes = QuoteWithLineItemsFactory.create_batch(quotes_per_client, owner=user, client=client)
            invoices = InvoiceWithLineItemsFactory.create_batch(invoices_per_client, owner=user, client=client)
            total_quotes += len(quotes)
            total_invoices += len(invoices)
    
    return {
        'users': users,
        'total_clients': total_clients,
        'total_quotes': total_quotes,
        'total_invoices': total_invoices,
        'sample_user': users[0] if users else None
    }