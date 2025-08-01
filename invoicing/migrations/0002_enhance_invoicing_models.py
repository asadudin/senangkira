# Generated migration for enhanced invoicing models
from django.db import migrations, models
import django.core.validators
from decimal import Decimal
import invoicing.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0001_initial'),
    ]

    operations = [
        # Update Item model
        migrations.AddField(
            model_name='item',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Whether this item is available for use'),
        ),
        migrations.AddField(
            model_name='item',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name='item',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='name',
            field=models.CharField(help_text='Item or service name', max_length=255),
        ),
        migrations.AlterField(
            model_name='item',
            name='description',
            field=models.TextField(blank=True, help_text='Detailed description of the item/service', null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='default_price',
            field=models.DecimalField(decimal_places=2, help_text='Default price for this item', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AlterField(
            model_name='item',
            name='owner',
            field=models.ForeignKey(help_text='The user who owns this item', on_delete=django.db.models.deletion.CASCADE, related_name='items', to='authentication.user'),
        ),
        
        # Update Quote model
        migrations.AlterField(
            model_name='quote',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent'), ('approved', 'Approved'), ('declined', 'Declined'), ('expired', 'Expired')], default='draft', help_text='Current status of the quote', max_length=20),
        ),
        migrations.AlterField(
            model_name='quote',
            name='quote_number',
            field=models.CharField(help_text='Auto-generated quote number', max_length=50),
        ),
        migrations.AddField(
            model_name='quote',
            name='title',
            field=models.CharField(blank=True, help_text='Optional title for the quote', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='quote',
            name='notes',
            field=models.TextField(blank=True, help_text='Internal notes for the quote', null=True),
        ),
        migrations.AddField(
            model_name='quote',
            name='terms',
            field=models.TextField(blank=True, help_text='Terms and conditions for the quote', null=True),
        ),
        migrations.AlterField(
            model_name='quote',
            name='issue_date',
            field=models.DateField(auto_now_add=True, help_text='Date when the quote was created'),
        ),
        migrations.AddField(
            model_name='quote',
            name='valid_until',
            field=models.DateField(blank=True, help_text='Quote expiration date', null=True),
        ),
        migrations.AlterField(
            model_name='quote',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total amount of the quote (auto-calculated)', max_digits=10),
        ),
        migrations.AddField(
            model_name='quote',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Subtotal before tax (auto-calculated)', max_digits=10),
        ),
        migrations.AddField(
            model_name='quote',
            name='tax_rate',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.0000'), help_text='Tax rate as decimal (e.g., 0.1000 for 10%)', max_digits=5),
        ),
        migrations.AddField(
            model_name='quote',
            name='tax_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Tax amount (auto-calculated)', max_digits=10),
        ),
        migrations.AddField(
            model_name='quote',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='quote',
            name='sent_at',
            field=models.DateTimeField(blank=True, help_text='When the quote was sent to client', null=True),
        ),
        migrations.AlterField(
            model_name='quote',
            name='owner',
            field=models.ForeignKey(help_text='The user who owns this quote', on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='authentication.user'),
        ),
        migrations.AlterField(
            model_name='quote',
            name='client',
            field=models.ForeignKey(help_text='The client this quote is for', on_delete=django.db.models.deletion.RESTRICT, related_name='quotes', to='clients.client'),
        ),
        
        # Update QuoteLineItem model
        migrations.AlterField(
            model_name='quotelineitem',
            name='description',
            field=models.TextField(help_text='Description of the item or service'),
        ),
        migrations.AlterField(
            model_name='quotelineitem',
            name='quantity',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), help_text='Quantity of items', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AlterField(
            model_name='quotelineitem',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, help_text='Price per unit', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AddField(
            model_name='quotelineitem',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, help_text='Order of line items in the quote'),
        ),
        migrations.AlterField(
            model_name='quotelineitem',
            name='quote',
            field=models.ForeignKey(help_text='The quote this line item belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='invoicing.quote'),
        ),
        
        # Update Invoice model
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent'), ('viewed', 'Viewed'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')], default='draft', help_text='Current status of the invoice', max_length=20),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='invoice_number',
            field=models.CharField(help_text='Auto-generated invoice number', max_length=50),
        ),
        migrations.AddField(
            model_name='invoice',
            name='title',
            field=models.CharField(blank=True, help_text='Optional title for the invoice', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='notes',
            field=models.TextField(blank=True, help_text='Internal notes for the invoice', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='terms',
            field=models.TextField(blank=True, help_text='Payment terms and conditions', null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='issue_date',
            field=models.DateField(auto_now_add=True, help_text='Date when the invoice was issued'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='due_date',
            field=models.DateField(help_text='Payment due date'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total amount of the invoice (auto-calculated)', max_digits=10),
        ),
        migrations.AddField(
            model_name='invoice',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Subtotal before tax (auto-calculated)', max_digits=10),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tax_rate',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.0000'), help_text='Tax rate as decimal (e.g., 0.1000 for 10%)', max_digits=5),
        ),
        migrations.AddField(
            model_name='invoice',
            name='tax_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Tax amount (auto-calculated)', max_digits=10),
        ),
        migrations.AddField(
            model_name='invoice',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='sent_at',
            field=models.DateTimeField(blank=True, help_text='When the invoice was sent to client', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='paid_at',
            field=models.DateTimeField(blank=True, help_text='When the invoice was marked as paid', null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='owner',
            field=models.ForeignKey(help_text='The user who owns this invoice', on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='authentication.user'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='client',
            field=models.ForeignKey(help_text='The client this invoice is for', on_delete=django.db.models.deletion.RESTRICT, related_name='invoices', to='clients.client'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='source_quote',
            field=models.OneToOneField(blank=True, help_text='The quote this invoice was created from (optional)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice', to='invoicing.quote'),
        ),
        
        # Update InvoiceLineItem model
        migrations.AlterField(
            model_name='invoicelineitem',
            name='description',
            field=models.TextField(help_text='Description of the item or service'),
        ),
        migrations.AlterField(
            model_name='invoicelineitem',
            name='quantity',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.00'), help_text='Quantity of items', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AlterField(
            model_name='invoicelineitem',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, help_text='Price per unit', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AddField(
            model_name='invoicelineitem',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, help_text='Order of line items in the invoice'),
        ),
        migrations.AlterField(
            model_name='invoicelineitem',
            name='invoice',
            field=models.ForeignKey(help_text='The invoice this line item belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='invoicing.invoice'),
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['owner', 'name'], name='invoicing_it_owner_i_b26eda_idx'),
        ),
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['owner', 'is_active'], name='invoicing_it_owner_i_e9a4c6_idx'),
        ),
        migrations.AddIndex(
            model_name='quote',
            index=models.Index(fields=['owner', 'status'], name='invoicing_qu_owner_i_6f4e99_idx'),
        ),
        migrations.AddIndex(
            model_name='quote',
            index=models.Index(fields=['owner', 'client'], name='invoicing_qu_owner_i_8a7b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='quote',
            index=models.Index(fields=['owner', 'quote_number'], name='invoicing_qu_owner_i_d5f7a2_idx'),
        ),
        migrations.AddIndex(
            model_name='quote',
            index=models.Index(fields=['valid_until'], name='invoicing_qu_valid_u_9e4b6f_idx'),
        ),
        migrations.AddIndex(
            model_name='quotelineitem',
            index=models.Index(fields=['quote', 'sort_order'], name='invoicing_qu_quote_i_c7d8e5_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['owner', 'status'], name='invoicing_in_owner_i_4a9b5c_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['owner', 'client'], name='invoicing_in_owner_i_2e8f7d_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['owner', 'invoice_number'], name='invoicing_in_owner_i_f6a9c4_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['due_date'], name='invoicing_in_due_dat_1b5e7a_idx'),
        ),
        migrations.AddIndex(
            model_name='invoicelineitem',
            index=models.Index(fields=['invoice', 'sort_order'], name='invoicing_in_invoice_8d3f5e_idx'),
        ),
        
        # Add constraints
        migrations.AddConstraint(
            model_name='item',
            constraint=models.UniqueConstraint(fields=('owner', 'name'), name='unique_item_name_per_owner'),
        ),
        migrations.AddConstraint(
            model_name='quote',
            constraint=models.UniqueConstraint(fields=('owner', 'quote_number'), name='unique_quote_number_per_owner'),
        ),
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(fields=('owner', 'invoice_number'), name='unique_invoice_number_per_owner'),
        ),
        
        # Update model options
        migrations.AlterModelOptions(
            name='item',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='quotelineitem',
            options={'ordering': ['sort_order', 'id']},
        ),
        migrations.AlterModelOptions(
            name='invoicelineitem',
            options={'ordering': ['sort_order', 'id']},
        ),
    ]