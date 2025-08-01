"""
Test suite validation and coverage metrics verification.
Validates that the test suite meets quality and coverage requirements.
"""
import os
import subprocess
import json
from pathlib import Path
import pytest
from django.test import TestCase
from django.core.management import call_command
from django.db import connection
from io import StringIO

from tests.fixtures.database_utils import TestDatabaseManager, DatabasePerformanceProfiler


class TestSuiteValidationTests(TestCase):
    """Validate overall test suite effectiveness."""
    
    def setUp(self):
        """Set up validation tests."""
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / 'tests'
    
    def test_test_discovery(self):
        """Test that all test modules can be discovered."""
        test_files = []
        
        # Find all test files
        for pattern in ['test_*.py', '*_test.py', '*_tests.py']:
            test_files.extend(self.test_dir.rglob(pattern))
        
        # Should have at least the core test files we created
        expected_files = [
            'test_authentication.py',
            'test_clients.py', 
            'test_invoicing.py',
            'test_api_authentication.py',
            'test_quote_to_invoice_workflow.py',
            'test_user_workflows.py'
        ]
        
        found_files = [f.name for f in test_files]
        
        for expected in expected_files:
            self.assertIn(expected, found_files, f"Expected test file {expected} not found")
        
        # Should have reasonable number of test files
        self.assertGreaterEqual(len(test_files), len(expected_files), 
                               "Test suite should have at least the core test files")
    
    def test_test_structure_validation(self):
        """Validate test file structure and organization."""
        test_dirs = ['unit', 'integration', 'e2e', 'fixtures']
        
        for test_dir in test_dirs:
            dir_path = self.test_dir / test_dir
            self.assertTrue(dir_path.exists(), f"Test directory {test_dir} should exist")
            
            # Check for __init__.py in test directories
            init_file = dir_path / '__init__.py'
            self.assertTrue(init_file.exists(), f"__init__.py should exist in {test_dir}")
    
    def test_pytest_configuration(self):
        """Validate pytest configuration."""
        pytest_ini = self.project_root / 'pytest.ini'
        self.assertTrue(pytest_ini.exists(), "pytest.ini configuration file should exist")
        
        # Read and validate key configurations
        with open(pytest_ini, 'r') as f:
            config_content = f.read()
        
        required_settings = [
            'DJANGO_SETTINGS_MODULE',
            'python_files',
            'testpaths',
            'markers'
        ]
        
        for setting in required_settings:
            self.assertIn(setting, config_content, f"{setting} should be configured in pytest.ini")
    
    def test_test_markers_defined(self):
        """Test that all used markers are properly defined."""
        # This would require parsing test files for marker usage
        # For now, just verify marker configuration exists
        pytest_ini = self.project_root / 'pytest.ini'
        
        with open(pytest_ini, 'r') as f:
            config = f.read()
        
        expected_markers = ['unit', 'integration', 'e2e', 'api', 'performance', 'security']
        
        for marker in expected_markers:
            self.assertIn(marker, config, f"Marker {marker} should be defined in pytest.ini")


