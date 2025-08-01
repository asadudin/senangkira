"""
Service layer for expense-related operations, including receipt image handling.
"""

import os
import uuid
import hashlib
from typing import Optional, Dict, List, Any
from decimal import Decimal
from datetime import datetime
from PIL import Image, ImageOps
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Expense, ExpenseAttachment


class ReceiptImageService:
    """
    Service for handling receipt image operations including upload, processing, and management.
    
    Features:
    - Image validation and processing
    - Automatic image optimization (resize, compression)
    - OCR text extraction (future enhancement)
    - Multiple format support (JPEG, PNG, WebP)
    - File size optimization
    - Secure file handling
    """
    
    # Supported image formats
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'WebP']
    SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
    
    # Image constraints
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DIMENSIONS = (2048, 2048)  # Max width/height
    THUMBNAIL_SIZE = (400, 400)
    COMPRESSION_QUALITY = 85
    
    # File storage paths
    RECEIPT_UPLOAD_PATH = 'receipts'
    THUMBNAIL_PATH = 'receipts/thumbnails'
    
    def __init__(self):
        """Initialize the receipt image service."""
        self.storage = default_storage
        
    def validate_image_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate uploaded image file for security and format compliance.
        
        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            
        Returns:
            Dict with validation results and metadata
            
        Raises:
            ValidationError: If file is invalid or not supported
        """
        if not file_content:
            raise ValidationError("Empty file provided")
            
        # Check file size
        if len(file_content) > self.MAX_FILE_SIZE:
            size_mb = len(file_content) / (1024 * 1024)
            raise ValidationError(f"File too large: {size_mb:.1f}MB (max: 10MB)")
            
        # Check file extension
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValidationError(f"Unsupported file format: {file_ext}")
            
        try:
            # Validate with PIL - this also checks for malicious files
            with Image.open(ContentFile(file_content)) as img:
                # Verify it's actually an image
                img.verify()
                
                # Reopen for metadata (verify() closes the image)
                img = Image.open(ContentFile(file_content))
                
                format_name = img.format
                if format_name not in self.SUPPORTED_FORMATS:
                    raise ValidationError(f"Unsupported image format: {format_name}")
                    
                width, height = img.size
                
                # Check dimensions
                if width > self.MAX_DIMENSIONS[0] or height > self.MAX_DIMENSIONS[1]:
                    raise ValidationError(
                        f"Image too large: {width}x{height} "
                        f"(max: {self.MAX_DIMENSIONS[0]}x{self.MAX_DIMENSIONS[1]})"
                    )
                    
                return {
                    'valid': True,
                    'format': format_name,
                    'width': width,
                    'height': height,
                    'size_bytes': len(file_content),
                    'size_mb': len(file_content) / (1024 * 1024)
                }
                
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")
    
    def process_receipt_image(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process and optimize receipt image for storage.
        
        Args:
            file_content: Raw image content
            filename: Original filename
            
        Returns:
            Dict with processed image data and metadata
        """
        # Validate first
        validation_result = self.validate_image_file(file_content, filename)
        
        try:
            with Image.open(ContentFile(file_content)) as original_img:
                # Convert to RGB if necessary (handles RGBA, P mode images)
                if original_img.mode in ('RGBA', 'P'):
                    # Create white background for transparent images
                    rgb_img = Image.new('RGB', original_img.size, (255, 255, 255))
                    if original_img.mode == 'P':
                        original_img = original_img.convert('RGBA')
                    rgb_img.paste(original_img, mask=original_img.split()[-1] if original_img.mode == 'RGBA' else None)
                    processed_img = rgb_img
                else:
                    processed_img = original_img.copy()
                
                # Auto-rotate based on EXIF orientation
                processed_img = ImageOps.exif_transpose(processed_img)
                
                # Resize if too large
                if (processed_img.width > self.MAX_DIMENSIONS[0] or 
                    processed_img.height > self.MAX_DIMENSIONS[1]):
                    processed_img.thumbnail(self.MAX_DIMENSIONS, Image.Resampling.LANCZOS)
                
                # Create thumbnail
                thumbnail_img = processed_img.copy()
                thumbnail_img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                
                # Save processed image
                from io import BytesIO
                processed_buffer = BytesIO()
                processed_img.save(
                    processed_buffer, 
                    format='JPEG', 
                    quality=self.COMPRESSION_QUALITY,
                    optimize=True
                )
                processed_content = processed_buffer.getvalue()
                
                # Save thumbnail
                thumbnail_buffer = BytesIO()
                thumbnail_img.save(
                    thumbnail_buffer,
                    format='JPEG',
                    quality=self.COMPRESSION_QUALITY,
                    optimize=True
                )
                thumbnail_content = thumbnail_buffer.getvalue()
                
                return {
                    'processed_content': processed_content,
                    'thumbnail_content': thumbnail_content,
                    'processed_size': len(processed_content),
                    'thumbnail_size': len(thumbnail_content),
                    'final_dimensions': processed_img.size,
                    'thumbnail_dimensions': thumbnail_img.size,
                    'compression_ratio': len(processed_content) / len(file_content),
                    'format': 'JPEG'
                }
                
        except Exception as e:
            raise ValidationError(f"Image processing failed: {str(e)}")
    
    def generate_secure_filename(self, original_filename: str, expense_id: str) -> str:
        """
        Generate a secure, unique filename for receipt storage.
        
        Args:
            original_filename: Original file name
            expense_id: UUID of the expense
            
        Returns:
            Secure filename with timestamp and hash
        """
        # Extract extension
        _, ext = os.path.splitext(original_filename.lower())
        if not ext:
            ext = '.jpg'  # Default extension
            
        # Create hash from expense_id and timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_string = f"{expense_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        filename_hash = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        
        return f"receipt_{expense_id}_{timestamp}_{filename_hash}{ext}"
    
    def save_receipt_image(self, expense: Expense, file_content: bytes, 
                          original_filename: str) -> ExpenseAttachment:
        """
        Save receipt image with processing and create attachment record.
        
        Args:
            expense: Expense instance to attach image to
            file_content: Raw image file content
            original_filename: Original filename
            
        Returns:
            ExpenseAttachment instance
            
        Raises:
            ValidationError: If processing or saving fails
        """
        try:
            # Process the image
            processed_data = self.process_receipt_image(file_content, original_filename)
            
            # Generate secure filename
            secure_filename = self.generate_secure_filename(original_filename, str(expense.id))
            thumbnail_filename = f"thumb_{secure_filename}"
            
            # Storage paths
            main_path = f"{self.RECEIPT_UPLOAD_PATH}/{secure_filename}"
            thumb_path = f"{self.THUMBNAIL_PATH}/{thumbnail_filename}"
            
            # Save main image
            main_file_path = self.storage.save(
                main_path,
                ContentFile(processed_data['processed_content'])
            )
            
            # Save thumbnail
            thumb_file_path = self.storage.save(
                thumb_path,
                ContentFile(processed_data['thumbnail_content'])
            )
            
            # Create attachment record
            attachment = ExpenseAttachment.objects.create(
                expense=expense,
                file_path=main_file_path,
                file_name=original_filename,
                file_size=processed_data['processed_size'],
                content_type='image/jpeg'
            )
            
            # Update expense with primary receipt if this is the first one
            if not expense.receipt_image:
                expense.receipt_image = main_file_path
                expense.save()
            
            return attachment
            
        except Exception as e:
            # Clean up any partially saved files
            try:
                if 'main_file_path' in locals():
                    self.storage.delete(main_file_path)
                if 'thumb_file_path' in locals():
                    self.storage.delete(thumb_file_path)
            except:
                pass
            
            raise ValidationError(f"Failed to save receipt image: {str(e)}")
    
    def delete_receipt_image(self, attachment: ExpenseAttachment) -> bool:
        """
        Delete receipt image and its thumbnail from storage.
        
        Args:
            attachment: ExpenseAttachment to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete main file
            if attachment.file_path and self.storage.exists(attachment.file_path):
                self.storage.delete(attachment.file_path)
            
            # Delete thumbnail (generate expected path)
            filename = os.path.basename(attachment.file_path)
            thumb_filename = f"thumb_{filename}"
            thumb_path = f"{self.THUMBNAIL_PATH}/{thumb_filename}"
            
            if self.storage.exists(thumb_path):
                self.storage.delete(thumb_path)
            
            return True
            
        except Exception as e:
            # Log error but don't raise - attachment deletion should still proceed
            print(f"Warning: Failed to delete receipt files: {str(e)}")
            return False
    
    def get_image_url(self, attachment: ExpenseAttachment, thumbnail: bool = False) -> Optional[str]:
        """
        Get URL for accessing stored receipt image.
        
        Args:
            attachment: ExpenseAttachment instance
            thumbnail: Whether to return thumbnail URL
            
        Returns:
            URL string or None if file doesn't exist
        """
        try:
            if thumbnail:
                # Generate thumbnail path
                filename = os.path.basename(attachment.file_path)
                thumb_filename = f"thumb_{filename}"
                thumb_path = f"{self.THUMBNAIL_PATH}/{thumb_filename}"
                
                if self.storage.exists(thumb_path):
                    return self.storage.url(thumb_path)
            else:
                if attachment.file_path and self.storage.exists(attachment.file_path):
                    return self.storage.url(attachment.file_path)
            
            return None
            
        except Exception:
            return None
    
    def batch_process_receipts(self, expense: Expense, file_list: List[Dict[str, Any]]) -> List[ExpenseAttachment]:
        """
        Process multiple receipt images for a single expense.
        
        Args:
            expense: Expense instance
            file_list: List of dicts with 'content' and 'filename' keys
            
        Returns:
            List of created ExpenseAttachment instances
            
        Raises:
            ValidationError: If any file processing fails
        """
        attachments = []
        created_attachments = []
        
        try:
            for file_data in file_list:
                attachment = self.save_receipt_image(
                    expense,
                    file_data['content'],
                    file_data['filename']
                )
                attachments.append(attachment)
                created_attachments.append(attachment.id)
            
            return attachments
            
        except Exception as e:
            # Clean up any successfully created attachments
            for attachment_id in created_attachments:
                try:
                    attachment = ExpenseAttachment.objects.get(id=attachment_id)
                    self.delete_receipt_image(attachment)
                    attachment.delete()
                except:
                    pass
            
            raise ValidationError(f"Batch receipt processing failed: {str(e)}")


class ExpenseAnalyticsService:
    """
    Service for expense analytics and reporting functionality.
    """
    
    @staticmethod
    def get_expense_summary(user, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Get comprehensive expense summary for a user within date range.
        
        Args:
            user: User instance
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dict with summary statistics
        """
        expenses = Expense.objects.filter(owner=user)
        
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)
        
        total_amount = expenses.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        expense_count = expenses.count()
        
        # Category breakdown
        category_breakdown = Expense.get_category_breakdown(user)
        if start_date or end_date:
            # Filter breakdown for date range
            filtered_expenses = expenses
            category_breakdown = []
            for category in ExpenseCategory.choices:
                cat_total = filtered_expenses.filter(category=category[0]).aggregate(
                    total=models.Sum('amount')
                )['total'] or Decimal('0.00')
                
                if cat_total > 0:
                    category_breakdown.append({
                        'category': category[0],
                        'category_display': category[1],
                        'total': cat_total,
                        'count': filtered_expenses.filter(category=category[0]).count()
                    })
        
        # Monthly trend (last 12 months)
        monthly_data = []
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        current_date = date.today()
        for i in range(12):
            month_date = current_date - relativedelta(months=i)
            month_total = Expense.get_monthly_total(user, month_date.year, month_date.month)
            monthly_data.append({
                'year': month_date.year,
                'month': month_date.month,
                'month_name': month_date.strftime('%B %Y'),
                'total': month_total
            })
        
        return {
            'total_amount': total_amount,
            'expense_count': expense_count,
            'average_expense': total_amount / expense_count if expense_count > 0 else Decimal('0.00'),
            'category_breakdown': category_breakdown,
            'monthly_trend': list(reversed(monthly_data)),  # Most recent first
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }