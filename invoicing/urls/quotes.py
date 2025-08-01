"""
Enhanced Quote URLs for SenangKira API with comprehensive endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views.quote_views import QuoteViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', QuoteViewSet, basename='quote')

urlpatterns = [
    path('', include(router.urls)),
]