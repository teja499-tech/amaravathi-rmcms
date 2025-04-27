import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

class Command(BaseCommand):
    help = 'Create user groups with their respective permissions'

    def handle(self, *args, **options):
        # Define groups and their permissions
        admin_group, created = Group.objects.get_or_create(name='Admin')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Admin group'))
        
        manager_group, created = Group.objects.get_or_create(name='Manager')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Manager group'))
        
        accountant_group, created = Group.objects.get_or_create(name='Accountant')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Accountant group'))
        
        clerk_group, created = Group.objects.get_or_create(name='Clerk')
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Clerk group'))

        # Define models and permissions for each group
        admin_models = [
            # All models - Admin has access to everything
            ('auth', ['user', 'group', 'permission']),
            ('admin', ['logentry']),
            ('contenttypes', ['contenttype']),
            ('sessions', ['session']),
            ('customers', ['customer', 'delivery', 'customerpayment']),
            ('suppliers', ['supplier', 'purchase', 'supplierpayment']),
            ('expenses', ['expensecategory', 'vehicle', 'expense']),
            ('employees', ['employee', 'attendance', 'salary']),
            ('accounts', ['ledgerentry', 'bankaccount', 'transaction']),
            ('commitments', ['commitment', 'paymentschedule']),
            ('core', ['profile', 'document']),
        ]

        manager_models = [
            # Manager has access to most business operations but not user management
            ('customers', ['customer', 'delivery', 'customerpayment']),
            ('suppliers', ['supplier', 'purchase', 'supplierpayment']),
            ('expenses', ['expensecategory', 'vehicle', 'expense']),
            ('employees', ['employee', 'attendance', 'salary']),
            ('accounts', ['ledgerentry', 'bankaccount', 'transaction']),
            ('commitments', ['commitment', 'paymentschedule']),
            ('core', ['document']),
        ]

        accountant_models = [
            # Accountant has access to financial data and reports
            ('customers', ['customer', 'delivery', 'customerpayment']),
            ('suppliers', ['supplier', 'purchase', 'supplierpayment']),
            ('expenses', ['expensecategory', 'vehicle', 'expense']),
            ('employees', ['salary']),
            ('accounts', ['ledgerentry', 'bankaccount', 'transaction']),
            ('commitments', ['commitment', 'paymentschedule']),
        ]

        clerk_models = [
            # Clerk has limited access to data entry and basic operations
            ('customers', ['customer', 'delivery', 'customerpayment']),
            ('suppliers', ['supplier', 'purchase']),
            ('expenses', ['expense']),
            ('employees', ['attendance']),
        ]

        # Dictionary to map group names to model permissions
        group_permissions = {
            'Admin': {
                'models': admin_models,
                'permissions': ['add', 'change', 'delete', 'view'],
                'group': admin_group
            },
            'Manager': {
                'models': manager_models,
                'permissions': ['add', 'change', 'delete', 'view'],
                'group': manager_group
            },
            'Accountant': {
                'models': accountant_models,
                'permissions': ['add', 'change', 'view'],  # No delete permission
                'group': accountant_group
            },
            'Clerk': {
                'models': clerk_models,
                'permissions': ['add', 'view'],  # Only add and view permissions
                'group': clerk_group
            }
        }

        # Assign permissions to groups
        for group_name, group_data in group_permissions.items():
            self.stdout.write(f'Setting up permissions for {group_name}')
            
            for app_label, models in group_data['models']:
                for model_name in models:
                    for permission_name in group_data['permissions']:
                        try:
                            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                            codename = f"{permission_name}_{model_name}"
                            
                            try:
                                permission = Permission.objects.get(content_type=content_type, codename=codename)
                                group_data['group'].permissions.add(permission)
                                self.stdout.write(f'  Added {permission_name} permission for {model_name} to {group_name}')
                            except Permission.DoesNotExist:
                                self.stdout.write(self.style.WARNING(f'  Permission {codename} does not exist'))
                                
                        except ContentType.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f'  ContentType for {app_label}.{model_name} does not exist'))

        self.stdout.write(self.style.SUCCESS('Successfully set up user groups and permissions')) 