"""
Django migration for dashboard performance optimizations.

This migration adds database indexes and constraints for optimal query performance.
"""

from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):
    atomic = False  # Required for CREATE INDEX CONCURRENTLY

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        # Add indexes to existing dashboard snapshot table
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS dashboard_snapshot_owner_date_idx "
            "ON dashboard_dashboardsnapshot(owner_id, snapshot_date);",
            reverse_sql="DROP INDEX IF EXISTS dashboard_snapshot_owner_date_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS dashboard_snapshot_period_type_idx "
            "ON dashboard_dashboardsnapshot(owner_id, period_type);",
            reverse_sql="DROP INDEX IF EXISTS dashboard_snapshot_period_type_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS dashboard_snapshot_updated_at_idx "
            "ON dashboard_dashboardsnapshot(updated_at DESC);",
            reverse_sql="DROP INDEX IF EXISTS dashboard_snapshot_updated_at_idx;"
        ),
        
        # Add indexes to category analytics table
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS category_analytics_owner_type_idx "
            "ON dashboard_categoryanalytics(owner_id, category_type);",
            reverse_sql="DROP INDEX IF EXISTS category_analytics_owner_type_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS category_analytics_owner_date_idx "
            "ON dashboard_categoryanalytics(owner_id, snapshot_date);",
            reverse_sql="DROP INDEX IF EXISTS category_analytics_owner_date_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS category_analytics_amount_idx "
            "ON dashboard_categoryanalytics(total_amount DESC);",
            reverse_sql="DROP INDEX IF EXISTS category_analytics_amount_idx;"
        ),
        
        # Add indexes to client analytics table
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS client_analytics_owner_revenue_idx "
            "ON dashboard_clientanalytics(owner_id, total_revenue DESC);",
            reverse_sql="DROP INDEX IF EXISTS client_analytics_owner_revenue_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS client_analytics_active_idx "
            "ON dashboard_clientanalytics(owner_id, is_active) WHERE is_active = true;",
            reverse_sql="DROP INDEX IF EXISTS client_analytics_active_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS client_analytics_last_invoice_idx "
            "ON dashboard_clientanalytics(owner_id, last_invoice_date DESC) "
            "WHERE last_invoice_date IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS client_analytics_last_invoice_idx;"
        ),
        
        # Add indexes to performance metrics table
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS performance_metric_owner_name_idx "
            "ON dashboard_performancemetric(owner_id, metric_name);",
            reverse_sql="DROP INDEX IF EXISTS performance_metric_owner_name_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS performance_metric_category_date_idx "
            "ON dashboard_performancemetric(metric_category, calculation_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS performance_metric_category_date_idx;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS performance_metric_time_series_idx "
            "ON dashboard_performancemetric(owner_id, metric_name, calculation_date DESC);",
            reverse_sql="DROP INDEX IF EXISTS performance_metric_time_series_idx;"
        ),
        
        # Optimize existing indexes on foreign keys and frequently queried fields
        migrations.RunSQL(
            "ANALYZE dashboard_dashboardsnapshot;",
            reverse_sql=""
        ),
        
        migrations.RunSQL(
            "ANALYZE dashboard_categoryanalytics;",
            reverse_sql=""
        ),
        
        migrations.RunSQL(
            "ANALYZE dashboard_clientanalytics;",
            reverse_sql=""
        ),
        
        migrations.RunSQL(
            "ANALYZE dashboard_performancemetric;",
            reverse_sql=""
        ),
        
        # Add database constraints for data integrity
        migrations.RunSQL(
            "ALTER TABLE dashboard_dashboardsnapshot "
            "ADD CONSTRAINT check_positive_revenue CHECK (total_revenue >= 0);",
            reverse_sql="ALTER TABLE dashboard_dashboardsnapshot DROP CONSTRAINT IF EXISTS check_positive_revenue;"
        ),
        
        migrations.RunSQL(
            "ALTER TABLE dashboard_dashboardsnapshot "
            "ADD CONSTRAINT check_positive_expenses CHECK (total_expenses >= 0);",
            reverse_sql="ALTER TABLE dashboard_dashboardsnapshot DROP CONSTRAINT IF EXISTS check_positive_expenses;"
        ),
        
        migrations.RunSQL(
            "ALTER TABLE dashboard_categoryanalytics "
            "ADD CONSTRAINT check_valid_percentage CHECK (percentage_of_total >= 0 AND percentage_of_total <= 100);",
            reverse_sql="ALTER TABLE dashboard_categoryanalytics DROP CONSTRAINT IF EXISTS check_valid_percentage;"
        ),
        
        migrations.RunSQL(
            "ALTER TABLE dashboard_clientanalytics "
            "ADD CONSTRAINT check_valid_payment_score CHECK (payment_score >= 0 AND payment_score <= 100);",
            reverse_sql="ALTER TABLE dashboard_clientanalytics DROP CONSTRAINT IF EXISTS check_valid_payment_score;"
        ),
    ]