from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Account, Transfer


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'account_number', 'opening_balance', 'color', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control',
                                           'placeholder': _('e.g. Azania Bank, My M-Pesa')}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control',
                                                     'placeholder': _('Last 4 digits or identifier')}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': _('Account Name'),
            'account_type': _('Account Type'),
            'account_number': _('Account Number'),
            'opening_balance': _('Opening Balance (TZS)'),
            'color': _('Color'),
            'notes': _('Notes'),
        }


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = ['from_account', 'to_account', 'amount', 'date', 'notes']
        widgets = {
            'from_account': forms.Select(attrs={'class': 'form-select'}),
            'to_account': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'from_account': _('From Account'),
            'to_account': _('To Account'),
            'amount': _('Amount (TZS)'),
            'date': _('Date'),
            'notes': _('Notes'),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['from_account'].queryset = Account.objects.filter(user=user, is_active=True)
            self.fields['to_account'].queryset = Account.objects.filter(user=user, is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        from_acc = cleaned_data.get('from_account')
        to_acc = cleaned_data.get('to_account')
        amount = cleaned_data.get('amount')

        if from_acc and to_acc and from_acc == to_acc:
            self.add_error('to_account', _('Cannot transfer to and from the same account.'))
            return cleaned_data

        if from_acc and not from_acc.is_active:
            self.add_error('from_account', _('The source account is inactive and cannot be used for transfers.'))
            return cleaned_data

        if to_acc and not to_acc.is_active:
            self.add_error('to_account', _('The destination account is inactive and cannot receive transfers.'))
            return cleaned_data

        if from_acc and to_acc and from_acc.user_id != to_acc.user_id:
            self.add_error('to_account', _('Transfers must be between accounts in the same user wallet.'))
            return cleaned_data

        if from_acc and amount is not None and amount > from_acc.current_balance:
            self.add_error('amount', _('Transfer amount exceeds the available balance in the source account.'))
            return cleaned_data

        if amount is not None and amount <= 0:
            self.add_error('amount', _('Transfer amount must be greater than zero.'))
            return cleaned_data

        return cleaned_data
