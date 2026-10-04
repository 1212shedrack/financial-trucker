import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views import View
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from core.views import log_action
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, ChangePasswordForm

logger = logging.getLogger('accounts')


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_action(user, 'CREATE', f'New user registered: {user.username}', request)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
        return render(request, self.template_name, {'form': form})


@method_decorator(never_cache, name='dispatch')
class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = UserLoginForm(request)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            remember_me = form.cleaned_data.get('remember_me')
            if not remember_me:
                request.session.set_expiry(0)
            log_action(user, 'LOGIN', f'User logged in from {request.META.get("REMOTE_ADDR")}', request)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(request.GET.get('next', 'dashboard'))
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    def post(self, request):
        if request.user.is_authenticated:
            log_action(request.user, 'LOGOUT', 'User logged out', request)
        logout(request)
        messages.info(request, 'You have been logged out.')
        response = redirect('landing')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response

    def get(self, request):
        if request.user.is_authenticated:
            log_action(request.user, 'LOGOUT', 'User logged out', request)
        logout(request)
        response = redirect('landing')
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response


class ProfileView(View):
    template_name = 'accounts/profile.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        form = UserProfileForm(instance=request.user.profile)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            try:
                form.save()
            except Exception:
                logger.exception('Failed to save profile update or photo')
                form.add_error(
                    None,
                    'Profile could not be saved. Please try again.',
                )
                return render(request, self.template_name, {'form': form})
            log_action(request.user, 'PROFILE_UPDATE', 'User updated profile', request)
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        return render(request, self.template_name, {'form': form})


class ChangePasswordView(View):
    template_name = 'accounts/change_password.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        form = ChangePasswordForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            old_pw = form.cleaned_data['old_password']
            if not request.user.check_password(old_pw):
                messages.error(request, 'Current password is incorrect.')
                return render(request, self.template_name, {'form': form})
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.save()
            update_session_auth_hash(request, request.user)
            log_action(request.user, 'PASSWORD_CHANGE', 'User changed password', request)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile')
        return render(request, self.template_name, {'form': form})


class PasswordResetRequestView(View):
    template_name = 'accounts/password_reset.html'

    def get(self, request):
        return render(request, self.template_name, {'form': PasswordResetForm()})

    def post(self, request):
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            users = User.objects.filter(email=email, is_active=True)
            for user in users:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    f'/accounts/password-reset/confirm/{uid}/{token}/'
                )
                send_mail(
                    subject='PFAMS — Password Reset',
                    message=f'Click the link to reset your password:\n{reset_url}',
                    from_email='noreply@pfams.com',
                    recipient_list=[email],
                    fail_silently=True,
                )
            messages.info(request, 'If that email exists, a reset link has been sent.')
            return redirect('password_reset_done')
        return render(request, self.template_name, {'form': form})


class PasswordResetDoneView(View):
    def get(self, request):
        return render(request, 'accounts/password_reset_done.html')


class PasswordResetConfirmView(View):
    template_name = 'accounts/password_reset_confirm.html'

    def _get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except Exception:
            return None

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user and default_token_generator.check_token(user, token):
            form = SetPasswordForm(user)
            return render(request, self.template_name, {'form': form, 'valid': True})
        return render(request, self.template_name, {'valid': False})

    def post(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user and default_token_generator.check_token(user, token):
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password reset successful. Please log in.')
                return redirect('password_reset_complete')
            return render(request, self.template_name, {'form': form, 'valid': True})
        return render(request, self.template_name, {'valid': False})


class PasswordResetCompleteView(View):
    def get(self, request):
        return render(request, 'accounts/password_reset_complete.html')