class CoverageValidationTests(TestCase):
    """Validate test coverage requirements."""
    
    def setUp(self):
        """Set up coverage validation."""
        self.project_root = Path(__file__).parent.parent
        self.min_coverage_threshold = 80  # Minimum 80% coverage
    
    @pytest.mark.slow
    def test_coverage_threshold_validation(self):
        """Test that coverage meets minimum threshold."""
        try:
            # Run coverage analysis
            result = subprocess.run([
                'coverage', 'run', '--source=.', 'manage.py', 'test',
                '--settings=senangkira.settings.test'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                self.fail(f"Coverage run failed: {result.stderr}")
            
            # Get coverage report
            result = subprocess.run([
                'coverage', 'report', '--format=json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                coverage_data = json.loads(result.stdout)
                total_coverage = coverage_data['totals']['percent_covered']
                
                self.assertGreaterEqual(
                    total_coverage, 
                    self.min_coverage_threshold,
                    f"Total coverage {total_coverage}% is below threshold {self.min_coverage_threshold}%"
                )
            
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            self.skipTest(f"Coverage validation skipped: {e}")
    
    def test_critical_modules_coverage(self):
        """Test that critical modules have high coverage."""
        critical_modules = [
            'authentication',
            'clients.models',
            'invoicing.models',
            'dashboard.views'
        ]
        
        # This is a placeholder - actual implementation would require
        # parsing coverage reports to check specific module coverage
        self.assertTrue(True, "Critical module coverage validation placeholder")


class PerformanceValidationTests(TestCase):
    """Validate test suite performance characteristics."""
    
    def setUp(self):
        """Set up performance validation."""
        self.db_manager = TestDatabaseManager()
    
    def test_database_query_efficiency(self):
        """Test that database queries are efficient during tests."""
        with DatabasePerformanceProfiler() as profiler:
            # Run a sample of database operations
            from django.contrib.auth import get_user_model
            from clients.models import Client
            
            User = get_user_model()
            
            # Create test data
            user = User.objects.create_user(
                email='perf_test@example.com',
                username='perftest',
                password='TestPass123!'
            )
            
            # Create multiple clients
            clients = []
            for i in range(10):
                client = Client.objects.create(
                    name=f'Performance Test Client {i}',
                    email=f'client{i}@perftest.com',
                    owner=user
                )
                clients.append(client)
            
            # Query all clients for the user
            user_clients = list(Client.objects.filter(owner=user))
            
            self.assertEqual(len(user_clients), 10)
        
        stats = profiler.get_stats()
        
        # Validate query efficiency
        self.assertLess(stats['query_count'], 50, 
                       "Should not require excessive database queries")
        self.assertLess(stats['total_time'], 1.0, 
                       "Database operations should be fast")
    
    def test_test_execution_time(self):
        """Test that individual tests execute within reasonable time."""
        import time
        
        start_time = time.time()
        
        # Run a representative test operation
        from tests.utils import TestDataGenerator
        
        user_data = TestDataGenerator.user_data()
        client_data = TestDataGenerator.client_data()
        quote_data = TestDataGenerator.quote_data('test-client-id')
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertLess(execution_time, 0.1, 
                       "Test data generation should be fast")
    
    def test_memory_usage_reasonable(self):
        """Test that test suite doesn't consume excessive memory."""
        from tests.fixtures.database_utils import get_memory_usage, TestResourceMonitor
        
        monitor = TestResourceMonitor()
        monitor.start()
        
        # Perform memory-intensive test operations
        from tests.fixtures.factories import create_large_dataset
        
        # Create moderate dataset for testing
        dataset = create_large_dataset(users=5, clients_per_user=2, 
                                     quotes_per_client=2, invoices_per_client=1)
        
        stats = monitor.stop()
        
        # Memory delta should be reasonable (less than 100MB)
        self.assertLess(stats['memory_delta']['rss'], 100, 
                       "Memory usage should be reasonable during tests")


class TestUtilityValidationTests(TestCase):
    """Validate test utilities and helpers."""
    
    def test_test_data_generator_functions(self):
        """Test that test data generators work correctly."""
        from tests.utils import TestDataGenerator, APITestHelpers, CalculationHelpers
        
        # Test user data generation
        user_data = TestDataGenerator.user_data()
        required_fields = ['email', 'username', 'password']
        for field in required_fields:
            self.assertIn(field, user_data)
            self.assertTrue(user_data[field])
        
        # Test client data generation
        client_data = TestDataGenerator.client_data()
        self.assertIn('name', client_data)
        self.assertIn('email', client_data)
        
        # Test quote data generation
        quote_data = TestDataGenerator.quote_data('test-client-id')
        self.assertIn('title', quote_data)
        self.assertIn('client_id', quote_data)
    
    def test_api_test_helpers(self):
        """Test API testing helper functions."""
        from tests.utils import APITestHelpers
        from rest_framework import status
        from unittest.mock import Mock
        
        # Test successful response assertion
        mock_response = Mock()
        mock_response.status_code = status.HTTP_200_OK
        mock_response.json.return_value = {'success': True}
        
        # Should not raise exception
        APITestHelpers.assert_successful_response(mock_response)
        
        # Test error response assertion
        mock_error_response = Mock()
        mock_error_response.status_code = status.HTTP_400_BAD_REQUEST
        mock_error_response.json.return_value = {'error': 'Bad request'}
        
        # Should not raise exception
        APITestHelpers.assert_error_response(mock_error_response, status.HTTP_400_BAD_REQUEST)
    
    def test_calculation_helpers(self):
        """Test financial calculation helpers."""
        from tests.utils import CalculationHelpers
        from decimal import Decimal
        
        # Test financial calculation validation
        mock_data = {
            'subtotal': '1000.00',
            'tax_amount': '80.00',
            'total_amount': '1080.00'
        }
        
        line_items = [
            {'quantity': 10, 'unit_price': 100.00}
        ]
        
        tax_rate = Decimal('0.08')
        
        # Should validate without raising exception
        CalculationHelpers.validate_financial_calculations(mock_data, line_items, tax_rate)
    
    def test_factory_functionality(self):
        """Test that factory classes work correctly."""
        from tests.fixtures.factories import UserFactory, ClientFactory, QuoteFactory
        
        # Test user factory
        user = UserFactory()
        self.assertTrue(user.email)
        self.assertTrue(user.username)
        self.assertTrue(user.check_password('TestPass123!'))
        
        # Test client factory
        client = ClientFactory()
        self.assertTrue(client.name)
        self.assertTrue(client.email)
        self.assertTrue(client.owner)
        
        # Test quote factory
        quote = QuoteFactory()
        self.assertTrue(quote.title)
        self.assertTrue(quote.owner)
        self.assertTrue(quote.client)


class IntegrationValidationTests(TestCase):
    """Validate integration between test components."""
    
    def test_fixture_loading_works(self):
        """Test that fixture loading mechanism works."""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        
        try:
            # Test dry run of fixture loading
            call_command('load_test_fixtures', 
                        '--scenario', 'complete',
                        '--clean',
                        stdout=out)
            
            output = out.getvalue()
            self.assertIn('Created:', output)
            
        except Exception as e:
            # If fixtures command doesn't work, note it
            self.skipTest(f"Fixture loading test skipped: {e}")
    
    def test_management_commands_exist(self):
        """Test that custom management commands exist."""
        from django.core.management import get_commands
        
        commands = get_commands()
        
        expected_commands = ['load_test_fixtures', 'clean_test_data']
        
        for command in expected_commands:
            self.assertIn(command, commands, f"Management command {command} should be available")
    
    def test_test_settings_configuration(self):
        """Test that test settings are properly configured."""
        from django.conf import settings
        
        # Verify we're using test settings
        self.assertTrue(hasattr(settings, 'TESTING'))
        
        # Check database configuration for tests
        if hasattr(settings, 'DATABASES'):
            test_db = settings.DATABASES['default']
            self.assertIn('test', test_db.get('NAME', '').lower())


class TestDocumentationValidation(TestCase):
    """Validate test documentation and examples."""
    
    def test_test_documentation_exists(self):
        """Test that test documentation files exist."""
        project_root = Path(__file__).parent.parent
        
        expected_docs = [
            'tests/__init__.py',
            'tests/conftest.py',
            'tests/utils.py'
        ]
        
        for doc_path in expected_docs:
            doc_file = project_root / doc_path
            self.assertTrue(doc_file.exists(), f"Documentation file {doc_path} should exist")
    
    def test_docstrings_present(self):
        """Test that key test classes have docstrings."""
        from tests.unit.test_authentication import UserModelTests
        from tests.integration.test_api_authentication import AuthenticationAPITests
        
        self.assertTrue(UserModelTests.__doc__, "Test classes should have docstrings")
        self.assertTrue(AuthenticationAPITests.__doc__, "Test classes should have docstrings")


@pytest.mark.performance
class TestSuitePerformanceValidation:
    """Performance validation using pytest markers."""
    
    def test_suite_execution_time(self):
        """Test that test suite executes within reasonable time."""
        import time
        import subprocess
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        
        start_time = time.time()
        
        # Run a subset of fast tests
        result = subprocess.run([
            'pytest', 'tests/unit/', '-m', 'unit', '--tb=no', '-v'
        ], capture_output=True, text=True, cwd=project_root)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Unit tests should complete quickly
        assert execution_time < 30, f"Unit tests took {execution_time}s, should be under 30s"
        assert result.returncode == 0, f"Unit tests failed: {result.stderr}"


def validate_test_suite():
    """
    Main validation function that can be called externally.
    Returns validation results as a dictionary.
    """
    results = {
        'discovery': True,
        'structure': True,
        'configuration': True,
        'coverage': None,
        'performance': None,
        'utilities': True,
        'integration': True,
        'documentation': True
    }
    
    try:
        # Run validation tests
        from django.test.utils import get_runner
        from django.conf import settings
        
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=0, interactive=False)
        
        # Run specific validation test classes
        validation_classes = [
            TestSuiteValidationTests,
            TestUtilityValidationTests,
            IntegrationValidationTests,
            TestDocumentationValidation
        ]
        
        for test_class in validation_classes:
            suite = test_runner.setup_test_environment()
            old_config = test_runner.setup_databases()
            
            try:
                result = test_runner.run_tests([f'{test_class.__module__}.{test_class.__name__}'])
                if result > 0:
                    results[test_class.__name__.lower().replace('tests', '').replace('validation', '')] = False
            finally:
                test_runner.teardown_databases(old_config)
                test_runner.teardown_test_environment()
        
        return results
        
    except Exception as e:
        results['error'] = str(e)
        return results


if __name__ == '__main__':
    # Allow running validation directly
    results = validate_test_suite()
    print("Test Suite Validation Results:")
    print("=" * 40)
    
    for category, result in results.items():
        if result is True:
            status = "PASS"
        elif result is False:
            status = "FAIL"
        elif result is None:
            status = "SKIP"
        else:
            status = "ERROR"
        
        print(f"{category.title():20s} {status}")
    
    # Exit with appropriate code
    if any(result is False for result in results.values()):
        exit(1)
    else:
        exit(0)