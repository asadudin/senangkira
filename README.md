# SenangKira - Django Invoice & Quote Management System

[![Django](https://img.shields.io/badge/Django-4.2.21-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-blue.svg)](https://postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3.1-green.svg)](https://celeryproject.org/)
[![Redis](https://img.shields.io/badge/Redis-4.6.0-red.svg)](https://redis.io/)

> **Professional invoice and quote management system for freelancers and small businesses**

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd senangkira

# Create virtual environment (Python 3.13+ required)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup database and run migrations
python tests/scripts/deploy_schema.py
python tests/scripts/create_initial_migrations.py
python manage.py migrate --fake-initial

# Create superuser and start server
python manage.py createsuperuser
python manage.py runserver
```

**🎉 Your SenangKira instance is now running at http://localhost:8000**

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Performance & Monitoring](#-performance--monitoring)
- [Troubleshooting](#-troubleshooting)

## 🎯 Overview

SenangKira is a comprehensive Django-based invoicing and quote management system designed for freelancers and small businesses. Built with modern Django practices, it provides a robust REST API backend with real-time capabilities, advanced caching, and comprehensive monitoring.

### Key Capabilities
- **Multi-tenant Architecture**: Secure data isolation per user/company
- **Professional Invoicing**: Complete quote-to-invoice workflow
- **Real-time Dashboard**: Live analytics and performance monitoring
- **Background Processing**: Celery-powered task queues
- **Enterprise Security**: JWT authentication with advanced permissions
- **Performance Optimized**: Advanced caching and database optimization

## ✨ Features

### 📊 Core Business Features
- **Client Management**: Complete customer relationship management
- **Quote System**: Professional quote creation and management
- **Invoice Generation**: Automated quote-to-invoice conversion
- **Expense Tracking**: Business expense management and categorization
- **Analytics Dashboard**: Real-time business performance insights

### 🔧 Technical Features
- **JWT Authentication**: Secure token-based authentication
- **REST API**: Comprehensive RESTful API with DRF
- **Real-time Updates**: WebSocket-powered live dashboard
- **Background Tasks**: Celery integration for heavy operations
- **Advanced Caching**: Multi-level caching with Redis
- **Performance Monitoring**: Integrated metrics and health checks
- **Email Reminders**: Automated reminder system

### 🛡️ Security & Performance
- **Multi-tenant Security**: Row-level security with owner isolation
- **Performance Optimization**: Strategic database indexing
- **Caching Strategy**: L1 (Memory) + L2 (Redis) caching
- **Monitoring Integration**: Prometheus metrics and Grafana dashboards
- **Scalable Architecture**: Designed for horizontal scaling

## 🏗️ Architecture

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django API    │    │   PostgreSQL    │
│   (Web/Mobile)  │◄──►│   REST Backend  │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼────┐  ┌──────▼──────┐ ┌─────▼─────┐
        │   Redis    │  │   Celery    │ │ Monitoring│
        │  Cache/    │  │  Workers    │ │ & Metrics │
        │  Queue     │  │             │ │           │
        └────────────┘  └─────────────┘ └───────────┘
```

### Project Structure
```
senangkira/
├── 📁 authentication/           # User management & JWT auth
├── 📁 clients/                  # Client/customer management
├── 📁 invoicing/               # Quotes & invoices (core business)
├── 📁 expenses/                # Expense tracking
├── 📁 dashboard/               # Analytics & real-time dashboard
│   ├── 🔧 celery.py            # Celery configuration
│   ├── 📊 performance_monitor.py # Performance monitoring
│   ├── 📈 prometheus_exporter.py # Metrics export
│   └── 🔄 cache_advanced.py    # Advanced caching system
├── 📁 reminders/               # Email reminder system
├── 📁 monitoring/              # System health monitoring
├── 📁 tests/                   # Organized test suite
│   ├── 📁 benchmarks/          # Performance tests
│   ├── 📁 legacy/              # Legacy test scripts
│   ├── 📁 scripts/             # Utility scripts
│   ├── 📁 validation/          # System validation
│   ├── 📁 unit/                # Unit tests
│   ├── 📁 integration/         # Integration tests
│   └── 📁 e2e/                 # End-to-end tests
├── 📁 docs/                    # Organized documentation
│   ├── 📁 analysis/            # Technical analysis & guides
│   ├── 📁 completed/           # Completed task documentation
│   ├── 📁 reports/             # Performance & analysis reports
│   ├── 📄 README.md            # Documentation index
│   └── 📄 PRD                  # Product requirements
├── 📁 scripts/                 # Deployment & utility scripts
├── 📄 requirements.txt         # Python dependencies
├── 📄 API_DOCUMENTATION.md     # Complete API reference
├── 📄 README_DOCKER.md         # Docker deployment guide
└── 📄 manage.py               # Django management
```

### Technology Stack
- **Backend**: Django 4.2.21 + Django REST Framework 3.14.0
- **Database**: PostgreSQL with UUID primary keys
- **Cache/Queue**: Redis 4.6.0
- **Task Queue**: Celery 5.3.1
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Image Processing**: Pillow 11.0.0
- **Database Driver**: psycopg[binary] 3.2.3 (Python 3.13 compatible)

## 🔧 Installation

### Prerequisites
- **Python 3.13+** (required for latest compatibility)
- **PostgreSQL 12+** (recommended 15+)
- **Redis 6+** (for caching and Celery)
- **Git** (for version control)

### Step-by-Step Installation

#### 1. Clone Repository
```bash
git clone <repository-url>
cd senangkira
```

#### 2. Python Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.13+
```

#### 3. Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(Django|celery|redis|psycopg)"
```

#### 4. Database Setup
```bash
# Create PostgreSQL database and deploy schema
python tests/scripts/deploy_schema.py

# Generate Django migrations matching existing schema
python tests/scripts/create_initial_migrations.py

# Apply migrations (fake since tables exist)
python manage.py migrate --fake-initial
```

#### 5. Initial Configuration
```bash
# Create Django superuser
python manage.py createsuperuser

# Collect static files (if needed)
python manage.py collectstatic --noinput
```

#### 6. Validation
```bash
# Run comprehensive validation
python tests/legacy/test_setup.py

# Django system check
python manage.py check

# Verify database connectivity
python manage.py dbshell -c "SELECT version();"
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/senangkira

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email Configuration (for reminders)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Cache Configuration
CACHE_ENCRYPTION_KEY=your-cache-encryption-key
```

### Database Configuration

#### PostgreSQL Setup
```sql
-- Create database and user
CREATE DATABASE senangkira;
CREATE USER senangkira_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE senangkira TO senangkira_user;

-- Enable UUID extension (if not enabled)
\c senangkira
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### Settings Customization
Key settings in `senangkira/settings.py`:

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'senangkira',
        'USER': 'senangkira_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

## 🚀 Running the Application

### Development Server

#### 1. Start Core Services
```bash
# Terminal 1: Start Redis (if not running as service)
redis-server

# Terminal 2: Start PostgreSQL (if not running as service)
# Linux: sudo systemctl start postgresql
# Mac: brew services start postgresql
# Windows: net start postgresql
```

#### 2. Start Django Development Server
```bash
# Terminal 3: Django development server
source venv/bin/activate
python manage.py runserver

# Server will start at http://localhost:8000
```

#### 3. Start Celery Workers (Optional)
```bash
# Terminal 4: Celery worker
source venv/bin/activate
celery -A dashboard worker --loglevel=info

# Terminal 5: Celery beat scheduler (for periodic tasks)
celery -A dashboard beat --loglevel=info
```

### Production Deployment

#### Using Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run production server
gunicorn senangkira.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

#### Using Docker (Future)
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Service Monitoring
```bash
# Check Django server
curl http://localhost:8000/api/health/

# Check Celery workers
celery -A dashboard inspect active

# Check Redis connection
redis-cli ping
```

## 📚 API Documentation

### Authentication Endpoints
```http
POST /api/auth/register/      # User registration
POST /api/auth/token/         # Obtain JWT tokens
POST /api/auth/token/refresh/ # Refresh JWT token
GET  /api/auth/profile/       # Get user profile
PUT  /api/auth/profile/       # Update user profile
```

### Core Business Endpoints
```http
# Clients
GET    /api/clients/          # List clients
POST   /api/clients/          # Create client
GET    /api/clients/{id}/     # Get client details
PUT    /api/clients/{id}/     # Update client
DELETE /api/clients/{id}/     # Delete client

# Quotes
GET    /api/quotes/           # List quotes
POST   /api/quotes/           # Create quote
GET    /api/quotes/{id}/      # Get quote details
PUT    /api/quotes/{id}/      # Update quote
POST   /api/quotes/{id}/convert/ # Convert to invoice

# Invoices
GET    /api/invoices/         # List invoices
POST   /api/invoices/         # Create invoice
GET    /api/invoices/{id}/    # Get invoice details
PUT    /api/invoices/{id}/    # Update invoice

# Expenses
GET    /api/expenses/         # List expenses
POST   /api/expenses/         # Create expense
GET    /api/expenses/{id}/    # Get expense details
PUT    /api/expenses/{id}/    # Update expense

# Dashboard & Analytics
GET    /api/dashboard/        # Dashboard data
GET    /api/dashboard/metrics/ # Performance metrics
```

### API Features
- **Pagination**: All list endpoints support pagination
- **Filtering**: Advanced filtering with django-filter
- **Ordering**: Sort by any field with `?ordering=field`
- **Search**: Full-text search where applicable
- **JWT Authentication**: All endpoints require valid JWT token

### Example API Usage
```bash
# Register new user
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "securepass123"}'

# Get JWT token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "securepass123"}'

# Use JWT token for authenticated requests
curl -X GET http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer your-jwt-token-here"
```

## 🛠️ Development

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-test.txt

# Run tests
python manage.py test
pytest

# Code quality checks
flake8
black --check .
isort --check-only .
```

### Available Management Commands
```bash
# Database operations
python manage.py migrate
python manage.py makemigrations
python manage.py dbshell

# User management
python manage.py createsuperuser
python manage.py changepassword

# Testing and validation
python manage.py test
python manage.py check
python test_setup.py

# Celery task testing
python manage.py test_celery
python manage.py test_celery_tasks

# Performance validation
python dashboard/management/commands/validate_performance.py
python tests/scripts/run_dashboard_benchmarks.py
```

### Project-Specific Commands
```bash
# Comprehensive system validation
python tests/legacy/test_setup.py

# Database schema deployment
python tests/scripts/deploy_schema.py

# Migration generation for existing schema
python tests/scripts/create_initial_migrations.py

# Celery monitoring and testing
python manage.py test_celery
python manage.py monitor_tasks

# Performance benchmarking
python tests/validation/validate_dashboard_benchmarks.py
python tests/scripts/run_dashboard_benchmarks.py
```

## 🧪 Testing

### Test Suite Overview
```bash
# Run all tests
python manage.py test

# Run specific test categories
python manage.py test tests.unit          # Unit tests
python manage.py test tests.integration   # Integration tests
python manage.py test tests.e2e          # End-to-end tests

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### Test Categories

#### Unit Tests
- Model validation and business logic
- Serializer functionality
- Utility functions
- Individual component testing

#### Integration Tests
- API endpoint testing
- Database integration
- Authentication flows
- Cross-component interactions

#### End-to-End Tests
- Complete user workflows
- Quote-to-invoice conversion
- Dashboard functionality
- Real-time features

### Performance Testing
```bash
# Dashboard performance benchmarks
python tests/scripts/run_dashboard_benchmarks.py

# Celery task performance
python manage.py test_celery_tasks

# Database query optimization
python dashboard/management/commands/validate_performance.py

# System validation
python tests/validation/validate_dashboard_benchmarks.py
```

## 🚀 Deployment

### Production Checklist

#### Security Configuration
```python
# In production settings
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# HTTPS settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

#### Database Optimization
```python
# Connection pooling
DATABASES['default']['OPTIONS'] = {
    'MAX_CONNS': 20,
    'OPTIONS': {
        'MAX_CONNS': 20,
    },
}
```

#### Static Files & Media
```bash
# Collect static files
python manage.py collectstatic --noinput

# Configure media file serving (use CDN in production)
```

### Docker Deployment (Recommended)
```dockerfile
# Dockerfile example
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "senangkira.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Environment-Specific Settings
```bash
# Development
export DJANGO_SETTINGS_MODULE=senangkira.settings

# Production
export DJANGO_SETTINGS_MODULE=senangkira.settings_production
```

## 📊 Performance & Monitoring

### Performance Features

#### Caching Strategy
- **L1 Cache**: In-memory caching for frequent data
- **L2 Cache**: Redis for shared cache across instances
- **Query Optimization**: Strategic database indexing
- **Cache Warming**: Predictive cache population

#### Monitoring Integration
```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics/

# Grafana dashboard generation
python manage.py generate_grafana_dashboard

# Performance monitoring
python dashboard/performance_monitor.py
```

### Key Performance Metrics
- **Response Time**: API endpoint performance
- **Database Queries**: Query count and optimization
- **Cache Hit Rate**: Caching effectiveness
- **Celery Tasks**: Background task performance
- **Memory Usage**: Application memory consumption

### Performance Optimization
```python
# Database query optimization
from django.db import connection
print(connection.queries)  # Debug query count

# Caching implementation
from django.core.cache import cache
cache.set('key', 'value', timeout=3600)

# Background task optimization
from dashboard.tasks import optimize_performance
optimize_performance.delay()
```

## 🔍 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
python manage.py dbshell -c "SELECT 1;"

# Reset database connections
python manage.py migrate --run-syncdb
```

#### Redis Connection Issues
```bash
# Check Redis status
redis-cli ping

# Check Redis configuration
redis-cli config get '*'

# Clear Redis cache
redis-cli flushall
```

#### Migration Issues
```bash
# Reset migrations (development only)
python manage.py migrate --fake app_name zero
python manage.py migrate app_name

# Show migration status
python manage.py showmigrations

# Fake apply specific migration
python manage.py migrate app_name 0001 --fake
```

#### Celery Issues
```bash
# Check Celery worker status
celery -A dashboard inspect active

# Purge Celery tasks
celery -A dashboard purge

# Monitor Celery tasks
celery -A dashboard events
```

### Performance Issues
```bash
# Database query analysis
python manage.py shell
from django.db import connection
print(connection.queries)

# Cache performance
python manage.py shell
from django.core.cache import cache
cache.get_stats()

# Memory profiling
pip install memory-profiler
python -m memory_profiler your_script.py
```

### Logging and Debugging
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Django debug toolbar (development only)
pip install django-debug-toolbar
```

### Error Resolution
```bash
# Clear compiled Python files
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# Reset virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📖 Additional Resources

### Documentation
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Project-Specific Documentation
- [`docs/analysis/README_CELERY.md`](docs/analysis/README_CELERY.md) - Celery implementation guide
- [`docs/analysis/README_REALTIME.md`](docs/analysis/README_REALTIME.md) - Real-time dashboard guide
- [`docs/PRD_Analysis.md`](docs/PRD_Analysis.md) - Project requirements analysis
- [`docs/Project_Tasks.md`](docs/Project_Tasks.md) - Task breakdown and progress
- [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) - Complete API reference
- [`README_DOCKER.md`](README_DOCKER.md) - Docker deployment guide
- [`tests/README.md`](tests/README.md) - Test suite organization
- [`docs/README.md`](docs/README.md) - Documentation index

### Development Tools
- **IDE**: VS Code with Python and Django extensions
- **Database**: pgAdmin or DBeaver for PostgreSQL management
- **API Testing**: Postman or HTTPie
- **Monitoring**: Grafana + Prometheus for production monitoring

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run test suite: `python manage.py test`
5. Commit changes: `git commit -m "Add your feature"`
6. Push to branch: `git push origin feature/your-feature`
7. Create Pull Request

### Code Standards
- Follow PEP 8 Python style guide
- Use Django best practices
- Write comprehensive tests
- Document new features
- Keep dependencies updated

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- **Documentation**: Check project docs in `/docs` folder
- **Issues**: Create GitHub issue for bugs/features
- **Development**: Follow troubleshooting guide above

---

**SenangKira** - Professional invoice and quote management made simple.

*Built with ❤️ using Django, PostgreSQL, and modern Python practices.*