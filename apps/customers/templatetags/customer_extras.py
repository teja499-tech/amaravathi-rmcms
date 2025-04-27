from django import template

register = template.Library()

@register.filter
def endswith(value, arg):
    """
    Check if the value ends with the specified string
    """
    if not value:
        return False
    return value.endswith(arg)

@register.filter
def lower(value):
    """
    Convert string to lowercase
    """
    if not value:
        return ""
    return value.lower()

@register.filter
def mul(value, arg):
    """
    Multiply the value by the argument
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value 