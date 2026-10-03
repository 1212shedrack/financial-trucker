from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    """In-app notification for a user."""

    NOTIFICATION_TYPES = [
        ('budget_warning', 'Budget Warning'),
        ('budget_exceeded', 'Budget Exceeded'),
        ('recurring_due', 'Recurring Transaction Due'),
        ('goal_milestone', 'Goal Milestone Reached'),
        ('unusual_spending', 'Unusual Spending Detected'),
        ('report_ready', 'Report Available'),
        ('info', 'Information'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        status = 'Read' if self.is_read else 'Unread'
        return f"[{status}] {self.user.username}: {self.title}"

    @property
    def icon(self):
        icons = {
            'budget_warning': 'bi-exclamation-triangle',
            'budget_exceeded': 'bi-x-circle',
            'recurring_due': 'bi-arrow-repeat',
            'goal_milestone': 'bi-trophy',
            'unusual_spending': 'bi-graph-up-arrow',
            'report_ready': 'bi-file-earmark-text',
            'info': 'bi-info-circle',
        }
        return icons.get(self.notification_type, 'bi-bell')

    @property
    def badge_class(self):
        classes = {
            'budget_warning': 'warning',
            'budget_exceeded': 'danger',
            'recurring_due': 'info',
            'goal_milestone': 'success',
            'unusual_spending': 'danger',
            'report_ready': 'primary',
            'info': 'secondary',
        }
        return classes.get(self.notification_type, 'secondary')
