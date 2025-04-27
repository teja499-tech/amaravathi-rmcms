from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from model_utils import FieldTracker


class User(AbstractUser):
    """
    Custom user model for the application.
    Extends Django's AbstractUser and adds custom fields.
    """
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
        VIEWER = 'VIEWER', _('Viewer')
    
    # Basic user information
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(
        max_length=20, 
        choices=Role.choices,
        default=Role.VIEWER
    )
    
    # Keep profile picture for avatar
    profile_picture = models.ImageField(upload_to='profile_pictures', blank=True, null=True)
    
    # Track field changes
    tracker = FieldTracker(fields=['role'])
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.full_name if self.full_name else self.username
    
    def save(self, *args, **kwargs):
        # If this is a new user (no ID yet) or role has changed
        is_new = self._state.adding
        
        super().save(*args, **kwargs)
        
        # Add user to the appropriate group based on role
        if is_new or self.tracker.has_changed('role'):
            self.groups.clear()  # Remove from all groups first
            if self.role:
                group, created = Group.objects.get_or_create(name=self.role)
                self.groups.add(group)


@receiver(post_save, sender=User)
def assign_user_to_group(sender, instance, created, **kwargs):
    """
    Signal to assign user to the appropriate group when saved.
    """
    # We'll handle this directly in the save method instead
    pass 