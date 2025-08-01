"""
Enhanced Quote views for SenangKira API with comprehensive CRUD operations and status management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from senangkira.permissions.base import IsOwner
from senangkira.utils.viewsets import MultiTenantViewSet
from ..models import Quote, QuoteLineItem, QuoteStatus
from ..serializers import (
    QuoteSerializer,
    QuoteListSerializer,
    QuoteCreateSerializer,
    QuoteStatusSerializer
)

logger = logging.getLogger(__name__)


class QuoteViewSet(MultiTenantViewSet):
    """
    Enhanced Quote API ViewSet with comprehensive CRUD operations and status management.
    
    Provides:
    - GET /api/quotes/ - List quotes with filtering and pagination
    - POST /api/quotes/ - Create new quote with line items
    - GET /api/quotes/{id}/ - Retrieve specific quote with line items
    - PUT /api/quotes/{id}/ - Update quote (full)
    - PATCH /api/quotes/{id}/ - Update quote (partial)
    - DELETE /api/quotes/{id}/ - Delete quote
    - POST /api/quotes/{id}/send/ - Send quote to client
    - POST /api/quotes/{id}/approve/ - Mark quote as approved
    - POST /api/quotes/{id}/decline/ - Mark quote as declined
    - POST /api/quotes/{id}/duplicate/ - Create duplicate quote
    - GET /api/quotes/statistics/ - Quote statistics and analytics
    """
    model = Quote
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'client']
    search_fields = ['quote_number', 'title', 'client__name', 'client__email']
    ordering_fields = ['quote_number', 'issue_date', 'valid_until', 'total_amount', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return quotes filtered by current user (multi-tenant)."""
        return Quote.objects.filter(owner=self.request.user).select_related('client').prefetch_related('line_items')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return QuoteListSerializer
        elif self.action == 'create':
            return QuoteCreateSerializer
        elif self.action in ['send', 'approve', 'decline']:
            return QuoteStatusSerializer
        return QuoteSerializer
    
    def perform_create(self, serializer):
        """Create quote with current user as owner."""
        quote = serializer.save(owner=self.request.user)
        logger.info(f"Quote created: {quote.quote_number} by {self.request.user.email}")
    
    def perform_update(self, serializer):
        """Update quote with logging."""
        quote = serializer.save()
        logger.info(f"Quote updated: {quote.quote_number} by {self.request.user.email}")
    
    def perform_destroy(self, instance):
        """Delete quote with logging."""
        quote_number = instance.quote_number
        super().perform_destroy(instance)
        logger.info(f"Quote deleted: {quote_number} by {self.request.user.email}")
    
    def list(self, request, *args, **kwargs):
        """List quotes with enhanced filtering and statistics."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add statistics to response
        all_quotes = self.get_queryset()
        stats = {
            'total_quotes': all_quotes.count(),
            'draft_quotes': all_quotes.filter(status=QuoteStatus.DRAFT).count(),
            'sent_quotes': all_quotes.filter(status=QuoteStatus.SENT).count(),
            'approved_quotes': all_quotes.filter(status=QuoteStatus.APPROVED).count(),
            'declined_quotes': all_quotes.filter(status=QuoteStatus.DECLINED).count(),
            'expired_quotes': all_quotes.filter(status=QuoteStatus.EXPIRED).count(),
            'total_value': all_quotes.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        }
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            
            # Add statistics to paginated response
            paginated_response.data['statistics'] = stats
            return paginated_response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'statistics': stats
        })
    
    def create(self, request, *args, **kwargs):
        """Create quote with enhanced validation and response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quote = serializer.save(owner=request.user)
        
        # Return full quote data using the detailed serializer
        response_serializer = QuoteSerializer(quote, context={'request': request})
        
        return Response(
            {
                'message': 'Quote created successfully',
                'quote': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve quote with detailed information."""
        instance = self.get_object()
        serializer = QuoteSerializer(instance, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update quote with enhanced response."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if quote can be edited
        if instance.status not in [QuoteStatus.DRAFT]:
            return Response(
                {'error': 'Only draft quotes can be edited'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = QuoteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        quote = serializer.save()
        
        return Response({
            'message': 'Quote updated successfully',
            'quote': QuoteSerializer(quote, context={'request': request}).data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete quote with confirmation message."""
        instance = self.get_object()
        
        # Check if quote can be deleted
        if instance.status not in [QuoteStatus.DRAFT, QuoteStatus.DECLINED]:
            return Response(
                {'error': 'Only draft or declined quotes can be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quote_number = instance.quote_number
        self.perform_destroy(instance)
        
        return Response({
            'message': f'Quote "{quote_number}" deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send quote to client."""
        quote = self.get_object()
        
        if quote.mark_as_sent():
            logger.info(f"Quote sent: {quote.quote_number} by {request.user.email}")
            return Response({
                'message': f'Quote "{quote.quote_number}" sent successfully',
                'quote': QuoteSerializer(quote, context={'request': request}).data
            })
        else:
            return Response(
                {'error': 'Quote cannot be sent in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Mark quote as approved."""
        quote = self.get_object()
        
        if quote.mark_as_approved():
            logger.info(f"Quote approved: {quote.quote_number} by {request.user.email}")
            return Response({
                'message': f'Quote "{quote.quote_number}" approved successfully',
                'quote': QuoteSerializer(quote, context={'request': request}).data
            })
        else:
            return Response(
                {'error': 'Quote cannot be approved in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Mark quote as declined."""
        quote = self.get_object()
        
        if quote.mark_as_declined():
            logger.info(f"Quote declined: {quote.quote_number} by {request.user.email}")
            return Response({
                'message': f'Quote "{quote.quote_number}" declined successfully',
                'quote': QuoteSerializer(quote, context={'request': request}).data
            })
        else:
            return Response(
                {'error': 'Quote cannot be declined in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of the quote."""
        original_quote = self.get_object()
        
        # Create duplicate quote data
        duplicate_data = {
            'client': original_quote.client.id,
            'title': f"Copy of {original_quote.title}" if original_quote.title else None,
            'notes': original_quote.notes,
            'terms': original_quote.terms,
            'tax_rate': original_quote.tax_rate,
            'line_items': []
        }
        
        # Copy line items
        for line_item in original_quote.line_items.all():
            duplicate_data['line_items'].append({
                'description': line_item.description,
                'quantity': line_item.quantity,
                'unit_price': line_item.unit_price,
                'sort_order': line_item.sort_order
            })
        
        # Create duplicate quote
        serializer = QuoteCreateSerializer(data=duplicate_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        duplicate_quote = serializer.save(owner=request.user)
        
        logger.info(f"Quote duplicated: {original_quote.quote_number} -> {duplicate_quote.quote_number} by {request.user.email}")
        
        return Response({
            'message': f'Quote duplicated successfully',
            'original_quote': original_quote.quote_number,
            'duplicate_quote': QuoteSerializer(duplicate_quote, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get comprehensive quote statistics."""
        queryset = self.get_queryset()
        
        # Basic counts
        total_quotes = queryset.count()
        status_counts = {}
        for status_choice in QuoteStatus.choices:
            status_counts[status_choice[0]] = queryset.filter(status=status_choice[0]).count()
        
        # Financial statistics
        financial_stats = queryset.aggregate(
            total_value=Sum('total_amount'),
            avg_value=Sum('total_amount') / Count('id') if total_quotes > 0 else 0
        )
        
        # Recent statistics (last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_quotes = queryset.filter(created_at__gte=thirty_days_ago)
        
        # Approval rate
        sent_quotes = queryset.filter(status__in=[QuoteStatus.SENT, QuoteStatus.APPROVED, QuoteStatus.DECLINED])
        approved_quotes = queryset.filter(status=QuoteStatus.APPROVED)
        approval_rate = (approved_quotes.count() / sent_quotes.count() * 100) if sent_quotes.count() > 0 else 0
        
        # Client statistics
        client_stats = queryset.values('client__name').annotate(
            quote_count=Count('id'),
            total_value=Sum('total_amount')
        ).order_by('-total_value')[:5]
        
        return Response({
            'total_quotes': total_quotes,
            'status_breakdown': status_counts,
            'financial': {
                'total_value': financial_stats['total_value'] or 0,
                'average_value': financial_stats['avg_value'] or 0
            },
            'recent_activity': {
                'quotes_last_30_days': recent_quotes.count(),
                'value_last_30_days': recent_quotes.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            },
            'performance': {
                'approval_rate': round(approval_rate, 2),
                'sent_quotes': sent_quotes.count(),
                'approved_quotes': approved_quotes.count()
            },
            'top_clients': list(client_stats)
        })
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get quotes expiring within the next 7 days."""
        from datetime import date, timedelta
        
        next_week = date.today() + timedelta(days=7)
        expiring_quotes = self.get_queryset().filter(
            status=QuoteStatus.SENT,
            valid_until__lte=next_week,
            valid_until__gte=date.today()
        ).order_by('valid_until')
        
        serializer = QuoteListSerializer(expiring_quotes, many=True, context={'request': request})
        
        return Response({
            'count': expiring_quotes.count(),
            'quotes': serializer.data
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
            Q(quote_number__icontains=query) |
            Q(title__icontains=query) |
            Q(client__name__icontains=query) |
            Q(client__email__icontains=query) |
            Q(line_items__description__icontains=query)
        ).distinct()
        
        # Apply additional filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        client_filter = request.query_params.get('client')
        if client_filter:
            queryset = queryset.filter(client=client_filter)
        
        queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = QuoteListSerializer(page, many=True, context={'request': request})
            paginated_response = self.get_paginated_response(serializer.data)
            paginated_response.data['search_query'] = query
            return paginated_response
        
        serializer = QuoteListSerializer(queryset, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'search_query': query,
            'count': queryset.count()
        })