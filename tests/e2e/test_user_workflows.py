"""
End-to-end tests for complete user workflows.
Tests full user journeys from login to task completion using browser automation.
"""
import pytest
import asyncio
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from playwright.async_api import async_playwright, expect

from clients.models import Client
from tests.utils import TestDataGenerator
from tests.e2e.conftest import PlaywrightTestCase

User = get_user_model()


class UserAuthenticationE2ETests(PlaywrightTestCase):
    """Test user authentication flows through the browser."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.user_data = TestDataGenerator.user_data(
            email='e2e-auth@example.com',
            username='e2eauthuser'
        )
        self.user = User.objects.create_user(**self.user_data)
    
    async def test_user_login_workflow(self):
        """Test complete user login workflow."""
        await self.setup_browser()
        
        try:
            # Navigate to login page
            await self.page.goto(f'{self.live_server_url}/login')
            
            # Verify login form is present
            await expect(self.page.locator('[data-testid="login-form"]')).to_be_visible()
            
            # Fill login form
            await self.page.fill('[data-testid="email-input"]', self.user_data['email'])
            await self.page.fill('[data-testid="password-input"]', self.user_data['password'])
            
            # Submit login form
            await self.page.click('[data-testid="login-button"]')
            
            # Wait for redirect to dashboard
            await self.page.wait_for_url(f'{self.live_server_url}/dashboard', timeout=5000)
            
            # Verify user is logged in
            await expect(self.page.locator('[data-testid="user-menu"]')).to_be_visible()
            await expect(self.page.locator('[data-testid="dashboard-title"]')).to_contain_text('Dashboard')
            
        finally:
            await self.teardown_browser()
    
    async def test_invalid_login_attempt(self):
        """Test login with invalid credentials."""
        await self.setup_browser()
        
        try:
            await self.page.goto(f'{self.live_server_url}/login')
            
            # Fill with invalid credentials
            await self.page.fill('[data-testid="email-input"]', self.user_data['email'])
            await self.page.fill('[data-testid="password-input"]', 'wrong_password')
            
            # Submit form
            await self.page.click('[data-testid="login-button"]')
            
            # Should remain on login page with error
            await expect(self.page.locator('[data-testid="error-message"]')).to_be_visible()
            await expect(self.page.locator('[data-testid="error-message"]')).to_contain_text('Invalid credentials')
            
        finally:
            await self.teardown_browser()
    
    async def test_user_logout_workflow(self):
        """Test user logout workflow."""
        await self.setup_browser()
        
        try:
            # Login first
            await self.login_user(self.user_data['email'], self.user_data['password'])
            
            # Click user menu
            await self.page.click('[data-testid="user-menu"]')
            
            # Click logout
            await self.page.click('[data-testid="logout-button"]')
            
            # Should redirect to login page
            await self.page.wait_for_url(f'{self.live_server_url}/login')
            
            # Verify user is logged out
            await expect(self.page.locator('[data-testid="login-form"]')).to_be_visible()
            
        finally:
            await self.teardown_browser()


class ClientManagementE2ETests(PlaywrightTestCase):
    """Test client management workflows through the browser."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.user = User.objects.create_user(
            email='e2e-client@example.com',
            username='e2eclientuser',
            password='ClientPass123!'
        )
    
    async def test_create_client_workflow(self):
        """Test complete client creation workflow."""
        await self.setup_browser()
        
        try:
            # Login
            await self.login_user('e2e-client@example.com', 'ClientPass123!')
            
            # Navigate to clients
            await self.navigate_to_clients()
            
            # Click create client button
            await self.page.click('[data-testid="create-client-button"]')
            
            # Fill client form
            client_data = TestDataGenerator.client_data(name='E2E Test Client')
            
            await self.page.fill('[data-testid="client-name-input"]', client_data['name'])
            await self.page.fill('[data-testid="client-email-input"]', client_data['email'])
            await self.page.fill('[data-testid="client-phone-input"]', client_data['phone'])
            await self.page.fill('[data-testid="client-address-input"]', client_data['address'])
            await self.page.fill('[data-testid="client-city-input"]', client_data['city'])
            
            # Submit form
            await self.page.click('[data-testid="save-client-button"]')
            
            # Wait for redirect and success notification
            await self.assert_notification('Client created successfully')
            
            # Verify client appears in list
            await expect(self.page.locator(f'[data-testid="client-{client_data["name"]}"]')).to_be_visible()
            
        finally:
            await self.teardown_browser()
    
    async def test_edit_client_workflow(self):
        """Test client editing workflow."""
        # Create client first
        client = Client.objects.create(
            name='Edit Test Client',
            email='edit@client.com',
            owner=self.user
        )
        
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-client@example.com', 'ClientPass123!')
            await self.navigate_to_clients()
            
            # Click edit button for the client
            await self.page.click(f'[data-testid="edit-client-{client.id}"]')
            
            # Update client name
            updated_name = 'Updated E2E Client'
            await self.page.fill('[data-testid="client-name-input"]', updated_name)
            
            # Save changes
            await self.page.click('[data-testid="save-client-button"]')
            
            # Verify update success
            await self.assert_notification('Client updated successfully')
            await expect(self.page.locator(f'[data-testid="client-{updated_name}"]')).to_be_visible()
            
        finally:
            await self.teardown_browser()


