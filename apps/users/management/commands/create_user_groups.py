from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.suppliers.models import Supplier, Purchase
from apps.customers.models import Customer, Delivery
from apps.expenses.models import Expense, Salary

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default user groups with appropriate permissions'

    def handle(self, *args, **options):
        self.stdout.write('Creating user groups...')

        # Create the groups
        admin_group, admin_created = Group.objects.get_or_create(name='ADMIN')
        accountant_group, accountant_created = Group.objects.get_or_create(name='ACCOUNTANT')
        viewer_group, viewer_created = Group.objects.get_or_create(name='VIEWER')

        # Clear existing permissions before adding new ones
        admin_group.permissions.clear()
        accountant_group.permissions.clear()
        viewer_group.permissions.clear()

        # Assign permissions to groups
        self._set_admin_permissions(admin_group)
        self._set_accountant_permissions(accountant_group)
        self._set_viewer_permissions(viewer_group)

        # Output results
        self.stdout.write(self.style.SUCCESS(f'Admin group {"created" if admin_created else "updated"} successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Accountant group {"created" if accountant_created else "updated"} successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Viewer group {"created" if viewer_created else "updated"} successfully!'))

    def _set_admin_permissions(self, group):
        """Add all permissions to Admin group"""
        # Get all permissions
        all_permissions = Permission.objects.all()
        
        # Add permissions to the admin group
        group.permissions.add(*all_permissions)
        
        self.stdout.write(f'Added {all_permissions.count()} permissions to Admin group')

    def _set_accountant_permissions(self, group):
        """Add Accountant-specific permissions"""
        # Models that accountants can fully manage
        financial_models = [
            Supplier, Purchase, Customer, Delivery, 
            Expense, Salary
        ]
        
        # Get permission for these models
        permissions = []
        for model in financial_models:
            content_type = ContentType.objects.get_for_model(model)
            model_permissions = Permission.objects.filter(content_type=content_type)
            permissions.extend(model_permissions)
            
        # User permissions - view only
        user_content_type = ContentType.objects.get_for_model(User)
        user_view_permission = Permission.objects.filter(
            content_type=user_content_type, 
            codename__startswith='view_'
        )
        permissions.extend(user_view_permission)
        
        # Add permissions to the accountant group
        group.permissions.add(*permissions)
        
        self.stdout.write(f'Added {len(permissions)} permissions to Accountant group')

    def _set_viewer_permissions(self, group):
        """Add Viewer-specific permissions (view only)"""
        # Get all 'view_' permissions
        view_permissions = Permission.objects.filter(codename__startswith='view_')
        
        # Add permissions to the viewer group
        group.permissions.add(*view_permissions)
        
        self.stdout.write(f'Added {view_permissions.count()} permissions to Viewer group') 