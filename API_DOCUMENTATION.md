# SenangKira API Documentation

A comprehensive Django REST Framework API for business management including invoicing, expense tracking, client management, and business analytics.

## Base URL
```
http://localhost:8000/api/
```

## Authentication

### JWT Token Authentication
The API uses JWT (JSON Web Token) authentication via `djangorestframework-simplejwt`.

**Endpoints:**
- `POST /api/auth/token/` - Obtain JWT token pair
- `POST /api/auth/token/refresh/` - Refresh access token
- `POST /api/auth/token/verify/` - Verify token validity

**Request Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Login Example:**
```json
POST /api/auth/token/
{
    "username": "your_username",
    "password": "your_password"
}

Response:
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### User Management
- `GET /api/auth/users/` - List users (admin only)
- `POST /api/auth/users/` - Create user
- `GET /api/auth/users/{id}/` - Get user details
- `PUT /api/auth/users/{id}/` - Update user
- `DELETE /api/auth/users/{id}/` - Delete user
- `GET /api/auth/users/me/` - Get current user profile
- `PUT /api/auth/users/me/` - Update current user profile

---

## Client Management

### Client Endpoints
- `GET /api/clients/` - List all clients
- `POST /api/clients/` - Create new client
- `GET /api/clients/{id}/` - Get client details
- `PUT /api/clients/{id}/` - Update client
- `PATCH /api/clients/{id}/` - Partial update client
- `DELETE /api/clients/{id}/` - Delete client

**Client Model Structure:**
```json
{
    "id": 1,
    "name": "Client Name",
    "email": "client@example.com",
    "phone": "+1234567890",
    "address": "Client Address",
    "company": "Company Name",
    "tax_number": "TAX123456",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "owner": 1
}
```

---

## Quote Management

### Quote Endpoints
- `GET /api/quotes/` - List all quotes
- `POST /api/quotes/` - Create new quote
- `GET /api/quotes/{id}/` - Get quote details
- `PUT /api/quotes/{id}/` - Update quote
- `PATCH /api/quotes/{id}/` - Partial update quote
- `DELETE /api/quotes/{id}/` - Delete quote

**Quote Model Structure:**
```json
{
    "id": 1,
    "quote_number": "QUO-2024-001",
    "client": 1,
    "issue_date": "2024-01-01",
    "expiry_date": "2024-01-31",
    "status": "draft",
    "subtotal": "1000.00",
    "tax_amount": "100.00",
    "total_amount": "1100.00",
    "terms": "Payment terms...",
    "notes": "Additional notes...",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "owner": 1,
    "line_items": [
        {
            "description": "Service/Product",
            "quantity": 1,
            "unit_price": "1000.00",
            "total": "1000.00"
        }
    ]
}
```

**Quote Status Options:**
- `draft` - Quote is being prepared
- `sent` - Quote sent to client
- `accepted` - Quote accepted by client
- `rejected` - Quote rejected by client
- `expired` - Quote has expired

---

## Invoice Management

### Invoice Endpoints
- `GET /api/invoices/` - List all invoices
- `POST /api/invoices/` - Create new invoice
- `GET /api/invoices/{id}/` - Get invoice details
- `PUT /api/invoices/{id}/` - Update invoice
- `PATCH /api/invoices/{id}/` - Partial update invoice
- `DELETE /api/invoices/{id}/` - Delete invoice

**Invoice Model Structure:**
```json
{
    "id": 1,
    "invoice_number": "INV-2024-001",
    "client": 1,
    "issue_date": "2024-01-01",
    "due_date": "2024-01-31",
    "status": "draft",
    "subtotal": "1000.00",
    "tax_amount": "100.00",
    "total_amount": "1100.00",
    "paid_amount": "0.00",
    "balance": "1100.00",
    "terms": "Payment terms...",
    "notes": "Additional notes...",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "owner": 1,
    "line_items": [
        {
            "description": "Service/Product",
            "quantity": 1,
            "unit_price": "1000.00",
            "total": "1000.00"
        }
    ],
    "payments": [
        {
            "amount": "500.00",
            "payment_date": "2024-01-15",
            "payment_method": "bank_transfer",
            "reference": "TXN123456"
        }
    ]
}
```

**Invoice Status Options:**
- `draft` - Invoice is being prepared
- `sent` - Invoice sent to client
- `paid` - Invoice fully paid
- `partial` - Invoice partially paid
- `overdue` - Invoice past due date
- `cancelled` - Invoice cancelled

---

## Expense Management

### Expense Endpoints
- `GET /api/expenses/` - List all expenses
- `POST /api/expenses/` - Create new expense
- `GET /api/expenses/{id}/` - Get expense details
- `PUT /api/expenses/{id}/` - Update expense
- `PATCH /api/expenses/{id}/` - Partial update expense
- `DELETE /api/expenses/{id}/` - Delete expense

### Expense Attachment Endpoints
- `GET /api/expenses/attachments/` - List all expense attachments
- `POST /api/expenses/attachments/` - Upload new attachment
- `GET /api/expenses/attachments/{id}/` - Get attachment details
- `DELETE /api/expenses/attachments/{id}/` - Delete attachment

**Expense Model Structure:**
```json
{
    "id": 1,
    "description": "Office supplies",
    "amount": "50.00",
    "category": "office",
    "expense_date": "2024-01-01",
    "receipt_number": "REC-001",
    "vendor": "Office Store",
    "tax_amount": "5.00",
    "is_billable": true,
    "client": 1,
    "status": "approved",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "owner": 1,
    "attachments": [
        {
            "id": 1,
            "file": "/media/expenses/receipt.pdf",
            "filename": "receipt.pdf",
            "uploaded_at": "2024-01-01T00:00:00Z"
        }
    ]
}
```

**Expense Categories:**
- `office` - Office supplies and equipment
- `travel` - Travel and transportation
- `meals` - Business meals and entertainment
- `software` - Software and subscriptions
- `marketing` - Marketing and advertising
- `other` - Other business expenses

---

## Dashboard & Analytics

### Main Dashboard Endpoints
- `GET /api/dashboard/overview/` - Dashboard overview
- `GET /api/dashboard/stats/` - Quick statistics
- `GET /api/dashboard/trends/` - Trend analysis
- `GET /api/dashboard/breakdown/` - Category breakdown
- `POST /api/dashboard/refresh/` - Refresh cache
- `GET /api/dashboard/kpis/` - Key Performance Indicators
- `GET /api/dashboard/clients/` - Client performance analysis
- `GET /api/dashboard/projections/` - Revenue projections
- `GET /api/dashboard/export/` - Export dashboard data

### Dashboard Snapshots
- `GET /api/dashboard/snapshots/` - List snapshots
- `POST /api/dashboard/snapshots/` - Create snapshot
- `GET /api/dashboard/snapshots/{id}/` - Get specific snapshot
- `POST /api/dashboard/snapshots/generate/` - Generate new snapshot

### Category Analytics
- `GET /api/dashboard/categories/` - List category analytics
- `GET /api/dashboard/categories/{id}/` - Get specific category analytics

### Client Analytics
- `GET /api/dashboard/clients/` - List client analytics
- `GET /api/dashboard/clients/{id}/` - Get specific client analytics

### Performance Metrics
- `GET /api/dashboard/metrics/` - List performance metrics
- `GET /api/dashboard/metrics/{id}/` - Get specific metric
- `GET /api/dashboard/metrics/prometheus/` - Prometheus metrics export

### Real-time Dashboard
- `GET /api/dashboard/realtime/aggregate/` - Real-time dashboard data
- `GET /api/dashboard/streaming/aggregate/` - Streaming dashboard data
- `POST /api/dashboard/realtime/recalculate/` - Trigger recalculation
- `GET /api/dashboard/health/` - Dashboard health check

### Celery Task Monitoring
- `GET /api/dashboard/celery/status/` - Overall Celery system status
- `GET /api/dashboard/celery/workers/` - Worker information and statistics
- `GET /api/dashboard/celery/queues/` - Queue status and backlogs
- `GET /api/dashboard/celery/tasks/` - Recent task execution history
- `GET /api/dashboard/celery/tasks/{task_id}/` - Specific task details
- `POST /api/dashboard/celery/tasks/{task_name}/execute/` - Execute a task
- `POST /api/dashboard/celery/health_check/` - Comprehensive health check

---

## System Monitoring

### Task Execution Monitoring
- `GET /api/monitoring/api/tasks/` - List task executions
- `POST /api/monitoring/api/tasks/` - Create task execution record
- `GET /api/monitoring/api/tasks/{id}/` - Get task execution details
- `PUT /api/monitoring/api/tasks/{id}/` - Update task execution
- `DELETE /api/monitoring/api/tasks/{id}/` - Delete task execution

### Health Metrics
- `GET /api/monitoring/api/health-metrics/` - List health metrics
- `POST /api/monitoring/api/health-metrics/` - Create health metric
- `GET /api/monitoring/api/health-metrics/{id}/` - Get health metric details
- `PUT /api/monitoring/api/health-metrics/{id}/` - Update health metric
- `DELETE /api/monitoring/api/health-metrics/{id}/` - Delete health metric

### System Alerts
- `GET /api/monitoring/api/alerts/` - List system alerts
- `POST /api/monitoring/api/alerts/` - Create alert
- `GET /api/monitoring/api/alerts/{id}/` - Get alert details
- `PUT /api/monitoring/api/alerts/{id}/` - Update alert
- `DELETE /api/monitoring/api/alerts/{id}/` - Delete alert

### Monitoring Dashboard
- `GET /api/monitoring/` - Monitoring dashboard view
- `GET /api/monitoring/api/health/` - System health check
- `GET /api/monitoring/api/metrics/` - System metrics

### General Monitoring API
- `GET /api/monitoring/api/monitoring/` - General monitoring data
- `POST /api/monitoring/api/monitoring/` - Submit monitoring data

---

## Core API Endpoints

### API Root
- `GET /api/` - API root with available endpoints
- `GET /api/health/` - API health check

---

## Request/Response Formats

### Standard Response Format
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/clients/?page=2",
    "previous": null,
    "results": [
        // Array of objects
    ]
}
```

