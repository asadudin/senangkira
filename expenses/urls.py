"""
URL configuration for expense management endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, ExpenseAttachmentViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', ExpenseViewSet, basename='expense')
router.register(r'attachments', ExpenseAttachmentViewSet, basename='expense-attachment')

# URL patterns  
urlpatterns = [
    path('', include(router.urls)),
]

# Custom URL patterns for additional endpoints
app_name = 'expenses'