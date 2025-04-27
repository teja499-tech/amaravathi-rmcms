from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

class Command(BaseCommand):
    help = 'Sets up user roles and their permissions'

    def handle(self, *args, **options):
        # Create groups if they don't exist
        admin_group, created = Group.objects.get_or_create(name='Admin')
        manager_group, created = Group.objects.get_or_create(name='Manager')
        accountant_group, created = Group.objects.get_or_create(name='Accountant')
        clerk_group, created = Group.objects.get_or_create(name='Clerk')
        
        self.stdout.write(self.style.SUCCESS('Created user role groups'))
        
        # Dictionary mapping models to their app labels
        model_app_mapping = {
            'customer': 'customers',
            'delivery': 'customers',
            'customerpayment': 'customers',
            'supplier': 'suppliers',
            'purchase': 'suppliers',
            'supplierpayment': 'suppliers',
            'expense': 'expenses',
            'expensecategory': 'expenses',
            'vehicle': 'expenses',
            'employee': 'employees',
            'salary': 'employees',
            'bankaccount': 'accounts',
            'transaction': 'accounts',
            'ledgerentry': 'accounts',
            'commitment': 'commitments',
            'commitmentpayment': 'commitments',
        }
        
        # Clear existing permissions
        admin_group.permissions.clear()
        manager_group.permissions.clear()
        accountant_group.permissions.clear()
        clerk_group.permissions.clear()
        
        # Set permissions for each model
        for model_name, app_label in model_app_mapping.items():
            try:
                model = apps.get_model(app_label, model_name)
                content_type = ContentType.objects.get_for_model(model)
                
                # Get all permissions for this model
                permissions = Permission.objects.filter(content_type=content_type)
                
                # Admin gets all permissions
                admin_group.permissions.add(*permissions)
                
                # Manager gets all permissions except delete for some models
                restricted_delete_models = ['bankaccount', 'transaction', 'ledgerentry']
                if model_name in restricted_delete_models:
                    manager_perms = permissions.exclude(codename__startswith='delete_')
                else:
                    manager_perms = permissions
                manager_group.permissions.add(*manager_perms)
                
                # Accountant gets financial permissions
                financial_models = [
                    'customerpayment', 'supplierpayment', 'expense',
                    'bankaccount', 'transaction', 'ledgerentry',
                    'commitment', 'commitmentpayment', 'salary'
                ]
                
                if model_name in financial_models:
                    # Can view, add, change but not delete
                    accountant_perms = permissions.exclude(codename__startswith='delete_')
                    accountant_group.permissions.add(*accountant_perms)
                else:
                    # Can only view non-financial models
                    view_perms = permissions.filter(codename__startswith='view_')
                    accountant_group.permissions.add(*view_perms)
                
                # Clerk gets limited permissions
                basic_models = [
                    'customer', 'delivery', 'customerpayment',
                    'supplier', 'purchase', 'expense'
                ]
                
                if model_name in basic_models:
                    # Can view and add but not change or delete
                    view_add_perms = permissions.filter(
                        codename__startswith='view_') | permissions.filter(
                        codename__startswith='add_')
                    clerk_group.permissions.add(*view_add_perms)
                else:
                    # Can only view other models
                    view_perms = permissions.filter(codename__startswith='view_')
                    clerk_group.permissions.add(*view_perms)
                
            except LookupError:
                self.stdout.write(self.style.WARNING(
                    f'Could not find model {model_name} in app {app_label}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully set up permissions for all roles'))
        
        # Print permission counts
        self.stdout.write(f'Admin group has {admin_group.permissions.count()} permissions')
        self.stdout.write(f'Manager group has {manager_group.permissions.count()} permissions')
        self.stdout.write(f'Accountant group has {accountant_group.permissions.count()} permissions')
        self.stdout.write(f'Clerk group has {clerk_group.permissions.count()} permissions') 