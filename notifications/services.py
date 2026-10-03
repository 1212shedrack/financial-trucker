"""
Notifications service — creates and manages in-app notifications.
"""
from notifications.models import Notification


def create_notification(user, notification_type, title, message):
    """Create and save a notification for a user."""
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
    )


def get_unread_count(user):
    """Return count of unread notifications for a user."""
    return Notification.objects.filter(user=user, is_read=False).count()


def send_budget_alerts(user):
    """Check all budgets and create notifications for warnings/exceeded."""
    from budgets.models import Budget
    budgets = Budget.objects.filter(user=user, period='monthly').select_related('category')
    for budget in budgets:
        if budget.is_exceeded:
            # Only send if no recent duplicate
            existing = Notification.objects.filter(
                user=user,
                notification_type='budget_exceeded',
                title__icontains=budget.category.name,
            ).order_by('-created_at').first()
            if not existing:
                create_notification(
                    user=user,
                    notification_type='budget_exceeded',
                    title=f'Budget Exceeded: {budget.category.name}',
                    message=(
                        f'You have exceeded your {budget.category.name} budget of '
                        f'TSh {budget.amount:,.0f}. '
                        f'Current spending: TSh {budget.spent_amount:,.0f}.'
                    ),
                )
        elif budget.is_warning:
            existing = Notification.objects.filter(
                user=user,
                notification_type='budget_warning',
                title__icontains=budget.category.name,
            ).order_by('-created_at').first()
            if not existing:
                create_notification(
                    user=user,
                    notification_type='budget_warning',
                    title=f'Budget Alert: {budget.category.name}',
                    message=(
                        f'You have used {budget.percentage_used}% of your '
                        f'{budget.category.name} budget. '
                        f'TSh {budget.remaining_amount:,.0f} remaining.'
                    ),
                )


def send_recurring_alerts(user):
    """Create notifications for recurring transactions due in the next 3 days."""
    from datetime import date, timedelta
    from transactions.models import RecurringTransaction
    today = date.today()
    upcoming = RecurringTransaction.objects.filter(
        user=user,
        active=True,
        next_due_date__range=[today, today + timedelta(days=3)],
    )
    for recurring in upcoming:
        existing = Notification.objects.filter(
            user=user,
            notification_type='recurring_due',
            title__icontains=recurring.title,
        ).order_by('-created_at').first()
        if not existing:
            create_notification(
                user=user,
                notification_type='recurring_due',
                title=f'Upcoming: {recurring.title}',
                message=(
                    f'Your recurring {recurring.get_transaction_type_display()} '
                    f'"{recurring.title}" of TSh {recurring.amount:,.0f} '
                    f'is due on {recurring.next_due_date}.'
                ),
            )


def check_goal_milestones(user):
    """Create notifications when goals reach 25%, 50%, 75%, 100%."""
    from goals.models import FinancialGoal
    goals = FinancialGoal.objects.filter(user=user, is_completed=False)
    milestones = [25, 50, 75, 100]
    for goal in goals:
        pct = goal.percentage_completed
        for milestone in milestones:
            if pct >= milestone:
                existing = Notification.objects.filter(
                    user=user,
                    notification_type='goal_milestone',
                    title__icontains=goal.name,
                    message__icontains=str(milestone),
                ).exists()
                if not existing:
                    msg = (
                        f'Congratulations! You have reached {milestone}% of your '
                        f'"{goal.name}" goal. '
                        f'TSh {goal.current_amount:,.0f} saved of TSh {goal.target_amount:,.0f}.'
                    )
                    if milestone == 100:
                        msg = f'🎉 Goal Completed! You have fully funded your "{goal.name}" goal!'
                    create_notification(
                        user=user,
                        notification_type='goal_milestone',
                        title=f'Goal Milestone: {goal.name}',
                        message=msg,
                    )
