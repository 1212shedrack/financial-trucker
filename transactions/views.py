import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from core.views import log_action
from .models import Category, Income, Expense, RecurringTransaction
from .forms import CategoryForm, IncomeForm, ExpenseForm, RecurringTransactionForm, TransactionFilterForm
from .services import validate_upload_file, get_upcoming_recurring

logger = logging.getLogger('transactions')

VALID_SORTS = {'-date', 'date', '-amount', 'amount'}


def _filter_query(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def _user_categories(user, cat_type=None):
    qs = Category.objects.filter(Q(user=user) | Q(is_default=True))
    if cat_type:
        qs = qs.filter(category_type__in=[cat_type, 'both'])
    return qs


def _apply_common_filters(qs, request):
    """Apply shared filter params (category, payment, dates, amounts, sort)."""
    if request.GET.get('category'):
        qs = qs.filter(category_id=request.GET['category'])
    if request.GET.get('payment_method'):
        qs = qs.filter(payment_method=request.GET['payment_method'])
    if request.GET.get('date_from'):
        qs = qs.filter(date__gte=request.GET['date_from'])
    if request.GET.get('date_to'):
        qs = qs.filter(date__lte=request.GET['date_to'])
    if request.GET.get('amount_min'):
        qs = qs.filter(amount__gte=request.GET['amount_min'])
    if request.GET.get('amount_max'):
        qs = qs.filter(amount__lte=request.GET['amount_max'])
    sort = request.GET.get('sort', '-date')
    if sort in VALID_SORTS:
        qs = qs.order_by(sort)
    return qs


# Income

class IncomeListView(LoginRequiredMixin, View):
    template_name = 'transactions/income_list.html'

    def get(self, request):
        qs = Income.objects.filter(user=request.user).select_related('category')
        form = TransactionFilterForm(request.GET or None, user=request.user)

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(source__icontains=q) | Q(description__icontains=q))

        qs = _apply_common_filters(qs, request)
        total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        page_obj = Paginator(qs, 20).get_page(request.GET.get('page'))

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'filter_form': form,
            'total_income': total,
            'q': q,
            'filter_query': _filter_query(request),
        })


class IncomeCreateView(LoginRequiredMixin, View):
    template_name = 'transactions/income_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': IncomeForm(user=request.user), 'action': 'Add'
        })

    def post(self, request):
        form = IncomeForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                if form.cleaned_data.get('attachment'):
                    validate_upload_file(form.cleaned_data['attachment'])
                income = form.save(commit=False)
                income.user = request.user
                try:
                    income.save()
                except Exception:
                    logger.exception('Failed to save income or attachment')
                    form.add_error(
                        None,
                        'Income could not be saved. Please try again.',
                    )
                    return render(request, self.template_name, {
                        'form': form,
                        'action': 'Add',
                    })
                log_action(request.user, 'CREATE', f'Income: {income.source} TSh {income.amount:,.0f}', request)
                messages.success(request, f'Income of TSh {income.amount:,.0f} added.')
                from notifications.services import send_budget_alerts
                send_budget_alerts(request.user)
                return redirect('income_list')
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class IncomeUpdateView(LoginRequiredMixin, View):
    template_name = 'transactions/income_form.html'

    def get(self, request, pk):
        income = get_object_or_404(Income, pk=pk, user=request.user)
        return render(request, self.template_name, {
            'form': IncomeForm(instance=income, user=request.user), 'action': 'Edit', 'object': income
        })

    def post(self, request, pk):
        income = get_object_or_404(Income, pk=pk, user=request.user)
        form = IncomeForm(request.POST, request.FILES, instance=income, user=request.user)
        if form.is_valid():
            try:
                if form.cleaned_data.get('attachment'):
                    validate_upload_file(form.cleaned_data['attachment'])
                try:
                    updated = form.save()
                except Exception:
                    logger.exception('Failed to update income or attachment')
                    form.add_error(
                        None,
                        'Income could not be saved. Please try again.',
                    )
                    return render(request, self.template_name, {
                        'form': form,
                        'action': 'Edit',
                        'object': income,
                    })
                log_action(request.user, 'UPDATE', f'Updated income: {updated.source}', request)
                messages.success(request, 'Income updated.')
                return redirect('income_list')
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': income})


