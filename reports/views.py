import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from core.views import log_action
from .services import ReportService


class ReportsDashboardView(LoginRequiredMixin, View):
    template_name = 'reports/dashboard.html'

    def get(self, request):
        today = timezone.now().date()
        return render(request, self.template_name, {
            'today': today,
            'this_month_start': today.replace(day=1),
        })


class ExportCSVView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        report_type = request.GET.get('type', 'all')
        try:
            df = date.fromisoformat(date_from) if date_from else None
            dt = date.fromisoformat(date_to) if date_to else None
        except ValueError:
            df = dt = None

        service = ReportService(request.user, df, dt)
        csv_bytes = service.generate_csv(report_type)
        log_action(request.user, 'EXPORT', f'Exported CSV report ({report_type})', request)
        response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="pfams_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        return response


class ExportExcelView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        report_type = request.GET.get('type', 'all')
        try:
            df = date.fromisoformat(date_from) if date_from else None
            dt = date.fromisoformat(date_to) if date_to else None
        except ValueError:
            df = dt = None

        service = ReportService(request.user, df, dt)
        excel_bytes = service.generate_excel(report_type)
        log_action(request.user, 'EXPORT', f'Exported Excel report ({report_type})', request)
        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="pfams_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        return response


class ExportPDFView(LoginRequiredMixin, View):
    def get(self, request):
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        report_type = request.GET.get('type', 'all')
        try:
            df = date.fromisoformat(date_from) if date_from else None
            dt = date.fromisoformat(date_to) if date_to else None
        except ValueError:
            df = dt = None

        service = ReportService(request.user, df, dt)
        pdf_bytes = service.generate_pdf(report_type)
        log_action(request.user, 'EXPORT', f'Exported PDF report ({report_type})', request)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="pfams_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response


class ImportCSVView(LoginRequiredMixin, View):
    template_name = 'reports/import.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return render(request, self.template_name)
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, self.template_name)
        if csv_file.size > 5 * 1024 * 1024:
            messages.error(request, 'File too large. Maximum 5MB.')
            return render(request, self.template_name)

        service = ReportService(request.user)
        result = service.validate_import_csv(csv_file)
        request.session['import_valid_rows'] = result['valid_rows']

        # Separate duplicates from clean rows for template display
        duplicate_rows = [r for r in result['valid_rows'] if r.get('is_duplicate')]
        clean_rows = [r for r in result['valid_rows'] if not r.get('is_duplicate')]

        return render(request, 'reports/import_preview.html', {
            'valid_rows': result['valid_rows'],   # all valid (for session count)
            'clean_rows': clean_rows,             # new records to be imported
            'duplicate_rows': duplicate_rows,     # existing records to be skipped
            'invalid_rows': result['invalid_rows'],
            'errors': result['errors'],
        })


class ImportConfirmView(LoginRequiredMixin, View):
    def post(self, request):
        valid_rows = request.session.get('import_valid_rows', [])
        if not valid_rows:
            messages.error(request, 'No valid rows to import. Please re-upload.')
            return redirect('reports_import')

        service = ReportService(request.user)
        result = service.import_transactions(valid_rows)
        del request.session['import_valid_rows']
        log_action(request.user, 'IMPORT', f'Imported {result["imported"]} transactions ({result["duplicates"]} duplicates skipped)', request)
        messages.success(
            request,
            f'Successfully imported {result["imported"]} transaction(s). '
            f'{result["duplicates"]} duplicate(s) skipped. '
            f'{result["skipped"]} error(s).'
        )
        return redirect('transaction_list')


