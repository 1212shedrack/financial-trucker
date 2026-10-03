from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from transactions.models import Category, Income, Expense, RecurringTransaction
from budgets.models import Budget
from goals.models import FinancialGoal, GoalContribution


class UserIsolationAndSecurityTestCase(TestCase):
    """
    Strict security and multi-tenant isolation tests.
    Verifies that User A's data can NEVER be viewed, modified, or deleted by User B.
    """
    def setUp(self):
        # Create User A
        self.user_a = User.objects.create_user(
            username='user_a',
            email='user_a@example.com',
            password='Password123!'
        )
        # Create User B
        self.user_b = User.objects.create_user(
            username='user_b',
            email='user_b@example.com',
            password='Password123!'
        )

        # Clients
        self.client_a = Client()
        self.client_a.login(username='user_a', password='Password123!')

        self.client_b = Client()
        self.client_b.login(username='user_b', password='Password123!')

        self.api_client_b = APIClient()
        self.api_client_b.force_authenticate(user=self.user_b)

        # User A's data
        self.cat_a = Category.objects.create(user=self.user_a, name='Secret A', category_type='expense')
        self.income_a = Income.objects.create(
            user=self.user_a, amount=Decimal('5000000'), source='Private Contract', date=date.today()
        )
        self.expense_a = Expense.objects.create(
            user=self.user_a, amount=Decimal('2000000'), description='Private Purchase', date=date.today(), category=self.cat_a
        )
        self.budget_a = Budget.objects.create(
            user=self.user_a, category=self.cat_a, amount=Decimal('3000000'), period='monthly', start_date=date.today()
        )
        self.goal_a = FinancialGoal.objects.create(
            user=self.user_a, name='Secret Vault', target_amount=Decimal('10000000'), current_amount=Decimal('1000000')
        )
        self.recurring_a = RecurringTransaction.objects.create(
            user=self.user_a, title='Secret Retainer', amount=Decimal('1000000'), transaction_type='income',
            frequency='monthly', start_date=date.today(), next_due_date=date.today()
        )

    def test_user_b_cannot_view_user_a_income_detail(self):
        response = self.client_b.get(reverse('income_detail', kwargs={'pk': self.income_a.pk}))
        self.assertEqual(response.status_code, 404)

    def test_user_b_cannot_edit_user_a_income(self):
        response = self.client_b.post(reverse('income_edit', kwargs={'pk': self.income_a.pk}), {
            'amount': '100',
            'source': 'Hacked',
            'date': str(date.today()),
            'payment_method': 'cash'
        })
        self.assertEqual(response.status_code, 404)
        self.income_a.refresh_from_db()
        self.assertEqual(self.income_a.source, 'Private Contract')

    def test_user_b_cannot_delete_user_a_income(self):
        response = self.client_b.post(reverse('income_delete', kwargs={'pk': self.income_a.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Income.objects.filter(pk=self.income_a.pk).exists())

    def test_user_b_cannot_view_user_a_expense_detail(self):
        response = self.client_b.get(reverse('expense_detail', kwargs={'pk': self.expense_a.pk}))
        self.assertEqual(response.status_code, 404)

    def test_user_b_cannot_edit_user_a_expense(self):
        response = self.client_b.post(reverse('expense_edit', kwargs={'pk': self.expense_a.pk}), {
            'amount': '100',
            'description': 'Hacked',
            'date': str(date.today()),
            'payment_method': 'cash'
        })
        self.assertEqual(response.status_code, 404)
        self.expense_a.refresh_from_db()
        self.assertEqual(self.expense_a.description, 'Private Purchase')

    def test_user_b_cannot_delete_user_a_expense(self):
        response = self.client_b.post(reverse('expense_delete', kwargs={'pk': self.expense_a.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Expense.objects.filter(pk=self.expense_a.pk).exists())

    def test_user_b_cannot_view_user_a_budget_detail(self):
        response = self.client_b.get(reverse('budget_detail', kwargs={'pk': self.budget_a.pk}))
        self.assertEqual(response.status_code, 404)

    def test_user_b_cannot_view_or_contribute_to_user_a_goal(self):
        # Web detail
        response = self.client_b.get(reverse('goal_detail', kwargs={'pk': self.goal_a.pk}))
        self.assertEqual(response.status_code, 404)
        # Web contribute
        response = self.client_b.post(reverse('goal_contribute', kwargs={'pk': self.goal_a.pk}), {
            'amount': '500000',
            'date': str(date.today())
        })
        self.assertEqual(response.status_code, 404)
        # API contribute
        res = self.api_client_b.post(f'/api/goals/{self.goal_a.pk}/contribute/', {'amount': '500000'})
        self.assertEqual(res.status_code, 404)

    def test_user_b_api_income_list_isolated(self):
        res = self.api_client_b.get('/api/income/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 0)

    def test_user_b_api_cannot_delete_user_a_income(self):
        res = self.api_client_b.delete(f'/api/income/{self.income_a.pk}/')
        self.assertEqual(res.status_code, 404)

    def test_user_cannot_delete_default_category_via_api(self):
        default_cat = Category.objects.create(name='Global Default', is_default=True, user=None)
        res = self.api_client_b.delete(f'/api/categories/{default_cat.pk}/')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Category.objects.filter(pk=default_cat.pk).exists())
