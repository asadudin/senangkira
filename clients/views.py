"""
Enhanced Client views for SenangKira API with multi-tenant support and comprehensive CRUD operations.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
import logging

from senangkira.permissions.base import IsOwner, IsOwnerOrReadOnly
from senangkira.utils.viewsets import MultiTenantViewSet
from .models import Client
from .serializers import (
    ClientSerializer,
    ClientListSerializer,
    ClientCreateSerializer,
    ClientUpdateSerializer
)

logger = logging.getLogger(__name__)


class ClientViewSet(MultiTenantViewSet):
    """
    Enhanced Client API ViewSet with multi-tenant support and comprehensive CRUD operations.
    
    Provides:
    - GET /api/clients/ - List clients with filtering and pagination
    - POST /api/clients/ - Create new client
    - GET /api/clients/{id}/ - Retrieve specific client
    - PUT /api/clients/{id}/ - Update client (full)
    - PATCH /api/clients/{id}/ - Update client (partial)
    - DELETE /api/clients/{id}/ - Delete client
    - GET /api/clients/active/ - List only active clients
    - POST /api/clients/{id}/deactivate/ - Deactivate client
    - POST /api/clients/{id}/activate/ - Activate client
    """
    model = Client
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'company']
    search_fields = ['name', 'email', 'phone', 'company']
    ordering_fields = ['name', 'email', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return clients filtered by current user (multi-tenant)."""
        return Client.objects.filter(owner=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ClientListSerializer
        elif self.action == 'create':
            return ClientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClientUpdateSerializer
        return ClientSerializer
    
    def perform_create(self, serializer):
        """Create client with current user as owner."""
        client = serializer.save(owner=self.request.user)
        logger.info(f"Client created: {client.name} by {self.request.user.email}")
    
    def perform_update(self, serializer):
        """Update client with logging."""
        client = serializer.save()
        logger.info(f"Client updated: {client.name} by {self.request.user.email}")
    
    def perform_destroy(self, instance):
        """Delete client with logging."""
        client_name = instance.name
        super().perform_destroy(instance)
        logger.info(f"Client deleted: {client_name} by {self.request.user.email}")
    
    def list(self, request, *args, **kwargs):
        """List clients with enhanced filtering and statistics."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add statistics to response
        total_clients = self.get_queryset().count()
        active_clients = self.get_queryset().filter(is_active=True).count()
        inactive_clients = total_clients - active_clients
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            
            # Add statistics to paginated response
            paginated_response.data['statistics'] = {
                'total_clients': total_clients,
                'active_clients': active_clients,
                'inactive_clients': inactive_clients,
                'filtered_count': queryset.count()
            }
            
            return paginated_response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'statistics': {
                'total_clients': total_clients,
                'active_clients': active_clients,
                'inactive_clients': inactive_clients,
                'filtered_count': queryset.count()
            }
        })
    
    def create(self, request, *args, **kwargs):
        """Create client with enhanced validation and response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        client = serializer.save(owner=request.user)
        
        # Return full client data using the detailed serializer
        response_serializer = ClientSerializer(client, context={'request': request})
        
        return Response(
            {
                'message': 'Client created successfully',
                'client': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve client with detailed information."""
        instance = self.get_object()
        serializer = ClientSerializer(instance, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update client with enhanced response."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        client = serializer.save()
        
        # Return full client data
        response_serializer = ClientSerializer(client, context={'request': request})
        
        return Response({
            'message': 'Client updated successfully',
            'client': response_serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete client with confirmation message."""
        instance = self.get_object()
        client_name = instance.name
        self.perform_destroy(instance)
        
        return Response({
            'message': f'Client "{client_name}" deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """List only active clients."""
        queryset = self.get_queryset().filter(is_active=True)
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ClientListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ClientListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a client."""
        client = self.get_object()
        
        if not client.is_active:
            return Response(
                {'message': 'Client is already inactive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        client.is_active = False
        client.save(update_fields=['is_active', 'updated_at'])
        
        logger.info(f"Client deactivated: {client.name} by {request.user.email}")
        
        return Response({
            'message': f'Client "{client.name}" deactivated successfully',
            'client': ClientSerializer(client, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a client."""
        client = self.get_object()
        
        if client.is_active:
            return Response(
                {'message': 'Client is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        client.is_active = True
        client.save(update_fields=['is_active', 'updated_at'])
        
        logger.info(f"Client activated: {client.name} by {request.user.email}")
        
        return Response({
            'message': f'Client "{client.name}" activated successfully',
            'client': ClientSerializer(client, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search functionality."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(company__icontains=query) |
            Q(address__icontains=query)
        )
        
        # Apply additional filters
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ClientListSerializer(page, many=True, context={'request': request})
            paginated_response = self.get_paginated_response(serializer.data)
            paginated_response.data['search_query'] = query
            return paginated_response
        
        serializer = ClientListSerializer(queryset, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'search_query': query,
            'count': queryset.count()
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get client statistics."""
        queryset = self.get_queryset()
        
        total_clients = queryset.count()
        active_clients = queryset.filter(is_active=True).count()
        inactive_clients = total_clients - active_clients
        
        # Recent statistics (last 30 days)
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_clients = queryset.filter(created_at__gte=thirty_days_ago).count()
        
        return Response({
            'total_clients': total_clients,
            'active_clients': active_clients,
            'inactive_clients': inactive_clients,
            'recent_clients': recent_clients,
            'conversion_rate': round((active_clients / total_clients * 100) if total_clients > 0 else 0, 2)
        })