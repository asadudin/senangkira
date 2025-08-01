"""
Enhanced Django admin configuration for Expense models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Expense, ExpenseAttachment, ExpenseCategory


class ExpenseAttachmentInline(admin.TabularInline):
    """Inline admin for expense attachments."""
    model = ExpenseAttachment
    extra = 0
    readonly_fields = ('file_size_mb', 'uploaded_at')
    fields = ('file_name', 'file_path', 'content_type', 'file_size_mb', 'uploaded_at')
    
    def file_size_mb(self, obj):
        """Display file size in MB."""
        if obj.file_size:
            return f"{obj.file_size_mb} MB"
        return "-"
    file_size_mb.short_description = "Size (MB)"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Expense model."""
    
    list_display = [
        'description', 'amount_display', 'date', 'category_display', 
        'owner', 'is_recent', 'is_reimbursable', 'attachment_count'
    ]
    
    list_filter = [
        'category', 'is_reimbursable', 'is_recurring', 'date',
        'created_at', 'owner'
    ]
    
    search_fields = [
        'description', 'notes', 'owner__email', 'owner__company_name'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'age_in_days', 'is_recent'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'description', 'amount', 'date', 'category')
        }),
        ('Details', {
            'fields': ('notes', 'receipt_image')
        }),
        ('Properties', {
            'fields': ('is_reimbursable', 'is_recurring')
        }),
        ('Ownership & Timestamps', {
            'fields': ('owner', 'created_at', 'updated_at', 'age_in_days', 'is_recent'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ExpenseAttachmentInline]
    
    ordering = ['-date', '-created_at']
    date_hierarchy = 'date'
    
    def amount_display(self, obj):
        """Display amount with currency symbol."""
        return f"${obj.amount:,.2f}"
    amount_display.short_description = "Amount"
    amount_display.admin_order_field = 'amount'
    
    def category_display(self, obj):
        """Display category with color coding."""
        colors = {
            'travel': '#e74c3c',
            'meals': '#f39c12', 
            'office_supplies': '#3498db',
            'software': '#9b59b6',
            'utilities': '#1abc9c',
            'rent': '#34495e',
            'marketing': '#e67e22',
            'equipment': '#95a5a6',
            'professional': '#2ecc71',
            'insurance': '#f1c40f',
            'taxes': '#c0392b',
            'other': '#7f8c8d'
        }
        
        color = colors.get(obj.category, '#7f8c8d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_display.short_description = "Category"
    category_display.admin_order_field = 'category'
    
    def attachment_count(self, obj):
        """Display number of attachments."""
        count = obj.attachments.count()
        if count > 0:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold;">{} files</span>',
                count
            )
        return "No files"
    attachment_count.short_description = "Attachments"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('owner').prefetch_related('attachments')


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    """Admin interface for ExpenseAttachment model."""
    
    list_display = [
        'file_name', 'expense_link', 'content_type', 'file_size_mb_display', 'uploaded_at'
    ]
    
    list_filter = ['content_type', 'uploaded_at']
    
    search_fields = [
        'file_name', 'expense__description', 'expense__owner__email'
    ]
    
    readonly_fields = [
        'id', 'file_size_mb_display', 'uploaded_at'
    ]
    
    fieldsets = (
        ('File Information', {
            'fields': ('id', 'file_name', 'file_path', 'content_type')
        }),
        ('File Properties', {
            'fields': ('file_size', 'file_size_mb_display', 'uploaded_at')
        }),
        ('Association', {
            'fields': ('expense',)
        })
    )
    
    def expense_link(self, obj):
        """Create a link to the related expense."""
        url = reverse('admin:expenses_expense_change', args=[obj.expense.id])
        return format_html('<a href="{}">{}</a>', url, obj.expense.description)
    expense_link.short_description = "Expense"
    expense_link.admin_order_field = 'expense__description'
    
    def file_size_mb_display(self, obj):
        """Display file size in MB."""
        return f"{obj.file_size_mb} MB"
    file_size_mb_display.short_description = "Size (MB)"
    file_size_mb_display.admin_order_field = 'file_size'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('expense', 'expense__owner')


# Custom admin actions
@admin.action(description='Mark selected expenses as reimbursable')
def mark_reimbursable(modeladmin, request, queryset):
    """Mark selected expenses as reimbursable."""
    updated = queryset.update(is_reimbursable=True)
    modeladmin.message_user(
        request,
        f"{updated} expenses marked as reimbursable."
    )

@admin.action(description='Mark selected expenses as non-reimbursable')
def mark_non_reimbursable(modeladmin, request, queryset):
    """Mark selected expenses as non-reimbursable."""
    updated = queryset.update(is_reimbursable=False)
    modeladmin.message_user(
        request,
        f"{updated} expenses marked as non-reimbursable."
    )

# Add custom actions to ExpenseAdmin
ExpenseAdmin.actions = [mark_reimbursable, mark_non_reimbursable]