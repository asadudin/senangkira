# SenangKira Test Suite Makefile
# Provides convenient commands for running different types of tests

.PHONY: help test test-unit test-integration test-e2e test-api test-all
.PHONY: test-coverage test-performance test-security test-smoke
.PHONY: lint format check-format type-check security-scan
.PHONY: install-test-deps setup-test-env clean-test-data load-fixtures
.PHONY: test-parallel test-fast test-slow test-ci
.PHONY: docs-test serve-coverage benchmark profile

# Variables
PYTHON := python
PIP := pip
PYTEST := pytest
COVERAGE := coverage
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy
BANDIT := bandit
SAFETY := safety

# Test settings
TEST_SETTINGS := --settings=senangkira.settings.test
PYTEST_ARGS := -v --tb=short --strict-markers
COVERAGE_ARGS := --cov=. --cov-report=html --cov-report=xml --cov-report=term-missing

# Help target
help: ## Show this help message
	@echo "SenangKira Test Suite Commands"
	@echo "=============================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation and setup
install-test-deps: ## Install test dependencies
	$(PIP) install -r requirements-test.txt
	playwright install --with-deps chromium

setup-test-env: ## Set up test environment
	$(PYTHON) manage.py migrate $(TEST_SETTINGS)
	$(PYTHON) manage.py collectstatic --noinput $(TEST_SETTINGS)

# Core test commands
test: ## Run all tests
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/

test-unit: ## Run unit tests only
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/unit/ -m "unit"

test-integration: ## Run integration tests only
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/integration/ -m "integration"

test-api: ## Run API tests only
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/integration/ -m "api"

test-e2e: ## Run end-to-end tests
	$(PYTHON) manage.py runserver $(TEST_SETTINGS) --noreload &
	sleep 5
	$(PYTEST) $(PYTEST_ARGS) tests/e2e/ -m "e2e" --browser chromium
	pkill -f "runserver.*$(TEST_SETTINGS)" || true

test-smoke: ## Run smoke tests for basic functionality
	$(PYTEST) $(PYTEST_ARGS) tests/ -m "smoke"

test-security: ## Run security-focused tests
	$(PYTEST) $(PYTEST_ARGS) tests/ -m "security"

test-performance: ## Run performance tests
	$(PYTEST) $(PYTEST_ARGS) tests/ -m "performance" --benchmark-json=benchmark-results.json

# Test execution modes
test-fast: ## Run fast tests only (exclude slow tests)
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/ -m "not slow"

test-slow: ## Run slow tests only
	$(PYTEST) $(PYTEST_ARGS) tests/ -m "slow"

test-parallel: ## Run tests in parallel
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/ -n auto

test-ci: ## Run tests in CI mode
	$(PYTEST) $(PYTEST_ARGS) $(COVERAGE_ARGS) tests/ --maxfail=1 --tb=line

test-all: ## Run comprehensive test suite
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) test-api
	$(MAKE) test-e2e

# Coverage and reporting
test-coverage: ## Generate detailed coverage report
	$(COVERAGE) run --source='.' manage.py test $(TEST_SETTINGS)
	$(COVERAGE) report --show-missing
	$(COVERAGE) html
	@echo "Coverage report available at htmlcov/index.html"

serve-coverage: ## Serve coverage reports locally
	cd htmlcov && $(PYTHON) -m http.server 8080

# Code quality
lint: ## Run all linting checks
	$(FLAKE8) .
	$(BLACK) --check --diff .
	$(ISORT) --check-only --diff .

format: ## Format code with black and isort
	$(BLACK) .
	$(ISORT) .

check-format: ## Check if code is properly formatted
	$(BLACK) --check .
	$(ISORT) --check-only .

type-check: ## Run type checking with mypy
	$(MYPY) . --ignore-missing-imports

# Security
security-scan: ## Run security scans
	$(BANDIT) -r . -x tests/ -f json -o bandit-report.json
	$(BANDIT) -r . -x tests/
	$(SAFETY) check --json --output safety-report.json
	$(SAFETY) check

