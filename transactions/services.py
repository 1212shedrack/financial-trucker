"""
Transaction business-logic services.
All monetary computations use Decimal — never float.
"""
from decimal import Decimal
from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone


def get_user_income(user, date_from=None, date_to=None):
    from transactions.models import Income
    qs = Income.objects.filter(user=user).select_related('category')
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def get_user_expenses(user, date_from=None, date_to=None):
    from transactions.models import Expense
    qs = Expense.objects.filter(user=user).select_related('category')
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def get_total_income(user, date_from=None, date_to=None):
    qs = get_user_income(user, date_from, date_to)
    result = qs.aggregate(total=Sum('amount'))['total']
    return result or Decimal('0')


def get_total_expenses(user, date_from=None, date_to=None):
    qs = get_user_expenses(user, date_from, date_to)
    result = qs.aggregate(total=Sum('amount'))['total']
    return result or Decimal('0')


def get_net_savings(user, date_from=None, date_to=None):
    return get_total_income(user, date_from, date_to) - get_total_expenses(user, date_from, date_to)


def get_upcoming_recurring(user, days=7):
    """Return recurring transactions due in the next `days` days."""
    from transactions.models import RecurringTransaction
    today = date.today()
    return RecurringTransaction.objects.filter(
        user=user,
        active=True,
        next_due_date__range=[today, today + timedelta(days=days)],
    ).select_related('category').order_by('next_due_date')


def advance_recurring_due_date(recurring):
    """Advance next_due_date based on frequency."""
    freq = recurring.frequency
    current = recurring.next_due_date
    if freq == 'daily':
        recurring.next_due_date = current + timedelta(days=1)
    elif freq == 'weekly':
        recurring.next_due_date = current + timedelta(weeks=1)
    elif freq == 'monthly':
        month = current.month + 1
        year = current.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(current.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                                 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        recurring.next_due_date = current.replace(year=year, month=month, day=day)
    elif freq == 'yearly':
        try:
            recurring.next_due_date = current.replace(year=current.year + 1)
        except ValueError:
            recurring.next_due_date = current.replace(year=current.year + 1, day=28)
    recurring.save(update_fields=['next_due_date'])


def validate_upload_file(f):
    """Validate uploaded file size and type. Raises ValueError on failure."""
    from django.conf import settings
    if f.size > settings.MAX_UPLOAD_SIZE:
        raise ValueError(f'File size exceeds 5MB limit.')
    allowed = settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_DOCUMENT_TYPES
    content_type = getattr(f, 'content_type', '')
    if content_type and content_type not in allowed:
        raise ValueError(f'File type "{content_type}" is not allowed.')
