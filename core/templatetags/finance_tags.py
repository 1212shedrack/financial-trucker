from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def currency(value, symbol='TSh'):
    """Format a Decimal value as TZS currency. E.g. 1500000 → TSh 1,500,000"""
    try:
        amount = Decimal(str(value))
        formatted = f"{amount:,.0f}"
        return f"{symbol} {formatted}"
    except (InvalidOperation, TypeError, ValueError):
        return f"{symbol} 0"


@register.filter
def percentage(value, decimals=1):
    """Format a number as percentage. E.g. 0.75 → 75.0%"""
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "0%"


@register.filter
def absolute_value(value):
    """Return absolute value of a number."""
    try:
        return abs(Decimal(str(value)))
    except (InvalidOperation, TypeError):
        return value


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (InvalidOperation, TypeError):
        return 0


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (InvalidOperation, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divide value by arg, return 0 if arg is 0."""
    try:
        arg = Decimal(str(arg))
        if arg == 0:
            return 0
        return Decimal(str(value)) / arg
    except (InvalidOperation, TypeError):
        return 0
