from notifications.models import Notification


def global_context(request):
    """Inject global variables into every template context."""
    context = {
        'currency_symbol': 'TSh',
        'default_currency': 'TZS',
    }
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        context['unread_notifications_count'] = unread_count
        try:
            context['user_profile'] = request.user.profile
        except Exception:
            context['user_profile'] = None
    return context
