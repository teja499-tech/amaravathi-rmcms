from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Template filter to check if user belongs to a specific group
    
    Usage:
    {% if request.user|has_group:"Admin" %}
        <li><a href="{% url 'admin_panel' %}">Admin Panel</a></li>
    {% endif %}
    """
    if user.is_superuser:
        return True
        
    try:
        group = Group.objects.get(name=group_name)
        return group in user.groups.all()
    except Group.DoesNotExist:
        return False

@register.filter(name='has_any_group')
def has_any_group(user, group_names):
    """
    Template filter to check if user belongs to any of the specified groups
    
    Usage:
    {% if request.user|has_any_group:"Admin,Manager" %}
        <li><a href="{% url 'manage_users' %}">Manage Users</a></li>
    {% endif %}
    """
    if user.is_superuser:
        return True
        
    groups = [name.strip() for name in group_names.split(',')]
    return user.groups.filter(name__in=groups).exists()

@register.filter(name='can_access')
def can_access(user, permission_string):
    """
    Template filter to check if user has permission to access a feature
    
    Format: "app_label.permission_codename"
    
    Usage:
    {% if request.user|can_access:"customers.add_customer" %}
        <a href="{% url 'customer_add' %}" class="btn btn-primary">Add Customer</a>
    {% endif %}
    """
    if user.is_superuser:
        return True
    
    return user.has_perm(permission_string)

@register.simple_tag(takes_context=True)
def show_if_allowed(context, permission_type, model_name):
    """
    Template tag to conditionally show content based on user permissions
    
    Usage:
    {% show_if_allowed "add" "customer" %}
        <a href="{% url 'customer_add' %}" class="btn btn-primary">Add Customer</a>
    {% endshow_if_allowed %}
    """
    user = context['request'].user
    
    # Superusers can access everything
    if user.is_superuser:
        return True
    
    # Check if user has the specific permission
    permission_string = f"{model_name}.{permission_type}_{model_name}"
    if user.has_perm(permission_string):
        return True
    
    # Role-based common checks
    if permission_type == 'view':
        # All authenticated users can view
        return True
    
    # Check for specific role permissions
    if permission_type == 'add' or permission_type == 'change':
        # Admin and Manager can add/change anything
        if user.groups.filter(name__in=['Admin', 'Manager']).exists():
            return True
        
        # Accountant can add/change financial records
        if model_name in ['customerpayment', 'supplierpayment', 'expense', 'bankaccount', 
                         'transaction', 'ledgerentry', 'commitment']:
            if user.groups.filter(name='Accountant').exists():
                return True
        
        # Clerk can add/change basic records
        if permission_type == 'add' and model_name in ['customer', 'delivery', 'customerpayment', 
                                                      'supplier', 'purchase', 'expense']:
            if user.groups.filter(name='Clerk').exists():
                return True
    
    return False 