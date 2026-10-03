from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from transactions.models import Category, Income, Expense
from analytics.services import FinancialAnalyticsService


class AnalyticsServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='analyticstest',
            email='analytics@example.com',
            password='testpassword123'
        )
        self.food_cat = Category.objects.create(user=self.user, name='Food', category_type='expense')
        self.transport_cat = Category.objects.create(user=self.user, name='Transport', category_type='expense')
        self.salary_cat = Category.objects.create(user=self.user, name='Salary', category_type='income')

        # Inflows
        Income.objects.create(
            user=self.user,
            amount=Decimal('1500000.00'),
            source='Tech Salary',
            category=self.salary_cat,
            date=date.today() - timedelta(days=10)
        )

        # Outflows
        Expense.objects.create(
            user=self.user,
            amount=Decimal('200000.00'),
            description='Monthly Groceries',
            category=self.food_cat,
            date=date.today() - timedelta(days=5),
            payment_method='mpesa'
        )
        Expense.objects.create(
            user=self.user,
            amount=Decimal('100000.00'),
            description='Fuel',
            category=self.transport_cat,
            date=date.today() - timedelta(days=2),
            payment_method='cash'
        )

    def test_analytics_summary(self):
        service = FinancialAnalyticsService(self.user)
        summary = service.get_summary()

        self.assertEqual(summary['total_income'], 1500000.0)
        self.assertEqual(summary['total_expenses'], 300000.0)
        self.assertEqual(summary['net_savings'], 1200000.0)
        self.assertEqual(summary['savings_rate'], 80.0)
        self.assertEqual(summary['top_category'], 'Food')
        self.assertEqual(summary['income_count'], 1)
        self.assertEqual(summary['expense_count'], 2)

    def test_category_breakdown(self):
        service = FinancialAnalyticsService(self.user)
        breakdown = service.get_expense_by_category()
        self.assertEqual(len(breakdown), 2)
        self.assertEqual(breakdown[0]['category'], 'Food')
        self.assertEqual(breakdown[0]['amount'], 200000.0)

    def test_insights_generation(self):
        service = FinancialAnalyticsService(self.user)
        insights = service.generate_insights()
        self.assertTrue(isinstance(insights, list))
        self.assertTrue(len(insights) > 0)

    def test_anomaly_detection_handles_datefield_values(self):
        service = FinancialAnalyticsService(self.user)
        for i in range(10):
            Expense.objects.create(
                user=self.user,
                amount=Decimal('50000.00') + Decimal(i * 1000),
                description=f'High Spend {i}',
                category=self.food_cat,
                date=date.today() - timedelta(days=i),
                payment_method='cash'
            )

        anomalies = service.detect_anomalies()
        self.assertIsInstance(anomalies, list)
