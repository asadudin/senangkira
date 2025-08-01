#!/usr/bin/env python
"""
Test Suite Validation Script
Comprehensive validation of the test suite implementation and effectiveness.
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings.test')

import django
django.setup()

from tests.test_coverage_validation import validate_test_suite


class TestSuiteValidator:
    """Comprehensive test suite validator."""
    
    def __init__(self):
        self.project_root = project_root
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_validation(self):
        """Run complete validation suite."""
        self.start_time = time.time()
        print("🧪 SenangKira Test Suite Validation")
        print("=" * 50)
        print(f"Starting validation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run validation categories
        self.validate_structure()
        self.validate_configuration()
        self.validate_dependencies()
        self.validate_test_execution()
        self.validate_coverage()
        self.validate_performance()
        self.validate_documentation()
        
        self.end_time = time.time()
        self.generate_report()
        
        return self.results
    
    def validate_structure(self):
        """Validate test suite structure."""
        print("📁 Validating test suite structure...")
        
        structure_checks = {
            'test_directories': self._check_test_directories(),
            'test_files': self._check_test_files(),
            'init_files': self._check_init_files(),
            'fixture_structure': self._check_fixture_structure()
        }
        
        self.results['structure'] = structure_checks
        self._print_category_results('Structure', structure_checks)
    
    def validate_configuration(self):
        """Validate test configuration files."""
        print("⚙️  Validating test configuration...")
        
        config_checks = {
            'pytest_ini': self._check_pytest_config(),
            'tox_ini': self._check_tox_config(),
            'makefile': self._check_makefile(),
            'github_workflow': self._check_github_workflow(),
            'requirements': self._check_test_requirements()
        }
        
        self.results['configuration'] = config_checks
        self._print_category_results('Configuration', config_checks)
    
    def validate_dependencies(self):
        """Validate test dependencies."""
        print("📦 Validating test dependencies...")
        
        dependency_checks = {
            'test_requirements': self._check_dependencies_installed(),
            'playwright': self._check_playwright_setup(),
            'database': self._check_database_setup()
        }
        
        self.results['dependencies'] = dependency_checks
        self._print_category_results('Dependencies', dependency_checks)
    
    def validate_test_execution(self):
        """Validate test execution."""
        print("🔬 Validating test execution...")
        
        execution_checks = {
            'unit_tests': self._run_unit_tests(),
            'integration_tests': self._run_integration_tests(),
            'test_discovery': self._check_test_discovery(),
            'fixtures': self._check_fixture_loading()
        }
        
        self.results['execution'] = execution_checks
        self._print_category_results('Execution', execution_checks)
    
    def validate_coverage(self):
        """Validate test coverage."""
        print("📊 Validating test coverage...")
        
        coverage_checks = {
            'coverage_run': self._run_coverage_analysis(),
            'coverage_threshold': self._check_coverage_threshold(),
            'coverage_report': self._generate_coverage_report()
        }
        
        self.results['coverage'] = coverage_checks
        self._print_category_results('Coverage', coverage_checks)
    
    def validate_performance(self):
        """Validate test performance."""
        print("⚡ Validating test performance...")
        
        performance_checks = {
            'execution_time': self._check_execution_time(),
            'memory_usage': self._check_memory_usage(),
            'database_queries': self._check_database_efficiency()
        }
        
        self.results['performance'] = performance_checks
        self._print_category_results('Performance', performance_checks)
    
    def validate_documentation(self):
        """Validate test documentation."""
        print("📖 Validating test documentation...")
        
        doc_checks = {
            'docstrings': self._check_docstrings(),
            'readme': self._check_test_readme(),
            'examples': self._check_test_examples()
        }
        
        self.results['documentation'] = doc_checks
        self._print_category_results('Documentation', doc_checks)
    
    # Structure validation methods
    def _check_test_directories(self):
        """Check that required test directories exist."""
        required_dirs = ['tests', 'tests/unit', 'tests/integration', 'tests/e2e', 'tests/fixtures']
        missing_dirs = []
        
        for dir_path in required_dirs:
            if not (self.project_root / dir_path).exists():
                missing_dirs.append(dir_path)
        
        return {
            'passed': len(missing_dirs) == 0,
            'message': f"Missing directories: {missing_dirs}" if missing_dirs else "All required directories exist",
            'details': {'missing': missing_dirs, 'required': required_dirs}
        }
    
    def _check_test_files(self):
        """Check that core test files exist."""
        required_files = [
            'tests/__init__.py',
            'tests/conftest.py',
            'tests/utils.py',
            'tests/unit/test_authentication.py',
            'tests/unit/test_clients.py',
            'tests/unit/test_invoicing.py',
            'tests/integration/test_api_authentication.py',
            'tests/integration/test_quote_to_invoice_workflow.py',
            'tests/e2e/test_user_workflows.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        return {
            'passed': len(missing_files) == 0,
            'message': f"Missing files: {missing_files}" if missing_files else "All required test files exist",
            'details': {'missing': missing_files, 'required': required_files}
        }
    
    def _check_init_files(self):
        """Check that __init__.py files exist in test directories."""
        test_dirs = ['tests', 'tests/unit', 'tests/integration', 'tests/e2e', 'tests/fixtures']
        missing_init = []
        
        for dir_path in test_dirs:
            init_file = self.project_root / dir_path / '__init__.py'
            if not init_file.exists():
                missing_init.append(f"{dir_path}/__init__.py")
        
        return {
            'passed': len(missing_init) == 0,
            'message': f"Missing __init__.py files: {missing_init}" if missing_init else "All __init__.py files exist",
            'details': {'missing': missing_init}
        }
    
    def _check_fixture_structure(self):
        """Check fixture structure."""
        fixture_files = [
            'tests/fixtures/__init__.py',
            'tests/fixtures/factories.py',
            'tests/fixtures/test_data.json',
            'tests/fixtures/database_utils.py'
        ]
        
        missing_fixtures = []
        for file_path in fixture_files:
            if not (self.project_root / file_path).exists():
                missing_fixtures.append(file_path)
        
        return {
            'passed': len(missing_fixtures) == 0,
            'message': f"Missing fixture files: {missing_fixtures}" if missing_fixtures else "All fixture files exist",
            'details': {'missing': missing_fixtures}
        }
    
    # Configuration validation methods
    def _check_pytest_config(self):
        """Check pytest configuration."""
        pytest_ini = self.project_root / 'pytest.ini'
        
        if not pytest_ini.exists():
            return {'passed': False, 'message': 'pytest.ini not found'}
        
        with open(pytest_ini, 'r') as f:
            content = f.read()
        
        required_sections = ['DJANGO_SETTINGS_MODULE', 'python_files', 'markers', 'testpaths']
        missing_sections = [section for section in required_sections if section not in content]
        
        return {
            'passed': len(missing_sections) == 0,
            'message': f"Missing sections: {missing_sections}" if missing_sections else "pytest.ini properly configured",
            'details': {'missing': missing_sections}
        }
    
    def _check_tox_config(self):
        """Check tox configuration."""
        tox_ini = self.project_root / 'tox.ini'
        return {
            'passed': tox_ini.exists(),
            'message': 'tox.ini exists' if tox_ini.exists() else 'tox.ini not found'
        }
    
    def _check_makefile(self):
        """Check Makefile."""
        makefile = self.project_root / 'Makefile'
        
        if not makefile.exists():
            return {'passed': False, 'message': 'Makefile not found'}
        
        with open(makefile, 'r') as f:
            content = f.read()
        
        required_targets = ['test', 'test-unit', 'test-integration', 'test-e2e', 'test-coverage']
        missing_targets = [target for target in required_targets if target not in content]
        
        return {
            'passed': len(missing_targets) == 0,
            'message': f"Missing targets: {missing_targets}" if missing_targets else "Makefile properly configured",
            'details': {'missing': missing_targets}
        }
    
    def _check_github_workflow(self):
        """Check GitHub workflow."""
        workflow_file = self.project_root / '.github' / 'workflows' / 'test.yml'
        return {
            'passed': workflow_file.exists(),
            'message': 'GitHub workflow exists' if workflow_file.exists() else 'GitHub workflow not found'
        }
    
    def _check_test_requirements(self):
        """Check test requirements file."""
        requirements_file = self.project_root / 'requirements-test.txt'
        
        if not requirements_file.exists():
            return {'passed': False, 'message': 'requirements-test.txt not found'}
        
        with open(requirements_file, 'r') as f:
            content = f.read()
        
        required_packages = ['pytest', 'pytest-django', 'factory_boy', 'playwright']
        missing_packages = [pkg for pkg in required_packages if pkg not in content]
        
        return {
            'passed': len(missing_packages) == 0,
            'message': f"Missing packages: {missing_packages}" if missing_packages else "All required test packages listed",
            'details': {'missing': missing_packages}
        }
    
    # Dependency validation methods
    def _check_dependencies_installed(self):
        """Check if test dependencies are installed."""
        try:
            import pytest
            import factory
            import playwright
            return {'passed': True, 'message': 'Core test dependencies installed'}
        except ImportError as e:
            return {'passed': False, 'message': f'Missing dependency: {e}'}
    
    def _check_playwright_setup(self):
        """Check Playwright setup."""
        try:
            from playwright.sync_api import sync_playwright
            return {'passed': True, 'message': 'Playwright properly installed'}
        except ImportError:
            return {'passed': False, 'message': 'Playwright not installed'}
    
    def _check_database_setup(self):
        """Check database setup for tests."""
        try:
            from django.db import connection
            connection.ensure_connection()
            return {'passed': True, 'message': 'Database connection successful'}
        except Exception as e:
            return {'passed': False, 'message': f'Database setup issue: {e}'}
    
    # Execution validation methods
    def _run_unit_tests(self):
        """Run unit tests to validate execution."""
        try:
            result = subprocess.run([
                'pytest', 'tests/unit/', '-v', '--tb=short', '-x'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)
            
            return {
                'passed': result.returncode == 0,
                'message': 'Unit tests pass' if result.returncode == 0 else 'Unit tests failed',
                'details': {'stdout': result.stdout, 'stderr': result.stderr}
            }
        except subprocess.TimeoutExpired:
            return {'passed': False, 'message': 'Unit tests timed out'}
        except Exception as e:
            return {'passed': False, 'message': f'Error running unit tests: {e}'}
    
    def _run_integration_tests(self):
        """Run integration tests to validate execution."""
        try:
            result = subprocess.run([
                'pytest', 'tests/integration/', '-v', '--tb=short', '-x'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=120)
            
            return {
                'passed': result.returncode == 0,
                'message': 'Integration tests pass' if result.returncode == 0 else 'Integration tests failed',
                'details': {'stdout': result.stdout, 'stderr': result.stderr}
            }
        except subprocess.TimeoutExpired:
            return {'passed': False, 'message': 'Integration tests timed out'}
        except Exception as e:
            return {'passed': False, 'message': f'Error running integration tests: {e}'}
    
    def _check_test_discovery(self):
        """Check test discovery."""
        try:
            result = subprocess.run([
                'pytest', '--collect-only', '-q'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0 and 'collected' in result.stdout:
                return {'passed': True, 'message': 'Test discovery successful'}
            else:
                return {'passed': False, 'message': 'Test discovery failed'}
        except Exception as e:
            return {'passed': False, 'message': f'Error in test discovery: {e}'}
    
    def _check_fixture_loading(self):
        """Check fixture loading functionality."""
        try:
            from django.core.management import call_command
            from io import StringIO
            
            out = StringIO()
            call_command('load_test_fixtures', '--scenario', 'complete', '--clean', stdout=out)
            
            return {'passed': True, 'message': 'Fixture loading works'}
        except Exception as e:
            return {'passed': False, 'message': f'Fixture loading failed: {e}'}
    
    # Coverage validation methods
    def _run_coverage_analysis(self):
        """Run coverage analysis."""
        try:
            result = subprocess.run([
                'coverage', 'run', '--source=.', 'manage.py', 'test',
                '--settings=senangkira.settings.test'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=180)
            
            return {
                'passed': result.returncode == 0,
                'message': 'Coverage analysis completed' if result.returncode == 0 else 'Coverage analysis failed'
            }
        except subprocess.TimeoutExpired:
            return {'passed': False, 'message': 'Coverage analysis timed out'}
        except Exception as e:
            return {'passed': False, 'message': f'Coverage analysis error: {e}'}
    
    def _check_coverage_threshold(self):
        """Check coverage threshold."""
        try:
            result = subprocess.run([
                'coverage', 'report', '--format=json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                coverage_data = json.loads(result.stdout)
                total_coverage = coverage_data['totals']['percent_covered']
                threshold = 80
                
                return {
                    'passed': total_coverage >= threshold,
                    'message': f'Coverage: {total_coverage:.1f}% (threshold: {threshold}%)',
                    'details': {'coverage': total_coverage, 'threshold': threshold}
                }
            else:
                return {'passed': False, 'message': 'Could not generate coverage report'}
        except Exception as e:
            return {'passed': False, 'message': f'Coverage threshold check failed: {e}'}
    
    def _generate_coverage_report(self):
        """Generate coverage report."""
        try:
            result = subprocess.run([
                'coverage', 'html'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            report_path = self.project_root / 'htmlcov' / 'index.html'
            
            return {
                'passed': result.returncode == 0 and report_path.exists(),
                'message': 'Coverage HTML report generated' if result.returncode == 0 else 'Coverage report failed',
                'details': {'report_path': str(report_path)}
            }
        except Exception as e:
            return {'passed': False, 'message': f'Coverage report generation failed: {e}'}
    
    # Performance validation methods
    def _check_execution_time(self):
        """Check test execution time."""
        start_time = time.time()
        
        try:
            result = subprocess.run([
                'pytest', 'tests/unit/', '-q'
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)
            
            execution_time = time.time() - start_time
            threshold = 30  # 30 seconds
            
            return {
                'passed': execution_time < threshold and result.returncode == 0,
                'message': f'Unit tests completed in {execution_time:.1f}s (threshold: {threshold}s)',
                'details': {'execution_time': execution_time, 'threshold': threshold}
            }
        except subprocess.TimeoutExpired:
            return {'passed': False, 'message': 'Test execution timed out'}
        except Exception as e:
            return {'passed': False, 'message': f'Execution time check failed: {e}'}
    
    def _check_memory_usage(self):
        """Check memory usage during tests."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run a subset of tests
            subprocess.run([
                'pytest', 'tests/unit/test_authentication.py', '-q'
            ], capture_output=True, cwd=self.project_root, timeout=30)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = memory_after - memory_before
            threshold = 100  # 100 MB
            
            return {
                'passed': memory_delta < threshold,
                'message': f'Memory usage: {memory_delta:.1f}MB (threshold: {threshold}MB)',
                'details': {'memory_delta': memory_delta, 'threshold': threshold}
            }
        except Exception as e:
            return {'passed': False, 'message': f'Memory usage check failed: {e}'}
    
    def _check_database_efficiency(self):
        """Check database query efficiency."""
        try:
            from django.test.utils import override_settings
            from django.db import connection
            
            # Reset query log
            connection.queries_log.clear()
            
            # Run database-intensive test
            result = subprocess.run([
                'pytest', 'tests/unit/test_authentication.py::UserModelTests::test_user_creation', '-q'
            ], capture_output=True, cwd=self.project_root, timeout=10)
            
            query_count = len(connection.queries)
            threshold = 50
            
            return {
                'passed': query_count < threshold and result.returncode == 0,
                'message': f'Database queries: {query_count} (threshold: {threshold})',
                'details': {'query_count': query_count, 'threshold': threshold}
            }
        except Exception as e:
            return {'passed': False, 'message': f'Database efficiency check failed: {e}'}
    
    # Documentation validation methods
    def _check_docstrings(self):
        """Check that test classes have docstrings."""
        try:
            from tests.unit.test_authentication import UserModelTests
            from tests.integration.test_api_authentication import AuthenticationAPITests
            
            classes_with_docstrings = 0
            total_classes = 2
            
            if UserModelTests.__doc__:
                classes_with_docstrings += 1
            if AuthenticationAPITests.__doc__:
                classes_with_docstrings += 1
            
            return {
                'passed': classes_with_docstrings == total_classes,
                'message': f'Docstrings: {classes_with_docstrings}/{total_classes} test classes documented'
            }
        except Exception as e:
            return {'passed': False, 'message': f'Docstring check failed: {e}'}
    
    def _check_test_readme(self):
        """Check for test documentation."""
        test_readme = self.project_root / 'tests' / 'README.md'
        return {
            'passed': test_readme.exists(),
            'message': 'Test README exists' if test_readme.exists() else 'Test README not found'
        }
    
    def _check_test_examples(self):
        """Check for test examples."""
        # Check if test files contain example methods
        example_patterns = ['example', 'sample', 'demo']
        test_files = list((self.project_root / 'tests').rglob('test_*.py'))
        
        files_with_examples = 0
        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read().lower()
                    if any(pattern in content for pattern in example_patterns):
                        files_with_examples += 1
            except Exception:
                continue
        
        return {
            'passed': files_with_examples > 0,
            'message': f'Examples found in {files_with_examples} test files'
        }
    
    # Utility methods
    def _print_category_results(self, category, checks):
        """Print results for a category."""
        passed = sum(1 for check in checks.values() if check.get('passed', False))
        total = len(checks)
        
        print(f"  {category}: {passed}/{total} checks passed")
        
        for check_name, result in checks.items():
            status = "✅" if result.get('passed', False) else "❌"
            message = result.get('message', 'No message')
            print(f"    {status} {check_name}: {message}")
        
        print()
    
    def generate_report(self):
        """Generate comprehensive validation report."""
        print("📋 Test Suite Validation Report")
        print("=" * 50)
        
        total_duration = self.end_time - self.start_time
        print(f"Validation completed in {total_duration:.2f} seconds")
        print()
        
        # Summary statistics
        total_checks = 0
        passed_checks = 0
        
        for category, checks in self.results.items():
            if isinstance(checks, dict):
                for check in checks.values():
                    if isinstance(check, dict) and 'passed' in check:
                        total_checks += 1
                        if check['passed']:
                            passed_checks += 1
        
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"Overall Results: {passed_checks}/{total_checks} checks passed ({success_rate:.1f}%)")
        print()
        
        # Category summaries
        for category, checks in self.results.items():
            if isinstance(checks, dict):
                category_passed = sum(1 for check in checks.values() 
                                    if isinstance(check, dict) and check.get('passed', False))
                category_total = sum(1 for check in checks.values() 
                                   if isinstance(check, dict) and 'passed' in check)
                
                status = "✅" if category_passed == category_total else "❌"
                print(f"{status} {category.title()}: {category_passed}/{category_total}")
        
        print()
        
        # Recommendations
        self._generate_recommendations()
        
        # Save report to file
        self._save_report()
    
    def _generate_recommendations(self):
        """Generate recommendations based on validation results."""
        print("💡 Recommendations")
        print("-" * 20)
        
        recommendations = []
        
        # Check for failed categories
        for category, checks in self.results.items():
            if isinstance(checks, dict):
                failed_checks = [name for name, check in checks.items() 
                               if isinstance(check, dict) and not check.get('passed', False)]
                
                if failed_checks:
                    if category == 'structure':
                        recommendations.append("Fix missing test directories and files")
                    elif category == 'configuration':
                        recommendations.append("Update test configuration files")
                    elif category == 'dependencies':
                        recommendations.append("Install missing test dependencies")
                    elif category == 'execution':
                        recommendations.append("Fix failing tests")
                    elif category == 'coverage':
                        recommendations.append("Improve test coverage")
                    elif category == 'performance':
                        recommendations.append("Optimize test performance")
                    elif category == 'documentation':
                        recommendations.append("Add test documentation")
        
        if not recommendations:
            recommendations = ["Test suite is well-configured and functioning properly"]
        
        for i, recommendation in enumerate(recommendations, 1):
            print(f"{i}. {recommendation}")
        
        print()
    
    def _save_report(self):
        """Save validation report to file."""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'duration': self.end_time - self.start_time,
            'results': self.results
        }
        
        report_file = self.project_root / 'test_validation_report.json'
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"📄 Detailed report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Could not save report: {e}")


def main():
    """Main entry point."""
    print("Starting SenangKira Test Suite Validation...")
    print()
    
    validator = TestSuiteValidator()
    results = validator.run_validation()
    
    # Exit with appropriate code
    all_passed = all(
        check.get('passed', False) 
        for category in results.values() 
        if isinstance(category, dict)
        for check in category.values()
        if isinstance(check, dict) and 'passed' in check
    )
    
    if all_passed:
        print("🎉 All validation checks passed!")
        sys.exit(0)
    else:
        print("❌ Some validation checks failed.")
        sys.exit(1)


if __name__ == '__main__':
    main()