from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


class Command(BaseCommand):
    help = 'Create user groups with appropriate permissions'

    def handle(self, *args, **options):
        # Create groups
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        accountant_group, _ = Group.objects.get_or_create(name='Accountant')
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        viewer_group, _ = Group.objects.get_or_create(name='Viewer')

        # Clear existing permissions
        admin_group.permissions.clear()
        accountant_group.permissions.clear()
        manager_group.permissions.clear()
        viewer_group.permissions.clear()

        # Get all models
        all_models = apps.get_models()
        
        # Exclude auth models that should only be managed in admin
        excluded_apps = ['auth', 'contenttypes', 'sessions', 'admin']
        excluded_models = ['user', 'group', 'permission']
        
        # Admin: All permissions
        all_permissions = Permission.objects.all()
        admin_group.permissions.add(*all_permissions)
        
        # Process each model and assign permissions
        for model in all_models:
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            
            # Skip excluded models
            if app_label in excluded_apps or model_name in excluded_models:
                continue
                
            content_type = ContentType.objects.get_for_model(model)
            
            # Get permissions
            view_perm = Permission.objects.get(
                content_type=content_type, 
                codename=f'view_{model_name}'
            )
            add_perm = Permission.objects.get(
                content_type=content_type, 
                codename=f'add_{model_name}'
            )
            change_perm = Permission.objects.get(
                content_type=content_type, 
                codename=f'change_{model_name}'
            )
            delete_perm = Permission.objects.get(
                content_type=content_type, 
                codename=f'delete_{model_name}'
            )
            
            # Accountant: View/add/change financial data
            if app_label in ['accounts', 'expenses', 'customers', 'suppliers', 'commitments']:
                accountant_group.permissions.add(view_perm, add_perm, change_perm)
            elif app_label not in ['auth']:
                # For non-financial data, accountants can only view
                accountant_group.permissions.add(view_perm)
            
            # Manager: View all data
            manager_group.permissions.add(view_perm)
            
            # Viewer: View all data (same as manager)
            viewer_group.permissions.add(view_perm)
            
        self.stdout.write(self.style.SUCCESS('Successfully set up user groups and permissions')) 