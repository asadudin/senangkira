# Tests Directory

Organized test suite for the SenangKira project.

## Directory Structure

### `/benchmarks/`
Performance testing and benchmark scripts:
- `performance_test_suite.py` - Main performance test runner
- `run_dashboard_benchmarks.py` - Dashboard performance benchmarks
- `performance_test_report_*.json` - Benchmark results

### `/legacy/`
Legacy test scripts (maintained for reference):
- `test_*.py` - Individual test scripts
- `test_setup.py` - Test environment setup
- `functional_test_conversion.py` - Test conversion utilities
- `integration_test_conversion.py` - Integration test helpers

### `/scripts/`
Utility and setup scripts:
- `create_initial_migrations.py` - Database migration generator
- `generate_migrations.py` - Migration utilities
- `deploy_schema.py` - Schema deployment script
- `run_test_validation.py` - Test validation runner

### `/validation/`
Model and system validation scripts:
- `validate_*.py` - Individual validation scripts
- `validate_models.py` - Database model validation
- `validate_monitoring.py` - System monitoring validation
- `validate_sk*.py` - Feature-specific validations

### Core Test Suite (`/`)
Main test suite organized by Django apps:
- `/unit/` - Unit tests for individual components
- `/integration/` - Integration tests for workflows
- `/e2e/` - End-to-end tests for user journeys
- `/fixtures/` - Test data and database utilities

## Running Tests

### Development Tests
```bash
# Run all tests
python -m pytest

# Run specific test category
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

### Performance Tests
```bash
# Run benchmark suite
python tests/benchmarks/performance_test_suite.py

# Run dashboard benchmarks
python tests/scripts/run_dashboard_benchmarks.py

# Validate performance
python tests/validation/validate_dashboard_benchmarks.py
```

### Legacy Tests
```bash
# Run individual legacy tests
python tests/legacy/test_sk502_simple.py
python tests/legacy/test_celery_simple.py
```

## Test Configuration

- `pytest.ini` - Pytest configuration
- `conftest.py` - Shared test fixtures
- `tox.ini` - Multi-environment testing

## Validation Scripts

Located in `/validation/` directory:
- Run after code changes to ensure system integrity
- Validate database models and relationships
- Check monitoring and performance metrics
- Verify feature implementations

## Adding New Tests

1. **Unit Tests**: Add to `/unit/` directory, named `test_<feature>.py`
2. **Integration Tests**: Add to `/integration/` directory
3. **Performance Tests**: Add to `/benchmarks/` directory
4. **Validation Scripts**: Add to `/validation/` directory

## CI/CD Integration

Tests are organized for easy CI/CD integration:
- Fast unit tests run on every commit
- Integration tests run on pull requests
- Performance tests run nightly
- Validation scripts run on deployment