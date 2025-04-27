from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Template filter to check if user belongs to a specific group.
    
    Usage:
    {% if user|has_group:"Admin" %}
        Show admin content
    {% endif %}
    """
    try:
        group = Group.objects.get(name=group_name)
        return group in user.groups.all() or user.is_superuser
    except Group.DoesNotExist:
        return False

@register.filter(name='has_perm')
def has_perm(user, perm):
    """
    Template filter to check if user has a specific permission.
    
    Usage:
    {% if user|has_perm:"customer.view_customer" %}
        Show customer content
    {% endif %}
    """
    return user.has_perm(perm) or user.is_superuser

@register.simple_tag(takes_context=True)
def can_access(context, model_name, action):
    """
    Template tag to check if user has permission to perform action on model.
    
    Usage:
    {% can_access "customer" "view" as can_view_customer %}
    {% if can_view_customer %}
        Show customer content
    {% endif %}
    """
    user = context['request'].user
    if not user.is_authenticated:
        return False
        
    if user.is_superuser:
        return True
        
    perm = f"{model_name}.{action}_{model_name}"
    return user.has_perm(perm) 