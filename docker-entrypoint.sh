#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting SenangKira Django Application${NC}"

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo -e "${YELLOW}⏳ Waiting for $service to be ready...${NC}"
    
    while ! nc -z $host $port; do
        echo -e "${YELLOW}⏳ $service is unavailable - sleeping...${NC}"
        sleep 1
    done
    
    echo -e "${GREEN}✅ $service is ready!${NC}"
}

# Wait for external database (if specified)
if [ "$DATABASE_URL" ]; then
    # Extract host and port from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ "$DB_HOST" ] && [ "$DB_PORT" ]; then
        echo -e "${YELLOW}🔗 Connecting to external PostgreSQL at $DB_HOST:$DB_PORT${NC}"
        wait_for_service $DB_HOST $DB_PORT "External PostgreSQL Database"
    fi
fi

# Wait for Redis
if [ "$CELERY_BROKER_URL" ]; then
    # Extract host and port from Redis URL
    REDIS_HOST=$(echo $CELERY_BROKER_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    REDIS_PORT=$(echo $CELERY_BROKER_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ "$REDIS_HOST" ] && [ "$REDIS_PORT" ]; then
        wait_for_service $REDIS_HOST $REDIS_PORT "Redis Cache"
    fi
fi

# Database operations
echo -e "${YELLOW}📊 Running database migrations...${NC}"
python manage.py migrate --noinput

# Create superuser if specified
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo -e "${YELLOW}👤 Creating superuser...${NC}"
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
fi

# Collect static files (production only)
if [ "$DEBUG" != "True" ]; then
    echo -e "${YELLOW}📁 Collecting static files...${NC}"
    python manage.py collectstatic --noinput
fi

# Warm up cache (optional)
if [ "$WARM_CACHE" = "true" ]; then
    echo -e "${YELLOW}🔥 Warming up cache...${NC}"
    python manage.py shell << EOF
try:
    from dashboard.tasks import warm_dashboard_cache
    warm_dashboard_cache.delay()
    print('Cache warming task queued')
except ImportError:
    print('Cache warming not available')
EOF
fi

# Health check
echo -e "${YELLOW}🏥 Running health checks...${NC}"
python manage.py check --deploy --verbosity=0

echo -e "${GREEN}✅ SenangKira is ready to start!${NC}"
echo -e "${GREEN}🎯 Starting application with command: $@${NC}"

# Execute the main command
exec "$@"