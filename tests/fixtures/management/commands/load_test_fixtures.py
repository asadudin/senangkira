"""
Django management command to load test fixtures.
Usage: python manage.py load_test_fixtures [--scenario scenario_name] [--clean]
"""
import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from datetime import datetime, date

from clients.models import Client
from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem
from expenses.models import Expense
from tests.fixtures.factories import (
    create_complete_business_scenario,
    create_quote_to_invoice_scenario,
    create_financial_reporting_scenario,
    create_large_dataset
)

User = get_user_model()


class Command(BaseCommand):
    """Load test fixtures into the database."""
    
    help = 'Load test fixtures into the database for testing and development'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--scenario',
            type=str,
            default='complete',
            choices=['complete', 'conversion', 'financial', 'large', 'json'],
            help='Test scenario to load (default: complete)'
        )
        
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean existing test data before loading'
        )
        
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users for large dataset (default: 10)'
        )
        
        parser.add_argument(
            '--file',
            type=str,
            help='JSON file to load fixtures from'
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        scenario = options['scenario']
        clean = options['clean']
        
        self.stdout.write(f'Loading test fixtures for scenario: {scenario}')
        
        if clean:
            self.clean_test_data()
        
        try:
            with transaction.atomic():
                if scenario == 'complete':
                    self.load_complete_scenario()
                elif scenario == 'conversion':
                    self.load_conversion_scenario()
                elif scenario == 'financial':
                    self.load_financial_scenario()
                elif scenario == 'large':
                    self.load_large_dataset(options['users'])
                elif scenario == 'json':
                    self.load_json_fixtures(options.get('file'))
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully loaded {scenario} test fixtures')
                )
        except Exception as e:
            raise CommandError(f'Failed to load fixtures: {str(e)}')
    
    def clean_test_data(self):
        """Clean existing test data."""
        self.stdout.write('Cleaning existing test data...')
        
        # Delete in reverse order of dependencies
        InvoiceLineItem.objects.all().delete()
        QuoteLineItem.objects.all().delete()
        Invoice.objects.all().delete()
        Quote.objects.all().delete()
        Expense.objects.all().delete()
        Client.objects.all().delete()
        
        # Only delete test users (those with test emails)
        User.objects.filter(email__contains='senangkira.com').delete()
        User.objects.filter(username__startswith='test').delete()
        
        self.stdout.write('Test data cleaned successfully')
    
    def load_complete_scenario(self):
        """Load complete business scenario."""
        self.stdout.write('Creating complete business scenario...')
        
        scenario = create_complete_business_scenario()
        
        self.stdout.write(f'Created:')
        self.stdout.write(f'  - 1 user: {scenario["user"].email}')
        self.stdout.write(f'  - {len(scenario["clients"])} clients')
        self.stdout.write(f'  - {sum(len(quotes) for quotes in scenario["quotes"].values())} quotes')
        self.stdout.write(f'  - {sum(len(invoices) for invoices in scenario["invoices"].values())} invoices')
        self.stdout.write(f'  - {len(scenario["expenses"])} expenses')
    
    def load_conversion_scenario(self):
        """Load quote-to-invoice conversion scenario."""
        self.stdout.write('Creating quote-to-invoice conversion scenario...')
        
        scenario = create_quote_to_invoice_scenario()
        
        self.stdout.write(f'Created:')
        self.stdout.write(f'  - 1 user: {scenario["user"].email}')
        self.stdout.write(f'  - 1 client: {scenario["client"].name}')
        self.stdout.write(f'  - 1 accepted quote: {scenario["quote"].title}')
    
    def load_financial_scenario(self):
        """Load financial reporting scenario."""
        self.stdout.write('Creating financial reporting scenario...')
        
        scenario = create_financial_reporting_scenario()
        
        self.stdout.write(f'Created:')
        self.stdout.write(f'  - 1 user: {scenario["user"].email}')
        self.stdout.write(f'  - 1 client: {scenario["client"].name}')
        self.stdout.write(f'  - 2 paid invoices')
        self.stdout.write(f'  - 2 expenses')
        self.stdout.write(f'  - Expected revenue: ${scenario["expected_revenue"]}')
        self.stdout.write(f'  - Expected expenses: ${scenario["expected_expenses"]}')
        self.stdout.write(f'  - Expected profit: ${scenario["expected_profit"]}')
    
    def load_large_dataset(self, user_count):
        """Load large dataset for performance testing."""
        self.stdout.write(f'Creating large dataset with {user_count} users...')
        
        dataset = create_large_dataset(users=user_count)
        
        self.stdout.write(f'Created:')
        self.stdout.write(f'  - {len(dataset["users"])} users')
        self.stdout.write(f'  - {dataset["total_clients"]} clients')
        self.stdout.write(f'  - {dataset["total_quotes"]} quotes')
        self.stdout.write(f'  - {dataset["total_invoices"]} invoices')
    
    def load_json_fixtures(self, file_path):
        """Load fixtures from JSON file."""
        if not file_path:
            # Use default test_data.json
            file_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', 
                'test_data.json'
            )
        
        if not os.path.exists(file_path):
            raise CommandError(f'Fixture file not found: {file_path}')
        
        self.stdout.write(f'Loading fixtures from: {file_path}')
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Load users first
        users = {}
        for user_data in data.get('users', []):
            user = User.objects.create_user(
                email=user_data['email'],
                username=user_data['username'],
                password=user_data['password'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                is_active=user_data.get('is_active', True),
                is_staff=user_data.get('is_staff', False),
                is_superuser=user_data.get('is_superuser', False)
            )
            users[user_data['id']] = user
        
        # Load clients
        clients = {}
        for client_data in data.get('clients', []):
            owner = users[client_data['owner']]
            client = Client.objects.create(
                name=client_data['name'],
                email=client_data['email'],
                phone=client_data.get('phone', ''),
                address=client_data.get('address', ''),
                city=client_data.get('city', ''),
                state=client_data.get('state', ''),
                postal_code=client_data.get('postal_code', ''),
                country=client_data.get('country', 'USA'),
                owner=owner
            )
            clients[client_data['id']] = client
        
        # Load quotes
        quotes = {}
        for quote_data in data.get('quotes', []):
            owner = users[quote_data['owner']]
            client = clients[quote_data['client']]
            
            quote = Quote.objects.create(
                title=quote_data['title'],
                description=quote_data.get('description', ''),
                status=quote_data.get('status', 'draft'),
                tax_rate=Decimal(str(quote_data.get('tax_rate', 0.08))),
                notes=quote_data.get('notes', ''),
                valid_until=datetime.strptime(quote_data['valid_until'], '%Y-%m-%d').date(),
                owner=owner,
                client=client
            )
            
            # Create line items
            for item_data in quote_data.get('line_items', []):
                QuoteLineItem.objects.create(
                    quote=quote,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data['quantity'])),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    sort_order=item_data['sort_order']
                )
            
            quotes[quote_data['id']] = quote
        
        # Load invoices
        invoices = {}
        for invoice_data in data.get('invoices', []):
            owner = users[invoice_data['owner']]
            client = clients[invoice_data['client']]
            source_quote = quotes.get(invoice_data.get('source_quote')) if invoice_data.get('source_quote') else None
            
            invoice = Invoice.objects.create(
                title=invoice_data['title'],
                description=invoice_data.get('description', ''),
                status=invoice_data.get('status', 'draft'),
                tax_rate=Decimal(str(invoice_data.get('tax_rate', 0.08))),
                due_date=datetime.strptime(invoice_data['due_date'], '%Y-%m-%d').date(),
                paid_date=datetime.strptime(invoice_data['paid_date'], '%Y-%m-%d').date() if invoice_data.get('paid_date') else None,
                payment_method=invoice_data.get('payment_method'),
                notes=invoice_data.get('notes', ''),
                owner=owner,
                client=client,
                source_quote=source_quote
            )
            
            # Create line items
            for item_data in invoice_data.get('line_items', []):
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data['quantity'])),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    sort_order=item_data['sort_order']
                )
            
            invoices[invoice_data['id']] = invoice
        
        # Load expenses
        for expense_data in data.get('expenses', []):
            owner = users[expense_data['owner']]
            
            Expense.objects.create(
                description=expense_data['description'],
                amount=Decimal(str(expense_data['amount'])),
                date=datetime.strptime(expense_data['date'], '%Y-%m-%d').date(),
                category=expense_data.get('category', 'other'),
                receipt_url=expense_data.get('receipt_url'),
                owner=owner
            )
        
        self.stdout.write(f'Loaded:')
        self.stdout.write(f'  - {len(users)} users')
        self.stdout.write(f'  - {len(clients)} clients')
        self.stdout.write(f'  - {len(quotes)} quotes')
        self.stdout.write(f'  - {len(invoices)} invoices')
        self.stdout.write(f'  - {len(data.get("expenses", []))} expenses')