from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class BaseModel(models.Model):
    """
    Abstract base model that provides common fields and methods.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class DatabaseConnectionTest(models.Model):
    """
    Dummy model to test database connection.
    This model can be safely removed after confirming the connection works.
    """
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.created_at}"


class ActivityLog(models.Model):
    """
    Model to track user actions for audit purposes.
    """
    ACTION_TYPES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='activities',
        verbose_name=_('User')
    )
    action_type = models.CharField(
        max_length=10, 
        choices=ACTION_TYPES,
        verbose_name=_('Action Type')
    )
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        verbose_name=_('Content Type')
    )
    object_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    change_summary = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('Change Summary')
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name=_('IP Address')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action_type']),
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        if self.content_type:
            return f"{self.get_action_type_display()} - {self.content_type.model} - {self.user}"
        return f"{self.get_action_type_display()} - {self.user}"
    
    @property
    def action_icon(self):
        """Return an icon class based on the action type"""
        icons = {
            'CREATE': 'bi bi-plus-circle',
            'UPDATE': 'bi bi-pencil',
            'DELETE': 'bi bi-trash',
            'LOGIN': 'bi bi-box-arrow-in-right',
            'LOGOUT': 'bi bi-box-arrow-right',
        }
        return icons.get(self.action_type, 'bi bi-question-circle')
        
    @property
    def object_name(self):
        """Return a friendly name for the affected object"""
        if not self.content_type:
            return None
            
        if hasattr(self.content_object, '__str__'):
            return str(self.content_object)
        else:
            return f"{self.content_type.model}#{self.object_id}" 