class QuoteWorkflowE2ETests(PlaywrightTestCase):
    """Test quote management workflows through the browser."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.user = User.objects.create_user(
            email='e2e-quote@example.com',
            username='e2equoteuser',
            password='QuotePass123!'
        )
        
        self.client = Client.objects.create(
            name='Quote Test Client',
            email='quote@client.com',
            owner=self.user
        )
    
    async def test_complete_quote_creation_workflow(self):
        """Test complete quote creation and management workflow."""
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-quote@example.com', 'QuotePass123!')
            await self.navigate_to_quotes()
            
            # Create new quote
            await self.page.click('[data-testid="create-quote-button"]')
            
            # Fill quote form
            await self.page.fill('[data-testid="quote-title-input"]', 'E2E Test Quote')
            await self.page.fill('[data-testid="quote-description-input"]', 'E2E test quote description')
            
            # Select client
            await self.page.click('[data-testid="client-select"]')
            await self.page.click(f'[data-testid="client-option-{self.client.id}"]')
            
            # Add line items
            await self.fill_line_item(0, 'Development Services', '40', '125.00')
            await self.page.click('[data-testid="add-line-item-button"]')
            await self.fill_line_item(1, 'Design Services', '20', '150.00')
            
            # Set tax rate
            await self.page.fill('[data-testid="tax-rate-input"]', '8.0')
            
            # Save quote
            await self.page.click('[data-testid="save-quote-button"]')
            
            # Verify quote created
            await self.assert_notification('Quote created successfully')
            
            # Verify calculations
            await expect(self.page.locator('[data-testid="quote-subtotal"]')).to_contain_text('$8,000.00')
            await expect(self.page.locator('[data-testid="quote-total"]')).to_contain_text('$8,640.00')
            
        finally:
            await self.teardown_browser()
    
    async def test_quote_send_and_approve_workflow(self):
        """Test quote sending and approval workflow."""
        from invoicing.models import Quote, QuoteLineItem
        
        # Create quote through models
        quote = Quote.objects.create(
            title='Send Test Quote',
            tax_rate=0.08,
            owner=self.user,
            client=self.client
        )
        
        QuoteLineItem.objects.create(
            quote=quote,
            description='Test Service',
            quantity=10,
            unit_price=100,
            sort_order=0
        )
        
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-quote@example.com', 'QuotePass123!')
            await self.navigate_to_quotes()
            
            # Find and open the quote
            await self.page.click(f'[data-testid="quote-{quote.id}"]')
            
            # Send quote
            await self.page.click('[data-testid="send-quote-button"]')
            await self.assert_notification('Quote sent successfully')
            
            # Verify status changed
            await expect(self.page.locator('[data-testid="quote-status"]')).to_contain_text('Sent')
            
            # Approve quote
            await self.page.click('[data-testid="approve-quote-button"]')
            await self.assert_notification('Quote approved successfully')
            
            # Verify status changed
            await expect(self.page.locator('[data-testid="quote-status"]')).to_contain_text('Accepted')
            
            # Verify convert to invoice button is available
            await expect(self.page.locator('[data-testid="convert-to-invoice-button"]')).to_be_visible()
            
        finally:
            await self.teardown_browser()


class InvoiceWorkflowE2ETests(PlaywrightTestCase):
    """Test invoice management workflows through the browser."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.user = User.objects.create_user(
            email='e2e-invoice@example.com',
            username='e2einvoiceuser',
            password='InvoicePass123!'
        )
        
        self.client = Client.objects.create(
            name='Invoice Test Client',
            email='invoice@client.com',
            owner=self.user
        )
    
    async def test_quote_to_invoice_conversion_workflow(self):
        """Test complete quote to invoice conversion workflow."""
        from invoicing.models import Quote, QuoteLineItem, QuoteStatus
        
        # Create approved quote
        quote = Quote.objects.create(
            title='Conversion Test Quote',
            tax_rate=0.08,
            status=QuoteStatus.ACCEPTED,
            owner=self.user,
            client=self.client
        )
        
        QuoteLineItem.objects.create(
            quote=quote,
            description='Conversion Service',
            quantity=15,
            unit_price=120,
            sort_order=0
        )
        
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-invoice@example.com', 'InvoicePass123!')
            await self.navigate_to_quotes()
            
            # Open quote
            await self.page.click(f'[data-testid="quote-{quote.id}"]')
            
            # Convert to invoice
            await self.page.click('[data-testid="convert-to-invoice-button"]')
            
            # Fill conversion form
            from datetime import date, timedelta
            due_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
            await self.page.fill('[data-testid="due-date-input"]', due_date)
            await self.page.fill('[data-testid="invoice-notes-input"]', 'Converted from quote')
            
            # Submit conversion
            await self.page.click('[data-testid="convert-button"]')
            
            # Should redirect to invoice
            await self.page.wait_for_url(f'{self.live_server_url}/invoices/*')
            
            # Verify invoice details
            await expect(self.page.locator('[data-testid="invoice-title"]')).to_contain_text('Conversion Test Quote')
            await expect(self.page.locator('[data-testid="invoice-subtotal"]')).to_contain_text('$1,800.00')
            await expect(self.page.locator('[data-testid="invoice-total"]')).to_contain_text('$1,944.00')
            
            # Verify source quote reference
            await expect(self.page.locator('[data-testid="source-quote"]')).to_contain_text(str(quote.id))
            
        finally:
            await self.teardown_browser()
    
    async def test_invoice_payment_workflow(self):
        """Test invoice payment marking workflow."""
        from invoicing.models import Invoice, InvoiceLineItem
        
        # Create sent invoice
        invoice = Invoice.objects.create(
            title='Payment Test Invoice',
            tax_rate=0.08,
            status='sent',
            owner=self.user,
            client=self.client
        )
        
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description='Payment Service',
            quantity=10,
            unit_price=200,
            sort_order=0
        )
        
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-invoice@example.com', 'InvoicePass123!')
            await self.navigate_to_invoices()
            
            # Open invoice
            await self.page.click(f'[data-testid="invoice-{invoice.id}"]')
            
            # Mark as paid
            await self.page.click('[data-testid="mark-paid-button"]')
            
            # Fill payment form
            from datetime import date
            payment_date = date.today().strftime('%Y-%m-%d')
            await self.page.fill('[data-testid="payment-date-input"]', payment_date)
            await self.page.select_option('[data-testid="payment-method-select"]', 'bank_transfer')
            await self.page.fill('[data-testid="payment-notes-input"]', 'Payment received via bank transfer')
            
            # Submit payment
            await self.page.click('[data-testid="confirm-payment-button"]')
            
            # Verify payment recorded
            await self.assert_notification('Invoice marked as paid')
            await expect(self.page.locator('[data-testid="invoice-status"]')).to_contain_text('Paid')
            await expect(self.page.locator('[data-testid="payment-date"]')).to_contain_text(payment_date)
            
        finally:
            await self.teardown_browser()


