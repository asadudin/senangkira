"""
Multi-tenant isolation middleware for SenangKira.
Ensures users can only access their own data.
"""

from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser


class TenantIsolationMiddleware:
    """
    Middleware to enforce tenant isolation.
    Adds user context for data filtering.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add tenant context to request
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            request.tenant_id = request.user.id
        else:
            request.tenant_id = None
            
        response = self.get_response(request)
        return response


class APIResponseMiddleware:
    """
    Middleware to standardize API responses and add security headers.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers for API endpoints
        if request.path.startswith('/api/'):
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            
        return response