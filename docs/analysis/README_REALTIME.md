# Real-Time Dashboard Aggregation API

Advanced real-time dashboard data aggregation endpoints with live streaming capabilities and WebSocket support.

## 🚀 **New Real-Time Endpoints**

### **GET** `/api/dashboard/realtime/aggregate/`
Real-time dashboard data with instant calculations and live metrics.

**Features:**
- Instant financial KPI calculations
- Live operational metrics (pending/overdue invoices)
- Client performance tracking
- Real-time alerts and notifications
- Performance scoring with trend analysis

**Response:**
```json
{
  "user_id": "uuid",
  "timestamp": "2024-01-15T10:30:00Z",
  "performance_score": 85.5,
  "metrics": [
    {
      "name": "Daily Revenue",
      "value": 2500.00,
      "change": 150.00,
      "trend": "up",
      "timestamp": "2024-01-15T10:30:00Z",
      "confidence": 0.95
    }
  ],
  "alerts": [
    {
      "level": "warning",
      "message": "5 invoices are overdue",
      "metric": "Overdue Invoices",
      "action_required": true
    }
  ]
}
```

### **GET** `/api/dashboard/streaming/aggregate/`
Server-Sent Events (SSE) streaming for continuous dashboard updates.

**Query Parameters:**
- `interval`: Update interval in seconds (default: 30, min: 10, max: 300)
- `max_updates`: Maximum number of updates (default: 100)

**Features:**
- Continuous real-time streaming
- Configurable update intervals
- Automatic connection management
- Progressive data enhancement

### **POST** `/api/dashboard/realtime/recalculate/`
Force immediate dashboard recalculation and cache refresh.

**Response:**
```json
{
  "success": true,
  "message": "Dashboard recalculation completed",
  "refresh_results": {
    "refreshed": true,
    "duration_seconds": 1.2
  },
  "performance_score": 78.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### **GET** `/api/dashboard/health/`
Dashboard system health check with performance metrics.

**Response:**
```json
{
  "status": "healthy",
  "response_time_ms": 45.2,
  "components": {
    "database": {"status": "healthy"},
    "cache": {"status": "healthy"},
    "aggregation_service": {"status": "healthy"}
  },
  "performance": {
    "response_time_ms": 45.2,
    "performance_grade": "excellent"
  }
}
```

## 🔄 **WebSocket Integration**

### Dashboard Data Streaming
**WebSocket URL:** `ws://localhost:8000/ws/dashboard/{user_id}/`

**Connection Flow:**
1. Establish WebSocket connection with JWT authentication
2. Configure update intervals and preferences
3. Receive continuous dashboard updates
4. Handle alerts and notifications

**Message Types:**

#### Client → Server
```javascript
// Configure update interval
{
  "type": "configure",
  "config": {
    "update_interval": 30
  }
}

// Request immediate update
{"type": "request_update"}

// Ping for connection testing
{"type": "ping"}
```

#### Server → Client
```javascript
// Dashboard update
{
  "type": "dashboard.update",
  "data": {
    "performance_score": 85.5,
    "metrics": [...],
    "alerts": [...]
  }
}

// Connection status
{"type": "connection.established"}

// Pong response
{"type": "pong"}
```

### Notification Streaming
**WebSocket URL:** `ws://localhost:8000/ws/dashboard/notifications/{user_id}/`

**Features:**
- Real-time alert notifications
- Alert acknowledgment
- Subscription management
- Priority-based notification routing

## 📊 **Real-Time Metrics**

### Financial Metrics
- **Daily Revenue**: Current day revenue vs previous day
- **Daily Expenses**: Current day expenses vs previous day  
- **Daily Profit**: Real-time profit calculation with trend analysis
- **Cash Flow**: Live cash flow monitoring

### Operational Metrics
- **Pending Invoices**: Live count with trend tracking
- **Overdue Invoices**: Real-time overdue monitoring
- **Quote Conversion**: Live conversion rate calculation
- **Client Activity**: Active client tracking

### Performance Indicators
- **Performance Score**: Composite score (0-100) based on all metrics
- **Trend Analysis**: Up/down/stable trend detection
- **Confidence Levels**: Metric reliability scoring (0.0-1.0)
- **Alert Generation**: Automatic threshold-based alerting

## 🎯 **Alert System**

### Alert Levels
- **Critical**: Negative profit, system failures
- **Warning**: High overdue invoices, performance degradation
- **Success**: Positive trends, targets achieved
- **Info**: General notifications, system updates

### Auto-Generated Alerts
- Negative daily profit → Critical alert
- >5 overdue invoices → Warning alert
- Revenue growth → Success alert
- System performance issues → Warning/Critical

## 🚀 **Performance Features**

