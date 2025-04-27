from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import models
from django.contrib.auth.models import Group, Permission
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import User
from .utils import (
    role_required, is_admin, is_accountant, is_viewer,
    admin_required, accountant_required, viewer_required,
    AdminRequiredMixin, AccountantRequiredMixin, ViewerRequiredMixin
)


@login_required
def user_profile(request):
    """
    View for a user to see their own profile
    """
    return render(request, 'users/profile.html')


@admin_required
def admin_dashboard(request):
    """
    Admin-only dashboard
    """
    users = User.objects.all()
    return render(request, 'users/admin_dashboard.html', {'users': users})


@accountant_required
def financial_dashboard(request):
    """
    Financial dashboard for admins and accountants
    """
    return render(request, 'users/financial_dashboard.html')


class UserListView(AdminRequiredMixin, ListView):
    """
    View for listing users - Admin only
    """
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply search filter
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                models.Q(username__icontains=search_query) |
                models.Q(full_name__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )
        
        # Apply role filter
        role = self.request.GET.get('role', '')
        if role:
            queryset = queryset.filter(role=role)
        
        # Apply status filter
        status = self.request.GET.get('status', '')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('-date_joined')


def login_view(request):
    """
    Redirect to Django's built-in login view
    """
    return redirect('login')


def logout_view(request):
    """
    Redirect to Django's built-in logout view
    """
    return redirect('logout')


# Add user management views with appropriate permissions
class UserDetailView(AdminRequiredMixin, DetailView):
    """
    View for showing user details - Admin only
    """
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'  # Use user_obj to avoid conflict with the request.user


class UserCreateView(AdminRequiredMixin, CreateView):
    """
    View for creating a new user - Admin only
    """
    model = User
    template_name = 'users/user_form.html'
    fields = ['username', 'full_name', 'email', 'phone_number', 'role', 'is_active']
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        # Set a default password
        user = form.save(commit=False)
        user.set_password('changeme')  # Default password, should be changed on first login
        messages.success(self.request, f"User {user.username} created successfully with default password.")
        return super().form_valid(form)


class UserUpdateView(AdminRequiredMixin, UpdateView):
    """
    View for updating a user - Admin only
    """
    model = User
    template_name = 'users/user_form.html'
    fields = ['full_name', 'email', 'phone_number', 'role', 'is_active']
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        messages.success(self.request, f"User {form.instance.username} updated successfully.")
        return super().form_valid(form)


@login_required
def change_password(request):
    """
    View for a user to change their own password
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('users:change_password')
            
        if new_password != confirm_password:
            messages.error(request, "New passwords don't match.")
            return redirect('users:change_password')
            
        request.user.set_password(new_password)
        request.user.save()
        messages.success(request, "Password changed successfully. Please login again.")
        return redirect('login')
        
    return render(request, 'users/change_password.html')


def is_admin(user):
    """Check if user is an admin."""
    return user.is_superuser or user.groups.filter(name='Admin').exists()

@user_passes_test(is_admin)
def manage_user_roles(request):
    """
    View for administrators to manage user roles and permissions.
    """
    users = User.objects.all().prefetch_related('groups')
    groups = Group.objects.all().prefetch_related('permissions')
    
    return render(request, 'users/manage_roles.html', {
        'users': users,
        'groups': groups,
    })

@user_passes_test(is_admin)
@require_POST
def assign_user_group(request):
    """
    API endpoint to assign a user to a group.
    """
    try:
        user_id = request.POST.get('user_id')
        group_id = request.POST.get('group_id')
        action = request.POST.get('action')  # 'add' or 'remove'
        
        user = User.objects.get(id=user_id)
        group = Group.objects.get(id=group_id)
        
        if action == 'add':
            user.groups.add(group)
            message = f"Added {user.username} to group {group.name}"
        elif action == 'remove':
            user.groups.remove(group)
            message = f"Removed {user.username} from group {group.name}"
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action'})
        
        return JsonResponse({'success': True, 'message': message})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})
    except Group.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Group not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# Add view classes and functions here 