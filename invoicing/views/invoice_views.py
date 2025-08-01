"""
Enhanced Invoice views for SenangKira API with comprehensive CRUD operations and payment management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date, timedelta
import logging

from senangkira.permissions.base import IsOwner
from senangkira.utils.viewsets import MultiTenantViewSet
from ..models import Invoice, InvoiceLineItem, InvoiceStatus, Quote
from ..serializers import (
    InvoiceSerializer,
    InvoiceListSerializer,
    InvoiceFromQuoteSerializer
)

logger = logging.getLogger(__name__)


class InvoiceViewSet(MultiTenantViewSet):
    """
    Enhanced Invoice API ViewSet with comprehensive CRUD operations and payment management.
    
    Provides:
    - GET /api/invoices/ - List invoices with filtering and pagination
    - POST /api/invoices/ - Create new invoice with line items
    - GET /api/invoices/{id}/ - Retrieve specific invoice with line items
    - PUT /api/invoices/{id}/ - Update invoice (draft only)
    - PATCH /api/invoices/{id}/ - Update invoice (partial, draft only)
    - DELETE /api/invoices/{id}/ - Delete invoice (draft only)
    - POST /api/invoices/{id}/send/ - Send invoice to client
    - POST /api/invoices/{id}/mark_paid/ - Mark invoice as paid
    - POST /api/invoices/{id}/cancel/ - Cancel invoice
    - POST /api/invoices/{id}/duplicate/ - Create duplicate invoice
    - POST /api/invoices/from_quote/ - Create invoice from quote
    - GET /api/invoices/statistics/ - Invoice statistics and analytics
    - GET /api/invoices/overdue/ - Get overdue invoices
    """
    model = Invoice
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'client']
    search_fields = ['invoice_number', 'title', 'client__name', 'client__email']
    ordering_fields = ['invoice_number', 'issue_date', 'due_date', 'total_amount', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return invoices filtered by current user (multi-tenant)."""
        return Invoice.objects.filter(owner=self.request.user).select_related('client', 'source_quote').prefetch_related('line_items')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'from_quote':
            return InvoiceFromQuoteSerializer
        return InvoiceSerializer
    
    def perform_create(self, serializer):
        """Create invoice with current user as owner."""
        invoice = serializer.save(owner=self.request.user)
        logger.info(f"Invoice created: {invoice.invoice_number} by {self.request.user.email}")
    
    def perform_update(self, serializer):
        """Update invoice with logging."""
        invoice = serializer.save()
        logger.info(f"Invoice updated: {invoice.invoice_number} by {self.request.user.email}")
    
    def perform_destroy(self, instance):
        """Delete invoice with logging."""
        invoice_number = instance.invoice_number
        super().perform_destroy(instance)
        logger.info(f"Invoice deleted: {invoice_number} by {self.request.user.email}")
    
    def list(self, request, *args, **kwargs):
        """List invoices with enhanced filtering and statistics."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add statistics to response
        all_invoices = self.get_queryset()
        stats = {
            'total_invoices': all_invoices.count(),
            'draft_invoices': all_invoices.filter(status=InvoiceStatus.DRAFT).count(),
            'sent_invoices': all_invoices.filter(status=InvoiceStatus.SENT).count(),
            'paid_invoices': all_invoices.filter(status=InvoiceStatus.PAID).count(),
            'overdue_invoices': all_invoices.filter(status=InvoiceStatus.OVERDUE).count(),
            'cancelled_invoices': all_invoices.filter(status=InvoiceStatus.CANCELLED).count(),
            'total_value': all_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'outstanding_value': all_invoices.exclude(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED]).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
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
        """Create invoice with enhanced validation and response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invoice = serializer.save(owner=request.user)
        
        # Return full invoice data using the detailed serializer
        response_serializer = InvoiceSerializer(invoice, context={'request': request})
        
        return Response(
            {
                'message': 'Invoice created successfully',
                'invoice': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve invoice with detailed information."""
        instance = self.get_object()
        serializer = InvoiceSerializer(instance, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Update invoice with enhanced response."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if invoice can be edited
        if instance.status not in [InvoiceStatus.DRAFT]:
            return Response(
                {'error': 'Only draft invoices can be edited'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = InvoiceSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        invoice = serializer.save()
        
        return Response({
            'message': 'Invoice updated successfully',
            'invoice': InvoiceSerializer(invoice, context={'request': request}).data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete invoice with confirmation message."""
        instance = self.get_object()
        
        # Check if invoice can be deleted
        if instance.status not in [InvoiceStatus.DRAFT]:
            return Response(
                {'error': 'Only draft invoices can be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice_number = instance.invoice_number
        self.perform_destroy(instance)
        
        return Response({
            'message': f'Invoice "{invoice_number}" deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send invoice to client."""
        invoice = self.get_object()
        
        if invoice.mark_as_sent():
            logger.info(f"Invoice sent: {invoice.invoice_number} by {request.user.email}")
            return Response({
                'message': f'Invoice "{invoice.invoice_number}" sent successfully',
                'invoice': InvoiceSerializer(invoice, context={'request': request}).data
            })
        else:
            return Response(
                {'error': 'Invoice cannot be sent in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid."""
        invoice = self.get_object()
        
        if invoice.mark_as_paid():
            logger.info(f"Invoice marked as paid: {invoice.invoice_number} by {request.user.email}")
            return Response({
                'message': f'Invoice "{invoice.invoice_number}" marked as paid successfully',
                'invoice': InvoiceSerializer(invoice, context={'request': request}).data
            })
        else:
            return Response(
                {'error': 'Invoice cannot be marked as paid in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel invoice."""
        invoice = self.get_object()
        
        if invoice.mark_as_cancelled():
            logger.info(f"Invoice cancelled: {invoice.invoice_number} by {request.user.email}")
            return Response({
                'message': f'Invoice "{invoice.invoice_number}" cancelled successfully',
                'invoice': InvoiceSerializer(invoice, context={'request': request}).data
            })
        else:
            return Response(
                {'error': 'Invoice cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of the invoice."""
        original_invoice = self.get_object()
        
        # Create duplicate invoice data
        duplicate_data = {
            'client': original_invoice.client.id,
            'title': f"Copy of {original_invoice.title}" if original_invoice.title else None,
            'notes': original_invoice.notes,
            'terms': original_invoice.terms,
            'tax_rate': original_invoice.tax_rate,
            'line_items': []
        }
        
        # Copy line items
        for line_item in original_invoice.line_items.all():
            duplicate_data['line_items'].append({
                'description': line_item.description,
                'quantity': line_item.quantity,
                'unit_price': line_item.unit_price,
                'sort_order': line_item.sort_order
            })
        
        # Create duplicate invoice
        serializer = InvoiceSerializer(data=duplicate_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        duplicate_invoice = serializer.save(owner=request.user)
        
        logger.info(f"Invoice duplicated: {original_invoice.invoice_number} -> {duplicate_invoice.invoice_number} by {request.user.email}")
        
        return Response({
            'message': f'Invoice duplicated successfully',
            'original_invoice': original_invoice.invoice_number,
            'duplicate_invoice': InvoiceSerializer(duplicate_invoice, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def from_quote(self, request):
        """Create invoice from quote (Quote-to-Invoice conversion)."""
        serializer = InvoiceFromQuoteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        invoice = serializer.save()
        
        logger.info(f"Invoice created from quote: {invoice.source_quote.quote_number} -> {invoice.invoice_number} by {request.user.email}")
        
        return Response({
            'message': 'Invoice created from quote successfully',
            'source_quote': invoice.source_quote.quote_number,
            'invoice': InvoiceSerializer(invoice, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get comprehensive invoice statistics."""
        queryset = self.get_queryset()
        
        # Basic counts
        total_invoices = queryset.count()
        status_counts = {}
        for status_choice in InvoiceStatus.choices:
            status_counts[status_choice[0]] = queryset.filter(status=status_choice[0]).count()
        
        # Financial statistics
        financial_stats = queryset.aggregate(
            total_value=Sum('total_amount'),
            avg_value=Sum('total_amount') / Count('id') if total_invoices > 0 else 0
        )
        
        # Outstanding amounts (unpaid invoices)
        outstanding_invoices = queryset.exclude(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED])
        outstanding_stats = outstanding_invoices.aggregate(
            outstanding_count=Count('id'),
            outstanding_value=Sum('total_amount')
        )
        
        # Recent statistics (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_invoices = queryset.filter(created_at__gte=thirty_days_ago)
        recent_paid = queryset.filter(paid_at__gte=thirty_days_ago)
        
        # Payment rate (paid vs sent)
        sent_invoices = queryset.filter(status__in=[InvoiceStatus.SENT, InvoiceStatus.VIEWED, InvoiceStatus.PAID, InvoiceStatus.OVERDUE])
        paid_invoices = queryset.filter(status=InvoiceStatus.PAID)
        payment_rate = (paid_invoices.count() / sent_invoices.count() * 100) if sent_invoices.count() > 0 else 0
        
        # Overdue analysis
        overdue_invoices = queryset.filter(due_date__lt=date.today()).exclude(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED])
        
        # Client statistics
        client_stats = queryset.values('client__name').annotate(
            invoice_count=Count('id'),
            total_value=Sum('total_amount'),
            outstanding_value=Sum('total_amount', filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.VIEWED, InvoiceStatus.OVERDUE]))
        ).order_by('-total_value')[:5]
        
        return Response({
            'total_invoices': total_invoices,
            'status_breakdown': status_counts,
            'financial': {
                'total_value': financial_stats['total_value'] or 0,
                'average_value': financial_stats['avg_value'] or 0,
                'outstanding_count': outstanding_stats['outstanding_count'] or 0,
                'outstanding_value': outstanding_stats['outstanding_value'] or 0
            },
            'recent_activity': {
                'invoices_last_30_days': recent_invoices.count(),
                'value_last_30_days': recent_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                'payments_last_30_days': recent_paid.count(),
                'payments_value_last_30_days': recent_paid.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            },
            'performance': {
                'payment_rate': round(payment_rate, 2),
                'sent_invoices': sent_invoices.count(),
                'paid_invoices': paid_invoices.count(),
                'overdue_count': overdue_invoices.count(),
                'overdue_value': overdue_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            },
            'top_clients': list(client_stats)
        })
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue invoices."""
        overdue_invoices = self.get_queryset().filter(
            due_date__lt=date.today()
        ).exclude(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED]).order_by('due_date')
        
        serializer = InvoiceListSerializer(overdue_invoices, many=True, context={'request': request})
        
        return Response({
            'count': overdue_invoices.count(),
            'total_overdue_amount': overdue_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'invoices': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get invoices due within the next 7 days."""
        next_week = date.today() + timedelta(days=7)
        due_soon_invoices = self.get_queryset().filter(
            status__in=[InvoiceStatus.SENT, InvoiceStatus.VIEWED],
            due_date__lte=next_week,
            due_date__gte=date.today()
        ).order_by('due_date')
        
        serializer = InvoiceListSerializer(due_soon_invoices, many=True, context={'request': request})
        
        return Response({
            'count': due_soon_invoices.count(),
            'total_amount': due_soon_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'invoices': serializer.data
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
            Q(invoice_number__icontains=query) |
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
            serializer = InvoiceListSerializer(page, many=True, context={'request': request})
            paginated_response = self.get_paginated_response(serializer.data)
            paginated_response.data['search_query'] = query
            return paginated_response
        
        serializer = InvoiceListSerializer(queryset, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'search_query': query,
            'count': queryset.count()
        })
    
    @action(detail=False, methods=['post'])
    def update_overdue_status(self, request):
        """Update overdue status for all invoices (maintenance endpoint)."""
        # Find invoices that should be marked as overdue
        overdue_candidates = self.get_queryset().filter(
            due_date__lt=date.today(),
            status__in=[InvoiceStatus.SENT, InvoiceStatus.VIEWED]
        )
        
        updated_count = 0
        for invoice in overdue_candidates:
            invoice.status = InvoiceStatus.OVERDUE
            invoice.save(update_fields=['status', 'updated_at'])
            updated_count += 1
        
        logger.info(f"Updated {updated_count} invoices to overdue status by {request.user.email}")
        
        return Response({
            'message': f'Updated {updated_count} invoices to overdue status',
            'updated_count': updated_count
        })