from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for ActivityLog model"""
    list_display = ('timestamp', 'user', 'action_type', 'content_type', 'object_id', 'ip_address')
    list_filter = ('action_type', 'timestamp', 'user', 'content_type')
    search_fields = ('user__username', 'change_summary', 'object_id')
    readonly_fields = ('timestamp', 'user', 'action_type', 'content_type', 'object_id', 
                      'change_summary', 'ip_address')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        # Prevent manual creation of logs
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing logs
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete logs
        return request.user.is_superuser 