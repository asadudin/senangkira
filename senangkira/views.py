"""
Main project views for SenangKira.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import sys
import django


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    API root endpoint providing available endpoints.
    """
    return Response({
        'message': 'SenangKira API - Invoice & Quote Management System',
        'version': '1.0.0',
        'endpoints': {
            'authentication': '/api/auth/',
            'clients': '/api/clients/',
            'quotes': '/api/quotes/',
            'invoices': '/api/invoices/',
            'expenses': '/api/expenses/',
            'dashboard': '/api/dashboard/',
            'admin': '/admin/',
            'health': '/api/health/'
        },
        'documentation': '/api/docs/' if settings.DEBUG else None
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    """
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response({
            'status': 'healthy',
            'database': 'connected',
            'django_version': django.get_version(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'debug_mode': settings.DEBUG
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)