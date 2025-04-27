from django.conf import settings
from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test

User = get_user_model()


def get_user_role(user):
    """
    Get the role of a user.
    
    Args:
        user: The user to check role for
        
    Returns:
        str: The role of the user or None if no role
    """
    if user.is_authenticated:
        return user.role
    return None


def role_required(roles):
    """
    Decorator for views that checks if the user has the required role.
    
    Args:
        roles: Single role string or list of roles
        
    Usage:
        @role_required('ADMIN')
        def admin_view(request):
            ...
            
        @role_required(['ADMIN', 'ACCOUNTANT'])
        def financial_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_role = get_user_role(request.user)
            
            # Convert single role to list
            required_roles = [roles] if isinstance(roles, str) else roles
            
            if not user_role or user_role not in required_roles:
                if request.user.is_authenticated:
                    # User is logged in but doesn't have the right role
                    messages.error(request, "You don't have permission to access this page.")
                    raise PermissionDenied("Insufficient permissions")
                else:
                    # User is not logged in, redirect to login
                    messages.info(request, "Please log in to access this page.")
                    return redirect(settings.LOGIN_URL)
                    
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def is_admin(user):
    """Check if a user has the Admin role"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.role == User.Role.ADMIN or 
        user.role == 'ADMIN' or 
        user.role == 'Admin' or 
        user.role == 'Administrator'
    )


def is_accountant(user):
    """Check if a user has the Accountant role"""
    return user.is_authenticated and (
        user.role == User.Role.ACCOUNTANT or 
        user.role == 'ACCOUNTANT' or 
        user.role == 'Accountant'
    )


def is_viewer(user):
    """Check if a user has the Viewer role"""
    return user.is_authenticated and user.role == User.Role.VIEWER


# Role-based mixins for class-based views
class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require Admin role for class-based views"""
    def test_func(self):
        return is_admin(self.request.user)
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Only administrators can access this page.")
            raise PermissionDenied("Admin access required")
        return redirect(settings.LOGIN_URL)


class AccountantRequiredMixin(UserPassesTestMixin):
    """Mixin to require Accountant or Admin role for class-based views"""
    def test_func(self):
        return is_admin(self.request.user) or is_accountant(self.request.user)
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Only accountants or administrators can access this page.")
            raise PermissionDenied("Accountant access required")
        return redirect(settings.LOGIN_URL)


class ViewerRequiredMixin(UserPassesTestMixin):
    """Mixin to require any authenticated user (all roles have at least viewer permissions)"""
    def test_func(self):
        return self.request.user.is_authenticated
    
    def handle_no_permission(self):
        messages.info(self.request, "Please log in to access this page.")
        return redirect(settings.LOGIN_URL)


# User passes test decorators for function-based views
def admin_required(function=None, login_url=None, redirect_field_name='next'):
    """
    Decorator for views that checks if the user is an admin.
    """
    actual_decorator = user_passes_test(
        is_admin,
        login_url=login_url or settings.LOGIN_URL,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def accountant_required(function=None, login_url=None, redirect_field_name='next'):
    """
    Decorator for views that checks if the user is an accountant or admin.
    """
    actual_decorator = user_passes_test(
        lambda u: is_admin(u) or is_accountant(u),
        login_url=login_url or settings.LOGIN_URL,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def viewer_required(function=None, login_url=None, redirect_field_name='next'):
    """
    Decorator for views that checks if the user is authenticated
    (all roles have at least viewer permissions).
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated,
        login_url=login_url or settings.LOGIN_URL,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator 