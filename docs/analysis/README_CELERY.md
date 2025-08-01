# Celery Task Processing System (SK-701)

Distributed task processing with Redis as message broker for SenangKira dashboard operations, caching, and background jobs.

## 🚀 **Architecture Overview**

### Core Components
- **Celery**: Distributed task queue for asynchronous processing
- **Redis**: Message broker and result backend with priority queues
- **Django Integration**: Seamless integration with existing dashboard system
- **Priority Queues**: Task routing for optimal resource allocation
- **Periodic Tasks**: Automated maintenance and optimization jobs
- **Monitoring**: Real-time metrics and system health tracking

### Queue Architecture
```
Priority Queues:
├── high_priority     → Critical dashboard operations (cache refresh, alerts)
├── cache_operations  → Cache warming and invalidation tasks
├── default           → Standard background processing
├── analytics         → Performance analysis and reporting
└── low_priority      → Maintenance and cleanup operations
```

## 📋 **Available Tasks**

### **Dashboard Operations**

#### `dashboard.tasks.refresh_dashboard_cache`
Refresh cached dashboard data for specified user or all users.

**Parameters:**
- `user_id` (int, optional): Specific user ID to refresh. If None, refresh all users.

**Queue:** `high_priority`

**Usage:**
```python
# Refresh for specific user
refresh_dashboard_cache.delay(user_id=123)

# Refresh for all users
refresh_dashboard_cache.delay()
```

#### `dashboard.tasks.warm_dashboard_cache`
Pre-warm dashboard cache for improved performance.

**Parameters:**
- `user_id` (int, optional): Specific user ID to warm cache for. If None, warm for all users.

**Queue:** `cache_operations`

**Usage:**
```python
# Warm cache for specific user
warm_dashboard_cache.delay(user_id=123)

# Warm cache for all users
warm_dashboard_cache.delay()
```

### **Analytics & Reporting**

#### `dashboard.tasks.performance_analysis`
Run comprehensive performance analysis on dashboard system.

**Queue:** `analytics`

**Usage:**
```python
performance_analysis.delay()
```

#### `dashboard.tasks.export_dashboard_data`
Export dashboard data in specified format.

**Parameters:**
- `user_id` (int): User ID to export data for
- `export_format` (str): Format to export data in (json, csv, pdf)
- `date_range` (dict): Date range for export

**Queue:** `low_priority`

**Usage:**
```python
export_dashboard_data.delay(
    user_id=123, 
    export_format='json'
)
```

### **Notifications & Communication**

#### `dashboard.tasks.send_notification`
Send user notifications (email, push, etc.).

**Parameters:**
- `user_id` (int): User ID to send notification to
- `message` (str): Notification message
- `notification_type` (str): Type of notification (info, warning, alert)

**Queue:** `high_priority`

**Usage:**
```python
send_notification.delay(
    user_id=123,
    message="Your dashboard has been updated",
    notification_type="info"
)
```

### **Maintenance Tasks**

#### `dashboard.tasks.cleanup_old_data`
Clean up old dashboard data for storage optimization.

**Parameters:**
- `days_old` (int): Number of days old data to clean up (default: 30)

**Queue:** `low_priority`

**Usage:**
```python
cleanup_old_data.delay(days_old=60)
```

#### `dashboard.tasks.debug_task`
Debug task for testing Celery setup.

**Queue:** `default`

**Usage:**
```python
debug_task.delay()
```

## ⏰ **Periodic Tasks**

### Automated Maintenance Schedule
```python
# Refresh dashboard cache every hour
'0 * * * *' → refresh_dashboard_cache (high_priority)

# Warm dashboard cache daily at 2 AM
'0 2 * * *' → warm_dashboard_cache (cache_operations)

# Performance analysis every 6 hours
'0 */6 * * *' → performance_analysis (analytics)
```

## 🔄 **Task Monitoring API**

### REST API Endpoints

#### **GET** `/api/dashboard/celery/status/`
Get overall Celery system health status.

