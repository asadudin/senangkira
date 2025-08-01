"""
Django management command for sending email reminders.
Can be run manually or scheduled via cron/system scheduler.
"""
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from reminders.services.reminder_service import ReminderService
from reminders.services.email_service import EmailService


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send email reminders for quotes and invoices'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to process reminders for (YYYY-MM-DD format, defaults to today)'
        )
        
        parser.add_argument(
            '--user-email',
            type=str,
            help='Process reminders for specific user email only'
        )
        
        parser.add_argument(
            '--reminder-type',
            type=str,
            choices=['quote_expiration', 'invoice_due', 'invoice_overdue'],
            help='Process only specific reminder type'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails'
        )
        
        parser.add_argument(
            '--test-email',
            action='store_true',
            help='Test email configuration before processing reminders'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        # Set up logging level
        if options['verbose']:
            logging.getLogger('reminders').setLevel(logging.DEBUG)
        
        # Test email configuration if requested
        if options['test_email']:
            self.test_email_configuration()
            return
        
        # Parse target date
        target_date = self.parse_target_date(options['date'])
        
        # Process reminders
        try:
            if options['dry_run']:
                self.dry_run_reminders(target_date, options)
            else:
                self.send_reminders(target_date, options)
                
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise CommandError(f"Failed to process reminders: {e}")
    
    def parse_target_date(self, date_str):
        """Parse target date from string or use today."""
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                target_date = timezone.make_aware(target_date)
                self.stdout.write(f"Processing reminders for: {target_date.date()}")
                return target_date
            except ValueError:
                raise CommandError("Invalid date format. Use YYYY-MM-DD.")
        else:
            target_date = timezone.now()
            self.stdout.write(f"Processing reminders for today: {target_date.date()}")
            return target_date
    
    def test_email_configuration(self):
        """Test email configuration."""
        self.stdout.write("Testing email configuration...")
        
        email_service = EmailService()
        success = email_service.test_email_configuration()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS("✓ Email configuration test successful")
            )
        else:
            self.stdout.write(
                self.style.ERROR("✗ Email configuration test failed")
            )
            raise CommandError("Email configuration test failed")
    
    def dry_run_reminders(self, target_date, options):
        """Show what reminders would be sent without sending."""
        self.stdout.write(
            self.style.WARNING(f"DRY RUN - No emails will be sent")
        )
        
        reminder_service = ReminderService()
        
        if options['user_email']:
            # Process single user
            user = self.get_user_by_email(options['user_email'])
            reminders = reminder_service.get_all_reminders_for_user(user, target_date)
            self.display_reminders_preview([user], reminders)
        else:
            # Process all users
            users = reminder_service.get_users_with_reminders_enabled()
            all_reminders = reminder_service.get_all_reminders_for_date(target_date)
            self.display_reminders_preview(users, all_reminders)
        
        self.stdout.write(
            self.style.WARNING("DRY RUN COMPLETE - No emails were sent")
        )
    
    def send_reminders(self, target_date, options):
        """Send reminders."""
        self.stdout.write("Starting reminder processing...")
        
        reminder_service = ReminderService()
        
        if options['user_email']:
            # Process single user
            user = self.get_user_by_email(options['user_email'])
            reminders = reminder_service.get_all_reminders_for_user(user, target_date)
            
            # Filter by reminder type if specified
            if options['reminder_type']:
                reminders = [r for r in reminders if r['reminder_type'] == options['reminder_type']]
            
            email_service = EmailService()
            stats = email_service.send_bulk_reminders(reminders)
            
            self.stdout.write(f"Processed {len(reminders)} reminders for {user.email}")
            
        else:
            # Process all users
            stats = reminder_service.process_daily_reminders(target_date)
        
        # Display results
        self.display_results(stats)
    
    def get_user_by_email(self, email):
        """Get user by email address."""
        from authentication.models import User
        
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"User with email '{email}' not found")
    
    def display_reminders_preview(self, users, reminders):
        """Display preview of reminders to be sent."""
        self.stdout.write(f"\nFound {len(users)} users with reminders enabled")
        self.stdout.write(f"Found {len(reminders)} reminders to process\n")
        
        if not reminders:
            self.stdout.write("No reminders to send.")
            return
        
        # Group reminders by type
        by_type = {}
        for reminder in reminders:
            reminder_type = reminder['reminder_type']
            if reminder_type not in by_type:
                by_type[reminder_type] = []
            by_type[reminder_type].append(reminder)
        
        # Display by type
        for reminder_type, type_reminders in by_type.items():
            self.stdout.write(f"\n{reminder_type.upper()} ({len(type_reminders)} reminders):")
            
            for reminder in type_reminders[:5]:  # Show first 5
                user = reminder['user']
                content = reminder['content_object']
                
                if hasattr(content, 'quote_number'):
                    content_desc = f"Quote #{content.quote_number}"
                elif hasattr(content, 'invoice_number'):
                    content_desc = f"Invoice #{content.invoice_number}"
                else:
                    content_desc = "Unknown"
                
                client_name = content.client.name if hasattr(content, 'client') else 'Unknown'
                
                self.stdout.write(
                    f"  → {user.email}: {content_desc} for {client_name}"
                )
            
            if len(type_reminders) > 5:
                self.stdout.write(f"  ... and {len(type_reminders) - 5} more")
    
    def display_results(self, stats):
        """Display processing results."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("REMINDER PROCESSING COMPLETE")
        self.stdout.write("="*50)
        
        total = stats.get('sent', 0) + stats.get('failed', 0) + stats.get('skipped', 0)
        
        self.stdout.write(f"Total processed: {total}")
        
        if stats.get('sent', 0) > 0:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully sent: {stats['sent']}")
            )
        
        if stats.get('failed', 0) > 0:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to send: {stats['failed']}")
            )
        
        if stats.get('skipped', 0) > 0:
            self.stdout.write(
                self.style.WARNING(f"⊘ Skipped (already sent): {stats['skipped']}")
            )
        
        success_rate = (stats.get('sent', 0) / total * 100) if total > 0 else 0
        self.stdout.write(f"Success rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            self.stdout.write(self.style.SUCCESS("All reminders processed successfully!"))
        elif success_rate >= 80:
            self.stdout.write(self.style.WARNING("Most reminders processed successfully."))
        else:
            self.stdout.write(self.style.ERROR("Many reminders failed. Check logs for details."))