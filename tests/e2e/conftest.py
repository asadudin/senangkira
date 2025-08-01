"""
Playwright configuration and fixtures for E2E testing.
Provides browser setup, page fixtures, and test utilities.
"""
import pytest
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from clients.models import Client
from tests.utils import TestDataGenerator

User = get_user_model()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for testing session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Set to False for debugging
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        yield browser
        await browser.close()


@pytest.fixture
async def browser_context(browser: Browser):
    """Create browser context for test isolation."""
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        ignore_https_errors=True,
        permissions=['clipboard-read', 'clipboard-write']
    )
    yield context
    await context.close()


@pytest.fixture
async def page(browser_context: BrowserContext):
    """Create page instance for testing."""
    page = await browser_context.new_page()
    yield page
    await page.close()


@pytest.fixture
def live_server():
    """Django live server for E2E testing."""
    from django.test import LiveServerTestCase
    from threading import Thread
    import socket
    
    # Find available port
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    
    # This is a simplified version - in practice you'd use Django's LiveServerTestCase
    # or pytest-django's live_server fixture
    return f'http://localhost:{port}'


@pytest.fixture
def test_user():
    """Create test user for E2E testing."""
    user_data = TestDataGenerator.user_data(
        email='e2e@example.com',
        username='e2euser'
    )
    return User.objects.create_user(**user_data)


@pytest.fixture
def test_client_model(test_user):
    """Create test client for E2E testing."""
    return Client.objects.create(
        name='E2E Test Client',
        email='client@e2e.com',
        phone='+1234567890',
        owner=test_user
    )


class PlaywrightTestCase(TransactionTestCase):
    """Base test case for Playwright E2E tests."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.live_server_url = 'http://localhost:8000'  # Adjust based on your setup
    
    async def setup_browser(self):
        """Setup browser for testing."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()
    
    async def teardown_browser(self):
        """Cleanup browser after testing."""
        await self.page.close()
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()
    
    async def login_user(self, email: str, password: str):
        """Login user through UI."""
        await self.page.goto(f'{self.live_server_url}/login')
        await self.page.fill('[data-testid="email-input"]', email)
        await self.page.fill('[data-testid="password-input"]', password)
        await self.page.click('[data-testid="login-button"]')
        
        # Wait for redirect to dashboard
        await self.page.wait_for_url(f'{self.live_server_url}/dashboard')
    
    async def navigate_to_quotes(self):
        """Navigate to quotes page."""
        await self.page.click('[data-testid="quotes-nav"]')
        await self.page.wait_for_url(f'{self.live_server_url}/quotes')
    
    async def navigate_to_invoices(self):
        """Navigate to invoices page.""" 
        await self.page.click('[data-testid="invoices-nav"]')
        await self.page.wait_for_url(f'{self.live_server_url}/invoices')
    
    async def navigate_to_clients(self):
        """Navigate to clients page."""
        await self.page.click('[data-testid="clients-nav"]')
        await self.page.wait_for_url(f'{self.live_server_url}/clients')
    
    async def wait_for_api_response(self, url_pattern: str):
        """Wait for specific API response."""
        await self.page.wait_for_response(
            lambda response: url_pattern in response.url and response.status == 200
        )
    
    async def take_screenshot(self, name: str):
        """Take screenshot for debugging."""
        await self.page.screenshot(path=f'tests/screenshots/{name}.png')
    
    async def assert_notification(self, message: str):
        """Assert notification message appears."""
        notification = self.page.locator('[data-testid="notification"]')
        await notification.wait_for(state='visible')
        await expect(notification).to_contain_text(message)
    
    async def fill_line_item(self, index: int, description: str, quantity: str, unit_price: str):
        """Fill line item in quote/invoice form."""
        await self.page.fill(f'[data-testid="line-item-{index}-description"]', description)
        await self.page.fill(f'[data-testid="line-item-{index}-quantity"]', quantity)
        await self.page.fill(f'[data-testid="line-item-{index}-unit-price"]', unit_price)


# Pytest fixtures for async support
@pytest.fixture
def playwright_test_case():
    """Fixture to provide PlaywrightTestCase functionality."""
    return PlaywrightTestCase()


# Helper for Playwright expect
try:
    from playwright.sync_api import expect
except ImportError:
    # Fallback if Playwright not installed
    def expect(locator):
        return locator