from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from transactions.models import Category, Income, Expense


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewuser',
            email='view@example.com',
            password='viewpassword123'
        )

    def test_landing_page(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)

    def test_templates_do_not_use_external_cdn_assets(self):
        response = self.client.get(reverse('landing'))
        content = response.content.decode()
        self.assertNotIn('cdn.jsdelivr.net', content)
        self.assertNotIn('fonts.googleapis.com', content)

    def test_service_worker_is_served_with_root_scope_permission(self):
        response = self.client.get(reverse('service_worker'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertEqual(response['Service-Worker-Allowed'], '/')

    def test_dashboard_redirect_unauthenticated(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_authenticated(self):
        self.client.login(username='viewuser', password='viewpassword123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_offline_queue_hook_is_only_on_create_forms(self):
        self.client.login(username='viewuser', password='viewpassword123')

        income_create = self.client.get(reverse('income_create'))
        expense_create = self.client.get(reverse('expense_create'))
        self.assertContains(income_create, 'data-offline-type="income"')
        self.assertContains(expense_create, 'data-offline-type="expense"')

        income = Income.objects.create(
            user=self.user,
            amount='1000',
            source='Existing',
            date=date.today(),
            payment_method='cash',
        )
        income_edit = self.client.get(
            reverse('income_edit', args=[income.pk])
        )
        self.assertNotContains(income_edit, 'data-offline-type=')

    def test_income_crud_views(self):
        self.client.login(username='viewuser', password='viewpassword123')
        # Create
        response = self.client.post(reverse('income_create'), {
            'amount': '300000',
            'source': 'Consulting Work',
            'date': date.today().isoformat(),
            'payment_method': 'mpesa'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Income.objects.filter(user=self.user).count(), 1)

        # List
        response = self.client.get(reverse('income_list'))
        self.assertEqual(response.status_code, 200)

    def test_expense_crud_views(self):
        self.client.login(username='viewuser', password='viewpassword123')
        # Create
        response = self.client.post(reverse('expense_create'), {
            'amount': '45000',
            'description': 'Lunch',
            'date': date.today().isoformat(),
            'payment_method': 'cash'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 1)

        # List
        response = self.client.get(reverse('expense_list'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_summary_respects_type_and_period_filters(self):
        self.client.login(username='viewuser', password='viewpassword123')
        today = date.today()
        previous_month = today.replace(day=1) - timedelta(days=1)

        Income.objects.create(
            user=self.user,
            amount='300000',
            source='Salary',
            date=today,
            payment_method='bank',
        )
        Expense.objects.create(
            user=self.user,
            amount='50000',
            description='Groceries',
            date=today,
            payment_method='cash',
        )
        Expense.objects.create(
            user=self.user,
            amount='200000',
            description='Old rent',
            date=previous_month,
            payment_method='bank',
        )

        response = self.client.get(reverse('dashboard'), {
            'type': 'expense',
            'period': 'month',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.context['summary']['total_expenses']), 50000.0)
        self.assertEqual(float(response.context['summary']['total_income']), 0.0)
        self.assertEqual(float(response.context['summary']['average_expense']), 50000.0)

    def test_dashboard_uses_safe_json_chart_payload(self):
        self.client.login(username='viewuser', password='viewpassword123')
        response = self.client.get(reverse('dashboard'), {'type': 'all', 'period': 'month'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'monthly-trends-data')
        self.assertContains(response, 'category-breakdown-data')

    def test_filters_are_automatic_and_pagination_preserves_query(self):
        self.client.login(username='viewuser', password='viewpassword123')
        for index in range(21):
            Income.objects.create(
                user=self.user,
                amount=Decimal('1000'),
                source=f'Income {index}',
                date=date.today(),
                payment_method='cash',
            )

        response = self.client.get(reverse('income_list'), {'q': 'Income', 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auto-filter-form')
        self.assertNotContains(response, 'Apply Filter')
        self.assertContains(response, 'page=1')
        self.assertContains(response, 'q=Income')