class IncomeDeleteView(LoginRequiredMixin, View):
    template_name = 'transactions/income_confirm_delete.html'

    def get(self, request, pk):
        return render(request, self.template_name, {
            'object': get_object_or_404(Income, pk=pk, user=request.user)
        })

    def post(self, request, pk):
        income = get_object_or_404(Income, pk=pk, user=request.user)
        log_action(request.user, 'DELETE', f'Deleted income: {income.source}', request)
        income.delete()
        messages.success(request, 'Income record deleted.')
        return redirect('income_list')


class IncomeDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        return render(request, 'transactions/income_detail.html', {
            'object': get_object_or_404(Income, pk=pk, user=request.user)
        })


# Expense

class ExpenseListView(LoginRequiredMixin, View):
    template_name = 'transactions/expense_list.html'

    def get(self, request):
        qs = Expense.objects.filter(user=request.user).select_related('category')

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(description__icontains=q) | Q(notes__icontains=q))

        qs = _apply_common_filters(qs, request)
        total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        page_obj = Paginator(qs, 20).get_page(request.GET.get('page'))

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'total_expenses': total,
            'categories': _user_categories(request.user, 'expense'),
            'q': q,
            'filter_query': _filter_query(request),
        })


class ExpenseCreateView(LoginRequiredMixin, View):
    template_name = 'transactions/expense_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': ExpenseForm(user=request.user), 'action': 'Add'
        })

    def post(self, request):
        form = ExpenseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                if form.cleaned_data.get('receipt'):
                    validate_upload_file(form.cleaned_data['receipt'])
                expense = form.save(commit=False)
                expense.user = request.user
                try:
                    expense.save()
                except Exception:
                    logger.exception('Failed to save expense or receipt')
                    form.add_error(
                        None,
                        'Expense could not be saved. Please try again.',
                    )
                    return render(request, self.template_name, {
                        'form': form,
                        'action': 'Add',
                    })
                log_action(request.user, 'CREATE', f'Expense: {expense.description} TSh {expense.amount:,.0f}', request)
                messages.success(request, f'Expense of TSh {expense.amount:,.0f} added.')
                from notifications.services import send_budget_alerts
                send_budget_alerts(request.user)
                return redirect('expense_list')
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class ExpenseUpdateView(LoginRequiredMixin, View):
    template_name = 'transactions/expense_form.html'

    def get(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, user=request.user)
        return render(request, self.template_name, {
            'form': ExpenseForm(instance=expense, user=request.user), 'action': 'Edit', 'object': expense
        })

    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, user=request.user)
        form = ExpenseForm(request.POST, request.FILES, instance=expense, user=request.user)
        if form.is_valid():
            try:
                if form.cleaned_data.get('receipt'):
                    validate_upload_file(form.cleaned_data['receipt'])
                try:
                    updated = form.save()
                except Exception:
                    logger.exception('Failed to update expense or receipt')
                    form.add_error(
                        None,
                        'Expense could not be saved. Please try again.',
                    )
                    return render(request, self.template_name, {
                        'form': form,
                        'action': 'Edit',
                        'object': expense,
                    })
                log_action(request.user, 'UPDATE', f'Updated expense: {updated.description}', request)
                messages.success(request, 'Expense updated.')
                return redirect('expense_list')
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': expense})


class ExpenseDeleteView(LoginRequiredMixin, View):
    template_name = 'transactions/expense_confirm_delete.html'

    def get(self, request, pk):
        return render(request, self.template_name, {
            'object': get_object_or_404(Expense, pk=pk, user=request.user)
        })

    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, user=request.user)
        log_action(request.user, 'DELETE', f'Deleted expense: {expense.description}', request)
        expense.delete()
        messages.success(request, 'Expense deleted.')
        return redirect('expense_list')


class ExpenseDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        return render(request, 'transactions/expense_detail.html', {
            'object': get_object_or_404(Expense, pk=pk, user=request.user)
        })


# Transactions (combined view)

