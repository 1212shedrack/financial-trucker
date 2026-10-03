"""
Account & Wallet Management Models.
Tracks Cash, Bank, and Mobile Money accounts and transfers between them.
"""
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


ACCOUNT_TYPES = [
    ('cash', _('Cash')),
    ('bank', _('Bank Account')),
    ('mpesa', 'M-Pesa'),
    ('airtel', 'Airtel Money'),
    ('tigo', 'Tigo Pesa'),
    ('halotel', 'Halotel'),
    ('savings', _('Savings Account')),
    ('other', _('Other')),
]

ACCOUNT_TYPE_ICONS = {
    'cash': 'bi-cash-stack',
    'bank': 'bi-bank',
    'mpesa': 'bi-phone',
    'airtel': 'bi-phone-fill',
    'tigo': 'bi-phone-vibrate',
    'halotel': 'bi-reception-4',
    'savings': 'bi-piggy-bank',
    'other': 'bi-wallet2',
}


class AccountQuerySet(models.QuerySet):
    def with_current_balance(self):
        from transactions.models import Income, Expense
        from django.db.models import OuterRef, Subquery, Sum, DecimalField, F
        from django.db.models.functions import Coalesce

        income_sub = Income.objects.filter(account=OuterRef('pk')).values('account').annotate(total=Sum('amount')).values('total')
        expense_sub = Expense.objects.filter(account=OuterRef('pk')).values('account').annotate(total=Sum('amount')).values('total')
        transfers_out_sub = Transfer.objects.filter(from_account=OuterRef('pk')).values('from_account').annotate(total=Sum('amount')).values('total')
        transfers_in_sub = Transfer.objects.filter(to_account=OuterRef('pk')).values('to_account').annotate(total=Sum('amount')).values('total')

        return self.annotate(
            annotated_balance=F('opening_balance')
            + Coalesce(Subquery(income_sub, output_field=DecimalField()), Decimal('0'))
            - Coalesce(Subquery(expense_sub, output_field=DecimalField()), Decimal('0'))
            + Coalesce(Subquery(transfers_in_sub, output_field=DecimalField()), Decimal('0'))
            - Coalesce(Subquery(transfers_out_sub, output_field=DecimalField()), Decimal('0'))
        )


class AccountManager(models.Manager):
    def get_queryset(self):
        return AccountQuerySet(self.model, using=self._db)

    def with_current_balance(self):
        return self.get_queryset().with_current_balance()


class Account(models.Model):
    """A financial account or wallet owned by the user."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=150,
                            help_text=_('e.g. "Azania Bank", "My M-Pesa"'),
                            verbose_name=_('Account Name'))
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='cash',
                                    verbose_name=_('Account Type'))
    account_number = models.CharField(max_length=100, blank=True,
                                      help_text=_('Last 4 digits or identifier'),
                                      verbose_name=_('Account Number'))
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'),
                                          verbose_name=_('Opening Balance (TZS)'))
    color = models.CharField(max_length=7, default='#0d6efd',
                             help_text=_('Hex color for UI display'),
                             verbose_name=_('Color'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    class Meta:
        ordering = ['account_type', 'name']
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        unique_together = [('user', 'name')]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    @property
    def icon(self):
        return ACCOUNT_TYPE_ICONS.get(self.account_type, 'bi-wallet2')

    @property
    def current_balance(self):
        if hasattr(self, 'annotated_balance') and self.annotated_balance is not None:
            return Decimal(str(self.annotated_balance))

        from transactions.models import Income, Expense

        income_total = Income.objects.filter(
            user=self.user, account=self
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        expense_total = Expense.objects.filter(
            user=self.user, account=self
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        transfers_out = Transfer.objects.filter(
            from_account=self
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        transfers_in = Transfer.objects.filter(
            to_account=self
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        return self.opening_balance + income_total - expense_total + transfers_in - transfers_out

    @property
    def available_balance(self):
        """Alias used for transfer validation and UI display."""
        return self.current_balance


class Transfer(models.Model):
    """A transfer of funds between two accounts. Never counts as income or expense."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers')
    from_account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='outgoing_transfers',
        verbose_name=_('From Account')
    )
    to_account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='incoming_transfers',
        verbose_name=_('To Account')
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Amount (TZS)'))
    date = models.DateField(verbose_name=_('Date'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = _('Transfer')
        verbose_name_plural = _('Transfers')

    def __str__(self):
        return f"TSh {self.amount:,.0f}: {self.from_account.name} → {self.to_account.name} ({self.date})"

    def clean(self):
        from django.core.exceptions import ValidationError
        from_account_id = self.from_account_id
        to_account_id = self.to_account_id

        if from_account_id is not None and to_account_id is not None and from_account_id == to_account_id:
            raise ValidationError(_('Cannot transfer to and from the same account.'))
        if self.amount is not None and self.amount <= Decimal('0'):
            raise ValidationError(_('Transfer amount must be greater than zero.'))
        if from_account_id is not None and self.from_account and not self.from_account.is_active:
            raise ValidationError(_('The source account is inactive and cannot be used for transfers.'))
        if to_account_id is not None and self.to_account and not self.to_account.is_active:
            raise ValidationError(_('The destination account is inactive and cannot receive transfers.'))
        if from_account_id is not None and to_account_id is not None and self.from_account and self.to_account and self.from_account.user_id != self.to_account.user_id:
            raise ValidationError(_('Transfers must be between accounts in the same user wallet.'))
        if from_account_id is not None and self.from_account and self.amount is not None and self.amount > self.from_account.current_balance:
            raise ValidationError(_('Transfer amount exceeds the available balance in the source account.'))