**Response:**
```json
{
  "status": "healthy",
  "message": "System is operating normally",
  "worker_count": 3,
  "active_tasks": 0,
  "success_rate": 98.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### **GET** `/api/dashboard/celery/workers/`
Get detailed worker information and statistics.

**Response:**
```json
{
  "workers": {
    "count": 3,
    "details": {
      "celery@worker1": [
        {"name": "dashboard.tasks.refresh_dashboard_cache", "id": "123456789"}
      ]
    }
  },
  "stats": {
    "celery@worker1": {
      "total": 100,
      "pool": {"max-concurrency": 4, "processes": [123, 124, 125, 126]}
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### **GET** `/api/dashboard/celery/queues/`
Get queue status and backlogs.

**Response:**
```json
{
  "queues": {
    "high_priority": {
      "name": "high_priority",
      "workers": ["celery@worker1", "celery@worker2"],
      "count": 2
    }
  },
  "total_queues": 5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### **GET** `/api/dashboard/celery/tasks/`
Get recent task execution history.

**Query Parameters:**
- `limit`: Number of recent tasks to retrieve (default: 50)

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "123456789",
      "name": "dashboard.tasks.refresh_dashboard_cache",
      "status": "success",
      "duration": 1.234,
      "started_at": "2024-01-15T10:29:00Z",
      "completed_at": "2024-01-15T10:29:01Z"
    }
  ],
  "count": 1
}
```

#### **GET** `/api/dashboard/celery/tasks/{task_id}/`
Get detailed information about a specific task.

#### **POST** `/api/dashboard/celery/tasks/{task_name}/execute/`
Execute a specific task with parameters.

**Request Body:**
```json
{
  "user_id": 123,
  "args": [],
  "kwargs": {}
}
```

#### **POST** `/api/dashboard/celery/health_check/`
Comprehensive health check of the Celery system.

## 📊 **Monitoring & Metrics**

### Prometheus Metrics
All Celery metrics are exposed via Prometheus endpoint at `/api/dashboard/metrics/prometheus/`.

#### Task Metrics
- `celery_tasks_total` → Total number of tasks executed by queue and status
- `celery_task_duration_seconds` → Task execution time histogram by queue and task name
- `celery_task_errors_total` → Total number of task errors by queue, task name, and error type

#### System Metrics
- `celery_workers_count` → Number of active workers
- `celery_queues_backlog` → Number of tasks waiting in each queue

### Grafana Dashboard
A comprehensive Grafana dashboard is available that includes both cache and Celery metrics:
- Worker count monitoring
- Queue backlog visualization
- Task throughput tracking
- Duration analysis (P95 and median)
- Error tracking and alerting

## 🔧 **Configuration**

### Django Settings
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Worker Configuration
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Queue Routing
CELERY_TASK_ROUTES = {
    'dashboard.tasks.refresh_dashboard_cache': {'queue': 'high_priority'},
    'dashboard.tasks.warm_dashboard_cache': {'queue': 'cache_operations'},
    'dashboard.tasks.export_dashboard_data': {'queue': 'low_priority'},
    'dashboard.tasks.performance_analysis': {'queue': 'analytics'},
    'dashboard.tasks.send_notification': {'queue': 'high_priority'},
    'dashboard.tasks.cleanup_old_data': {'queue': 'low_priority'},
}

# Periodic Tasks
CELERY_BEAT_SCHEDULE = {
    'refresh-dashboard-cache-hourly': {
        'task': 'dashboard.tasks.refresh_dashboard_cache',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'high_priority'}
    },
    # ... more schedules
}
```

## 🚀 **Deployment**

### Installation Requirements
```bash
pip install celery redis
```

### Starting Workers
```bash
# Start worker with specific queues
celery -A senangkira worker -Q high_priority,cache_operations,default -l info

# Start worker with all queues
celery -A senangkira worker -l info

# Start worker with concurrency control
celery -A senangkira worker --concurrency=4 -l info
```

### Starting Beat Scheduler
```bash
# Start periodic task scheduler
celery -A senangkira beat -l info
```

### Starting with Flower (Monitoring)
```bash
# Install flower for web-based monitoring
pip install flower

# Start flower
celery -A senangkira flower
```

## 💻 **Usage Examples**

### Python Client
```python
from dashboard.tasks import refresh_dashboard_cache, warm_dashboard_cache

# Execute tasks asynchronously
refresh_result = refresh_dashboard_cache.delay(user_id=123)
warm_result = warm_dashboard_cache.delay(user_id=123)

# Check task status
print(f"Refresh task state: {refresh_result.state}")
print(f"Warm task state: {warm_result.state}")

# Get results (if needed)
if refresh_result.ready():
    result = refresh_result.get()
    print(f"Refresh result: {result}")
```

### Management Commands
```bash
# Test Celery setup
python manage.py test_celery

# Test specific tasks
python manage.py test_celery_tasks --task refresh --user-id 123

# Run all tasks synchronously for testing
python manage.py test_celery_tasks --sync
```

## 🧪 **Testing**

### Test Suite
Comprehensive test suite covering:
- Task execution and routing
- Queue configuration
- Integration with caching system
- Monitoring and tracking functionality
- Error handling and retry mechanisms
- Performance benchmarks

### Running Tests
```bash
# Run Celery tests
python manage.py test dashboard.tests_celery

# Run specific test class
python manage.py test dashboard.tests_celery.CeleryTaskTests

# Run with coverage
coverage run --source='.' manage.py test dashboard.tests_celery
coverage report
```

## 🛡️ **Error Handling & Retry Logic**

### Retry Configuration
All tasks include automatic retry logic:
- **Max Retries**: 3 attempts for most tasks
- **Backoff**: Exponential backoff starting at 60 seconds
- **Retry Conditions**: Network errors, database issues, temporary failures

### Error Tracking
- Comprehensive error logging
- Task failure tracking in monitoring system
- Automatic alerting for critical failures

## 📈 **Performance Optimization**

### Best Practices
1. **Queue Selection**: Route tasks to appropriate priority queues
2. **Task Granularity**: Break large tasks into smaller units
3. **Resource Management**: Configure worker concurrency appropriately
4. **Monitoring**: Track queue backlogs and worker performance
5. **Retry Logic**: Implement smart retry strategies for transient failures

### Scaling Guidelines
- **Low Load**: 1-2 workers with concurrency 2-4
- **Medium Load**: 2-4 workers with concurrency 4-8
- **High Load**: 4+ workers with dedicated queue workers

## 🔒 **Security**

### Authentication
- Tasks only accessible through Django application
- User-specific task isolation
- JWT-based API access control

### Data Protection
- Secure result backend configuration
- Redis authentication (if configured)
- Encrypted task data (if sensitive)

---

**🎉 Celery task processing system successfully implemented with distributed processing, priority queues, comprehensive monitoring, and seamless integration with SK-603 caching system!**