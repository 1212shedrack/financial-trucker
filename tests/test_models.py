from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from core.models import AuditLog
from accounts.models import UserProfile
from transactions.models import Category, Income, Expense, RecurringTransaction
from budgets.models import Budget
from goals.models import FinancialGoal, GoalContribution
from notifications.models import Notification


class ModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )

    def test_user_profile_creation(self):
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.preferred_currency, 'TZS')
        self.assertEqual(self.user.profile.currency_symbol, 'TSh')

    def test_category_and_transactions(self):
        category = Category.objects.create(
            user=self.user,
            name='Food',
            category_type='expense',
            icon='bi-egg-fried',
            color='#fd7e14'
        )
        income = Income.objects.create(
            user=self.user,
            amount=Decimal('500000.00'),
            source='Freelance Job',
            date=date.today(),
            payment_method='mpesa'
        )
        expense = Expense.objects.create(
            user=self.user,
            amount=Decimal('50000.00'),
            description='Lunch & Coffee',
            category=category,
            date=date.today(),
            payment_method='cash'
        )
        self.assertEqual(income.amount, Decimal('500000.00'))
        self.assertEqual(expense.amount, Decimal('50000.00'))
        self.assertEqual(expense.category.name, 'Food')

    def test_budget_properties(self):
        category = Category.objects.create(
            user=self.user,
            name='Transport',
            category_type='expense'
        )
        budget = Budget.objects.create(
            user=self.user,
            category=category,
            amount=Decimal('100000.00'),
            period='monthly',
            start_date=date.today().replace(day=1)
        )
        Expense.objects.create(
            user=self.user,
            category=category,
            amount=Decimal('85000.00'),
            description='Fuel & Daladala',
            date=date.today()
        )
        self.assertEqual(budget.spent_amount, Decimal('85000.00'))
        self.assertEqual(budget.remaining_amount, Decimal('15000.00'))
        self.assertEqual(budget.percentage_used, 85)
        self.assertTrue(budget.is_warning)
        self.assertFalse(budget.is_exceeded)

    def test_goal_properties(self):
        goal = FinancialGoal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('1000000.00'),
            current_amount=Decimal('250000.00'),
            target_date=date.today() + timedelta(days=90)
        )
        GoalContribution.objects.create(
            goal=goal,
            amount=Decimal('250000.00'),
            date=date.today()
        )
        goal.current_amount += Decimal('250000.00')
        goal.save()

        self.assertEqual(goal.percentage_completed, 50)
        self.assertEqual(goal.remaining_amount, Decimal('500000.00'))
        self.assertFalse(goal.is_completed)

    def test_notification_creation(self):
        notif = Notification.objects.create(
            user=self.user,
            notification_type='budget_warning',
            title='Budget Alert',
            message='You have used 85% of Transport budget.'
        )
        self.assertEqual(notif.badge_class, 'warning')
        self.assertFalse(notif.is_read)
