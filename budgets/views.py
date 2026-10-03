from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from core.views import log_action
from .models import Budget
from .forms import BudgetForm


class BudgetListView(LoginRequiredMixin, View):
    template_name = 'budgets/budget_list.html'

    def get(self, request):
        budgets = Budget.objects.filter(user=request.user).select_related('category').order_by('-created_at')
        return render(request, self.template_name, {'budgets': budgets})


class BudgetCreateView(LoginRequiredMixin, View):
    template_name = 'budgets/budget_form.html'

    def get(self, request):
        form = BudgetForm(user=request.user)
        return render(request, self.template_name, {'form': form, 'action': 'Create'})

    def post(self, request):
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            log_action(request.user, 'CREATE', f'Created budget: {budget.category.name} TSh {budget.amount:,.0f}', request)
            messages.success(request, f'Budget for "{budget.category.name}" created.')
            return redirect('budget_list')
        return render(request, self.template_name, {'form': form, 'action': 'Create'})


class BudgetUpdateView(LoginRequiredMixin, View):
    template_name = 'budgets/budget_form.html'

    def get(self, request, pk):
        budget = get_object_or_404(Budget, pk=pk, user=request.user)
        form = BudgetForm(instance=budget, user=request.user)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': budget})

    def post(self, request, pk):
        budget = get_object_or_404(Budget, pk=pk, user=request.user)
        form = BudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            form.save()
            log_action(request.user, 'UPDATE', f'Updated budget: {budget.category.name}', request)
            messages.success(request, 'Budget updated.')
            return redirect('budget_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': budget})


class BudgetDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        budget = get_object_or_404(Budget, pk=pk, user=request.user)
        name = budget.category.name
        log_action(request.user, 'DELETE', f'Deleted budget: {name}', request)
        budget.delete()
        messages.success(request, f'Budget for "{name}" deleted.')
        return redirect('budget_list')


class BudgetDetailView(LoginRequiredMixin, View):
    template_name = 'budgets/budget_detail.html'

    def get(self, request, pk):
        budget = get_object_or_404(Budget, pk=pk, user=request.user)
        from transactions.models import Expense
        from django.db.models import Sum
        recent_expenses = Expense.objects.filter(
            user=request.user, category=budget.category
        ).order_by('-date')[:20]
        return render(request, self.template_name, {
            'budget': budget,
            'recent_expenses': recent_expenses,
        })
