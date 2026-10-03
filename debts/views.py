from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction as db_transaction
from django.utils import timezone
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, InvalidOperation
from .models import Debt, DebtRepayment
from .forms import DebtForm, DebtRepaymentForm


class DebtListView(LoginRequiredMixin, View):
    template_name = 'debts/debt_list.html'

    def get(self, request):
        debts = Debt.objects.filter(user=request.user).prefetch_related('repayments')
        loans = [d for d in debts if d.debt_type == 'loan']
        receivables = [d for d in debts if d.debt_type == 'receivable']
        return render(request, self.template_name, {
            'loans': loans,
            'receivables': receivables,
            'total_owed': sum(d.remaining_balance for d in loans),
            'total_receivable': sum(d.remaining_balance for d in receivables),
        })


class DebtCreateView(LoginRequiredMixin, View):
    template_name = 'debts/debt_form.html'

    def get(self, request):
        form = DebtForm(initial={'start_date': timezone.now().date()})
        return render(request, self.template_name, {'form': form, 'action': 'Add'})

    def post(self, request):
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            debt.user = request.user
            debt.save()
            messages.success(request, f'Debt "{debt.name}" recorded.')
            return redirect('debt_detail', pk=debt.pk)
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class DebtDetailView(LoginRequiredMixin, View):
    template_name = 'debts/debt_detail.html'

    def get(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        return render(request, self.template_name, {
            'debt': debt,
            'repayments': debt.repayments.all(),
            'repayment_form': DebtRepaymentForm(initial={'date': timezone.now().date()}),
        })


class DebtUpdateView(LoginRequiredMixin, View):
    template_name = 'debts/debt_form.html'

    def get(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        return render(request, self.template_name, {
            'form': DebtForm(instance=debt), 'action': 'Edit', 'object': debt
        })

    def post(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        form = DebtForm(request.POST, instance=debt)
        if form.is_valid():
            form.save()
            messages.success(request, f'Debt "{debt.name}" updated.')
            return redirect('debt_detail', pk=debt.pk)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': debt})


class DebtDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        name = debt.name
        debt.delete()
        messages.success(request, f'Debt "{name}" deleted.')
        return redirect('debt_list')


class DebtRepaymentCheckView(LoginRequiredMixin, View):
    """JSON pre-check endpoint — returns overpayment info without saving."""

    def post(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        try:
            raw = request.POST.get('amount', '').strip()
            if not raw:
                return JsonResponse({'error': str(_('Amount is required.'))}, status=400)
            amount = Decimal(raw)
        except (InvalidOperation, ValueError):
            return JsonResponse({'error': str(_('Invalid amount.'))}, status=400)

        if amount <= 0:
            return JsonResponse({'error': str(_('Amount must be greater than zero.'))}, status=400)

        remaining = debt.remaining_balance
        is_over = amount > remaining

        return JsonResponse({
            'is_overpayment': is_over,
            'payment_amount': str(amount),
            'remaining_balance': str(remaining),
            'overpayment_amount': str(amount - remaining if is_over else Decimal('0')),
        })


class DebtRepaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        form = DebtRepaymentForm(request.POST)

        if not form.is_valid():
            messages.error(request, str(_('Invalid repayment data. Please check the amount.')))
            return redirect('debt_detail', pk=pk)

        amount = form.cleaned_data['amount']

        if amount <= 0:
            messages.error(request, str(_('Payment amount must be greater than zero.')))
            return redirect('debt_detail', pk=pk)

        remaining = debt.remaining_balance

        if amount > remaining and request.POST.get('confirm_overpayment') != '1':
            messages.warning(request, str(_(
                'Payment of TZS %(amount)s exceeds the remaining balance of '
                'TZS %(remaining)s. Please confirm the overpayment.'
            ) % {'amount': f'{amount:,.0f}', 'remaining': f'{remaining:,.0f}'}))
            return redirect('debt_detail', pk=pk)

        with db_transaction.atomic():
            debt_locked = Debt.objects.select_for_update().get(pk=pk, user=request.user)
            repayment = form.save(commit=False)
            repayment.debt = debt_locked
            repayment.save()

            new_remaining = debt_locked.remaining_balance
            if new_remaining <= 0:
                debt_locked.status = 'paid'
            elif debt_locked.total_paid > 0:
                debt_locked.status = 'partial'
            debt_locked.save(update_fields=['status', 'updated_at'])

        messages.success(request, str(
            _('Repayment of TZS %(amount)s recorded.') % {'amount': f'{repayment.amount:,.0f}'}
        ))
        return redirect('debt_detail', pk=pk)
