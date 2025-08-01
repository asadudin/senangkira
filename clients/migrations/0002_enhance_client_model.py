# Generated migration for enhanced Client model
from django.db import migrations, models
import django.core.validators
import clients.models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='company',
            field=models.CharField(blank=True, help_text="Client's company name (if different from name)", max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='tax_id',
            field=models.CharField(blank=True, help_text="Client's tax ID or business registration number", max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='notes',
            field=models.TextField(blank=True, help_text='Additional notes about the client', null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Whether this client is active'),
        ),
        migrations.AlterField(
            model_name='client',
            name='name',
            field=models.CharField(help_text="Client's full name or company name", max_length=255),
        ),
        migrations.AlterField(
            model_name='client',
            name='email',
            field=models.EmailField(blank=True, help_text="Client's email address", max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='phone',
            field=models.CharField(blank=True, help_text="Client's phone number (international format)", max_length=50, null=True, validators=[clients.models.validate_phone_number]),
        ),
        migrations.AlterField(
            model_name='client',
            name='address',
            field=models.TextField(blank=True, help_text="Client's full address", null=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='owner',
            field=models.ForeignKey(help_text='The user who owns this client record', on_delete=django.db.models.deletion.CASCADE, related_name='clients', to='authentication.user'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['owner', 'name'], name='clients_cli_owner_i_aacf3f_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['owner', 'email'], name='clients_cli_owner_i_8c8cc3_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['owner', 'is_active'], name='clients_cli_owner_i_d72e7e_idx'),
        ),
        migrations.AddConstraint(
            model_name='client',
            constraint=models.UniqueConstraint(condition=models.Q(('email__isnull', False), ('email', ''), _negated=True), fields=('owner', 'email'), name='unique_client_email_per_owner'),
        ),
    ]