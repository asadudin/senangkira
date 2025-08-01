# Enhanced expense models migration
from django.db import migrations, models
import django.core.validators
from decimal import Decimal
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        # Update Expense model fields
        migrations.AlterField(
            model_name='expense',
            name='description',
            field=models.CharField(help_text='Description of the expense', max_length=500),
        ),
        migrations.AlterField(
            model_name='expense',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Expense amount (must be positive)',
                max_digits=10,
                validators=[
                    django.core.validators.MinValueValidator(Decimal('0.01'), message='Expense amount must be positive'),
                    django.core.validators.MaxValueValidator(Decimal('99999999.99'), message='Expense amount too large')
                ]
            ),
        ),
        migrations.AlterField(
            model_name='expense',
            name='date',
            field=models.DateField(help_text='Date when the expense occurred'),
        ),
        migrations.AlterField(
            model_name='expense',
            name='receipt_image',
            field=models.CharField(blank=True, help_text='Path to receipt image file', max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='expense',
            name='owner',
            field=models.ForeignKey(help_text='The user who owns this expense', on_delete=models.CASCADE, related_name='expenses', to='authentication.user'),
        ),
        
        # Add new fields
        migrations.AddField(
            model_name='expense',
            name='category',
            field=models.CharField(
                choices=[
                    ('office_supplies', 'Office Supplies'),
                    ('travel', 'Travel & Transportation'),
                    ('meals', 'Meals & Entertainment'),
                    ('utilities', 'Utilities'),
                    ('rent', 'Rent & Facilities'),
                    ('marketing', 'Marketing & Advertising'),
                    ('software', 'Software & Subscriptions'),
                    ('equipment', 'Equipment & Hardware'),
                    ('professional', 'Professional Services'),
                    ('insurance', 'Insurance'),
                    ('taxes', 'Taxes & Fees'),
                    ('other', 'Other')
                ],
                default='other',
                help_text='Category of the expense',
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='expense',
            name='notes',
            field=models.TextField(blank=True, help_text='Additional notes about the expense', null=True),
        ),
        migrations.AddField(
            model_name='expense',
            name='is_reimbursable',
            field=models.BooleanField(default=True, help_text='Whether this expense is reimbursable'),
        ),
        migrations.AddField(
            model_name='expense',
            name='is_recurring',
            field=models.BooleanField(default=False, help_text='Whether this is a recurring expense'),
        ),
        migrations.AddField(
            model_name='expense',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, help_text='When the expense record was last updated'),
        ),
        
        # Update id field
        migrations.AlterField(
            model_name='expense',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique identifier for the expense', primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='expense',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, help_text='When the expense record was created'),
        ),
        
        # Create ExpenseAttachment model
        migrations.CreateModel(
            name='ExpenseAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file_path', models.CharField(help_text='Path to the attachment file', max_length=500)),
                ('file_name', models.CharField(help_text='Original name of the file', max_length=255)),
                ('file_size', models.PositiveIntegerField(help_text='Size of the file in bytes')),
                ('content_type', models.CharField(help_text='MIME type of the file', max_length=100)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, help_text='When the attachment was uploaded')),
                ('expense', models.ForeignKey(help_text='The expense this attachment belongs to', on_delete=models.CASCADE, related_name='attachments', to='expenses.expense')),
            ],
            options={
                'db_table': 'expenses_attachment',
                'ordering': ['-uploaded_at'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(fields=['owner', 'date'], name='expenses_owner_date_idx'),
        ),
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(fields=['owner', 'category'], name='expenses_owner_category_idx'),
        ),
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(fields=['owner', 'amount'], name='expenses_owner_amount_idx'),
        ),
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(fields=['date'], name='expenses_date_idx'),
        ),
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(fields=['category'], name='expenses_category_idx'),
        ),
        
        # Add constraints
        migrations.AddConstraint(
            model_name='expense',
            constraint=models.CheckConstraint(check=models.Q(amount__gt=0), name='expense_amount_positive'),
        ),
        
        # Update model options
        migrations.AlterModelOptions(
            name='expense',
            options={'ordering': ['-date', '-created_at']},
        ),
    ]