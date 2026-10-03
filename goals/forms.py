from django import forms
from django.utils.translation import gettext_lazy as _
from .models import FinancialGoal, GoalContribution


class FinancialGoalForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    class Meta:
        model = FinancialGoal
        fields = ['name', 'description', 'target_amount', 'target_date', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Emergency Fund')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'target_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'target_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Education')}),
        }
        labels = {
            'name': _('Goal Name'),
            'description': _('Description / Purpose'),
            'target_amount': _('Target Amount (TZS)'),
            'target_date': _('Target Date'),
            'category': _('Category'),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            return name
        user = self.user or (self.instance.user if self.instance and self.instance.pk else None)
        if user:
            qs = FinancialGoal.objects.filter(user=user, name__iexact=name, is_completed=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('A active goal with this name already exists.'))
        return name

    def clean_target_amount(self):
        amount = self.cleaned_data.get('target_amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_('Target amount must be greater than zero.'))
        return amount


class GoalContributionForm(forms.ModelForm):
    class Meta:
        model = GoalContribution
        fields = ['amount', 'date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional notes')}),
        }
        labels = {
            'amount': _('Amount (TZS)'),
            'date': _('Date'),
            'notes': _('Notes'),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_('Contribution amount must be greater than zero.'))
        return amount
