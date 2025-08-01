"""
Base utility views for SenangKira API.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..permissions.base import IsTenantOwner


class TenantViewSetMixin:
    """
    Mixin to add tenant isolation to ViewSets.
    Automatically filters querysets by owner.
    """
    permission_classes = [IsAuthenticated, IsTenantOwner]
    
    def get_queryset(self):
        """
        Filter queryset to only include objects owned by the current user.
        """
        if hasattr(self, 'queryset') and self.queryset is not None:
            return self.queryset.filter(owner=self.request.user)
        return super().get_queryset().filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        """
        Set the owner to the current user when creating objects.
        """
        serializer.save(owner=self.request.user)


class BaseAPIViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Base ViewSet with tenant isolation and common functionality.
    """
    pass


class ReadOnlyTenantViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet with tenant isolation.
    """
    pass