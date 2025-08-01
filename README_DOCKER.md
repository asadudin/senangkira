# SenangKira Docker Setup

Complete Docker configuration for the SenangKira Django business management system with PostgreSQL, Redis, Celery, and Nginx.

## 🚀 Quick Start

### Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd senangkira

# Start development environment (auto-reload enabled)
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build

# Access the application
open http://localhost:8000/api/
```

### Production Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your production values
nano .env

# Start production environment
docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build

# Check status
docker-compose ps
```

## 📋 Services

| Service | Port | Description |
|---------|------|-------------|
| **web** | 8000 | Django application server |
| **db** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache & message broker |
| **celery-worker** | - | Background task processor |
| **celery-beat** | - | Periodic task scheduler |
| **celery-flower** | 5555 | Celery monitoring dashboard |
| **nginx** | 80/443 | Reverse proxy & static files |

## 🔧 Configuration

### Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

**Essential Variables:**
```env
SECRET_KEY=your-super-secret-key-change-this
DB_PASSWORD=your-secure-database-password
SUPERUSER_USERNAME=admin
SUPERUSER_EMAIL=admin@yourdomain.com
SUPERUSER_PASSWORD=your-admin-password
```

### Multi-Stage Dockerfile

The Dockerfile uses multi-stage builds:
- **base**: Common dependencies and system packages
- **production**: Optimized production image with non-root user
- **development**: Development image with test dependencies and source mounting

### Docker Compose Configurations

1. **docker-compose.yaml** - Base configuration
2. **docker-compose.dev.yaml** - Development overrides (hot reload, debug mode)
3. **docker-compose.prod.yaml** - Production overrides (optimized settings, monitoring)

## 🛠️ Development Workflow

### Starting Development Environment

```bash
# Start with logs
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up

# Start in background
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d

# View logs
docker-compose logs -f web
```

### Database Operations

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Load fixtures
docker-compose exec web python manage.py loaddata fixtures/test_data.json
```

### Celery Operations

```bash
# Check worker status
docker-compose exec celery-worker celery -A senangkira inspect active

# Monitor tasks via Flower
open http://localhost:5555

# Execute specific task
docker-compose exec web python manage.py shell
>>> from dashboard.tasks import refresh_dashboard_cache
>>> refresh_dashboard_cache.delay()
```

## 🚀 Production Deployment

### SSL Configuration

1. Place certificates in `./ssl/` directory:
   ```
   ssl/
   ├── cert.pem
   └── key.pem
   ```

2. Update nginx configuration for HTTPS
3. Set `ALLOWED_HOSTS` in .env file

### Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Configure secure database password
- [ ] Set up SSL certificates
- [ ] Configure email settings for reminders
- [ ] Set appropriate `ALLOWED_HOSTS`
- [ ] Enable monitoring with Flower authentication
- [ ] Set up log rotation
- [ ] Configure backup strategy

### Starting Production

```bash
# Start production environment
docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d

# Monitor logs
docker-compose logs -f

# Check health
curl http://localhost/api/health/
```

## 🔍 Monitoring & Maintenance

### Health Checks

All services include health checks:
```bash
# Check service health
docker-compose ps

# Detailed health status
docker inspect --format='{{.State.Health.Status}}' senangkira_web
```

### Backup & Restore

```bash
# Database backup
docker-compose exec db pg_dump -U padux senangkira > backup.sql

# Database restore
cat backup.sql | docker-compose exec -T db psql -U padux senangkira

# Volume backup
docker run --rm -v senangkira_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

### Log Management

```bash
# View application logs
docker-compose logs -f web

# View Celery logs
docker-compose logs -f celery-worker

# View Nginx access logs
docker-compose exec nginx tail -f /var/log/nginx/access.log
```

## 🐛 Troubleshooting

### Common Issues

**Database Connection Issues:**
```bash
# Check database status
docker-compose exec db pg_isready -U padux

# View database logs
docker-compose logs db
```

**Celery Worker Issues:**
```bash
# Check worker status
docker-compose exec celery-worker celery -A senangkira inspect ping

# Restart worker
docker-compose restart celery-worker
```

**Permission Issues:**
```bash
# Fix file permissions
docker-compose exec web chown -R appuser:appuser /app

# Check running processes
docker-compose exec web ps aux
```

### Performance Tuning

**Database Optimization:**
- Increase `shared_buffers` for better performance
- Tune `max_connections` based on load
- Enable connection pooling

**Application Optimization:**
- Adjust Gunicorn worker count based on CPU cores
- Configure Redis memory limits
- Enable static file compression

## 📊 Monitoring

### Application Metrics

- **Django**: `/api/health/` endpoint
- **Celery**: Flower dashboard at `:5555`
- **Database**: PostgreSQL statistics
- **Redis**: Redis INFO command

### Log Aggregation

Consider integrating with:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana + Prometheus
- Cloud logging services

## 🔐 Security

### Security Features

- Non-root container user
- Secret management via environment variables
- Rate limiting via Nginx
- HTTPS support with SSL termination
- Security headers in Nginx configuration

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SSL certificates
- [ ] Configure firewall rules
- [ ] Enable container security scanning
- [ ] Set up monitoring and alerting
- [ ] Regular security updates

## 📚 Additional Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Celery Production Guide](https://docs.celeryproject.org/en/stable/userguide/deploying.html)
- [PostgreSQL Tuning Guide](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)

## 🆘 Support

For issues and questions:
1. Check service logs: `docker-compose logs [service]`
2. Review health checks: `docker-compose ps`
3. Consult the main API documentation: `API_DOCUMENTATION.md`
4. Check Django project logs in `./logs/` directory