### Error Response Format
```json
{
    "error": "Error message",
    "details": {
        "field": ["Field-specific error messages"]
    }
}
```

### Common HTTP Status Codes
- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Query Parameters

### Pagination
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

### Filtering
- `search` - Search across multiple fields
- `ordering` - Sort by field (prefix with `-` for descending)
- `created_at__gte` - Filter by creation date (greater than or equal)
- `created_at__lte` - Filter by creation date (less than or equal)
- `status` - Filter by status
- `client` - Filter by client ID

### Example Requests
```
GET /api/invoices/?status=paid&ordering=-created_at&page=1&page_size=10
GET /api/clients/?search=john&ordering=name
GET /api/expenses/?category=office&expense_date__gte=2024-01-01
```

---

## Data Ownership & Security

### Multi-tenant Architecture
All resources are automatically filtered by the authenticated user's ownership. Users can only access their own:
- Clients
- Quotes
- Invoices
- Expenses
- Dashboard data
- Monitoring data

### Permission Levels
- **Owner** - Full CRUD access to own resources
- **Admin** - System-wide access (user management, system monitoring)
- **Staff** - Extended permissions for business operations

---

## Rate Limiting

The API implements rate limiting to ensure fair usage:
- **Authenticated users**: 1000 requests per hour
- **Anonymous users**: 100 requests per hour
- **Admin users**: 5000 requests per hour

