from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Debt, DebtRepayment
from transactions.models import PAYMENT_METHODS


class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = ['debt_type', 'name', 'description',
                  'principal_amount', 'interest_rate',
                  'start_date', 'due_date', 'notes']
        widgets = {
            'debt_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control',
                                           'placeholder': _(
                                               'Person or institution name')}),
            'description': forms.Textarea(attrs={'class': 'form-control',
                                                 'rows': 2}),
            'principal_amount': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'start_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control',
                                               'type': 'date'}),
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'debt_type': _('Debt Type'),
            'name': _('Name'),
            'description': _('Description'),
            'principal_amount': _('Principal Amount (TZS)'),
            'interest_rate': _('Interest Rate (% p.a.)'),
            'start_date': _('Start Date'),
            'due_date': _('Due Date'),
            'notes': _('Notes'),
        }


class DebtRepaymentForm(forms.ModelForm):
    class Meta:
        model = DebtRepayment
        fields = ['amount', 'date', 'payment_method', 'notes']
        widgets = {
            'amount': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
            'date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(
                choices=PAYMENT_METHODS, attrs={'class': 'form-select'}),
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'amount': _('Amount (TZS)'),
            'date': _('Date'),
            'payment_method': _('Payment Method'),
            'notes': _('Notes'),
        }
