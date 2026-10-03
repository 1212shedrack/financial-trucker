from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class FinancialGoal(models.Model):
    """A savings goal the user wants to achieve."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=200, verbose_name=_('Goal Name'))
    description = models.TextField(blank=True, verbose_name=_('Description / Purpose'))
    target_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                        verbose_name=_('Target Amount (TZS)'))
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'),
                                         verbose_name=_('Currently Saved'))
    target_date = models.DateField(null=True, blank=True, verbose_name=_('Target Date'))
    category = models.CharField(max_length=100, blank=True, verbose_name=_('Category'))
    is_completed = models.BooleanField(default=False, verbose_name=_('Completed'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Financial Goal')
        verbose_name_plural = _('Financial Goals')

    def __str__(self):
        return f"{self.name} — {self.percentage_completed}% complete"

    @property
    def remaining_amount(self):
        remaining = self.target_amount - self.current_amount
        return max(remaining, Decimal('0'))

    @property
    def percentage_completed(self):
        if self.target_amount == 0:
            return 0
        pct = int((self.current_amount / self.target_amount) * 100)
        return min(pct, 100)

    @property
    def days_remaining(self):
        if not self.target_date:
            return None
        delta = self.target_date - timezone.now().date()
        return delta.days

    @property
    def required_monthly_saving(self):
        if not self.target_date:
            return None
        days = self.days_remaining
        if days is None or days <= 0:
            return self.remaining_amount
        months = max(Decimal(str(days)) / Decimal('30'), Decimal('1'))
        return self.remaining_amount / months

    @property
    def status_class(self):
        pct = self.percentage_completed
        if pct >= 100:
            return 'success'
        if pct >= 50:
            return 'info'
        return 'warning'


class GoalContribution(models.Model):
    """A single contribution (deposit) made toward a savings goal."""

    goal = models.ForeignKey(FinancialGoal, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Amount (TZS)'))
    date = models.DateField(verbose_name=_('Date'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = _('Goal Contribution')
        verbose_name_plural = _('Goal Contributions')

    def __str__(self):
        return f"TSh {self.amount:,.0f} → {self.goal.name} on {self.date}"
