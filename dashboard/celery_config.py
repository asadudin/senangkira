"""
Celery Configuration for SenangKira Dashboard System

This module configures Celery for distributed task processing with Redis as the message broker.
It integrates with the existing caching system (SK-603) and provides monitoring capabilities.

Architecture:
- Redis Broker: redis://localhost:6379/0 (default)
- Redis Backend: redis://localhost:6379/1 (results)
- Task Queues: 
  - high_priority: Critical dashboard operations
  - default: Standard processing tasks
  - low_priority: Background maintenance tasks
  - cache_operations: Cache warming and invalidation
  - analytics: Performance and usage analytics
"""

import os
from celery import Celery
from django.conf import settings

# This file is no longer used as the main Celery configuration
# The configuration is now in the dashboard app's __init__.py and tasks.py files
# This file is kept for reference only