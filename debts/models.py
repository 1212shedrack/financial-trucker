"""
Debt and Loan Management Models.
Tracks debts owed by the user (loans) and debts owed to the user (receivables).
"""
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


DEBT_TYPES = [
    ('loan', _('Loan (I Owe)')),
    ('receivable', _('Receivable (Owed to Me)')),
]

DEBT_STATUS = [
    ('active', _('Active')),
    ('paid', _('Paid Off')),
    ('overdue', _('Overdue')),
    ('partial', _('Partially Paid')),
]


class Debt(models.Model):
    """A loan or debt record. Tracks amounts
    owed to/from a person or institution."""

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE, related_name='debts')
    debt_type = models.CharField(
        max_length=20, choices=DEBT_TYPES,
        default='loan', verbose_name=_('Debt Type'))
    name = models.CharField(max_length=200,
                            help_text=_('Person or institution name'),
                            verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    principal_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text=_('Original loan or debt amount'),
        verbose_name=_('Principal Amount (TZS)')
    )
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        help_text=_('Annual interest rate as'
                    'percentage (e.g. 12.5 for 12.5%)'),
        verbose_name=_('Interest Rate (% p.a.)')
    )
    start_date = models.DateField(verbose_name=_('Start Date'))
    due_date = models.DateField(null=True,
                                blank=True, verbose_name=_('Due Date'))
    status = models.CharField(max_length=20,
                              choices=DEBT_STATUS, default='active',
                              verbose_name=_('Status'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Debt')
        verbose_name_plural = _('Debts')

    def __str__(self):
        label = 'Loan' if self.debt_type == 'loan' else 'Receivable'
        return f"{label}: {self.name} — TSh {self.principal_amount:,.0f}"

    @property
    def total_paid(self):
        return self.repayments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')

    @property
    def remaining_balance(self):
        return max(self.principal_amount - self.total_paid, Decimal('0'))

    @property
    def percentage_paid(self):
        if self.principal_amount == 0:
            return 0
        pct = int((self.total_paid / self.principal_amount) * 100)
        return min(pct, 100)

    @property
    def is_overdue(self):
        from django.utils import timezone
        if not self.due_date:
            return False
        return self.due_date < timezone.now().date() and self.remaining_balance > 0


class DebtRepayment(models.Model):
    """A single repayment/payment made against a debt."""

    debt = models.ForeignKey(Debt, on_delete=models.CASCADE,
                             related_name='repayments')
    amount = models.DecimalField(max_digits=15, decimal_places=2,
                                 verbose_name=_('Amount (TZS)'))
    date = models.DateField(verbose_name=_('Date'))
    payment_method = models.CharField(max_length=20, default='cash',
                                      verbose_name=_('Payment Method'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = _('Debt Repayment')
        verbose_name_plural = _('Debt Repayments')

    def __str__(self):
        return f"TSh {self.amount:,.0f} → {self.debt.name} on {self.date}"
