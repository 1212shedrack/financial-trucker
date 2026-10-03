"""
Management command to seed the database with default categories and optional demo data.
Usage:
  python manage.py seed_data          # Default categories only
  python manage.py seed_data --demo   # + demo user with realistic TZS transactions
  python manage.py seed_data --clear  # Clear all demo data first
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction


DEFAULT_INCOME_CATEGORIES = [
    {'name': 'Salary', 'icon': 'bi-briefcase', 'color': '#198754'},
    {'name': 'Business', 'icon': 'bi-shop', 'color': '#0d6efd'},
    {'name': 'Freelance', 'icon': 'bi-laptop', 'color': '#6610f2'},
    {'name': 'Gift', 'icon': 'bi-gift', 'color': '#e83e8c'},
    {'name': 'Investment', 'icon': 'bi-graph-up-arrow', 'color': '#20c997'},
    {'name': 'Other', 'icon': 'bi-plus-circle', 'color': '#6c757d'},
]

DEFAULT_EXPENSE_CATEGORIES = [
    {'name': 'Food & Dining', 'icon': 'bi-egg-fried', 'color': '#fd7e14'},
    {'name': 'Transport', 'icon': 'bi-bus-front', 'color': '#0dcaf0'},
    {'name': 'Rent', 'icon': 'bi-house', 'color': '#dc3545'},
    {'name': 'Bills & Utilities', 'icon': 'bi-lightning-charge', 'color': '#ffc107'},
    {'name': 'Education', 'icon': 'bi-book', 'color': '#6610f2'},
    {'name': 'Health', 'icon': 'bi-heart-pulse', 'color': '#d63384'},
    {'name': 'Shopping', 'icon': 'bi-bag', 'color': '#0d6efd'},
    {'name': 'Entertainment', 'icon': 'bi-music-note-beamed', 'color': '#6f42c1'},
    {'name': 'Business', 'icon': 'bi-briefcase', 'color': '#198754'},
    {'name': 'Other', 'icon': 'bi-three-dots', 'color': '#6c757d'},
]


class Command(BaseCommand):
    help = 'Seed default categories and optional demo data (TZS)'

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Create demo user with sample transactions')
        parser.add_argument('--clear', action='store_true', help='Clear existing demo data first')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self._clear_demo_data()

        self._create_default_categories()

        if options['demo']:
            self._create_demo_data()

        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))

    def _clear_demo_data(self):
        demo_user = User.objects.filter(email='demo@pfams.com').first()
        if demo_user:
            demo_user.delete()
            self.stdout.write('Cleared demo user data.')

    def _create_default_categories(self):
        from transactions.models import Category
        count = 0
        for cat_data in DEFAULT_INCOME_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                user=None, name=cat_data['name'], category_type='income',
                defaults={'icon': cat_data['icon'], 'color': cat_data['color'], 'is_default': True}
            )
            if created:
                count += 1

        for cat_data in DEFAULT_EXPENSE_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                user=None, name=cat_data['name'], category_type='expense',
                defaults={'icon': cat_data['icon'], 'color': cat_data['color'], 'is_default': True}
            )
            if created:
                count += 1

        self.stdout.write(f'Created {count} default categories.')

    def _create_demo_data(self):
        from transactions.models import Category, Income, Expense, RecurringTransaction
        from budgets.models import Budget
        from goals.models import FinancialGoal, GoalContribution

        # Create demo user
        if User.objects.filter(email='demo@pfams.com').exists():
            self.stdout.write('Demo user already exists. Skipping.')
            return

        demo_user = User.objects.create_user(
            username='demo',
            email='demo@pfams.com',
            password='Demo1234!',
            first_name='Demo',
            last_name='User',
        )
        demo_user.profile.full_name = 'Demo User'
        demo_user.profile.monthly_income_target = Decimal('1500000')
        demo_user.profile.monthly_savings_target = Decimal('300000')
        demo_user.profile.save()

        # Get categories
        salary_cat = Category.objects.filter(name='Salary', category_type='income').first()
        freelance_cat = Category.objects.filter(name='Freelance', category_type='income').first()
        food_cat = Category.objects.filter(name='Food & Dining', category_type='expense').first()
        transport_cat = Category.objects.filter(name='Transport', category_type='expense').first()
        rent_cat = Category.objects.filter(name='Rent', category_type='expense').first()
        bills_cat = Category.objects.filter(name='Bills & Utilities', category_type='expense').first()
        entertainment_cat = Category.objects.filter(name='Entertainment', category_type='expense').first()
        health_cat = Category.objects.filter(name='Health', category_type='expense').first()

        today = date.today()
        income_records = 0
        expense_records = 0

        # Generate 6 months of realistic TZS data
        for months_ago in range(6, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=months_ago * 30))
            month_start = month_start.replace(day=1)

            # Monthly salary
            Income.objects.create(
                user=demo_user, amount=Decimal('1500000'),
                source='Monthly Salary', category=salary_cat,
                date=month_start + timedelta(days=random.randint(0, 4)),
                payment_method='bank', description='Salary from employer'
            )
            income_records += 1

            # Occasional freelance
            if random.random() > 0.4:
                Income.objects.create(
                    user=demo_user, amount=Decimal(str(random.randint(150, 500) * 1000)),
                    source='Freelance Project', category=freelance_cat,
                    date=month_start + timedelta(days=random.randint(10, 25)),
                    payment_method='mpesa', description='Freelance web development'
                )
                income_records += 1

            # Monthly rent (1st of month)
            Expense.objects.create(
                user=demo_user, amount=Decimal('400000'),
                description='Monthly Rent', category=rent_cat,
                date=month_start + timedelta(days=1),
                payment_method='bank', notes='House rent'
            )
            expense_records += 1

            # Food — weekly groceries
            for week in range(4):
                Expense.objects.create(
                    user=demo_user, amount=Decimal(str(random.randint(35, 80) * 1000)),
                    description='Grocery Shopping', category=food_cat,
                    date=month_start + timedelta(days=week * 7 + random.randint(0, 5)),
                    payment_method=random.choice(['cash', 'mpesa']),
                )
                expense_records += 1

            # Transport
            for _ in range(random.randint(8, 15)):
                Expense.objects.create(
                    user=demo_user, amount=Decimal(str(random.randint(2, 15) * 1000)),
                    description='Transport/Daladala', category=transport_cat,
                    date=month_start + timedelta(days=random.randint(0, 27)),
                    payment_method=random.choice(['cash', 'tigo']),
                )
                expense_records += 1

            # Bills
            Expense.objects.create(
                user=demo_user, amount=Decimal(str(random.randint(30, 60) * 1000)),
                description='Electricity Bill', category=bills_cat,
                date=month_start + timedelta(days=random.randint(10, 20)),
                payment_method='mpesa',
            )
            Expense.objects.create(
                user=demo_user, amount=Decimal('50000'),
                description='Internet (TTCL)', category=bills_cat,
                date=month_start + timedelta(days=random.randint(1, 5)),
                payment_method='mpesa',
            )
            expense_records += 2

            # Entertainment — occasional
            if random.random() > 0.5:
                Expense.objects.create(
                    user=demo_user, amount=Decimal(str(random.randint(20, 80) * 1000)),
                    description='Entertainment', category=entertainment_cat,
                    date=month_start + timedelta(days=random.randint(12, 28)),
                    payment_method='cash',
                )
                expense_records += 1

        # Recurring transactions
        RecurringTransaction.objects.create(
            user=demo_user, title='Monthly Salary', amount=Decimal('1500000'),
            transaction_type='income', category=salary_cat,
            frequency='monthly', start_date=today.replace(day=1),
            next_due_date=today.replace(day=1) + timedelta(days=30),
            payment_method='bank', notes='Regular monthly salary'
        )
        RecurringTransaction.objects.create(
            user=demo_user, title='House Rent', amount=Decimal('400000'),
            transaction_type='expense', category=rent_cat,
            frequency='monthly', start_date=today.replace(day=1),
            next_due_date=today.replace(day=1) + timedelta(days=30),
            payment_method='bank',
        )
        RecurringTransaction.objects.create(
            user=demo_user, title='Internet (TTCL)', amount=Decimal('50000'),
            transaction_type='expense', category=bills_cat,
            frequency='monthly', start_date=today.replace(day=1),
            next_due_date=today.replace(day=1) + timedelta(days=15),
            payment_method='mpesa',
        )

        # Budgets
        Budget.objects.create(
            user=demo_user, category=food_cat, amount=Decimal('300000'),
            period='monthly', start_date=today.replace(day=1),
            notes='Monthly food budget'
        )
        Budget.objects.create(
            user=demo_user, category=transport_cat, amount=Decimal('100000'),
            period='monthly', start_date=today.replace(day=1),
        )
        Budget.objects.create(
            user=demo_user, category=entertainment_cat, amount=Decimal('80000'),
            period='monthly', start_date=today.replace(day=1),
        )

        # Financial goals
        emergency_goal = FinancialGoal.objects.create(
            user=demo_user, name='Emergency Fund',
            description='6 months of living expenses saved',
            target_amount=Decimal('5000000'),
            current_amount=Decimal('1200000'),
            target_date=today + timedelta(days=365),
            category='Savings',
        )
        GoalContribution.objects.create(
            goal=emergency_goal, amount=Decimal('200000'), date=today - timedelta(days=30)
        )
        GoalContribution.objects.create(
            goal=emergency_goal, amount=Decimal('200000'), date=today - timedelta(days=60)
        )

        FinancialGoal.objects.create(
            user=demo_user, name='Buy Laptop',
            description='New laptop for work',
            target_amount=Decimal('2500000'),
            current_amount=Decimal('800000'),
            target_date=today + timedelta(days=180),
            category='Technology',
        )

        FinancialGoal.objects.create(
            user=demo_user, name='Vacation Fund',
            description='Holiday trip to Zanzibar',
            target_amount=Decimal('1500000'),
            current_amount=Decimal('0'),
            target_date=today + timedelta(days=270),
            category='Travel',
        )

        # Accounts & Wallets
        from accounts_wallet.models import Account, Transfer
        cash_wallet = Account.objects.create(
            user=demo_user, name='Cash Wallet', account_type='cash',
            opening_balance=Decimal('150000'), color='#198754'
        )
        crdb_bank = Account.objects.create(
            user=demo_user, name='CRDB Bank Account', account_type='bank',
            account_number='4892', opening_balance=Decimal('2500000'), color='#0d6efd'
        )
        mpesa_wallet = Account.objects.create(
            user=demo_user, name='M-Pesa Wallet', account_type='mpesa',
            account_number='0755xxx123', opening_balance=Decimal('350000'), color='#dc3545'
        )

        # Sample Transfer
        Transfer.objects.create(
            user=demo_user, from_account=crdb_bank, to_account=mpesa_wallet,
            amount=Decimal('100000'), date=today - timedelta(days=5),
            notes='Mobile wallet top-up'
        )

        # Sample Debts & Loans
        from debts.models import Debt, DebtRepayment
        bank_loan = Debt.objects.create(
            user=demo_user, debt_type='loan', name='Azania Bank Personal Loan',
            description='Home renovation loan', principal_amount=Decimal('1200000'),
            interest_rate=Decimal('10.0'), start_date=today - timedelta(days=60),
            due_date=today + timedelta(days=120), status='partial'
        )
        DebtRepayment.objects.create(
            debt=bank_loan, amount=Decimal('300000'), date=today - timedelta(days=30),
            payment_method='bank', notes='Monthly installment'
        )

        receivable = Debt.objects.create(
            user=demo_user, debt_type='receivable', name='John (Colleague)',
            description='Short term loan given to John', principal_amount=Decimal('250000'),
            start_date=today - timedelta(days=15), due_date=today + timedelta(days=15), status='active'
        )

        self.stdout.write(
            f'Created demo user: demo@pfams.com / Demo1234!\n'
            f'Income records: {income_records}\n'
            f'Expense records: {expense_records}\n'
            f'Accounts created: Cash, CRDB Bank, M-Pesa\n'
            f'Debts created: Bank Loan & Receivable'
        )

