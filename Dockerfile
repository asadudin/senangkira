# Multi-stage build for production optimization
FROM python:3.13-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-traditional \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base AS production

# Create non-root user for security
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Copy application code
COPY --chown=appuser:appuser manage.py .
COPY --chown=appuser:appuser senangkira/ senangkira/
COPY --chown=appuser:appuser authentication/ authentication/
COPY --chown=appuser:appuser clients/ clients/
COPY --chown=appuser:appuser invoicing/ invoicing/
COPY --chown=appuser:appuser expenses/ expenses/
COPY --chown=appuser:appuser dashboard/ dashboard/
COPY --chown=appuser:appuser reminders/ reminders/
COPY --chown=appuser:appuser monitoring/ monitoring/

# Create required directories with proper permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media \
    && chown -R appuser:appuser /app/logs /app/staticfiles /app/media \
    && chmod 755 /app/logs /app/staticfiles /app/media

# Copy entrypoint script
COPY --chown=appuser:appuser docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# Run entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "senangkira.wsgi:application"]

# Development stage
FROM base AS development

# Install development dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy all application files for development
COPY . .

# Create required directories
RUN mkdir -p logs staticfiles media

# Expose port for development
EXPOSE 8000

# Run development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]