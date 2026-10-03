from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


PAYMENT_METHODS = [
    ('cash', _('Cash')),
    ('mpesa', 'M-Pesa'),
    ('airtel', 'Airtel Money'),
    ('tigo', 'Tigo Pesa'),
    ('halotel', 'Halotel'),
    ('bank', _('Bank Transfer')),
    ('card', _('Card')),
    ('other', _('Other')),
]


class Category(models.Model):
    """Income or expense category — either system-wide default or user-specific."""

    CATEGORY_TYPES = [
        ('income', _('Income')),
        ('expense', _('Expense')),
        ('both', _('Both')),
    ]

    # null user = system/default category visible to all
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='categories')
    name = models.CharField(max_length=100, verbose_name=_('Category Name'))
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='both',
                                     verbose_name=_('Category Type'))
    icon = models.CharField(max_length=50, default='bi-tag',
                            help_text=_('Bootstrap Icon class name'),
                            verbose_name=_('Icon'))
    color = models.CharField(max_length=7, default='#6c757d',
                             help_text=_('Hex color code'),
                             verbose_name=_('Color'))
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        owner = 'Default' if self.user is None else self.user.username
        return f"{self.name} ({self.get_category_type_display()}) [{owner}]"


class Income(models.Model):
    """Records a single income transaction for a user."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Amount (TZS)'))
    source = models.CharField(max_length=200, verbose_name=_('Source / Payer'))
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes',
        verbose_name=_('Category')
    )
    account = models.ForeignKey(
        'accounts_wallet.Account', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incomes',
        help_text=_('Wallet/account this income was received into'),
        verbose_name=_('Account')
    )
    date = models.DateField(verbose_name=_('Date'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash',
                                      verbose_name=_('Payment Method'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    attachment = models.FileField(upload_to='income_attachments/%Y/%m/', null=True, blank=True,
                                  verbose_name=_('Attachment / Receipt'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
        ]
        verbose_name = _('Income')
        verbose_name_plural = _('Income Records')

    def __str__(self):
        return f"{self.source} — TSh {self.amount:,.0f} ({self.date})"


class Expense(models.Model):
    """Records a single expense transaction for a user."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Amount (TZS)'))
    description = models.CharField(max_length=300, verbose_name=_('Description'))
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses',
        verbose_name=_('Category')
    )
    account = models.ForeignKey(
        'accounts_wallet.Account', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='expenses',
        help_text=_('Wallet/account this expense was paid from'),
        verbose_name=_('Account')
    )
    date = models.DateField(verbose_name=_('Date'))
    time = models.TimeField(null=True, blank=True, verbose_name=_('Time'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash',
                                      verbose_name=_('Payment Method'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    receipt = models.FileField(upload_to='receipts/%Y/%m/', null=True, blank=True,
                               verbose_name=_('Receipt Upload'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
        ]
        verbose_name = _('Expense')
        verbose_name_plural = _('Expenses')

    def __str__(self):
        return f"{self.description} — TSh {self.amount:,.0f} ({self.date})"


class RecurringTransaction(models.Model):
    """Scheduled repeating income or expense."""

    TRANSACTION_TYPES = [
        ('income', _('Income')),
        ('expense', _('Expense')),
    ]
    FREQUENCIES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Amount (TZS)'))
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES,
                                        verbose_name=_('Transaction Type'))
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('Category')
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash',
                                      verbose_name=_('Payment Method'))
    frequency = models.CharField(max_length=10, choices=FREQUENCIES, verbose_name=_('Frequency'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    next_due_date = models.DateField(verbose_name=_('Next Due Date'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('End Date'))
    active = models.BooleanField(default=True, verbose_name=_('Active'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_due_date']
        indexes = [
            models.Index(fields=['user', 'active', 'next_due_date']),
        ]
        verbose_name = _('Recurring Transaction')
        verbose_name_plural = _('Recurring Transactions')

    def __str__(self):
        return f"{self.title} — {self.get_frequency_display()} — TSh {self.amount:,.0f}"
