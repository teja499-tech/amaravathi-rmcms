from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.apps import apps
from django.conf import settings

def group_required(*group_names):
    """Decorator that checks if a user belongs to at least one of the specified groups."""
    def in_groups(user):
        if user.is_authenticated:
            if user.is_superuser or bool(user.groups.filter(name__in=group_names)):
                return True
        return False
    return user_passes_test(in_groups, login_url='login')

def role_required(role):
    """
    Decorator for views that checks whether a user has a specific role or higher.
    
    Args:
        role: The minimum role required to access the view.
              Valid roles are 'admin', 'manager', 'accountant', 'clerk'
    
    Returns:
        Function that takes a user object and returns True if the user has the required role
    """
    roles_hierarchy = {
        'admin': ['Admin'],
        'manager': ['Admin', 'Manager'],
        'accountant': ['Admin', 'Manager', 'Accountant'],
        'clerk': ['Admin', 'Manager', 'Accountant', 'Clerk']
    }
    
    allowed_groups = roles_hierarchy.get(role.lower(), [])
    
    def check_role(user):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        user_groups = user.groups.values_list('name', flat=True)
        return any(group in allowed_groups for group in user_groups)
    
    return user_passes_test(check_role, login_url=settings.LOGIN_URL)

def admin_required(view_func):
    """Decorator that checks if a user has admin role."""
    return role_required('admin')(view_func)

def manager_required(view_func):
    """Decorator that checks if a user has manager role or higher."""
    return role_required('manager')(view_func)

def accountant_required(view_func):
    """Decorator that checks if a user has accountant role or higher."""
    return role_required('accountant')(view_func)

def clerk_required(view_func):
    """Decorator that checks if a user has clerk role or higher."""
    return role_required('clerk')(view_func)

def permission_required(perm):
    """Decorator that checks if a user has the specified permission."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser or request.user.has_perm(perm):
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied
        return wrapped_view
    return decorator

def check_role_based_permission(model_name, action):
    """Decorator that checks if a user has permission to perform an action on a model.
    
    Args:
        model_name (str): Name of the model (e.g., 'customer', 'delivery')
        action (str): Action to perform ('view', 'add', 'change', 'delete')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(reverse('login'))
                
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            perm = f"{model_name.lower().split('.')[-1]}.{action}_{model_name.lower().split('.')[-1]}"
            
            if request.user.has_perm(perm):
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied
                
        return wrapped_view
    return decorator

# Helper function for context processors
def _check_role_based_permission(user, model_name, action):
    """Check if a user has permission to perform an action on a model.
    
    Args:
        user: User object
        model_name (str): Name of the model (e.g., 'customer', 'delivery')
        action (str): Action to perform ('view', 'add', 'change', 'delete')
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    if not user.is_authenticated:
        return False
        
    if user.is_superuser:
        return True
        
    perm = f"{model_name.lower()}.{action}_{model_name.lower()}"
    return user.has_perm(perm)

def can_access_model(model_name, permission='view'):
    """
    Decorator that checks if a user has permission to access a specific model.
    
    Args:
        model_name (str): The name of the model (e.g., 'customer', 'expense').
        permission (str): The permission type ('view', 'add', 'change', 'delete').
    
    Returns:
        Function: The decorator.
    """
    def decorator(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(reverse('login'))
                
            # Map model_name to app_label if needed
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
            
            app_label = model_app_mapping.get(model_name.lower(), model_name.lower())
            
            # Direct permission check
            perm_codename = f'{permission}_{model_name.lower()}'
            if request.user.has_perm(f'{app_label}.{perm_codename}'):
                return function(request, *args, **kwargs)
                
            # Role-based permission check
            user_groups = request.user.groups.values_list('name', flat=True)
            
            # Financial models - special handling
            financial_models = [
                'customerpayment', 'supplierpayment', 'expense',
                'bankaccount', 'transaction', 'ledgerentry',
                'commitment', 'commitmentpayment', 'salary'
            ]
            
            # Basic models
            basic_models = [
                'customer', 'delivery', 'customerpayment',
                'supplier', 'purchase', 'expense'
            ]
            
            # Admin has all permissions
            if 'Admin' in user_groups:
                return function(request, *args, **kwargs)
                
            # Manager has all permissions except delete for financial models
            if 'Manager' in user_groups:
                if model_name.lower() in financial_models and permission == 'delete':
                    messages.error(request, 'Managers cannot delete financial records.')
                    return HttpResponseForbidden('Access denied. Admin rights required for this action.')
                return function(request, *args, **kwargs)
                
            # Accountant has view/add/change but not delete for financial models
            if 'Accountant' in user_groups:
                if model_name.lower() in financial_models:
                    if permission != 'delete':
                        return function(request, *args, **kwargs)
                else:  # Non-financial models
                    if permission == 'view':
                        return function(request, *args, **kwargs)
                        
            # Clerk has view/add for basic models, view-only for others
            if 'Clerk' in user_groups:
                if model_name.lower() in basic_models:
                    if permission in ['view', 'add']:
                        return function(request, *args, **kwargs)
                elif permission == 'view':
                    return function(request, *args, **kwargs)
                    
            # Access denied
            messages.error(request, 'You do not have permission to perform this action.')
            return HttpResponseForbidden('Access denied. Insufficient permissions.')
            
        return wrapper
    return decorator 