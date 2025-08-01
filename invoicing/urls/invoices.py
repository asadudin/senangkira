"""
Invoice URLs for SenangKira API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views.invoice_views import InvoiceViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]