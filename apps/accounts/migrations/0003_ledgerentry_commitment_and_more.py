# Generated by Django 5.2 on 2025-04-24 02:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
        ('commitments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledgerentry',
            name='commitment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ledger_entries', to='commitments.operationalcommitment'),
        ),
        migrations.AlterField(
            model_name='ledgerentry',
            name='transaction_type',
            field=models.CharField(choices=[('income', 'Income'), ('expense', 'Expense'), ('transfer', 'Transfer'), ('purchase', 'Purchase'), ('sale', 'Sale'), ('adjustment', 'Adjustment'), ('operational', 'Operational')], max_length=20),
        ),
    ]
