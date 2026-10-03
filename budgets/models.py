from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Budget(models.Model):
    """Monthly/weekly/yearly spending budget for a category."""

    PERIODS = [
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
        ('custom', _('Custom')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey('transactions.Category', on_delete=models.CASCADE,
                                 related_name='budgets', verbose_name=_('Category'))
    amount = models.DecimalField(max_digits=15, decimal_places=2,
                                 verbose_name=_('Budget Limit (TZS)'))
    period = models.CharField(max_length=10, choices=PERIODS, default='monthly',
                              verbose_name=_('Period'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('End Date (Custom)'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'period'])]
        verbose_name = _('Budget')
        verbose_name_plural = _('Budgets')

    def __str__(self):
        return f"{self.category.name} budget — TSh {self.amount:,.0f} ({self.get_period_display()})"

    @property
    def spent_amount(self):
        from transactions.models import Expense
        from django.db.models import Sum

        qs = Expense.objects.filter(user=self.user, category=self.category)
        today = timezone.now().date()

        if self.period == 'monthly':
            qs = qs.filter(date__year=self.start_date.year, date__month=self.start_date.month)
        elif self.period == 'weekly':
            week_end = self.start_date + timedelta(days=6)
            qs = qs.filter(date__range=[self.start_date, week_end])
        elif self.period == 'yearly':
            qs = qs.filter(date__year=self.start_date.year)
        elif self.period == 'custom' and self.end_date:
            qs = qs.filter(date__range=[self.start_date, self.end_date])

        result = qs.aggregate(total=Sum('amount'))['total']
        return result or Decimal('0')

    @property
    def remaining_amount(self):
        return self.amount - self.spent_amount

    @property
    def percentage_used(self):
        if self.amount == 0:
            return 0
        pct = int((self.spent_amount / self.amount) * 100)
        return min(pct, 100)

    @property
    def is_warning(self):
        return 80 <= self.percentage_used < 100

    @property
    def is_exceeded(self):
        return self.spent_amount > self.amount

    @property
    def status_class(self):
        if self.is_exceeded:
            return 'danger'
        if self.is_warning:
            return 'warning'
        return 'success'
