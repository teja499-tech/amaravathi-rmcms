import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils.module_loading import import_string
from django.conf import settings
from .models import ActivityLog
import inspect
import logging

logger = logging.getLogger(__name__)

# List of models to exclude from tracking
EXCLUDED_MODELS = getattr(settings, 'ACTIVITY_LOG_EXCLUDED_MODELS', [
    'auth.permission',
    'admin.logentry',
    'sessions.session',
    'contenttypes.contenttype',
    'core.activitylog'
])

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_change_summary(instance, created=False):
    """Generate a summary of changes to the instance"""
    if created:
        return f"Created {instance._meta.model_name}"
    
    # Try to get the changed fields
    if hasattr(instance, 'get_dirty_fields'):
        dirty_fields = instance.get_dirty_fields()
        if dirty_fields:
            fields_list = ", ".join(dirty_fields.keys())
            return f"Updated fields: {fields_list}"
    
    return f"Updated {instance._meta.model_name}"

@receiver(post_save)
def track_model_save(sender, instance, created, **kwargs):
    """Track model creation and updates"""
    # Skip if model is in excluded list
    model_label = f"{instance._meta.app_label}.{instance._meta.model_name}"
    if model_label in EXCLUDED_MODELS:
        return
    
    # Skip ActivityLog itself to avoid infinite recursion
    if instance.__class__.__name__ == 'ActivityLog':
        return
    
    try:
        # Get current user from thread locals if available
        user = None
        try:
            from threading import local
            _thread_locals = local()
            user = getattr(_thread_locals, 'user', None)
        except (ImportError, AttributeError):
            pass
        
        # Create activity log entry
        content_type = ContentType.objects.get_for_model(instance)
        action_type = 'CREATE' if created else 'UPDATE'
        
        # Get change summary
        change_summary = get_change_summary(instance, created)
        
        ActivityLog.objects.create(
            user=user,
            action_type=action_type,
            content_type=content_type,
            object_id=str(instance.pk),
            change_summary=change_summary
        )
    except Exception as e:
        logger.error(f"Error tracking model save: {e}")

@receiver(post_delete)
def track_model_delete(sender, instance, **kwargs):
    """Track model deletion"""
    # Skip if model is in excluded list
    model_label = f"{instance._meta.app_label}.{instance._meta.model_name}"
    if model_label in EXCLUDED_MODELS:
        return
    
    try:
        # Get current user from thread locals if available
        user = None
        try:
            from threading import local
            _thread_locals = local()
            user = getattr(_thread_locals, 'user', None)
        except (ImportError, AttributeError):
            pass
        
        # Create activity log entry
        content_type = ContentType.objects.get_for_model(instance)
        
        # Create a summary with the object's string representation
        summary = f"Deleted {instance._meta.model_name}: {str(instance)}"
        
        ActivityLog.objects.create(
            user=user,
            action_type='DELETE',
            content_type=content_type,
            object_id=str(instance.pk),
            change_summary=summary
        )
    except Exception as e:
        logger.error(f"Error tracking model delete: {e}")

@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track user login events"""
    try:
        ip_address = get_client_ip(request) if request else None
        
        ActivityLog.objects.create(
            user=user,
            action_type='LOGIN',
            change_summary=f"User {user.username} logged in",
            ip_address=ip_address
        )
    except Exception as e:
        logger.error(f"Error tracking user login: {e}")

@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track user logout events"""
    try:
        # User might be None if session was already expired
        if not user:
            return
            
        ip_address = get_client_ip(request) if request else None
        
        ActivityLog.objects.create(
            user=user,
            action_type='LOGOUT',
            change_summary=f"User {user.username} logged out",
            ip_address=ip_address
        )
    except Exception as e:
        logger.error(f"Error tracking user logout: {e}")

class ActivityLogMiddleware:
    """Middleware to capture the current user for activity logging"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Store user in thread local storage
        if hasattr(request, 'user') and request.user.is_authenticated:
            from threading import local
            _thread_locals = local()
            _thread_locals.user = request.user
            
        response = self.get_response(request)
        return response 