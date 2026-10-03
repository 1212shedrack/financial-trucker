import logging
from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Sum

from analytics.services import FinancialAnalyticsService
from transactions.services import get_upcoming_recurring
from budgets.models import Budget
from goals.models import FinancialGoal
from notifications.models import Notification
from transactions.models import Income, Expense
from accounts_wallet.models import Account
from .models import AuditLog

logger = logging.getLogger('core')


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action, description, request=None):
    ip = get_client_ip(request) if request else None
    AuditLog.objects.create(user=user, action=action, description=description, ip_address=ip)


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing.html')


def switch_language_view(request):
    """Switch user language preference (English vs Swahili)."""
    from django.conf import settings
    from django.utils import translation
    lang_code = request.GET.get('lang', 'en')
    if lang_code in ['en', 'sw']:
        translation.activate(lang_code)
        if hasattr(request, 'session'):
            request.session['_language'] = lang_code
        redirect_to = request.META.get('HTTP_REFERER', '/dashboard/')
        response = redirect(redirect_to)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
        return response
    return redirect('/dashboard/')



@login_required
def dashboard_view(request):
    user = request.user
    today = timezone.now().date()

    transaction_type, period, date_from, date_to = get_dashboard_filters(request)

    service = FinancialAnalyticsService(user)
    summary = service.get_summary(
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
    )
    monthly_trends = service.get_monthly_trends(
        months=12,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
    )
    category_breakdown = service.get_expense_by_category(date_from=date_from, date_to=date_to)
    if transaction_type == 'income':
        category_breakdown = []
    insights = service.generate_insights()

    recent_income = list(Income.objects.filter(user=user, date__gte=date_from, date__lte=date_to).select_related('category').order_by('-date', '-created_at')[:5])
    recent_expenses = list(Expense.objects.filter(user=user, date__gte=date_from, date__lte=date_to).select_related('category').order_by('-date', '-created_at')[:5])
    if transaction_type == 'income':
        recent_expenses = []
    elif transaction_type == 'expense':
        recent_income = []

    recent_transactions = []
    for item in recent_income:
        recent_transactions.append({'type': 'income', 'obj': item})
    for item in recent_expenses:
        recent_transactions.append({'type': 'expense', 'obj': item})
    recent_transactions.sort(key=lambda x: (x['obj'].date, x['obj'].created_at), reverse=True)
    recent_transactions = recent_transactions[:10]

    budgets = Budget.objects.filter(user=user).select_related('category')
    goals = FinancialGoal.objects.filter(user=user, is_completed=False).order_by('-created_at')[:5]
    upcoming_recurring = get_upcoming_recurring(user, days=7)
    notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]

    active_accounts = Account.objects.filter(user=user, is_active=True).with_current_balance()
    total_wallet_balance = sum(acc.current_balance for acc in active_accounts)

    context = {
        'summary': summary,
        'monthly_trends': monthly_trends,
        'category_breakdown': category_breakdown,
        'insights': insights,
        'recent_transactions': recent_transactions,
        'budgets': budgets,
        'goals': goals,
        'upcoming_recurring': upcoming_recurring,
        'notifications': notifications,
        'type': transaction_type,
        'period': period,
        'range_param': period,
        'date_from': date_from,
        'date_to': date_to,
        'today': today,
        'total_balance': total_wallet_balance,
        'net_savings': Decimal(str(summary['net_savings'])),
        'total_income': Decimal(str(summary['total_income'])),
        'total_expenses': Decimal(str(summary['total_expenses'])),
        'savings_rate': summary['savings_rate'],
        'avg_daily_spending': summary['avg_daily_spending'],
        'selected_type': transaction_type,
        'selected_period': period,
        'range_options': [
            ('Today', 'today'),
            ('This Week', 'week'),
            ('This Month', 'month'),
            ('This Year', 'year'),
            ('Custom Range', 'custom'),
        ],
    }
    return render(request, 'core/dashboard.html', context)


def _get_date_range(range_param, request=None):
    """Resolve a named range or custom dates into (date_from, date_to)."""
    today = timezone.now().date()
    if range_param == 'today':
        return today, today
    elif range_param == 'week':
        week_start = today - timedelta(days=today.weekday())
        return week_start, today
    elif range_param == 'month':
        return today.replace(day=1), today
    elif range_param == 'last_month':
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    elif range_param == 'year':
        return today.replace(month=1, day=1), today
    elif range_param == 'custom':
        request = request or type('RequestStub', (), {'GET': {}})()
        try:
            date_from = date.fromisoformat(request.GET.get('start_date') or request.GET.get('date_from', str(today.replace(day=1))))
            date_to = date.fromisoformat(request.GET.get('end_date') or request.GET.get('date_to', str(today)))
            if date_to < date_from:
                date_from, date_to = date_to, date_from
            return date_from, date_to
        except (ValueError, TypeError):
            return today.replace(day=1), today
    else:
        return today.replace(day=1), today


def get_dashboard_filters(request):
    """Normalize and validate dashboard GET filters for type/period/date range."""
    transaction_type = (request.GET.get('type', 'all') or 'all').lower()
    if transaction_type not in {'all', 'income', 'expense'}:
        transaction_type = 'all'

    period = (request.GET.get('period', request.GET.get('range', 'month')) or 'month').lower()
    if period not in {'today', 'week', 'month', 'year', 'custom'}:
        period = 'month'

    if period == 'custom':
        date_from, date_to = _get_date_range(period, request)
    else:
        date_from, date_to = _get_date_range(period, request)

    return transaction_type, period, date_from, date_to


def handler404(request, exception=None):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)
