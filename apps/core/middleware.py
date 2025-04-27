from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import resolve, reverse

class PermissionMiddleware:
    """
    Middleware to handle permission denied errors gracefully.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Process PermissionDenied exception and redirect to permission denied page with error message.
        """
        if isinstance(exception, PermissionDenied):
            # Get the current URL name
            try:
                url_name = resolve(request.path_info).url_name
                app_name = resolve(request.path_info).app_name
                full_name = f"{app_name}:{url_name}" if app_name else url_name
                
                # Create a user-friendly message
                model_name = None
                action = None
                
                if 'add' in url_name:
                    action = 'add'
                    model_name = url_name.replace('_add', '').replace('add_', '')
                elif 'edit' in url_name or 'update' in url_name:
                    action = 'edit'
                    model_name = url_name.replace('_edit', '').replace('edit_', '').replace('_update', '').replace('update_', '')
                elif 'delete' in url_name:
                    action = 'delete'
                    model_name = url_name.replace('_delete', '').replace('delete_', '')
                elif 'view' in url_name or 'detail' in url_name:
                    action = 'view'
                    model_name = url_name.replace('_view', '').replace('view_', '').replace('_detail', '').replace('detail_', '')
                else:
                    # Try to extract from URL parts
                    parts = url_name.split('_')
                    if len(parts) > 1:
                        model_name = parts[0]
                        action = parts[1]
                
                if model_name and action:
                    message = f"You don't have permission to {action} {model_name.replace('_', ' ')}."
                else:
                    message = "You don't have permission to access this page."
                
                # Instead of redirecting to dashboard, render the permission denied template
                from apps.core.views import permission_denied_view
                return permission_denied_view(request, message=message)
            except Exception:
                # Fallback message
                from apps.core.views import permission_denied_view
                return permission_denied_view(request, message="You don't have permission to access this page.") 