Rate limit headers included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

---

## Webhooks & Real-time Updates

### Dashboard Real-time Data
- WebSocket endpoint for live dashboard updates
- Server-sent events for streaming analytics
- Automatic cache invalidation on data changes

### Celery Integration
- Background task processing for reports
- Asynchronous email notifications
- Scheduled data aggregation tasks

---

## Development & Testing

### Development Server
```bash
python manage.py runserver
```

### API Testing
Use tools like Postman, curl, or HTTPie:
```bash
# Get JWT token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_user", "password": "your_pass"}'

# Use token for authenticated requests
curl -H "Authorization: Bearer your_token" \
  http://localhost:8000/api/clients/
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Production Considerations

### Security
- HTTPS required in production
- JWT tokens have configurable expiration
- CORS properly configured
- SQL injection protection via Django ORM
- XSS protection with proper serialization

### Performance
- Database query optimization with select_related/prefetch_related
- Redis caching for frequently accessed data
- Celery for background task processing
- PostgreSQL with proper indexing

### Monitoring
- Comprehensive logging with structured format
- Prometheus metrics export
- Health check endpoints for load balancers
- Task execution monitoring with alerts

---

This API documentation covers all major endpoints and functionality of the SenangKira business management system. For implementation details, refer to the Django models and serializers in the respective app directories.