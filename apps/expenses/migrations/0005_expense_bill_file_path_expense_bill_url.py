# Generated by Django 5.2 on 2025-04-23 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0004_expensecategory_default_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='bill_file_path',
            field=models.CharField(blank=True, help_text='Path to the expense bill in Supabase Storage', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='expense',
            name='bill_url',
            field=models.URLField(blank=True, help_text='URL to the expense bill in Supabase Storage', null=True),
        ),
    ]