class DashboardWorkflowE2ETests(PlaywrightTestCase):
    """Test dashboard functionality through the browser."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.user = User.objects.create_user(
            email='e2e-dashboard@example.com',
            username='e2edashboarduser',
            password='DashboardPass123!'
        )
    
    async def test_dashboard_overview_workflow(self):
        """Test dashboard overview and navigation."""
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-dashboard@example.com', 'DashboardPass123!')
            
            # Should be on dashboard after login
            await expect(self.page.locator('[data-testid="dashboard-title"]')).to_be_visible()
            
            # Verify key metrics are displayed
            await expect(self.page.locator('[data-testid="total-revenue"]')).to_be_visible()
            await expect(self.page.locator('[data-testid="total-expenses"]')).to_be_visible()
            await expect(self.page.locator('[data-testid="net-profit"]')).to_be_visible()
            
            # Test navigation to different sections
            await self.page.click('[data-testid="view-quotes-link"]')
            await self.page.wait_for_url(f'{self.live_server_url}/quotes')
            
            await self.page.go_back()
            await self.page.click('[data-testid="view-invoices-link"]')
            await self.page.wait_for_url(f'{self.live_server_url}/invoices')
            
            await self.page.go_back()
            await self.page.click('[data-testid="view-clients-link"]')
            await self.page.wait_for_url(f'{self.live_server_url}/clients')
            
            # Return to dashboard
            await self.page.click('[data-testid="dashboard-nav"]')
            await self.page.wait_for_url(f'{self.live_server_url}/dashboard')
            
        finally:
            await self.teardown_browser()
    
    async def test_dashboard_refresh_workflow(self):
        """Test dashboard data refresh functionality."""
        await self.setup_browser()
        
        try:
            await self.login_user('e2e-dashboard@example.com', 'DashboardPass123!')
            
            # Click refresh button
            await self.page.click('[data-testid="refresh-dashboard-button"]')
            
            # Wait for API call to complete
            await self.wait_for_api_response('/api/dashboard/refresh')
            
            # Verify refresh notification
            await self.assert_notification('Dashboard data refreshed')
            
            # Verify loading state handled properly
            refresh_button = self.page.locator('[data-testid="refresh-dashboard-button"]')
            await expect(refresh_button).not_to_be_disabled()
            
        finally:
            await self.teardown_browser()


# Utility function for running async tests in Django TestCase
def run_async_test(test_func):
    """Utility to run async test functions in Django TestCase."""
    def wrapper(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_func(self))
        finally:
            loop.close()
    return wrapper


# Apply async wrapper to test methods
for attr_name in dir(UserAuthenticationE2ETests):
    if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(UserAuthenticationE2ETests, attr_name)):
        setattr(UserAuthenticationE2ETests, attr_name, run_async_test(getattr(UserAuthenticationE2ETests, attr_name)))

for attr_name in dir(ClientManagementE2ETests):
    if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(ClientManagementE2ETests, attr_name)):
        setattr(ClientManagementE2ETests, attr_name, run_async_test(getattr(ClientManagementE2ETests, attr_name)))

for attr_name in dir(QuoteWorkflowE2ETests):
    if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(QuoteWorkflowE2ETests, attr_name)):
        setattr(QuoteWorkflowE2ETests, attr_name, run_async_test(getattr(QuoteWorkflowE2ETests, attr_name)))

for attr_name in dir(InvoiceWorkflowE2ETests):
    if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(InvoiceWorkflowE2ETests, attr_name)):
        setattr(InvoiceWorkflowE2ETests, attr_name, run_async_test(getattr(InvoiceWorkflowE2ETests, attr_name)))

for attr_name in dir(DashboardWorkflowE2ETests):
    if attr_name.startswith('test_') and asyncio.iscoroutinefunction(getattr(DashboardWorkflowE2ETests, attr_name)):
        setattr(DashboardWorkflowE2ETests, attr_name, run_async_test(getattr(DashboardWorkflowE2ETests, attr_name)))