### Optimization
- **Sub-100ms Response**: Target response time for all endpoints
- **Intelligent Caching**: Multi-level caching with smart invalidation
- **Parallel Processing**: Concurrent metric calculations
- **Resource Pooling**: Efficient database connection management

### Monitoring
- **Health Checks**: Comprehensive system health monitoring
- **Performance Grades**: Automatic performance classification
- **Response Time Tracking**: Real-time performance metrics
- **Error Detection**: Automatic error detection and reporting

## 🔒 **Security**

- **JWT Authentication**: Required for all endpoints
- **Multi-Tenant Isolation**: Complete data isolation per user
- **Rate Limiting**: Configurable rate limits for streaming endpoints
- **WebSocket Authentication**: Secure WebSocket connections
- **Input Validation**: Comprehensive request validation

## 💻 **Usage Examples**

### JavaScript Client
```javascript
// Real-time dashboard data
const response = await fetch('/api/dashboard/realtime/aggregate/', {
  headers: {
    'Authorization': `Bearer ${jwt_token}`
  }
});
const dashboardData = await response.json();

// WebSocket connection
const ws = new WebSocket(`ws://localhost:8000/ws/dashboard/${userId}/`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'dashboard.update') {
    updateDashboard(data.data);
  }
};

// Configure update interval
ws.send(JSON.stringify({
  type: 'configure',
  config: { update_interval: 60 }
}));
```

### Server-Sent Events
```javascript
const eventSource = new EventSource('/api/dashboard/streaming/aggregate/?interval=30');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'dashboard_update') {
    updateDashboard(data);
  }
};
```

### Python Client
```python
import requests
from decimal import Decimal

# Get real-time dashboard data
response = requests.get(
    'http://localhost:8000/api/dashboard/realtime/aggregate/',
    headers={'Authorization': f'Bearer {jwt_token}'}
)

dashboard_data = response.json()
performance_score = dashboard_data['performance_score']
metrics = dashboard_data['metrics']
alerts = dashboard_data['alerts']

# Trigger recalculation
recalc_response = requests.post(
    'http://localhost:8000/api/dashboard/realtime/recalculate/',
    headers={'Authorization': f'Bearer {jwt_token}'}
)
```

## 🧪 **Testing**

### Test Suite
- **Unit Tests**: 15+ test methods for real-time functionality
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Response time and caching validation
- **WebSocket Tests**: Connection and message handling

### Running Tests
```bash
# Run real-time dashboard tests
python manage.py test dashboard.test_realtime

# Run specific test class
python manage.py test dashboard.test_realtime.RealTimeDashboardAPITests

# Run with coverage
coverage run --source='.' manage.py test dashboard.test_realtime
coverage report
```

## 📈 **Monitoring & Analytics**

### Performance Metrics
- Response time percentiles (P50, P95, P99)
- Cache hit rates by endpoint
- WebSocket connection duration
- Error rates and failure patterns

### Business Metrics
- Dashboard usage patterns
- Alert frequency and resolution
- Real-time data accuracy
- User engagement with live features

## 🔧 **Configuration**

### Settings
```python
# Real-time dashboard settings
REALTIME_DASHBOARD = {
    'UPDATE_INTERVALS': {
        'MIN': 10,  # seconds
        'MAX': 300,  # seconds
        'DEFAULT': 30  # seconds
    },
    'CACHE_TIMEOUT': 300,  # 5 minutes
    'MAX_WEBSOCKET_CONNECTIONS': 100,
    'PERFORMANCE_THRESHOLDS': {
        'EXCELLENT': 100,  # ms
        'GOOD': 500,  # ms
        'POOR': 1000  # ms
    }
}
```

### WebSocket Configuration
```python
# channels/routing.py
from django.urls import re_path
from dashboard.websocket_consumer import DashboardConsumer, DashboardNotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/dashboard/(?P<user_id>\w+)/$', DashboardConsumer.as_asgi()),
    re_path(r'ws/dashboard/notifications/(?P<user_id>\w+)/$', DashboardNotificationConsumer.as_asgi()),
]
```

## 🚀 **Deployment Notes**

### Requirements
- Redis for caching and WebSocket channel layer
- Django Channels for WebSocket support
- Celery for background task processing (optional)
- Load balancer with WebSocket support

### Production Checklist
- [ ] Configure Redis for production
- [ ] Set up WebSocket load balancing
- [ ] Enable monitoring and alerting
- [ ] Configure rate limiting
- [ ] Set up SSL/TLS for WebSocket connections
- [ ] Test failover scenarios

---

**🎉 Real-time dashboard aggregation endpoints successfully implemented with comprehensive business intelligence, live streaming, and WebSocket support!**