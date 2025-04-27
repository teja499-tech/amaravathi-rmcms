from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User


class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for creating new users that includes role and full name.
    """
    class Meta:
        model = User
        fields = ('username', 'full_name', 'email', 'role', 'phone_number')


class CustomUserChangeForm(UserChangeForm):
    """
    Custom form for updating users.
    """
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('username', 'full_name', 'email', 'role', 'phone_number', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'full_name', 'email', 'phone_number')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'email', 'phone_number', 'profile_picture')}),
        (_('Role and Permissions'), {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        (_('Personal info'), {
            'fields': ('full_name', 'email', 'phone_number'),
        }),
        (_('Role and Permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    ordering = ('username',)


# Re-register Group and add a clearer name
admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_permissions_count')
    filter_horizontal = ('permissions',)
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = 'Number of Permissions' 