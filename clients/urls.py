"""
Enhanced Client URLs for SenangKira API with comprehensive endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', ClientViewSet, basename='client')

urlpatterns = [
    path('', include(router.urls)),
]