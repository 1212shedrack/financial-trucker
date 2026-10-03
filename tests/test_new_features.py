from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from accounts_wallet.models import Account, Transfer
from accounts_wallet.forms import TransferForm
from debts.models import Debt, DebtRepayment
from transactions.models import Income, Expense, Category
from analytics.services import FinancialAnalyticsService


class NewFeaturesTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')

        self.account_cash = Account.objects.create(
            user=self.user, name='Cash Wallet', account_type='cash', opening_balance=Decimal('50000')
        )
        self.account_bank = Account.objects.create(
            user=self.user, name='CRDB Bank', account_type='bank', opening_balance=Decimal('200000')
        )

    def test_account_balance_and_transfer(self):
        # 1. Transfer 20,000 from Bank to Cash
        transfer = Transfer.objects.create(
            user=self.user, from_account=self.account_bank, to_account=self.account_cash,
            amount=Decimal('20000'), date=date.today()
        )
        self.assertEqual(self.account_bank.current_balance, Decimal('180000'))
        self.assertEqual(self.account_cash.current_balance, Decimal('70000'))

    def test_transfer_rejects_insufficient_balance_and_inactive_accounts(self):
        inactive_account = Account.objects.create(
            user=self.user,
            name='Inactive Wallet',
            account_type='cash',
            opening_balance=Decimal('15000'),
            is_active=False,
        )

        form = TransferForm(
            user=self.user,
            data={
                'from_account': self.account_bank.pk,
                'to_account': self.account_cash.pk,
                'amount': Decimal('250000'),
                'date': date.today(),
                'notes': 'Too large',
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)

        form = TransferForm(
            user=self.user,
            data={
                'from_account': self.account_bank.pk,
                'to_account': inactive_account.pk,
                'amount': Decimal('20000'),
                'date': date.today(),
                'notes': 'Inactive destination',
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('to_account', form.errors)

    def test_account_deactivation_and_reactivation(self):
        self.account_cash.is_active = False
        self.account_cash.save(update_fields=['is_active'])

        response = self.client.get(reverse('account_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.account_cash, response.context['accounts'])
        self.assertIn(self.account_bank, response.context['accounts'])

        inactive_response = self.client.post(reverse('account_activate', args=[self.account_cash.pk]))
        self.assertEqual(inactive_response.status_code, 302)
        self.account_cash.refresh_from_db()
        self.assertTrue(self.account_cash.is_active)

    def test_debt_and_repayment(self):
        debt = Debt.objects.create(
            user=self.user, debt_type='loan', name='Friend Loan', principal_amount=Decimal('100000'),
            start_date=date.today(), due_date=date.today() + timedelta(days=30)
        )
        self.assertEqual(debt.remaining_balance, Decimal('100000'))

        # Pay 40,000
        repayment = DebtRepayment.objects.create(
            debt=debt, amount=Decimal('40000'), date=date.today()
        )
        self.assertEqual(debt.remaining_balance, Decimal('60000'))
        self.assertEqual(debt.total_paid, Decimal('40000'))

    def test_net_worth_calculation(self):
        service = FinancialAnalyticsService(self.user)
        net_worth_data = service.get_net_worth()
        # Assets: 50k + 200k = 250k. Liabilities: 0. Net Worth: 250k
        self.assertEqual(net_worth_data['total_assets'], 250000.0)
        self.assertEqual(net_worth_data['net_worth'], 250000.0)

    def test_financial_health_score(self):
        service = FinancialAnalyticsService(self.user)
        score_data = service.calculate_health_score()
        self.assertIn('total_score', score_data)
        self.assertIn('grade', score_data)
        self.assertGreaterEqual(score_data['total_score'], 0)

    def test_financial_calendar(self):
        service = FinancialAnalyticsService(self.user)
        events = service.get_financial_calendar(days_ahead=30)
        self.assertIsInstance(events, list)

    def test_backup_export_view(self):
        response = self.client.get(reverse('backup_export'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('version', response.json())

    def test_language_switch(self):
        response = self.client.get(reverse('switch_language') + '?lang=sw', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Miamala', response.content.decode('utf-8'))

