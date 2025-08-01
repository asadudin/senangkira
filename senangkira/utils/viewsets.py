"""
Utility viewsets for multi-tenant applications.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class MultiTenantViewSet(viewsets.ModelViewSet):
    """
    Base viewset that provides multi-tenant functionality.
    Automatically filters querysets by the current user (owner).
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Return objects for the current user only.
        Subclasses should override this method to provide proper filtering.
        """
        if hasattr(self.queryset.model, 'owner'):
            return super().get_queryset().filter(owner=self.request.user)
        return super().get_queryset()
    
    def perform_create(self, serializer):
        """
        Set the owner to the current user when creating objects.
        """
        if hasattr(serializer.Meta.model, 'owner'):
            serializer.save(owner=self.request.user)
        else:
            serializer.save()