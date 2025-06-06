# Generated by Django 5.2 on 2025-04-24 23:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0003_alter_material_current_stock'),
        ('suppliers', '0006_purchase_due_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplierpayment',
            name='purchase_order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='supplier_payments', to='materials.purchaseorder', verbose_name='Purchase Order'),
        ),
    ]
