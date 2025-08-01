"""
Database utilities for test data management.
Provides functions for database setup, cleanup, and test isolation.
"""
import os
from django.core.management import call_command
from django.db import connection, transaction
from django.test.utils import setup_test_environment, teardown_test_environment
from django.conf import settings


class TestDatabaseManager:
    """Manages test database setup and cleanup."""
    
    def __init__(self):
        self.test_db_name = None
    
    def setup_test_database(self):
        """Set up test database."""
        setup_test_environment()
        
        # Create test database
        from django.test.utils import setup_databases
        self.test_db_config = setup_databases(
            verbosity=1,
            interactive=False,
            keepdb=False
        )
        
        return self.test_db_config
    
    def teardown_test_database(self):
        """Tear down test database."""
        if hasattr(self, 'test_db_config'):
            from django.test.utils import teardown_databases
            teardown_databases(self.test_db_config, verbosity=1)
        
        teardown_test_environment()
    
    def reset_sequences(self):
        """Reset database sequences after bulk operations."""
        with connection.cursor() as cursor:
            # Get all tables
            tables = connection.introspection.table_names()
            
            # Reset sequences for PostgreSQL
            if connection.vendor == 'postgresql':
                for table in tables:
                    cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)")
            
            # Reset sequences for SQLite
            elif connection.vendor == 'sqlite':
                cursor.execute("DELETE FROM sqlite_sequence")
    
    def get_database_stats(self):
        """Get current database statistics."""
        from django.contrib.auth import get_user_model
        from clients.models import Client
        from invoicing.models import Quote, Invoice
        from expenses.models import Expense
        
        User = get_user_model()
        
        stats = {
            'users': User.objects.count(),
            'clients': Client.objects.count(),
            'quotes': Quote.objects.count(),
            'invoices': Invoice.objects.count(),
            'expenses': Expense.objects.count(),
            'total_objects': 0
        }
        
        stats['total_objects'] = sum(stats.values()) - stats['total_objects']
        
        return stats


class TestDataIsolation:
    """Provides test data isolation utilities."""
    
    @staticmethod
    def create_isolated_user():
        """Create an isolated test user that won't conflict with other tests."""
        from django.contrib.auth import get_user_model
        import uuid
        
        User = get_user_model()
        unique_id = str(uuid.uuid4())[:8]
        
        return User.objects.create_user(
            email=f'test_{unique_id}@senangkira.com',
            username=f'test_{unique_id}',
            password='TestPass123!'
        )
    
    @staticmethod
    def cleanup_user_data(user):
        """Clean up all data associated with a specific user."""
        from clients.models import Client
        from invoicing.models import Quote, Invoice
        from expenses.models import Expense
        
        # Delete in order of dependencies
        Invoice.objects.filter(owner=user).delete()
        Quote.objects.filter(owner=user).delete()
        Expense.objects.filter(owner=user).delete()
        Client.objects.filter(owner=user).delete()
        user.delete()
    
    @staticmethod
    def get_user_data_counts(user):
        """Get counts of data objects for a specific user."""
        from clients.models import Client
        from invoicing.models import Quote, Invoice
        from expenses.models import Expense
        
        return {
            'clients': Client.objects.filter(owner=user).count(),
            'quotes': Quote.objects.filter(owner=user).count(),
            'invoices': Invoice.objects.filter(owner=user).count(),
            'expenses': Expense.objects.filter(owner=user).count()
        }


class DatabasePerformanceProfiler:
    """Profiles database performance during tests."""
    
    def __init__(self):
        self.query_count = 0
        self.queries = []
        self.start_queries = None
    
    def __enter__(self):
        """Start profiling."""
        from django.db import connection
        self.start_queries = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop profiling and calculate stats."""
        from django.db import connection
        self.query_count = len(connection.queries) - self.start_queries
        self.queries = connection.queries[self.start_queries:]
    
    def get_stats(self):
        """Get performance statistics."""
        total_time = sum(float(query['time']) for query in self.queries)
        
        return {
            'query_count': self.query_count,
            'total_time': total_time,
            'average_time': total_time / self.query_count if self.query_count > 0 else 0,
            'queries': self.queries
        }
    
    def print_stats(self):
        """Print performance statistics."""
        stats = self.get_stats()
        print(f"Database Queries: {stats['query_count']}")
        print(f"Total Time: {stats['total_time']:.4f}s")
        print(f"Average Time: {stats['average_time']:.4f}s")
        
        if stats['query_count'] > 0:
            print("\nSlowest queries:")
            sorted_queries = sorted(stats['queries'], key=lambda q: float(q['time']), reverse=True)
            for query in sorted_queries[:5]:
                print(f"  {query['time']}s: {query['sql'][:100]}...")


def backup_test_data(backup_file='test_data_backup.json'):
    """Backup current test data to JSON file."""
    call_command('dumpdata', 
                '--natural-foreign', 
                '--natural-primary',
                '--exclude=contenttypes',
                '--exclude=auth.permission',
                '--exclude=sessions',
                '--output=backups/' + backup_file)


def restore_test_data(backup_file='test_data_backup.json'):
    """Restore test data from JSON file."""
    if os.path.exists('backups/' + backup_file):
        call_command('loaddata', 'backups/' + backup_file)
    else:
        raise FileNotFoundError(f"Backup file not found: backups/{backup_file}")


def create_test_media_files():
    """Create test media files for file upload testing."""
    import tempfile
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # Create test PDF file
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    pdf_file = SimpleUploadedFile(
        "test_receipt.pdf",
        pdf_content,
        content_type="application/pdf"
    )
    
    # Create test image file
    from PIL import Image
    import io
    
    image = Image.new('RGB', (100, 100), color='red')
    image_io = io.BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)
    
    image_file = SimpleUploadedFile(
        "test_image.png",
        image_io.getvalue(),
        content_type="image/png"
    )
    
    return {
        'pdf': pdf_file,
        'image': image_file
    }


def verify_database_integrity():
    """Verify database integrity after test operations."""
    from django.core.management import call_command
    from io import StringIO
    
    out = StringIO()
    try:
        call_command('check', '--database=default', stdout=out)
        return True, out.getvalue()
    except Exception as e:
        return False, str(e)


def get_memory_usage():
    """Get current memory usage statistics."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024,  # MB
        'percent': process.memory_percent()
    }


class TestResourceMonitor:
    """Monitor system resources during tests."""
    
    def __init__(self):
        self.start_memory = None
        self.start_time = None
    
    def start(self):
        """Start monitoring."""
        import time
        self.start_memory = get_memory_usage()
        self.start_time = time.time()
    
    def stop(self):
        """Stop monitoring and return stats."""
        import time
        end_memory = get_memory_usage()
        end_time = time.time()
        
        return {
            'duration': end_time - self.start_time,
            'memory_start': self.start_memory,
            'memory_end': end_memory,
            'memory_delta': {
                'rss': end_memory['rss'] - self.start_memory['rss'],
                'vms': end_memory['vms'] - self.start_memory['vms'],
                'percent': end_memory['percent'] - self.start_memory['percent']
            }
        }