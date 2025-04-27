from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def abs_value(value):
    """Returns the absolute value of a number"""
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    """Divides the value by the argument"""
    try:
        value = float(value) 
        arg = float(arg)
        if arg:  # Avoid division by zero
            return value / arg
        return 0
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculates what percentage value is of total"""
    try:
        if total:
            return (float(value) / float(total)) * 100
        return 0
    except (ValueError, TypeError):
        return 0 