class TransactionListView(LoginRequiredMixin, View):
    template_name = 'transactions/transaction_list.html'

    def get(self, request):
        income_qs = Income.objects.filter(user=request.user).select_related('category')
        expense_qs = Expense.objects.filter(user=request.user).select_related('category')

        q = request.GET.get('q', '').strip()
        t_type = request.GET.get('type', '')

        if q:
            income_qs = income_qs.filter(Q(source__icontains=q) | Q(description__icontains=q))
            expense_qs = expense_qs.filter(Q(description__icontains=q) | Q(notes__icontains=q))

        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            income_qs = income_qs.filter(date__gte=date_from)
            expense_qs = expense_qs.filter(date__gte=date_from)
        if date_to:
            income_qs = income_qs.filter(date__lte=date_to)
            expense_qs = expense_qs.filter(date__lte=date_to)

        rows = []
        if t_type != 'expense':
            rows += [{'type': 'income', 'obj': i, 'date': i.date, 'amount': i.amount} for i in income_qs]
        if t_type != 'income':
            rows += [{'type': 'expense', 'obj': e, 'date': e.date, 'amount': e.amount} for e in expense_qs]

        rows.sort(key=lambda x: (x['date'], x['obj'].created_at), reverse=True)
        page_obj = Paginator(rows, 25).get_page(request.GET.get('page'))

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'q': q,
            't_type': t_type,
            'date_from': date_from or '',
            'date_to': date_to or '',
            'filter_query': _filter_query(request),
        })


# Categories

class CategoryListView(LoginRequiredMixin, View):
    template_name = 'transactions/category_list.html'

    def get(self, request):
        return render(request, self.template_name, {
            'default_categories': Category.objects.filter(is_default=True).order_by('name'),
            'user_categories': Category.objects.filter(user=request.user).order_by('name'),
        })


class CategoryCreateView(LoginRequiredMixin, View):
    template_name = 'transactions/category_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': CategoryForm(user=request.user), 'action': 'Add'
        })

    def post(self, request):
        form = CategoryForm(request.POST, user=request.user)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.save()
            messages.success(request, f'Category "{cat.name}" created.')
            return redirect('category_list')
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class CategoryUpdateView(LoginRequiredMixin, View):
    template_name = 'transactions/category_form.html'

    def get(self, request, pk):
        cat = get_object_or_404(Category, pk=pk, user=request.user)
        return render(request, self.template_name, {
            'form': CategoryForm(instance=cat, user=request.user), 'action': 'Edit', 'object': cat
        })

    def post(self, request, pk):
        cat = get_object_or_404(Category, pk=pk, user=request.user)
        form = CategoryForm(request.POST, instance=cat, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{cat.name}" updated.')
            return redirect('category_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': cat})


class CategoryDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cat = get_object_or_404(Category, pk=pk, user=request.user)
        used = Income.objects.filter(category=cat).count() + Expense.objects.filter(category=cat).count()
        if used:
            messages.error(request, f'Cannot delete "{cat.name}" — used by {used} transaction(s). Reassign first.')
            return redirect('category_list')
        name = cat.name
        cat.delete()
        messages.success(request, f'Category "{name}" deleted.')
        return redirect('category_list')


# Recurring

class RecurringListView(LoginRequiredMixin, View):
    template_name = 'transactions/recurring_list.html'

    def get(self, request):
        qs = RecurringTransaction.objects.filter(user=request.user).select_related('category').order_by('next_due_date')
        return render(request, self.template_name, {'recurring_list': qs})


class RecurringCreateView(LoginRequiredMixin, View):
    template_name = 'transactions/recurring_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': RecurringTransactionForm(user=request.user), 'action': 'Add'
        })

    def post(self, request):
        form = RecurringTransactionForm(request.POST, user=request.user)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.user = request.user
            rec.save()
            messages.success(request, f'Recurring "{rec.title}" created.')
            return redirect('recurring_list')
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class RecurringUpdateView(LoginRequiredMixin, View):
    template_name = 'transactions/recurring_form.html'

    def get(self, request, pk):
        rec = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
        return render(request, self.template_name, {
            'form': RecurringTransactionForm(instance=rec, user=request.user), 'action': 'Edit', 'object': rec
        })

    def post(self, request, pk):
        rec = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
        form = RecurringTransactionForm(request.POST, instance=rec, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurring transaction updated.')
            return redirect('recurring_list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'object': rec})


class RecurringDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rec = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
        title = rec.title
        rec.delete()
        messages.success(request, f'"{title}" deleted.')
        return redirect('recurring_list')


class RecurringToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rec = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
        rec.active = not rec.active
        rec.save(update_fields=['active'])
        messages.success(request, f'"{rec.title}" {"activated" if rec.active else "deactivated"}.')
        return redirect('recurring_list')
