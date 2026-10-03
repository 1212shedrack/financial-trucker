from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Category, Income, Expense, RecurringTransaction


BS = {'class': 'form-control'}
BS_SELECT = {'class': 'form-select'}
BS_DATE = {'class': 'form-control', 'type': 'date'}
BS_TIME = {'class': 'form-control', 'type': 'time'}
BS_NUM = {'class': 'form-control', 'min': '0', 'step': '1'}


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={**BS, 'placeholder': _('Category name')}),
            'category_type': forms.Select(attrs=BS_SELECT),
            'icon': forms.TextInput(attrs={**BS, 'placeholder': 'bi-tag'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
        }
        labels = {
            'name': _('Category Name'),
            'category_type': _('Category Type'),
            'icon': _('Icon'),
            'color': _('Color'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        category_type = self.data.get('category_type', 'both')
        qs = Category.objects.filter(user=self.user, name__iexact=name, category_type=category_type)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('You already have a category with this name.'))
        return name


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['amount', 'source', 'category', 'date', 'payment_method', 'description', 'notes', 'attachment']
        widgets = {
            'amount': forms.NumberInput(attrs={**BS_NUM, 'placeholder': '0'}),
            'source': forms.TextInput(attrs={**BS, 'placeholder': _('e.g. Monthly Salary')}),
            'category': forms.Select(attrs=BS_SELECT),
            'date': forms.DateInput(attrs=BS_DATE),
            'payment_method': forms.Select(attrs=BS_SELECT),
            'description': forms.Textarea(attrs={**BS, 'rows': 2, 'placeholder': _('Brief description')}),
            'notes': forms.Textarea(attrs={**BS, 'rows': 2, 'placeholder': _('Additional notes')}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'amount': _('Amount (TZS)'),
            'source': _('Source / Payer'),
            'category': _('Category'),
            'date': _('Date'),
            'payment_method': _('Payment Method'),
            'description': _('Description'),
            'notes': _('Notes'),
            'attachment': _('Attachment / Receipt'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                category_type__in=['income', 'both']
            ).filter(
                models_Q := __import__('django.db.models', fromlist=['Q']).Q(user=user) |
                           __import__('django.db.models', fromlist=['Q']).Q(is_default=True)
            )
        self.fields['category'].required = False
        self.fields['attachment'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_('Amount must be greater than zero.'))
        return amount


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'description', 'category', 'date', 'time', 'payment_method', 'notes', 'receipt']
        widgets = {
            'amount': forms.NumberInput(attrs={**BS_NUM, 'placeholder': '0'}),
            'description': forms.TextInput(attrs={**BS, 'placeholder': _('e.g. Grocery shopping')}),
            'category': forms.Select(attrs=BS_SELECT),
            'date': forms.DateInput(attrs=BS_DATE),
            'time': forms.TimeInput(attrs=BS_TIME),
            'payment_method': forms.Select(attrs=BS_SELECT),
            'notes': forms.Textarea(attrs={**BS, 'rows': 2, 'placeholder': _('Additional notes')}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'amount': _('Amount (TZS)'),
            'description': _('Description'),
            'category': _('Category'),
            'date': _('Date'),
            'time': _('Time'),
            'payment_method': _('Payment Method'),
            'notes': _('Notes'),
            'receipt': _('Receipt Upload'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user, category_type__in=['expense', 'both']) |
                Q(is_default=True, category_type__in=['expense', 'both'])
            )
        self.fields['category'].required = False
        self.fields['time'].required = False
        self.fields['receipt'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_('Amount must be greater than zero.'))
        return amount


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ['title', 'amount', 'transaction_type', 'category', 'payment_method',
                  'frequency', 'start_date', 'next_due_date', 'end_date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={**BS, 'placeholder': _('e.g. Monthly Rent')}),
            'amount': forms.NumberInput(attrs={**BS_NUM, 'placeholder': '0'}),
            'transaction_type': forms.Select(attrs=BS_SELECT),
            'category': forms.Select(attrs=BS_SELECT),
            'payment_method': forms.Select(attrs=BS_SELECT),
            'frequency': forms.Select(attrs=BS_SELECT),
            'start_date': forms.DateInput(attrs=BS_DATE),
            'next_due_date': forms.DateInput(attrs=BS_DATE),
            'end_date': forms.DateInput(attrs=BS_DATE),
            'notes': forms.Textarea(attrs={**BS, 'rows': 2}),
        }
        labels = {
            'title': _('Title'),
            'amount': _('Amount (TZS)'),
            'transaction_type': _('Transaction Type'),
            'category': _('Category'),
            'payment_method': _('Payment Method'),
            'frequency': _('Frequency'),
            'start_date': _('Start Date'),
            'next_due_date': _('Next Due Date'),
            'end_date': _('End Date'),
            'notes': _('Notes'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(is_default=True)
            )
        self.fields['category'].required = False
        self.fields['end_date'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_('Amount must be greater than zero.'))
        return amount


class TransactionFilterForm(forms.Form):
    TRANSACTION_TYPE_CHOICES = [('', _('All')), ('income', _('Income')), ('expense', _('Expense'))]
    SORT_CHOICES = [
        ('-date', _('Date (newest)')), ('date', _('Date (oldest)')),
        ('-amount', _('Amount (highest)')), ('amount', _('Amount (lowest)')),
    ]

    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': _('Search...')}))
    transaction_type = forms.ChoiceField(choices=TRANSACTION_TYPE_CHOICES, required=False,
                                          widget=forms.Select(attrs={'class': 'form-select'}))
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False,
                                       widget=forms.Select(attrs={'class': 'form-select'}),
                                       empty_label=_('All Categories'))
    payment_method = forms.ChoiceField(choices=[('', _('All Methods'))] + [
        ('cash', _('Cash')), ('mpesa', 'M-Pesa'), ('airtel', 'Airtel Money'),
        ('tigo', 'Tigo Pesa'), ('halotel', 'Halotel'),
        ('bank', _('Bank')), ('card', _('Card')), ('other', _('Other'))
    ], required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    date_from = forms.DateField(required=False, label=_('From Date'),
                                widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_to = forms.DateField(required=False, label=_('To Date'),
                              widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    amount_min = forms.DecimalField(required=False, min_value=0,
                                    widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Min')}))
    amount_max = forms.DecimalField(required=False, min_value=0,
                                    widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Max')}))
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False,
                             widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from django.db.models import Q
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(is_default=True)
            )
