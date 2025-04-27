from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.db import transaction


class Command(BaseCommand):
    help = 'Sets up user roles and permissions for the application'

    def handle(self, *args, **options):
        self.stdout.write('Setting up user roles and permissions...')
        
        with transaction.atomic():
            # Create groups
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            manager_group, _ = Group.objects.get_or_create(name='Manager')
            accountant_group, _ = Group.objects.get_or_create(name='Accountant')
            clerk_group, _ = Group.objects.get_or_create(name='Clerk')
            
            # Clear existing permissions
            admin_group.permissions.clear()
            manager_group.permissions.clear()
            accountant_group.permissions.clear()
            clerk_group.permissions.clear()
            
            # Define model permissions for each role
            role_permissions = {
                'Admin': {
                    # Admin can do everything
                    'all_models': ['view', 'add', 'change', 'delete'],
                },
                'Manager': {
                    'customer': ['view', 'add', 'change', 'delete'],
                    'delivery': ['view', 'add', 'change', 'delete'],
                    'customerpayment': ['view', 'add', 'change', 'delete'],
                    'supplier': ['view', 'add', 'change', 'delete'],
                    'purchase': ['view', 'add', 'change', 'delete'],
                    'supplierpayment': ['view', 'add', 'change', 'delete'],
                    'expense': ['view', 'add', 'change', 'delete'],
                    'vehicle': ['view', 'add', 'change', 'delete'],
                    'employee': ['view', 'add', 'change', 'delete'],
                    'salary': ['view', 'add', 'change', 'delete'],
                    'expensecategory': ['view', 'add', 'change', 'delete'],
                    'commitment': ['view', 'add', 'change', 'delete'],
                    'bankaccount': ['view'],
                    'transaction': ['view'],
                },
                'Accountant': {
                    'customer': ['view'],
                    'delivery': ['view'],
                    'customerpayment': ['view', 'add', 'change'],
                    'supplier': ['view'],
                    'purchase': ['view'],
                    'supplierpayment': ['view', 'add', 'change'],
                    'expense': ['view', 'add', 'change'],
                    'vehicle': ['view'],
                    'employee': ['view'],
                    'salary': ['view', 'add', 'change'],
                    'expensecategory': ['view'],
                    'commitment': ['view', 'add', 'change'],
                    'bankaccount': ['view', 'add', 'change'],
                    'transaction': ['view', 'add', 'change'],
                },
                'Clerk': {
                    'customer': ['view', 'add'],
                    'delivery': ['view', 'add'],
                    'customerpayment': ['view', 'add'],
                    'supplier': ['view'],
                    'purchase': ['view'],
                    'supplierpayment': ['view'],
                    'expense': ['view'],
                    'vehicle': ['view'],
                    'employee': ['view'],
                    'salary': ['view'],
                    'expensecategory': ['view'],
                    'commitment': ['view'],
                    'bankaccount': ['view'],
                    'transaction': ['view'],
                }
            }
            
            # Get all ContentTypes
            content_types = {}
            for app_label in ['customers', 'suppliers', 'expenses', 'employees', 'commitments', 'accounts', 'core']:
                try:
                    app_models = apps.get_app_config(app_label).get_models()
                    for model in app_models:
                        model_name = model.__name__.lower()
                        content_types[model_name] = ContentType.objects.get_for_model(model)
                except LookupError:
                    self.stdout.write(self.style.WARNING(f'App {app_label} not found'))
            
            # Assign permissions to groups
            self._assign_permissions(admin_group, role_permissions['Admin'], content_types)
            self._assign_permissions(manager_group, role_permissions['Manager'], content_types)
            self._assign_permissions(accountant_group, role_permissions['Accountant'], content_types)
            self._assign_permissions(clerk_group, role_permissions['Clerk'], content_types)
            
            self.stdout.write(self.style.SUCCESS('Successfully set up user roles and permissions'))
    
    def _assign_permissions(self, group, role_perms, content_types):
        """Assign permissions to a group based on role permissions."""
        # Handle all_models permissions
        if 'all_models' in role_perms:
            actions = role_perms['all_models']
            for model_name, content_type in content_types.items():
                for action in actions:
                    codename = f'{action}_{model_name}'
                    try:
                        perm = Permission.objects.get(content_type=content_type, codename=codename)
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Permission {codename} not found for {content_type}'))
        
        # Handle model-specific permissions
        for model_name, actions in role_perms.items():
            if model_name == 'all_models':
                continue
                
            content_type = content_types.get(model_name)
            if not content_type:
                self.stdout.write(self.style.WARNING(f'ContentType for {model_name} not found'))
                continue
                
            for action in actions:
                codename = f'{action}_{model_name}'
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=codename)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Permission {codename} not found for {content_type}')) 