# SenangKira Docker Configuration for External Infrastructure

## Overview

Updated Docker configuration for SenangKira that uses **external PostgreSQL database** and **external Nginx reverse proxy**, with only containerized Redis and Django application services.

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   External Nginx    │    │   Docker Services   │    │  External Database  │
│   Reverse Proxy     │◄──►│   - Django Web      │◄──►│   PostgreSQL Server │
│   (SSL Termination) │    │   - Redis Cache     │    │                     │
└─────────────────────┘    │   - Celery Workers  │    └─────────────────────┘
                           │   - Celery Beat     │
                           │   - Celery Flower   │
                           └─────────────────────┘
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your external database details
nano .env
```

**Required Environment Variables:**
```env
DATABASE_URL=postgresql://username:password@your-postgres-host:5432/senangkira
SECRET_KEY=your-super-secret-key-change-this
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### 2. Start Services
```bash
# Development
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up

# Production
docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

## 📋 Services Overview

### Containerized Services
- **web** (port 8000) - Django application with Gunicorn
- **redis** (port 6379) - Cache and message broker
- **celery-worker** - Background task processor
- **celery-beat** - Scheduled task manager
- **celery-flower** (port 5555) - Task monitoring dashboard

### External Dependencies
- **PostgreSQL** - Database server (your infrastructure)
- **Nginx** - Reverse proxy with SSL termination (your infrastructure)

## 🔧 External Infrastructure Setup

### PostgreSQL Database Setup

1. **Create Database:**
```sql
CREATE DATABASE senangkira;
CREATE USER senangkira_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE senangkira TO senangkira_user;

-- Enable required extensions
\c senangkira
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

2. **Configure Connection:**
```bash
# Update .env file
DATABASE_URL=postgresql://senangkira_user:secure_password@your-db-host:5432/senangkira
```

3. **Initialize Schema:**
```bash
# Deploy schema to external database
psql -h your-db-host -U senangkira_user -d senangkira -f docs/schema.sql

# Run Django migrations
docker-compose exec web python manage.py migrate
```

### Nginx Reverse Proxy Setup

1. **Use Example Configuration:**
```bash
# Copy example configuration
cp nginx.external.conf.example /etc/nginx/sites-available/senangkira

# Edit for your domain and paths
sudo nano /etc/nginx/sites-available/senangkira

# Enable site
sudo ln -s /etc/nginx/sites-available/senangkira /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

2. **Key Configuration Points:**
- **Upstream**: Points to `localhost:8000` (Docker web service)
- **SSL**: Configure your SSL certificates
- **Static Files**: Serve from external path or proxy to container
- **Rate Limiting**: Protect API endpoints
- **Security Headers**: HSTS, CSP, etc.

## 🔒 Security Considerations

### Database Security
- Use strong database passwords
- Restrict database access by IP
- Enable SSL connections if database is remote
- Regular backup strategy

### Application Security
- Use strong `SECRET_KEY`
- Restrict `ALLOWED_HOSTS` to your domains
- Configure HTTPS-only cookies in production
- Monitor application logs

### Network Security
- Use private networks for database connections
- Configure firewall rules
- Implement rate limiting in Nginx
- Regular security updates

## 🚀 Deployment Workflow

### Development Deployment
```bash
# 1. Set up external database
createdb senangkira
psql senangkira -f docs/schema.sql

# 2. Configure environment
cp .env.example .env
# Edit DATABASE_URL for local database

# 3. Start development containers
docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up

# 4. Run migrations
docker-compose exec web python manage.py migrate
```

### Production Deployment
```bash
# 1. Set up production database and Nginx
# (Follow PostgreSQL and Nginx setup above)

# 2. Configure production environment
cp .env.example .env
# Set production values

# 3. Start production services
docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d

# 4. Create superuser
docker-compose exec web python manage.py createsuperuser

# 5. Collect static files (if needed)
docker-compose exec web python manage.py collectstatic --noinput
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl https://yourdomain.com/api/health/

# Container health
docker-compose ps

# Celery monitoring
open https://yourdomain.com/flower/
```

### Log Management
```bash
# Application logs
docker-compose logs -f web

# Celery logs
docker-compose logs -f celery-worker

# Nginx logs (external)
tail -f /var/log/nginx/senangkira_access.log
```

### Backup Strategy
```bash
# Database backup (external)
pg_dump -h your-db-host -U senangkira_user senangkira > backup_$(date +%Y%m%d).sql

# Redis backup (container)
docker-compose exec redis redis-cli BGSAVE
docker cp senangkira_redis:/data/dump.rdb ./redis_backup.rdb

# Application files backup
tar -czf app_backup_$(date +%Y%m%d).tar.gz logs/ media/
```

## 🔧 Configuration Examples

### Environment Variables (.env)
```env
# Django Configuration
DEBUG=False
SECRET_KEY=your-256-bit-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# External Database
DATABASE_URL=postgresql://senangkira_user:secure_password@db.yourdomain.com:5432/senangkira

# Email Configuration
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password

# Monitoring
FLOWER_USER=admin
FLOWER_PASSWORD=secure-flower-password

# Superuser (auto-created)
SUPERUSER_USERNAME=admin
SUPERUSER_EMAIL=admin@yourdomain.com
SUPERUSER_PASSWORD=secure-admin-password
```

### Nginx Location Block Example
```nginx
upstream senangkira_backend {
    server senangkira_web:8000;  # Container name in padux network
}

location /api/ {
    limit_req zone=api burst=20 nodelay;
    
    proxy_pass http://senangkira_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

## 🛠️ Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Test from container
docker-compose exec web python manage.py dbshell -c "SELECT 1;"

# Test from host
pg_isready -h your-db-host -p 5432 -U senangkira_user
```

**Nginx Proxy Issues:**
```bash
# Check Nginx configuration
sudo nginx -t

# Check upstream connection (from within padux network or external Nginx)
curl -I http://senangkira_web:8000/api/health/

# Check Nginx logs
tail -f /var/log/nginx/error.log
```

**Container Issues:**
```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs web

# Restart services
docker-compose restart web
```

## 📚 Benefits of External Infrastructure

### Advantages
- **Database Persistence**: Data survives container restarts
- **Performance**: Dedicated database server resources
- **Backup Control**: Direct database backup management
- **SSL Termination**: Nginx handles SSL certificates
- **Load Balancing**: Easy to add multiple app instances
- **Monitoring**: External infrastructure monitoring tools

### Considerations
- **Network Latency**: Ensure low latency to database
- **Security**: Secure network connections between services
- **Maintenance**: Manage external infrastructure updates
- **Complexity**: Additional infrastructure components to maintain

This configuration provides production-ready deployment while maintaining flexibility and security through external infrastructure management.