from django.urls import reverse
from django.conf import settings
from django.db.models import Sum
from apps.core.decorators import _check_role_based_permission

def url_variables(request):
    """
    Adds commonly used URLs to the template context.
    """
    return {
        'DASHBOARD_URL': reverse('dashboard'),
        'LOGIN_URL': settings.LOGIN_URL,
        'LOGOUT_URL': reverse('logout'),
    }

def user_roles(request):
    """
    Adds user role information to the template context to manage menu visibility based on permissions.
    """
    context = {
        'is_admin': False,
        'is_manager': False,
        'is_accountant': False,
        'is_clerk': False,
        'can_view_customer': False,
        'can_add_customer': False,
        'can_change_customer': False,
        'can_delete_customer': False,
        'can_view_delivery': False,
        'can_add_delivery': False,
        'can_change_delivery': False,
        'can_delete_delivery': False,
        'can_view_payment': False,
        'can_add_payment': False,
        'can_change_payment': False,
        'can_delete_payment': False,
        'can_view_supplier': False,
        'can_add_supplier': False,
        'can_change_supplier': False,
        'can_delete_supplier': False,
        'can_view_purchase': False,
        'can_add_purchase': False,
        'can_change_purchase': False,
        'can_delete_purchase': False,
        'can_view_supplier_payment': False,
        'can_add_supplier_payment': False,
        'can_change_supplier_payment': False,
        'can_delete_supplier_payment': False,
        'can_view_expense': False,
        'can_add_expense': False,
        'can_change_expense': False,
        'can_delete_expense': False,
        'can_view_expense_category': False,
        'can_add_expense_category': False,
        'can_change_expense_category': False,
        'can_delete_expense_category': False,
        'can_view_vehicle': False,
        'can_add_vehicle': False,
        'can_change_vehicle': False,
        'can_delete_vehicle': False,
        'can_view_employee': False,
        'can_add_employee': False,
        'can_change_employee': False,
        'can_delete_employee': False,
        'can_view_salary': False,
        'can_add_salary': False,
        'can_change_salary': False,
        'can_delete_salary': False,
        'can_view_commitment': False,
        'can_add_commitment': False,
        'can_change_commitment': False,
        'can_delete_commitment': False,
        'can_view_bank_account': False,
        'can_add_bank_account': False,
        'can_change_bank_account': False,
        'can_delete_bank_account': False,
        'can_view_transaction': False,
        'can_add_transaction': False,
        'can_change_transaction': False,
        'can_delete_transaction': False,
    }
    
    user = request.user
    
    if not user.is_authenticated:
        return context
    
    # Get user groups
    user_groups = list(user.groups.values_list('name', flat=True))
    
    # Set role flags
    context['is_admin'] = user.is_superuser or 'Admin' in user_groups
    context['is_manager'] = context['is_admin'] or 'Manager' in user_groups
    context['is_accountant'] = context['is_manager'] or 'Accountant' in user_groups
    context['is_clerk'] = context['is_accountant'] or 'Clerk' in user_groups
    
    # Set permissions based on role
    models = [
        'customer', 'delivery', 'customerpayment', 'supplier', 'purchase', 
        'supplierpayment', 'expense', 'expensecategory', 'vehicle', 
        'employee', 'salary', 'commitment', 'bankaccount', 'transaction'
    ]
    
    actions = ['view', 'add', 'change', 'delete']
    
    for model in models:
        for action in actions:
            permission_key = f'can_{action}_{model}'
            if model == 'customerpayment':
                context_key = f'can_{action}_payment'
            elif model == 'supplierpayment':
                context_key = f'can_{action}_supplier_payment'
            elif model == 'expensecategory':
                context_key = f'can_{action}_expense_category'
            elif model == 'bankaccount':
                context_key = f'can_{action}_bank_account'
            else:
                context_key = permission_key
                
            context[context_key] = _check_role_based_permission(user, model, action)
    
    return context 

def permissions(request):
    """
    Context processor that adds permission flags to the template context.
    """
    if not request.user.is_authenticated:
        return {}
    
    # Build a dictionary of permissions for common models and actions
    perms = {}
    
    # List of models to check permissions for
    models = [
        'customer', 'delivery', 'customerpayment',
        'supplier', 'purchase', 'supplierpayment',
        'expense', 'expensecategory', 'vehicle',
        'employee', 'salary', 'commitment',
        'bankaccount', 'transaction'
    ]
    
    # List of actions to check
    actions = ['view', 'add', 'change', 'delete']
    
    # Check permissions for each model and action
    for model in models:
        perms[model] = {}
        for action in actions:
            perm_key = f"{action}_{model}"
            perms[model][action] = _check_role_based_permission(request.user, model, action)
    
    # Add permissions to template context
    context = {
        'perms': perms,
        'is_admin': request.user.groups.filter(name='Admin').exists() or request.user.is_superuser,
        'is_manager': request.user.groups.filter(name='Manager').exists(),
        'is_accountant': request.user.groups.filter(name='Accountant').exists(),
        'is_clerk': request.user.groups.filter(name='Clerk').exists(),
    }
    
    return context 