class BackupExportView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        from transactions.models import Income, Expense, Category, RecurringTransaction
        from budgets.models import Budget
        from goals.models import FinancialGoal
        from accounts_wallet.models import Account, Transfer
        from debts.models import Debt

        backup_data = {
            'version': '1.0',
            'exported_at': str(timezone.now()),
            'user': user.username,
            'categories': list(Category.objects.filter(user=user).values('name', 'category_type', 'icon', 'color')),
            'accounts': list(Account.objects.filter(user=user, is_active=True).values('name', 'account_type', 'opening_balance', 'color', 'notes')),
            'incomes': list(Income.objects.filter(user=user).values('amount', 'source', 'date', 'payment_method', 'description', 'notes')),
            'expenses': list(Expense.objects.filter(user=user).values('amount', 'description', 'date', 'payment_method', 'notes')),
            'budgets': list(Budget.objects.filter(user=user).values('amount', 'period', 'created_at')),
            'goals': list(FinancialGoal.objects.filter(user=user).values('name', 'description', 'target_amount', 'current_amount', 'target_date', 'is_completed')),
            'debts': list(Debt.objects.filter(user=user).values('debt_type', 'name', 'description', 'principal_amount', 'start_date', 'due_date', 'status')),
            'transfers': list(Transfer.objects.filter(user=user).values('amount', 'date', 'notes')),
        }

        log_action(request.user, 'BACKUP_EXPORT', 'Exported full JSON system backup', request)
        response = HttpResponse(json.dumps(backup_data, indent=2, default=str), content_type='application/json')
        filename = f"pfams_backup_{user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class BackupRestoreView(LoginRequiredMixin, View):
    template_name = 'reports/backup_restore.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        backup_file = request.FILES.get('backup_file')
        if not backup_file or not backup_file.name.endswith('.json'):
            messages.error(request, 'Please upload a valid JSON backup file.')
            return render(request, self.template_name)

        try:
            content = json.loads(backup_file.read().decode('utf-8'))
            if 'version' not in content or 'categories' not in content:
                raise ValueError('Invalid backup schema structure')
        except Exception as e:
            messages.error(request, f'Failed to parse backup file: {str(e)}')
            return render(request, self.template_name)

        from django.db import transaction as db_transaction
        from transactions.models import Income, Expense, Category
        from accounts_wallet.models import Account, Transfer
        from budgets.models import Budget
        from debts.models import Debt, DebtRepayment
        from goals.models import FinancialGoal
        user = request.user

        restored_counts = {
            'categories': 0, 'incomes': 0, 'expenses': 0,
            'goals': 0, 'debts': 0, 'accounts': 0, 'budgets': 0,
            'duplicates_skipped': 0,
        }

        try:
            with db_transaction.atomic():
                # 1. Categories — get or create, track name→object map
                cat_map = {}
                for cat_data in content.get('categories', []):
                    cat, created = Category.objects.get_or_create(
                        user=user, name=cat_data['name'],
                        defaults={'category_type': cat_data.get('category_type', 'both')}
                    )
                    cat_map[cat_data['name']] = cat
                    if created:
                        restored_counts['categories'] += 1

                # 2. Accounts — get or create, track name→object map
                account_map = {}
                for acc in content.get('accounts', []):
                    acct, created = Account.objects.get_or_create(
                        user=user, name=acc['name'],
                        defaults={
                            'account_type': acc.get('account_type', 'cash'),
                            'opening_balance': acc.get('opening_balance', 0),
                            'color': acc.get('color', '#0d6efd'),
                            'notes': acc.get('notes', ''),
                        }
                    )
                    account_map[acc['name']] = acct
                    if created:
                        restored_counts['accounts'] += 1

                # 3. Incomes — with duplicate check by (user, source, amount, date)
                for inc in content.get('incomes', []):
                    category = cat_map.get(inc.get('category')) if inc.get('category') else None
                    obj, created = Income.objects.get_or_create(
                        user=user,
                        source=inc['source'],
                        amount=inc['amount'],
                        date=inc['date'],
                        defaults={
                            'payment_method': inc.get('payment_method', 'cash'),
                            'description': inc.get('description', ''),
                            'notes': inc.get('notes', ''),
                            'category': category,
                        }
                    )
                    if created:
                        restored_counts['incomes'] += 1
                    else:
                        restored_counts['duplicates_skipped'] += 1

                # 4. Expenses — with duplicate check by (user, description, amount, date)
                for exp in content.get('expenses', []):
                    category = cat_map.get(exp.get('category')) if exp.get('category') else None
                    obj, created = Expense.objects.get_or_create(
                        user=user,
                        description=exp['description'],
                        amount=exp['amount'],
                        date=exp['date'],
                        defaults={
                            'payment_method': exp.get('payment_method', 'cash'),
                            'notes': exp.get('notes', ''),
                            'category': category,
                        }
                    )
                    if created:
                        restored_counts['expenses'] += 1
                    else:
                        restored_counts['duplicates_skipped'] += 1

                # 5. Goals — with duplicate check by (user, name)
                for g in content.get('goals', []):
                    obj, created = FinancialGoal.objects.get_or_create(
                        user=user,
                        name=g['name'],
                        defaults={
                            'description': g.get('description', ''),
                            'target_amount': g['target_amount'],
                            'current_amount': g.get('current_amount', 0),
                            'target_date': g.get('target_date'),
                            'is_completed': g.get('is_completed', False),
                        }
                    )
                    if created:
                        restored_counts['goals'] += 1
                    else:
                        restored_counts['duplicates_skipped'] += 1

                # 6. Budgets — with category lookup
                for b in content.get('budgets', []):
                    category_name = b.get('category')
                    category = cat_map.get(category_name) if category_name else None
                    if category:
                        obj, created = Budget.objects.get_or_create(
                            user=user,
                            category=category,
                            period=b.get('period', 'monthly'),
                            defaults={'amount': b.get('amount', 0)},
                        )
                        if created:
                            restored_counts['budgets'] += 1

                # 7. Debts — with duplicate check by (user, name, start_date)
                for d in content.get('debts', []):
                    obj, created = Debt.objects.get_or_create(
                        user=user,
                        name=d['name'],
                        start_date=d['start_date'],
                        defaults={
                            'debt_type': d.get('debt_type', 'loan'),
                            'description': d.get('description', ''),
                            'principal_amount': d.get('principal_amount', 0),
                            'due_date': d.get('due_date'),
                            'status': d.get('status', 'active'),
                            'notes': d.get('notes', ''),
                        }
                    )
                    if created:
                        restored_counts['debts'] += 1
                    else:
                        restored_counts['duplicates_skipped'] += 1

            log_action(user, 'BACKUP_RESTORE', f'Restored full backup: {restored_counts}', request)
            msg = (
                f'Backup restored! Restored: '
                f'{restored_counts["incomes"]} Incomes, '
                f'{restored_counts["expenses"]} Expenses, '
                f'{restored_counts["goals"]} Goals, '
                f'{restored_counts["debts"]} Debts, '
                f'{restored_counts["budgets"]} Budgets, '
                f'{restored_counts["accounts"]} Accounts.'
            )
            if restored_counts['duplicates_skipped'] > 0:
                msg += f' ({restored_counts["duplicates_skipped"]} duplicate items skipped).'
            messages.success(request, msg)
            return redirect('dashboard')
        except Exception as err:
            messages.error(request, f'Error restoring backup data: {str(err)}')
            return render(request, self.template_name)



