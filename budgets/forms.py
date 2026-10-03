from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Budget


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'period', 'start_date', 'end_date', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'period': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'category': _('Category'),
            'amount': _('Budget Limit (TZS)'),
            'period': _('Period'),
            'start_date': _('Start Date'),
            'end_date': _('End Date (Custom)'),
            'notes': _('Notes'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from django.db.models import Q
            from transactions.models import Category
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user, category_type__in=['expense', 'both']) |
                Q(is_default=True, category_type__in=['expense', 'both'])
            )
        self.fields['end_date'].required = False

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get('amount')
        if amount is not None and amount <= 0:
            self.add_error('amount', _('Budget amount must be greater than zero.'))
        return cleaned
