# Generated by Django 5.2 on 2025-04-25 00:25

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0008_alter_concretedelivery_grade_alter_mixratio_grade'),
    ]

    operations = [
        migrations.AddField(
            model_name='concretedelivery',
            name='due_date',
            field=models.DateField(blank=True, help_text='Payment due date for this delivery', null=True),
        ),
        migrations.AddField(
            model_name='concretedelivery',
            name='received_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
        migrations.AddField(
            model_name='concretedelivery',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AddField(
            model_name='customerpayment',
            name='concrete_delivery',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='concrete_payments', to='customers.concretedelivery'),
        ),
    ]
