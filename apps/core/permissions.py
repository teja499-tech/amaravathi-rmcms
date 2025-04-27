from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from functools import wraps

# Role-based test functions
def is_admin(user):
    return user.is_authenticated and user.groups.filter(name='Admin').exists()

def is_accountant(user):
    return user.is_authenticated and (
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Accountant').exists()
    )

def is_manager(user):
    return user.is_authenticated and (
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Accountant').exists() or 
        user.groups.filter(name='Manager').exists()
    )

def is_viewer(user):
    return user.is_authenticated and (
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Accountant').exists() or 
        user.groups.filter(name='Manager').exists() or 
        user.groups.filter(name='Viewer').exists()
    )

# Role-based decorators
admin_required = user_passes_test(is_admin)
accountant_required = user_passes_test(is_accountant)
manager_required = user_passes_test(is_manager)
viewer_required = user_passes_test(is_viewer)

# Mixins for class-based views
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)

class AccountantRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_accountant(self.request.user)

class ManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_manager(self.request.user)

class ViewerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_viewer(self.request.user)

# Permission checks for edit operations
def can_edit_financial_data(user):
    return user.is_authenticated and (
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Accountant').exists()
    )

def can_view_financial_data(user):
    return is_viewer(user)

# Permission enforcement function for views
def permission_required(*groups):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            if any(request.user.groups.filter(name=group).exists() for group in groups):
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied("You don't have permission to access this page.")
        return wrapper
    return decorator 