# Test data management
clean-test-data: ## Clean test data from database
	$(PYTHON) manage.py clean_test_data $(TEST_SETTINGS) --confirm

load-fixtures: ## Load test fixtures
	$(PYTHON) manage.py load_test_fixtures $(TEST_SETTINGS) --scenario complete

load-fixtures-json: ## Load test fixtures from JSON
	$(PYTHON) manage.py load_test_fixtures $(TEST_SETTINGS) --scenario json

create-test-user: ## Create test user for manual testing
	$(PYTHON) manage.py shell $(TEST_SETTINGS) -c "
	from django.contrib.auth import get_user_model;
	User = get_user_model();
	user, created = User.objects.get_or_create(
		email='test@senangkira.com',
		defaults={'username': 'testuser', 'is_active': True}
	);
	if created: user.set_password('TestPass123!'); user.save();
	print(f'Test user: {user.email} (created: {created})')
	"

# Performance and profiling
benchmark: ## Run performance benchmarks
	$(PYTEST) tests/ -m "performance" --benchmark-only --benchmark-json=benchmark-results.json
	@echo "Benchmark results saved to benchmark-results.json"

profile: ## Profile test execution
	$(PYTEST) tests/unit/ --profile --profile-svg

memory-profile: ## Profile memory usage during tests
	$(PYTHON) -m memory_profiler $(PYTEST) tests/unit/test_models.py

# Documentation testing
docs-test: ## Test documentation examples
	$(PYTHON) -m doctest README.md
	$(PYTHON) manage.py test tests.test_documentation $(TEST_SETTINGS)

# Database operations
reset-test-db: ## Reset test database
	$(PYTHON) manage.py flush $(TEST_SETTINGS) --noinput
	$(PYTHON) manage.py migrate $(TEST_SETTINGS)

backup-test-data: ## Backup test data
	mkdir -p backups
	$(PYTHON) manage.py dumpdata $(TEST_SETTINGS) \
		--natural-foreign --natural-primary \
		--exclude contenttypes --exclude auth.permission \
		--exclude sessions > backups/test_data_$(shell date +%Y%m%d_%H%M%S).json

# Utility commands
test-debug: ## Run tests with debugging enabled
	$(PYTEST) $(PYTEST_ARGS) tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb

test-verbose: ## Run tests with maximum verbosity
	$(PYTEST) -vvv --tb=long tests/

test-quiet: ## Run tests with minimal output
	$(PYTEST) -q tests/

test-failed: ## Re-run only failed tests
	$(PYTEST) --lf tests/

test-new: ## Run tests for new/modified code only
	$(PYTEST) --testmon tests/

# Environment checks
check-deps: ## Check for dependency issues
	$(PIP) check
	$(SAFETY) check --short-report

check-env: ## Check test environment setup
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Django version: $$($(PYTHON) -c 'import django; print(django.get_version())')"
	@echo "Pytest version: $$($(PYTEST) --version)"
	@echo "Database connection test..."
	@$(PYTHON) manage.py check $(TEST_SETTINGS) --database default

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf benchmark-results.json
	rm -rf bandit-report.json
	rm -rf safety-report.json

# Complete test pipeline
test-pipeline: ## Run complete test pipeline (CI simulation)
	@echo "Running complete test pipeline..."
	$(MAKE) check-deps
	$(MAKE) check-env
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security-scan
	$(MAKE) test-all
	$(MAKE) test-coverage
	@echo "Test pipeline completed successfully!"

# Development workflow
dev-test: ## Quick development test cycle
	$(MAKE) format
	$(MAKE) test-fast
	$(MAKE) test-coverage

# File watching for continuous testing
watch-tests: ## Watch files and run tests on changes
	@echo "Watching for file changes..."
	@which entr > /dev/null || (echo "Please install 'entr' first: brew install entr" && exit 1)
	find . -name "*.py" | entr -c $(MAKE) test-fast