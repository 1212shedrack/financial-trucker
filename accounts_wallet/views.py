from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction as db_transaction
from .models import Account, Transfer
from .forms import AccountForm, TransferForm


# ACCOUNTS

class AccountListView(LoginRequiredMixin, View):
    template_name = 'accounts_wallet/account_list.html'

    def get(self, request):
        accounts = Account.objects.filter(user=request.user, is_active=True).with_current_balance()
        inactive_accounts = Account.objects.filter(user=request.user, is_active=False).with_current_balance()
        total_balance = sum(acc.current_balance for acc in accounts)
        return render(request, self.template_name, {
            'accounts': accounts,
            'inactive_accounts': inactive_accounts,
            'total_balance': total_balance,
        })


class AccountCreateView(LoginRequiredMixin, View):
    template_name = 'accounts_wallet/account_form.html'

    def get(self, request):
        form = AccountForm()
        return render(request, self.template_name, {'form': form, 'action': 'Add'})

    def post(self, request):
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f'Account "{account.name}" created.')
            return redirect('account_list')
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class AccountUpdateView(LoginRequiredMixin, View):
    template_name = 'accounts_wallet/account_form.html'

    def get(self, request, pk):
        account = get_object_or_404(Account, pk=pk, user=request.user)
        form = AccountForm(instance=account)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': account})

    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk, user=request.user)
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Account "{account.name}" updated.')
            return redirect('account_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': account})


class AccountDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk, user=request.user)
        account.is_active = False
        account.save()
        messages.success(request, f'Account "{account.name}" deactivated.')
        return redirect('account_list')


class AccountActivateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        account = get_object_or_404(Account, pk=pk, user=request.user)
        account.is_active = True
        account.save(update_fields=['is_active'])
        messages.success(request, f'Account "{account.name}" activated.')
        return redirect('account_list')


# TRANSFERS

class TransferListView(LoginRequiredMixin, View):
    template_name = 'accounts_wallet/transfer_list.html'

    def get(self, request):
        transfers = Transfer.objects.filter(user=request.user).select_related('from_account', 'to_account').order_by('-date', '-created_at')
        return render(request, self.template_name, {'transfers': transfers})


class TransferCreateView(LoginRequiredMixin, View):
    template_name = 'accounts_wallet/transfer_form.html'

    def get(self, request):
        form = TransferForm(user=request.user)
        return render(request, self.template_name, {'form': form, 'action': 'New'})

    def post(self, request):
        form = TransferForm(user=request.user, data=request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                transfer = form.save(commit=False)
                transfer.user = request.user
                transfer.save()
            messages.success(request, f'Transfer of TSh {transfer.amount:,.0f} recorded.')
            return redirect('transfer_list')
        return render(request, self.template_name, {'form': form, 'action': 'New'})


class TransferDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        transfer = get_object_or_404(Transfer, pk=pk, user=request.user)
        transfer.delete()
        messages.success(request, 'Transfer deleted.')
        return redirect('transfer_list')
