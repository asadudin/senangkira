"""
Django management command to clean test data.
Usage: python manage.py clean_test_data [--confirm]
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from clients.models import Client
from invoicing.models import Quote, Invoice, QuoteLineItem, InvoiceLineItem
from expenses.models import Expense

User = get_user_model()


class Command(BaseCommand):
    """Clean test data from the database."""
    
    help = 'Clean test data from the database'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without interactive prompt'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        confirm = options['confirm']
        dry_run = options['dry_run']
        
        # Count existing test data
        test_users = User.objects.filter(
            email__contains='senangkira.com'
        ).union(
            User.objects.filter(username__startswith='test')
        )
        
        test_clients = Client.objects.filter(owner__in=test_users)
        test_quotes = Quote.objects.filter(owner__in=test_users)
        test_invoices = Invoice.objects.filter(owner__in=test_users)
        test_expenses = Expense.objects.filter(owner__in=test_users)
        test_quote_items = QuoteLineItem.objects.filter(quote__owner__in=test_users)
        test_invoice_items = InvoiceLineItem.objects.filter(invoice__owner__in=test_users)
        
        # Show what will be deleted
        self.stdout.write('Test data to be deleted:')
        self.stdout.write(f'  - {test_users.count()} test users')
        self.stdout.write(f'  - {test_clients.count()} test clients')
        self.stdout.write(f'  - {test_quotes.count()} test quotes')
        self.stdout.write(f'  - {test_quote_items.count()} test quote line items')
        self.stdout.write(f'  - {test_invoices.count()} test invoices')
        self.stdout.write(f'  - {test_invoice_items.count()} test invoice line items')
        self.stdout.write(f'  - {test_expenses.count()} test expenses')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No data was actually deleted'))
            return
        
        # Confirm deletion
        if not confirm:
            confirm = input('Are you sure you want to delete all test data? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write('Operation cancelled')
                return
        
        try:
            with transaction.atomic():
                # Delete in reverse order of dependencies
                deleted_counts = {}
                
                deleted_counts['invoice_items'] = test_invoice_items.delete()[0]
                deleted_counts['quote_items'] = test_quote_items.delete()[0]
                deleted_counts['invoices'] = test_invoices.delete()[0]
                deleted_counts['quotes'] = test_quotes.delete()[0]
                deleted_counts['expenses'] = test_expenses.delete()[0]
                deleted_counts['clients'] = test_clients.delete()[0]
                deleted_counts['users'] = test_users.delete()[0]
                
                self.stdout.write(self.style.SUCCESS('Successfully deleted test data:'))
                for item_type, count in deleted_counts.items():
                    self.stdout.write(f'  - {count} {item_type}')
                
        except Exception as e:
            raise CommandError(f'Failed to clean test data: {str(e)}')