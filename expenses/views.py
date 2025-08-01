"""
Enhanced views for expense management with receipt image handling.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from senangkira.utils.viewsets import MultiTenantViewSet
from .models import Expense, ExpenseAttachment, ExpenseCategory
from .serializers import (
    ExpenseSerializer, ExpenseListSerializer, ExpenseCreateSerializer,
    ExpenseAttachmentSerializer, ReceiptUploadSerializer, ExpenseSummarySerializer
)
from .services import ReceiptImageService, ExpenseAnalyticsService


class ExpenseFilter(filters.FilterSet):
    """
    Advanced filtering for expense queries.
    """
    
    # Date range filters
    date_from = filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='date', lookup_expr='lte')
    date_range = filters.DateFromToRangeFilter(field_name='date')
    
    # Amount range filters
    amount_min = filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = filters.NumberFilter(field_name='amount', lookup_expr='lte')
    amount_range = filters.RangeFilter(field_name='amount')
    
    # Category filters
    category = filters.MultipleChoiceFilter(choices=ExpenseCategory.choices)
    category_not = filters.MultipleChoiceFilter(field_name='category', exclude=True)
    
    # Boolean filters
    is_reimbursable = filters.BooleanFilter()
    is_recurring = filters.BooleanFilter()
    has_receipts = filters.BooleanFilter(method='filter_has_receipts')
    is_recent = filters.BooleanFilter(method='filter_is_recent')
    
    # Text search
    search = filters.CharFilter(method='filter_search')
    
    # Period filters
    this_month = filters.BooleanFilter(method='filter_this_month')
    last_month = filters.BooleanFilter(method='filter_last_month')
    this_quarter = filters.BooleanFilter(method='filter_this_quarter')
    this_year = filters.BooleanFilter(method='filter_this_year')
    
    class Meta:
        model = Expense
        fields = [
            'category', 'is_reimbursable', 'is_recurring',
            'date_from', 'date_to', 'amount_min', 'amount_max'
        ]
    
    def filter_has_receipts(self, queryset, name, value):
        """Filter expenses with/without receipt attachments."""
        if value:
            return queryset.filter(attachments__isnull=False).distinct()
        else:
            return queryset.filter(attachments__isnull=True)
    
    def filter_is_recent(self, queryset, name, value):
        """Filter recent expenses (within 30 days)."""
        cutoff_date = date.today() - timedelta(days=30)
        if value:
            return queryset.filter(date__gte=cutoff_date)
        else:
            return queryset.filter(date__lt=cutoff_date)
    
    def filter_search(self, queryset, name, value):
        """Search in description and notes."""
        return queryset.filter(
            Q(description__icontains=value) | Q(notes__icontains=value)
        )
    
    def filter_this_month(self, queryset, name, value):
        """Filter expenses from current month."""
        if value:
            today = date.today()
            start_of_month = today.replace(day=1)
            return queryset.filter(date__gte=start_of_month, date__lte=today)
        return queryset
    
    def filter_last_month(self, queryset, name, value):
        """Filter expenses from last month."""
        if value:
            today = date.today()
            start_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end_of_last_month = today.replace(day=1) - timedelta(days=1)
            return queryset.filter(date__gte=start_of_last_month, date__lte=end_of_last_month)
        return queryset
    
    def filter_this_quarter(self, queryset, name, value):
        """Filter expenses from current quarter."""
        if value:
            today = date.today()
            quarter = (today.month - 1) // 3 + 1
            start_of_quarter = date(today.year, (quarter - 1) * 3 + 1, 1)
            return queryset.filter(date__gte=start_of_quarter, date__lte=today)
        return queryset
    
    def filter_this_year(self, queryset, name, value):
        """Filter expenses from current year."""
        if value:
            today = date.today()
            start_of_year = date(today.year, 1, 1)
            return queryset.filter(date__gte=start_of_year, date__lte=today)
        return queryset


class ExpenseViewSet(MultiTenantViewSet):
    """
    Enhanced ViewSet for expense management with receipt handling.
    
    Provides CRUD operations for expenses with advanced filtering,
    receipt image management, and analytics capabilities.
    """
    
    queryset = Expense.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExpenseFilter
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ExpenseListSerializer
        elif self.action == 'create':
            return ExpenseCreateSerializer
        elif self.action in ['upload_receipts']:
            return ReceiptUploadSerializer
        elif self.action in ['summary', 'analytics']:
            return ExpenseSummarySerializer
        return ExpenseSerializer
    
    def get_queryset(self):
        """Optimized queryset with prefetch for attachments."""
        queryset = super().get_queryset()
        
        if self.action == 'list':
            # Optimize for list view with attachment count
            queryset = queryset.prefetch_related('attachments').annotate(
                attachment_count=Count('attachments')
            )
        elif self.action in ['retrieve', 'update', 'partial_update']:
            # Optimize for detail view
            queryset = queryset.prefetch_related('attachments')
        
        return queryset.select_related('owner')
    
    def perform_create(self, serializer):
        """Set owner when creating expense."""
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_receipts(self, request, pk=None):
        """
        Upload receipt images for an expense.
        
        POST /api/expenses/{id}/upload_receipts/
        Content-Type: multipart/form-data
        
        Form fields:
        - files: List of image files (max 5 files, 10MB each)
        """
        expense = self.get_object()
        
        # Prepare data for serializer
        data = {
            'expense_id': expense.id,
            'files': request.FILES.getlist('files')
        }
        
        serializer = ReceiptUploadSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            result = serializer.save()
            
            # Return updated expense data
            expense.refresh_from_db()
            expense_serializer = ExpenseSerializer(expense, context={'request': request})
            
            return Response({
                'message': f"Successfully uploaded {result['uploaded_count']} receipt(s)",
                'upload_summary': {
                    'uploaded_count': result['uploaded_count'],
                    'total_attachments': expense.attachments.count()
                },
                'expense': expense_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def delete_receipt(self, request, pk=None):
        """
        Delete a specific receipt attachment.
        
        DELETE /api/expenses/{id}/delete_receipt/?attachment_id={uuid}
        """
        expense = self.get_object()
        attachment_id = request.query_params.get('attachment_id')
        
        if not attachment_id:
            return Response(
                {'error': 'attachment_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attachment = ExpenseAttachment.objects.get(
                id=attachment_id,
                expense=expense
            )
            
            # Delete the file from storage
            service = ReceiptImageService()
            service.delete_receipt_image(attachment)
            
            # Delete the attachment record
            attachment.delete()
            
            # Update expense primary receipt if necessary
            if expense.receipt_image == attachment.file_path:
                # Set to first remaining attachment or None
                remaining_attachment = expense.attachments.first()
                expense.receipt_image = remaining_attachment.file_path if remaining_attachment else None
                expense.save()
            
            return Response({
                'message': 'Receipt deleted successfully',
                'remaining_attachments': expense.attachments.count()
            }, status=status.HTTP_200_OK)
            
        except ExpenseAttachment.DoesNotExist:
            return Response(
                {'error': 'Receipt attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get expense summary and analytics.
        
        GET /api/expenses/summary/
        
        Query parameters:
        - start_date: Start date for period (YYYY-MM-DD)
        - end_date: End date for period (YYYY-MM-DD)
        - period: Predefined period (month, quarter, year)
        """
        # Parse date parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        period = request.query_params.get('period')
        
        # Handle predefined periods
        today = date.today()
        if period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start_date = date(today.year, (quarter - 1) * 3 + 1, 1)
            end_date = today
        elif period == 'year':
            start_date = date(today.year, 1, 1)
            end_date = today
        elif period == 'last_month':
            start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end_date = today.replace(day=1) - timedelta(days=1)
        
        # Parse string dates
        if isinstance(start_date, str):
            try:
                start_date = date.fromisoformat(start_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if isinstance(end_date, str):
            try:
                end_date = date.fromisoformat(end_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get summary data
        service = ExpenseAnalyticsService()
        summary_data = service.get_expense_summary(request.user, start_date, end_date)
        
        serializer = ExpenseSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get expense categories with counts and totals.
        
        GET /api/expenses/categories/
        """
        # Get category breakdown for user
        breakdown = Expense.get_category_breakdown(request.user)
        
        # Add category choices information
        category_info = []
        category_totals = {item['category']: item for item in breakdown}
        
        for category_code, category_name in ExpenseCategory.choices:
            info = category_totals.get(category_code, {
                'category': category_code,
                'category_display': category_name,
                'total': Decimal('0.00'),
                'count': 0
            })
            category_info.append(info)
        
        return Response({
            'categories': category_info,
            'total_categories': len(ExpenseCategory.choices),
            'categories_with_expenses': len(breakdown)
        })
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent expenses (last 30 days).
        
        GET /api/expenses/recent/
        """
        cutoff_date = date.today() - timedelta(days=30)
        recent_expenses = self.get_queryset().filter(date__gte=cutoff_date)
        
        serializer = ExpenseListSerializer(recent_expenses, many=True, context={'request': request})
        
        return Response({
            'count': recent_expenses.count(),
            'cutoff_date': cutoff_date,
            'expenses': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get quick expense statistics.
        
        GET /api/expenses/stats/
        """
        queryset = self.get_queryset()
        
        # Basic stats
        total_expenses = queryset.count()
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Period stats
        today = date.today()
        this_month = queryset.filter(date__gte=today.replace(day=1))
        this_month_count = this_month.count()
        this_month_total = this_month.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Category stats
        top_category = queryset.values('category').annotate(
            total=Sum('amount')
        ).order_by('-total').first()
        
        return Response({
            'total_expenses': total_expenses,
            'total_amount': total_amount,
            'average_expense': total_amount / total_expenses if total_expenses > 0 else Decimal('0.00'),
            'this_month': {
                'count': this_month_count,
                'total': this_month_total
            },
            'top_category': top_category,
            'reimbursable_count': queryset.filter(is_reimbursable=True).count(),
            'with_receipts_count': queryset.filter(attachments__isnull=False).distinct().count()
        })


class ExpenseAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for expense attachment management.
    Provides read-only access to attachment metadata and download URLs.
    """
    
    queryset = ExpenseAttachment.objects.all()
    serializer_class = ExpenseAttachmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter attachments by expense owner."""
        return super().get_queryset().filter(expense__owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Get download URL for attachment.
        
        GET /api/attachments/{id}/download/
        """
        attachment = self.get_object()
        service = ReceiptImageService()
        
        image_url = service.get_image_url(attachment)
        thumbnail_url = service.get_image_url(attachment, thumbnail=True)
        
        if not image_url:
            return Response(
                {'error': 'File not found or inaccessible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'download_url': image_url,
            'thumbnail_url': thumbnail_url,
            'file_name': attachment.file_name,
            'file_size': attachment.file_size,
            'content_type': attachment.content_type
        })