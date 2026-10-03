from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import UserProfile


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email address')})
    )
    full_name = forms.CharField(
        max_length=200, required=False,
        label=_('Full Name'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Full name (optional)')})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Username')}),
        }
        labels = {
            'username': _('Username'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': _('Password')})
        self.fields['password1'].label = _('Password')
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': _('Confirm password')})
        self.fields['password2'].label = _('Confirm Password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            if hasattr(user, 'profile'):
                user.profile.full_name = self.cleaned_data.get('full_name', '')
                user.profile.save()
        return user


class UserLoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False,
        label=_('Remember me'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': _('Username')})
        self.fields['username'].label = _('Username')
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': _('Password')})
        self.fields['password'].label = _('Password')


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['full_name', 'phone_number', 'profile_photo', 'preferred_currency',
                  'timezone', 'monthly_income_target', 'monthly_savings_target']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255...'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'preferred_currency': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'monthly_income_target': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1000'}),
            'monthly_savings_target': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1000'}),
        }
        labels = {
            'full_name': _('Full Name'),
            'phone_number': _('Phone Number'),
            'profile_photo': _('Profile Photo'),
            'preferred_currency': _('Preferred Currency'),
            'timezone': _('Timezone'),
            'monthly_income_target': _('Monthly Income Target (TZS)'),
            'monthly_savings_target': _('Monthly Savings Target (TZS)'),
        }


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label=_('Current Password')
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label=_('New Password')
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label=_('Confirm New Password')
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password1')
        p2 = cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('New passwords do not match.'))
        if p1 and len(p1) < 8:
            raise forms.ValidationError(_('Password must be at least 8 characters.'))
        return cleaned
